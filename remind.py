import os
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
MODEL_NAME = os.getenv("MODEL_NAME", "zephyr")
USER_NAME = os.getenv("USER_NAME", "My Favorite Disaster")

CALLMEBOT_API_KEY = os.getenv("CALLMEBOT_API_KEY")
WHATSAPP_PHONE = os.getenv("WHATSAPP_PHONE")  # international format, no +, e.g. 447xxxxxxxxx

CALLMEBOT_URL = "https://api.callmebot.com/whatsapp.php"

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
            f"Then list today's workout with these exercises: {exercises}. "
            f"Format the exercises as a short numbered list with a brief description of each. "
            f"Keep the whole message punchy and under 300 words."
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


def send_whatsapp(message: str) -> None:
    response = requests.get(CALLMEBOT_URL, params={
        "phone": WHATSAPP_PHONE,
        "text": message,
        "apikey": CALLMEBOT_API_KEY,
    }, timeout=30)
    response.raise_for_status()


if __name__ == "__main__":
    try:
        message = get_zephyr_message()
        print(f"ZEPHYR SAYS:\n{message}\n")

        if CALLMEBOT_API_KEY and WHATSAPP_PHONE:
            send_whatsapp(message)
            print("WhatsApp sent.")
        else:
            print("(WhatsApp disabled — set CALLMEBOT_API_KEY and WHATSAPP_PHONE in .env to enable)")

    except requests.exceptions.ConnectionError:
        print("Ollama isn't running, you muppet. Start it with: ollama serve")
    except Exception as e:
        print(f"Fuck! Something crashed: {e}")
        raise
