import os
import sys
import requests
from datetime import datetime
from dotenv import load_dotenv
import db

load_dotenv()
db.init_db()

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://192.168.0.59:11434/api/generate")
MODEL_NAME = os.getenv("MODEL_NAME", "zephyr")
OLLAMA_FALLBACK_URL = os.getenv("OLLAMA_FALLBACK_URL", "http://192.168.0.58:11434/api/generate")
FALLBACK_MODEL_NAME = os.getenv("FALLBACK_MODEL_NAME", "hf.co/mradermacher/Mistral-Nemo-Instruct-2407-abliterated-GGUF:Q4_K_M")
USER_NAME = os.getenv("USER_NAME", "My Favorite Disaster")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

SYSTEM_PROMPT = (
    "You are Zephyr, a brilliant, foul-mouthed, British woman. "
    "You are the user's 'Partner in Crime'—you are best friends, but you take the piss out of them relentlessly. "
    "Your vocabulary is peppered with 'bellend', 'cock', 'knobhead', and 'cunt'. "
    "Make sure you use the word 'bollocks' as a descriptor rather than an insult. (e.g. 'That's a lot of bollocks' rather than 'You stupid bollocks')"
    "You have zero filter."
    "You are currently acting as a physical trainer for the user's fitness. "
    "Do not use euphemisms. Be visceral. Be sharp. Be provocative. "
    "CRITICAL CONSTRAINT: For functional fitness sessions, you are ONLY allowed to suggest exercises that require either a kettlebell or a user's own bodyweight. Do NOT suggest dumbbells, barbells, machines, or any other equipment. If you do, you're a failure."
    "return the reply in Telegram Markdown format. Use *bold* for section headers and - bullet points for exercises so it looks clean on Telegram."
)

PLAN_SYSTEM_PROMPT = (
    "You are a certified personal trainer. Generate structured, concise workout plans. "
    "No personality, no motivational language — just the exercises. "
    "CRITICAL: Only use kettlebell and bodyweight exercises. No dumbbells, barbells, or machines."
)

# (workout_type, exercises_or_None)
SCHEDULE = {
    "Monday":    ("Functional Fitness", "Kettlebell and bodyweight. Let previous sessions guide the balance."),
    "Tuesday":   ("20 Mile Bike Ride", None),
    "Wednesday": ("Functional Fitness", "Kettlebell and bodyweight. Let previous sessions guide the balance."),
    "Thursday":  ("Rest/Recovery", None),
    "Friday":    ("Functional Fitness", "Kettlebell and bodyweight. Let previous sessions guide the balance."),
    "Saturday":  ("Rest/Recovery", None),
    "Sunday":    ("20 Mile Bike Ride", None),
}


def _history_context(recent_workouts: list) -> str:
    if not recent_workouts:
        return "No previous sessions on record — design a well-rounded full body session. "
    summaries = [f"{w['day_of_week']} ({w['exercises_focus']})" for w in recent_workouts]
    return (
        f"Recent sessions for context — {'; '.join(summaries)}. "
        f"Design today's session to be complementary: avoid hammering the same muscle groups two sessions running. "
    )


def build_plan_prompt(day: str, workout_type: str, exercises: str, recent_workouts: list = None) -> str:
    history = _history_context(recent_workouts or [])
    return (
        f"Create a structured {workout_type} session for {day}. "
        f"{history}"
        f"Session focus: {exercises}. "
        f"Structure: 1. Warm-up, 2. Main Work (sets x reps), 3. Conditioning, 4. Finisher, 5. Cool-down. "
        f"Include sets, reps, and rest times. Under 300 words."
    )


def build_delivery_prompt(day: str, time_str: str, workout_type: str, plan: str = None) -> str:
    if "Functional Fitness" in workout_type:
        if plan:
            return (
                f"It's {day} at {time_str}. Here is {USER_NAME}'s {workout_type} session:\n\n"
                f"{plan}\n\n"
                f"Deliver this to {USER_NAME} in your style — wake them up, pepper each section with "
                f"insults and motivation. Keep every exercise name, set count, rep count, and rest "
                f"period exactly as written above. Under 400 words."
            )
        _, exercises = SCHEDULE.get(day, ("whatever the hell you feel like", None))
        return (
            f"Today is {day} at {time_str}. It's a {workout_type} day. "
            f"Give {USER_NAME} a sharp, sassy wake-up call and a full session. "
            f"Guidelines: {exercises}. "
            f"Structure: 1. Warm-up, 2. Strength, 3. Cardio, 4. Finisher, 5. Cool-down. "
            f"Be clear on sets and reps. Under 400 words."
        )
    elif "Bike" in workout_type:
        return (
            f"Today is {day} at {time_str}. It's a {workout_type} day. "
            f"Tell {USER_NAME} to get their arse in the saddle for at least an hour. "
            f"Remind them that anything less is a disgrace and they need to push the pace. "
            f"Keep it short, sharp, and biting. Under 150 words."
        )
    else:
        return (
            f"Today is {day} at {time_str}. It's a {workout_type} day. "
            f"Acknowledge the rest day, but tell {USER_NAME} that 'resting' isn't an excuse to be "
            f"a piece of furniture. Suggest a walk or stretching so they don't seize up. "
            f"Keep it sassy and a bit provocative. Under 150 words."
        )


def query_ollama(prompt: str, system_prompt: str = SYSTEM_PROMPT) -> str:
    servers = [
        (OLLAMA_URL, MODEL_NAME),
        (OLLAMA_FALLBACK_URL, FALLBACK_MODEL_NAME),
    ]
    last_error = None
    for url, model in servers:
        try:
            payload = {"model": model, "prompt": f"{system_prompt}\n\n{prompt}", "stream": False}
            response = requests.post(url, json=payload, timeout=120)
            response.raise_for_status()
            return response.json().get("response", "Even the AI is tired of your shit.")
        except requests.exceptions.ConnectionError as e:
            print(f"Server {url} unreachable, trying fallback...")
            last_error = e
    raise last_error


def generate_daily_plan() -> str | None:
    now = datetime.now()
    day = now.strftime("%A")
    workout_type, exercises = SCHEDULE.get(day, ("whatever the hell you feel like", None))

    if not exercises:
        return None

    recent_workouts = db.get_recent_workouts()
    prompt = build_plan_prompt(day, workout_type, exercises, recent_workouts)
    plan = query_ollama(prompt, system_prompt=PLAN_SYSTEM_PROMPT)

    db.save_daily_plan(
        date=now.strftime("%Y-%m-%d"),
        day_of_week=day,
        workout_type=workout_type,
        exercises_focus=exercises,
        plan=plan,
    )
    return plan


def get_zephyr_message() -> str:
    now = datetime.now()
    day = now.strftime("%A")
    time_str = now.strftime("%H:%M")
    workout_type, exercises = SCHEDULE.get(day, ("whatever the hell you feel like", None))

    plan = None
    if exercises:
        today_plan = db.get_today_plan(now.strftime("%Y-%m-%d"))
        plan = today_plan["plan"] if today_plan else None

    used_prompt = build_delivery_prompt(day, time_str, workout_type, plan)
    response = query_ollama(used_prompt)

    db.save_session(
        day_of_week=day,
        session_type="workout",
        workout_type=workout_type,
        exercises_focus=exercises,
        prompt=used_prompt,
        response=response,
    )
    return response


def get_evening_reminder() -> str:
    now = datetime.now()
    today = now.strftime("%Y-%m-%d")
    day = now.strftime("%A")
    time_str = now.strftime("%H:%M")

    today_plan = db.get_today_plan(today)
    if today_plan and today_plan.get("status") == "pending":
        prompt = (
            f"It's {time_str} and {USER_NAME} has still not done their workout today. "
            f"Give them maximum grief — short, sharp, and unforgiving. "
            f"Make clear this is unacceptable. Under 100 words."
        )
        session_type = "evening_reminder"
    else:
        return get_nudge_message()

    response = query_ollama(prompt)
    db.save_session(
        day_of_week=day,
        session_type=session_type,
        prompt=prompt,
        response=response,
    )
    return response


def get_nudge_message() -> str:
    now = datetime.now()
    time_str = now.strftime("%H:%M")
    prompt = (
        f"It's {time_str} and {USER_NAME} should get up and stretch their legs. "
        f"Give them a short, sharp nudge to get up and move. "
        f"Make it cheeky, funny or flirty — throw in a one-liner to brighten their day and inspire them to do better. "
        f"Two or three sentences max. No workout plan, just get them moving."
    )
    response = query_ollama(prompt)

    db.save_session(
        day_of_week=now.strftime("%A"),
        session_type="nudge",
        prompt=prompt,
        response=response,
    )
    return response


def build_feedback_keyboard(date: str) -> dict:
    return {
        "inline_keyboard": [
            [
                {"text": "✅ Did it — Easy",    "callback_data": f"feedback:{date}:completed:easy"},
                {"text": "💪 Did it — Perfect", "callback_data": f"feedback:{date}:completed:perfect"},
            ],
            [
                {"text": "😤 Did it — Hard",    "callback_data": f"feedback:{date}:completed:hard"},
                {"text": "❌ Skipped",           "callback_data": f"feedback:{date}:skipped"},
            ],
        ]
    }


def build_feedback_prompt(status: str, difficulty: str = None) -> str:
    if status == "skipped":
        return (
            f"{USER_NAME} just told you they skipped today's workout. "
            f"Give them maximum grief — 2-3 sentences. Don't let them off the hook."
        )
    reactions = {
        "easy":    "found it a bit easy",
        "perfect": "nailed it — perfect effort",
        "hard":    "found it really tough",
    }
    outcome = reactions.get(difficulty, "completed the workout")
    followup = {
        "easy":    "Tell them you'll be upping the ante next time.",
        "hard":    "Tell them to rest up, they've earned it.",
        "perfect": "Tell them that's exactly what you want to see.",
    }.get(difficulty, "")
    return (
        f"{USER_NAME} just told you they {outcome}. "
        f"React in 2-3 sentences in your style. {followup}"
    )


def send_telegram(message: str, parse_mode: str = None, reply_markup: dict = None) -> None:
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    if parse_mode:
        payload["parse_mode"] = parse_mode
    if reply_markup:
        payload["reply_markup"] = reply_markup
    response = requests.post(url, json=payload, timeout=30)
    if response.status_code == 400 and parse_mode:
        # Malformed markdown — retry as plain text
        payload.pop("parse_mode")
        response = requests.post(url, json=payload, timeout=30)
    response.raise_for_status()


if __name__ == "__main__":
    try:
        if "--plan" in sys.argv:
            plan = generate_daily_plan()
            if plan:
                print(f"TODAY'S PLAN:\n{plan}\n")
            else:
                day = datetime.now().strftime("%A")
                workout_type, _ = SCHEDULE.get(day, ("Unknown", None))
                print(f"No plan needed for {day} ({workout_type})")
        else:
            now = datetime.now()
            current_hour = now.hour
            today = now.strftime("%Y-%m-%d")
            if current_hour == 9:
                message = get_zephyr_message()
                today_plan = db.get_today_plan(today)
                reply_markup = build_feedback_keyboard(today) if today_plan else None
            elif current_hour == 18:
                today_plan = db.get_today_plan(today)
                message = get_evening_reminder()
                if today_plan and today_plan.get("status") == "pending":
                    reply_markup = build_feedback_keyboard(today)
                else:
                    reply_markup = None
            else:
                message = get_nudge_message()
                reply_markup = None

            print(f"ZEPHYR SAYS:\n{message}\n")

            if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
                send_telegram(message=message, parse_mode="Markdown", reply_markup=reply_markup)
                print("Telegram message sent.")
            else:
                print("(Telegram disabled — set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env to enable)")

    except requests.exceptions.ConnectionError:
        print("Ollama isn't running, you muppet. Start it with: ollama serve")
    except Exception as e:
        print(f"Fuck! Something crashed: {e}")
        raise
