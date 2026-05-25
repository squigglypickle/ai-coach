"""
Integration tests — hit Ollama for real, Telegram stays blocked, db uses a temp file.

Run with:
    pytest -m integration -s                          # today, now
    pytest -m integration -s --day Monday             # Monday, now
    pytest -m integration -s --day Monday --time 09:00
    pytest -m integration -s --day Sunday --time 18:00
"""
import os
import pytest
from unittest.mock import patch
from datetime import datetime, timedelta
from remind import get_zephyr_message, get_nudge_message, generate_daily_plan, SCHEDULE

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def _make_fake_now(request):
    day_name = request.config.getoption("--day")
    time_str = request.config.getoption("--time")
    now = datetime.now()

    if day_name or time_str:
        target_day = DAYS.index(day_name) if day_name else now.weekday()
        days_ahead = (target_day - now.weekday()) % 7
        base = (now + timedelta(days=days_ahead)).replace(hour=0, minute=0, second=0, microsecond=0)
        if time_str:
            h, m = map(int, time_str.split(":"))
            base = base.replace(hour=h, minute=m)
        else:
            base = base.replace(hour=now.hour, minute=now.minute)
        return base

    return now


@pytest.fixture(autouse=True)
def temp_db(tmp_path):
    """Point db at a fresh temp file for each integration test."""
    import db as db_module
    test_db = str(tmp_path / "test_coach.db")
    original = db_module.DB_PATH
    db_module.DB_PATH = test_db
    db_module.init_db()
    yield test_db
    db_module.DB_PATH = original


@pytest.mark.integration
def test_zephyr_workout_response(request):
    fake_now = _make_fake_now(request)
    day = fake_now.strftime("%A")
    time_str = fake_now.strftime("%H:%M")

    print(f"\n--- Day: {day}  Time: {time_str} ---")

    with patch("remind.datetime") as mock_dt:
        mock_dt.now.return_value = fake_now
        message = get_zephyr_message()

    print(f"--- Zephyr says ---\n{message}\n")
    assert len(message) > 0

    import db
    saved = db.get_recent_workouts(limit=10) + _get_all_nudges()
    print(f"--- Saved to db: {len(saved)} session(s) ---")


def _get_all_nudges():
    import db
    import sqlite3
    with sqlite3.connect(db.DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        return [dict(r) for r in conn.execute("SELECT * FROM sessions WHERE session_type='nudge'").fetchall()]


@pytest.mark.integration
def test_plan_then_zephyr(request):
    """Full two-step flow: generate plan, then get Zephyr to deliver it."""
    fake_now = _make_fake_now(request)
    day = fake_now.strftime("%A")
    workout_type, exercises = SCHEDULE.get(day, ("Unknown", None))

    print(f"\n--- Day: {day}  ({workout_type}) ---")

    with patch("remind.datetime") as mock_dt:
        mock_dt.now.return_value = fake_now
        plan = generate_daily_plan()

    if plan:
        print(f"--- Plan (stored) ---\n{plan}\n")
    else:
        print(f"--- No plan generated (not a functional fitness day) ---\n")

    with patch("remind.datetime") as mock_dt:
        mock_dt.now.return_value = fake_now
        message = get_zephyr_message()

    print(f"--- Zephyr says ---\n{message}\n")
    assert len(message) > 0


@pytest.mark.integration
def test_nudge_response(request):
    fake_now = _make_fake_now(request)
    time_str = fake_now.strftime("%H:%M")

    print(f"\n--- Time: {time_str} ---")

    with patch("remind.datetime") as mock_dt:
        mock_dt.now.return_value = fake_now
        message = get_nudge_message()

    print(f"--- Nudge says ---\n{message}\n")
    assert len(message) > 0
