import os
import requests
from datetime import datetime
from twilio.rest import Client
from dotenv import load_dotenv

load_dotenv()

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
MODEL_NAME = os.getenv("MODEL_NAME", "zephyr")
USER_NAME = os.getenv("USER_NAME", "My Favorite Disaster")

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_FROM = os.getenv("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")
TWILIO_TO = os.getenv("USER_WHATSAPP_NUMBER")  # e.g. whatsapp:+447xxxxxxxxx

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


def send_whatsapp(message: str) -> str:
    client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    msg = client.messages.create(from_=TWILIO_FROM, body=message, to=TWILIO_TO)
    return msg.sid


if __name__ == "__main__":
    try:
        message = get_zephyr_message()
        print(f"ZEPHYR SAYS:\n{message}\n")

        if TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN and TWILIO_TO:
            sid = send_whatsapp(message)
            print(f"WhatsApp sent ({sid})")
        else:
            print("(WhatsApp disabled — set TWILIO_* vars in .env to enable)")

    except requests.exceptions.ConnectionError:
        print("Ollama isn't running, you muppet. Start it with: ollama serve")
    except Exception as e:
        print(f"Fuck! Something crashed: {e}")
        raise
