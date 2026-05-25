"""
Telegram feedback listener — run this as a long-lived service.

Polls for button callbacks from workout messages, stores the feedback,
and sends a Zephyr-style acknowledgement.

Run with:
    source venv/bin/activate
    python listener.py

Or as a systemd service pointing at venv/bin/python.
"""
import os
import time
import requests
from datetime import datetime
from dotenv import load_dotenv
import db
from remind import build_feedback_prompt, query_ollama, send_telegram

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")


def _get_updates(offset: int = None) -> list:
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
    params = {"timeout": 30}
    if offset is not None:
        params["offset"] = offset
    response = requests.get(url, params=params, timeout=35)
    response.raise_for_status()
    return response.json().get("result", [])


def _answer_callback(callback_query_id: str) -> None:
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/answerCallbackQuery"
    requests.post(url, json={"callback_query_id": callback_query_id}, timeout=10)


def _process_callback(callback_query: dict) -> None:
    data = callback_query.get("data", "")
    parts = data.split(":")

    if parts[0] != "feedback" or len(parts) < 3:
        return

    date = parts[1]
    status = parts[2]
    difficulty = parts[3] if len(parts) > 3 else None

    today = datetime.now().strftime("%Y-%m-%d")
    if date != today:
        print(f"Ignoring stale feedback for {date}")
        _answer_callback(callback_query["id"])
        return

    db.update_plan_feedback(date=date, status=status, difficulty=difficulty)
    _answer_callback(callback_query["id"])

    prompt = build_feedback_prompt(status, difficulty)
    message = query_ollama(prompt)
    send_telegram(message)
    print(f"Feedback recorded: {status}/{difficulty} for {date}")


def run():
    print("Zephyr listener started. Waiting for feedback...")
    offset = None
    while True:
        try:
            updates = _get_updates(offset)
            for update in updates:
                offset = update["update_id"] + 1
                if "callback_query" in update:
                    _process_callback(update["callback_query"])
        except requests.exceptions.ConnectionError:
            print("Telegram unreachable, retrying in 30s...")
            time.sleep(30)
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(5)


if __name__ == "__main__":
    run()
