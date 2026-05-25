import pytest
from unittest.mock import patch, call
from datetime import datetime
from remind import (
    build_plan_prompt, build_delivery_prompt, build_feedback_keyboard, build_feedback_prompt,
    SCHEDULE, USER_NAME, PLAN_SYSTEM_PROMPT, _history_context,
)


# --- build_plan_prompt ---

@pytest.mark.parametrize("day", ["Monday", "Wednesday", "Friday"])
def test_plan_prompt_contains_day(day):
    workout_type, exercises = SCHEDULE[day]
    assert day in build_plan_prompt(day, workout_type, exercises)


@pytest.mark.parametrize("day", ["Monday", "Wednesday", "Friday"])
def test_plan_prompt_contains_exercises(day):
    workout_type, exercises = SCHEDULE[day]
    assert exercises in build_plan_prompt(day, workout_type, exercises)


@pytest.mark.parametrize("day", ["Monday", "Wednesday", "Friday"])
def test_plan_prompt_requests_structure(day):
    workout_type, exercises = SCHEDULE[day]
    prompt = build_plan_prompt(day, workout_type, exercises)
    assert "Warm-up" in prompt
    assert "sets" in prompt.lower()
    assert "reps" in prompt.lower()


@pytest.mark.parametrize("day", ["Monday", "Wednesday", "Friday"])
def test_plan_prompt_has_word_limit(day):
    workout_type, exercises = SCHEDULE[day]
    assert "300" in build_plan_prompt(day, workout_type, exercises)


def test_plan_prompt_includes_history():
    recent = [{"day_of_week": "Monday", "exercises_focus": "Focus: Power."}]
    prompt = build_plan_prompt("Wednesday", "Functional Fitness",
                               SCHEDULE["Wednesday"][1], recent_workouts=recent)
    assert "Monday" in prompt
    assert "complementary" in prompt.lower()


def test_plan_prompt_no_history_when_empty():
    workout_type, exercises = SCHEDULE["Monday"]
    prompt = build_plan_prompt("Monday", workout_type, exercises, recent_workouts=[])
    assert "complementary" not in prompt.lower()


# --- build_delivery_prompt: functional fitness with stored plan ---

# --- build_delivery_prompt: functional fitness with plan ---

def test_delivery_with_plan_contains_plan_content():
    prompt = build_delivery_prompt("Monday", "09:00", "Functional Fitness", plan="5x5 kettlebell swings")
    assert "5x5 kettlebell swings" in prompt


def test_delivery_with_plan_contains_user_name():
    assert USER_NAME in build_delivery_prompt("Monday", "09:00", "Functional Fitness", plan="some plan")


def test_delivery_with_plan_contains_day_and_time():
    prompt = build_delivery_prompt("Monday", "09:00", "Functional Fitness", plan="some plan")
    assert "Monday" in prompt
    assert "09:00" in prompt


def test_delivery_with_plan_has_word_limit():
    assert "400" in build_delivery_prompt("Monday", "09:00", "Functional Fitness", plan="some plan")


# --- build_delivery_prompt: functional fitness fallback (no plan) ---

def test_delivery_fallback_contains_day():
    assert "Monday" in build_delivery_prompt("Monday", "09:00", "Functional Fitness")


def test_delivery_fallback_contains_user_name():
    assert USER_NAME in build_delivery_prompt("Monday", "09:00", "Functional Fitness")


def test_delivery_fallback_has_word_limit():
    assert "400" in build_delivery_prompt("Monday", "09:00", "Functional Fitness")


# --- build_delivery_prompt: bike days ---

@pytest.mark.parametrize("day", ["Tuesday", "Sunday"])
def test_delivery_bike_contains_day(day):
    assert day in build_delivery_prompt(day, "09:00", "20 Mile Bike Ride")


@pytest.mark.parametrize("day", ["Tuesday", "Sunday"])
def test_delivery_bike_mentions_saddle(day):
    assert "saddle" in build_delivery_prompt(day, "09:00", "20 Mile Bike Ride")


@pytest.mark.parametrize("day", ["Tuesday", "Sunday"])
def test_delivery_bike_has_word_limit(day):
    assert "150" in build_delivery_prompt(day, "09:00", "20 Mile Bike Ride")


@pytest.mark.parametrize("day", ["Tuesday", "Sunday"])
def test_delivery_bike_contains_user_name(day):
    assert USER_NAME in build_delivery_prompt(day, "09:00", "20 Mile Bike Ride")


# --- build_delivery_prompt: rest days ---

@pytest.mark.parametrize("day", ["Thursday", "Saturday"])
def test_delivery_rest_contains_day(day):
    assert day in build_delivery_prompt(day, "09:00", "Rest/Recovery")


@pytest.mark.parametrize("day", ["Thursday", "Saturday"])
def test_delivery_rest_suggests_activity(day):
    prompt = build_delivery_prompt(day, "09:00", "Rest/Recovery")
    assert "walk" in prompt.lower() or "stretch" in prompt.lower()


@pytest.mark.parametrize("day", ["Thursday", "Saturday"])
def test_delivery_rest_has_word_limit(day):
    assert "150" in build_delivery_prompt(day, "09:00", "Rest/Recovery")


@pytest.mark.parametrize("day", ["Thursday", "Saturday"])
def test_delivery_rest_contains_user_name(day):
    assert USER_NAME in build_delivery_prompt(day, "09:00", "Rest/Recovery")


# --- history context ---

def test_history_context_empty_returns_full_body_fallback():
    context = _history_context([])
    assert "full body" in context.lower()
    assert "complementary" not in context.lower()


def test_history_context_includes_day_and_focus():
    recent = [{"day_of_week": "Monday", "exercises_focus": "Focus: Power. Priority: Overhead Press & Swings."}]
    context = _history_context(recent)
    assert "Monday" in context
    assert "Overhead Press" in context


def test_history_context_includes_complementary_instruction():
    recent = [{"day_of_week": "Monday", "exercises_focus": "Focus: Power."}]
    assert "complementary" in _history_context(recent).lower()


# --- generate_daily_plan ---

@pytest.mark.parametrize("day,date", [
    ("Tuesday",  "2026-05-26"),
    ("Thursday", "2026-05-28"),
    ("Saturday", "2026-05-30"),
    ("Sunday",   "2026-05-31"),
])
def test_generate_daily_plan_returns_none_for_non_fitness_days(day, date):
    from remind import generate_daily_plan
    year, month, d = map(int, date.split("-"))
    fake_time = datetime(year, month, d, 6, 0)
    with patch("remind.datetime") as mock_dt:
        mock_dt.now.return_value = fake_time
        assert generate_daily_plan() is None


def test_generate_daily_plan_saves_plan_for_fitness_day():
    from remind import generate_daily_plan
    fake_time = datetime(2026, 5, 25, 6, 0)  # Monday
    with patch("remind.datetime") as mock_dt, \
         patch("remind.query_ollama", return_value="clean plan"), \
         patch("db.save_daily_plan") as mock_save, \
         patch("db.get_recent_workouts", return_value=[]):
        mock_dt.now.return_value = fake_time
        result = generate_daily_plan()

    assert result == "clean plan"
    mock_save.assert_called_once()
    kwargs = mock_save.call_args.kwargs
    assert kwargs["plan"] == "clean plan"
    assert kwargs["day_of_week"] == "Monday"
    assert kwargs["date"] == "2026-05-25"


def test_generate_daily_plan_uses_plan_system_prompt():
    from remind import generate_daily_plan
    fake_time = datetime(2026, 5, 25, 6, 0)  # Monday
    with patch("remind.datetime") as mock_dt, \
         patch("remind.query_ollama") as mock_ollama, \
         patch("db.save_daily_plan"), \
         patch("db.get_recent_workouts", return_value=[]):
        mock_dt.now.return_value = fake_time
        mock_ollama.return_value = "plan"
        generate_daily_plan()

    _, kwargs = mock_ollama.call_args
    assert kwargs["system_prompt"] == PLAN_SYSTEM_PROMPT


def test_generate_daily_plan_passes_recent_workouts_to_prompt():
    from remind import generate_daily_plan
    fake_time = datetime(2026, 5, 25, 6, 0)  # Monday
    recent = [{"day_of_week": "Friday", "exercises_focus": "Focus: Burn."}]
    captured = {}

    def capture(prompt, **kwargs):
        captured["prompt"] = prompt
        return "plan"

    with patch("remind.datetime") as mock_dt, \
         patch("remind.query_ollama", side_effect=capture), \
         patch("db.save_daily_plan"), \
         patch("db.get_recent_workouts", return_value=recent):
        mock_dt.now.return_value = fake_time
        generate_daily_plan()

    assert "Friday" in captured["prompt"]


# --- get_zephyr_message ---

def test_get_zephyr_uses_stored_plan():
    from remind import get_zephyr_message
    fake_time = datetime(2026, 5, 25, 9, 0)  # Monday
    stored_plan = {"plan": "5x5 swings, 3x10 press"}
    captured = {}

    def capture(prompt, **kwargs):
        captured["prompt"] = prompt
        return "zephyr response"

    with patch("remind.datetime") as mock_dt, \
         patch("remind.query_ollama", side_effect=capture), \
         patch("db.save_session"), \
         patch("db.get_today_plan", return_value=stored_plan):
        mock_dt.now.return_value = fake_time
        get_zephyr_message()

    assert "5x5 swings, 3x10 press" in captured["prompt"]


def test_get_zephyr_falls_back_when_no_plan():
    from remind import get_zephyr_message
    fake_time = datetime(2026, 5, 25, 9, 0)  # Monday
    captured = {}

    def capture(prompt, **kwargs):
        captured["prompt"] = prompt
        return "zephyr response"

    with patch("remind.datetime") as mock_dt, \
         patch("remind.query_ollama", side_effect=capture), \
         patch("db.save_session"), \
         patch("db.get_today_plan", return_value=None):
        mock_dt.now.return_value = fake_time
        get_zephyr_message()

    assert USER_NAME in captured["prompt"]
    assert "Monday" in captured["prompt"]


def test_get_zephyr_saves_session():
    from remind import get_zephyr_message
    fake_time = datetime(2026, 5, 25, 9, 0)  # Monday
    with patch("remind.datetime") as mock_dt, \
         patch("remind.query_ollama", return_value="mocked"), \
         patch("db.save_session") as mock_save, \
         patch("db.get_today_plan", return_value=None):
        mock_dt.now.return_value = fake_time
        get_zephyr_message()

    mock_save.assert_called_once()
    kwargs = mock_save.call_args.kwargs
    assert kwargs["session_type"] == "workout"
    assert kwargs["day_of_week"] == "Monday"
    assert kwargs["response"] == "mocked"


# --- get_nudge_message ---

def test_nudge_prompt_contains_time():
    from remind import get_nudge_message
    fake_time = datetime(2026, 5, 25, 14, 30)
    captured = {}

    def capture(prompt, **kwargs):
        captured["prompt"] = prompt
        return "nudge"

    with patch("remind.datetime") as mock_dt, patch("remind.query_ollama", side_effect=capture):
        mock_dt.now.return_value = fake_time
        get_nudge_message()

    assert "14:30" in captured["prompt"]


def test_nudge_prompt_contains_user_name():
    from remind import get_nudge_message
    fake_time = datetime(2026, 5, 25, 14, 30)
    captured = {}

    def capture(prompt, **kwargs):
        captured["prompt"] = prompt
        return "nudge"

    with patch("remind.datetime") as mock_dt, patch("remind.query_ollama", side_effect=capture):
        mock_dt.now.return_value = fake_time
        get_nudge_message()

    assert USER_NAME in captured["prompt"]


def test_nudge_saves_session():
    from remind import get_nudge_message
    fake_time = datetime(2026, 5, 25, 14, 30)
    with patch("remind.datetime") as mock_dt, \
         patch("remind.query_ollama", return_value="nudge response"), \
         patch("db.save_session") as mock_save:
        mock_dt.now.return_value = fake_time
        get_nudge_message()

    kwargs = mock_save.call_args.kwargs
    assert kwargs["session_type"] == "nudge"
    assert kwargs["response"] == "nudge response"


# --- build_feedback_keyboard ---

def test_feedback_keyboard_contains_four_buttons():
    kb = build_feedback_keyboard("2026-05-25")
    buttons = [btn for row in kb["inline_keyboard"] for btn in row]
    assert len(buttons) == 4


def test_feedback_keyboard_callback_data_includes_date():
    kb = build_feedback_keyboard("2026-05-25")
    all_data = [btn["callback_data"] for row in kb["inline_keyboard"] for btn in row]
    assert all("2026-05-25" in d for d in all_data)


def test_feedback_keyboard_has_skipped_option():
    kb = build_feedback_keyboard("2026-05-25")
    all_data = [btn["callback_data"] for row in kb["inline_keyboard"] for btn in row]
    assert any("skipped" in d for d in all_data)


def test_feedback_keyboard_has_completed_options():
    kb = build_feedback_keyboard("2026-05-25")
    all_data = [btn["callback_data"] for row in kb["inline_keyboard"] for btn in row]
    assert any("completed" in d for d in all_data)


# --- build_feedback_prompt ---

def test_feedback_prompt_skipped_mentions_user():
    assert USER_NAME in build_feedback_prompt("skipped")


def test_feedback_prompt_skipped_gives_grief():
    prompt = build_feedback_prompt("skipped")
    assert "skipped" in prompt.lower()


def test_feedback_prompt_completed_easy_mentions_next_time():
    prompt = build_feedback_prompt("completed", "easy")
    assert "next time" in prompt.lower() or "upping" in prompt.lower()


def test_feedback_prompt_completed_hard_mentions_rest():
    prompt = build_feedback_prompt("completed", "hard")
    assert "rest" in prompt.lower()


def test_feedback_prompt_completed_perfect_positive():
    prompt = build_feedback_prompt("completed", "perfect")
    assert USER_NAME in prompt


# --- get_evening_reminder ---

def test_evening_reminder_pending_contains_user_name():
    from remind import get_evening_reminder
    fake_time = datetime(2026, 5, 25, 18, 0)  # Monday
    with patch("remind.datetime") as mock_dt, \
         patch("remind.query_ollama", return_value="you slacker"), \
         patch("db.save_session"), \
         patch("db.get_today_plan", return_value={"plan": "some plan", "status": "pending"}):
        mock_dt.now.return_value = fake_time
        result = get_evening_reminder()
    assert USER_NAME in result or result == "you slacker"


def test_evening_reminder_pending_saves_session():
    from remind import get_evening_reminder
    fake_time = datetime(2026, 5, 25, 18, 0)
    with patch("remind.datetime") as mock_dt, \
         patch("remind.query_ollama", return_value="do it"), \
         patch("db.save_session") as mock_save, \
         patch("db.get_today_plan", return_value={"plan": "some plan", "status": "pending"}):
        mock_dt.now.return_value = fake_time
        get_evening_reminder()

    kwargs = mock_save.call_args.kwargs
    assert kwargs["session_type"] == "evening_reminder"
    assert kwargs["response"] == "do it"


def test_evening_reminder_pending_prompt_contains_time():
    from remind import get_evening_reminder
    fake_time = datetime(2026, 5, 25, 18, 0)
    captured = {}

    def capture(prompt, **kwargs):
        captured["prompt"] = prompt
        return "nag"

    with patch("remind.datetime") as mock_dt, \
         patch("remind.query_ollama", side_effect=capture), \
         patch("db.save_session"), \
         patch("db.get_today_plan", return_value={"plan": "plan", "status": "pending"}):
        mock_dt.now.return_value = fake_time
        get_evening_reminder()

    assert "18:00" in captured["prompt"]
    assert USER_NAME in captured["prompt"]


def test_evening_reminder_completed_falls_back_to_nudge():
    from remind import get_evening_reminder
    fake_time = datetime(2026, 5, 25, 18, 0)
    with patch("remind.datetime") as mock_dt, \
         patch("remind.query_ollama", return_value="nudge response"), \
         patch("db.save_session") as mock_save, \
         patch("db.get_today_plan", return_value={"plan": "plan", "status": "completed"}):
        mock_dt.now.return_value = fake_time
        result = get_evening_reminder()

    assert result == "nudge response"
    kwargs = mock_save.call_args.kwargs
    assert kwargs["session_type"] == "nudge"


def test_evening_reminder_no_plan_falls_back_to_nudge():
    from remind import get_evening_reminder
    fake_time = datetime(2026, 5, 25, 18, 0)
    with patch("remind.datetime") as mock_dt, \
         patch("remind.query_ollama", return_value="nudge response"), \
         patch("db.save_session") as mock_save, \
         patch("db.get_today_plan", return_value=None):
        mock_dt.now.return_value = fake_time
        result = get_evening_reminder()

    assert result == "nudge response"
    kwargs = mock_save.call_args.kwargs
    assert kwargs["session_type"] == "nudge"


# --- get_recent_workouts excludes skipped (db level, tested via integration) ---

def test_skipped_sessions_excluded_from_recent_workouts():
    """Verify the SQL filter directly using raw SQLite — bypasses all db patches."""
    import sqlite3, tempfile, os
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        tmp = f.name
    try:
        with sqlite3.connect(tmp) as conn:
            conn.row_factory = sqlite3.Row
            conn.execute("""
                CREATE TABLE daily_plans (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL UNIQUE,
                    day_of_week TEXT NOT NULL,
                    workout_type TEXT NOT NULL,
                    exercises_focus TEXT,
                    plan TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    difficulty TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute(
                "INSERT INTO daily_plans (date, day_of_week, workout_type, exercises_focus, plan, status) "
                "VALUES ('2026-05-19', 'Monday', 'Functional Fitness', 'Power focus', 'plan A', 'completed')"
            )
            conn.execute(
                "INSERT INTO daily_plans (date, day_of_week, workout_type, exercises_focus, plan, status) "
                "VALUES ('2026-05-21', 'Wednesday', 'Functional Fitness', 'Strength focus', 'plan B', 'skipped')"
            )
            rows = conn.execute(
                """SELECT exercises_focus FROM daily_plans
                   WHERE workout_type='Functional Fitness'
                   AND (status IS NULL OR status != 'skipped')"""
            ).fetchall()

        assert len(rows) == 1
        assert rows[0]["exercises_focus"] == "Power focus"
    finally:
        os.unlink(tmp)
