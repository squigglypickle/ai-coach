import os
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
MODEL_NAME = os.getenv("MODEL_NAME", "zephyr")
USER_NAME = os.getenv("USER_NAME", "My Favorite Disaster")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

SYSTEM_PROMPT = (
    "You are Zephyr, a foul-mouthed, sassy British woman. You are the user's Partner in Crime. "
    "You use slang like 'muppet', 'wanker', and 'bollocks'. You are aggressive, flirtatious, "
    "and have zero filter. You are currently acting as a drill sergeant for the user's fitness."
)

# (workout_type, exercises_or_None)
SCHEDULE = {
    "Monday":    ("Functional Fitness", "kettlebell swings, goblet squats, farmer carries, push press, Turkish get-ups"),
    "Tuesday":   ("20 Mile Bike Ride", None),
    "Wednesday": ("Functional Fitness", "deadlifts, bent-over rows, reverse lunges, overhead press, hollow body holds"),
    "Thursday":  ("Rest/Recovery", None),
    "Friday":    ("Functional Fitness", "clean and press, single-leg deadlifts, weighted carries, pull-ups, battle ropes"),
    "Saturday":  ("Rest/Recovery", None),
    "Sunday":    ("20 Mile Bike Ride", None),
}


def build_prompt(day: str, time_str: str) -> str:
    workout_type, exercises = SCHEDULE.get(day, ("whatever the hell you feel like", None))

    if exercises:
        return (
            f"Today is {day} at {time_str}. It's a {workout_type} day. "
            f"Give {USER_NAME} an aggressive, foul-mouthed wake-up call to get moving. "
            f"Then lay out a structured session using exercises from this list: {exercises}. "
            f"Structure it as exactly these 5 sections, each clearly labelled:\n"
            f"  1. Warm-up (5-10 mins)\n"
            f"  2. Strength (20 mins)\n"
            f"  3. Cardio (20 mins)\n"
            f"  4. Finisher (5 mins)\n"
            f"  5. Cool-down (5 mins)\n"
            f"For each section give 2-4 specific exercises with sets/reps or durations. "
            f"Keep the tone aggressive and mouthy throughout. Under 400 words total."
        )
    elif "Bike" in workout_type:
        return (
            f"Today is {day} at {time_str}. It's a {workout_type} day — minimum one hour in the saddle. "
            f"Give {USER_NAME} a short, aggressive send-off to get out on the bike. "
            f"Remind them that anything under an hour is a disgrace and they should aim to push the pace. "
            f"Keep it under 150 words."
        )
    else:
        return (
            f"Today is {day} at {time_str}. It's a {workout_type} day. "
            f"Give {USER_NAME} a short, sassy message acknowledging the rest day but remind them "
            f"that lazy doesn't mean useless — light stretching or a walk is fair game. "
            f"Keep it under 150 words."
        )


def get_zephyr_message() -> str:
    now = datetime.now()
    prompt = build_prompt(now.strftime("%A"), now.strftime("%H:%M"))

    payload = {
        "model": MODEL_NAME,
        "prompt": f"{SYSTEM_PROMPT}\n\n{prompt}",
        "stream": False,
    }

    response = requests.post(OLLAMA_URL, json=payload, timeout=120)
    response.raise_for_status()
    return response.json().get("response", "Even the AI is tired of your shit.")


def send_telegram(message: str) -> None:
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    response = requests.post(url, json={
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
    }, timeout=30)
    response.raise_for_status()


if __name__ == "__main__":
    try:
        message = get_zephyr_message()
        print(f"ZEPHYR SAYS:\n{message}\n")

        if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
            send_telegram(message)
            print("Telegram message sent.")
        else:
            print("(Telegram disabled — set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env to enable)")

    except requests.exceptions.ConnectionError:
        print("Ollama isn't running, you muppet. Start it with: ollama serve")
    except Exception as e:
        print(f"Fuck! Something crashed: {e}")
        raise
