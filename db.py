import os
import sqlite3

DB_PATH = os.getenv("DB_PATH", os.path.join(os.path.dirname(__file__), "coach.db"))

CREATE_SESSIONS = """
    CREATE TABLE IF NOT EXISTS sessions (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
        day_of_week     TEXT NOT NULL,
        session_type    TEXT NOT NULL,
        workout_type    TEXT,
        exercises_focus TEXT,
        prompt          TEXT NOT NULL,
        response        TEXT NOT NULL
    )
"""

CREATE_DAILY_PLANS = """
    CREATE TABLE IF NOT EXISTS daily_plans (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        date            TEXT NOT NULL UNIQUE,
        day_of_week     TEXT NOT NULL,
        workout_type    TEXT NOT NULL,
        exercises_focus TEXT,
        plan            TEXT NOT NULL,
        status          TEXT DEFAULT 'pending',
        difficulty      TEXT,
        created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
    )
"""


def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with _connect() as conn:
        conn.execute(CREATE_SESSIONS)
        conn.execute(CREATE_DAILY_PLANS)
        for col, defn in [("status", "TEXT DEFAULT 'pending'"), ("difficulty", "TEXT")]:
            try:
                conn.execute(f"ALTER TABLE daily_plans ADD COLUMN {col} {defn}")
            except Exception:
                pass  # column already exists


def save_session(*, day_of_week, session_type, workout_type=None, exercises_focus=None, prompt, response):
    with _connect() as conn:
        conn.execute(
            """INSERT INTO sessions
               (day_of_week, session_type, workout_type, exercises_focus, prompt, response)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (day_of_week, session_type, workout_type, exercises_focus, prompt, response),
        )


def save_daily_plan(*, date, day_of_week, workout_type, exercises_focus, plan):
    with _connect() as conn:
        conn.execute(
            """INSERT INTO daily_plans (date, day_of_week, workout_type, exercises_focus, plan)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(date) DO UPDATE SET
                   plan=excluded.plan,
                   created_at=CURRENT_TIMESTAMP""",
            (date, day_of_week, workout_type, exercises_focus, plan),
        )


def update_plan_feedback(*, date: str, status: str, difficulty: str = None):
    with _connect() as conn:
        conn.execute(
            "UPDATE daily_plans SET status=?, difficulty=? WHERE date=?",
            (status, difficulty, date),
        )


def get_today_plan(date: str):
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM daily_plans WHERE date = ?", (date,)
        ).fetchone()
    return dict(row) if row else None


def get_recent_workouts(limit=3):
    """Return the most recent completed (or pending) functional fitness plans, newest first.
    Skipped sessions are excluded so they don't influence future workout design."""
    with _connect() as conn:
        rows = conn.execute(
            """SELECT day_of_week, exercises_focus, created_at
               FROM daily_plans
               WHERE workout_type = 'Functional Fitness'
               AND (status IS NULL OR status != 'skipped')
               ORDER BY created_at DESC
               LIMIT ?""",
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]
