import pytest
from unittest.mock import patch
from datetime import datetime

MOCK_OLLAMA_RESPONSE = "Get off your arse. This is a test response."

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def pytest_addoption(parser):
    parser.addoption("--day", choices=DAYS, default=None, help="Day of week to simulate")
    parser.addoption("--time", default=None, help="Time to simulate, e.g. 09:00")


@pytest.fixture(autouse=True)
def block_ollama(request):
    if request.node.get_closest_marker("integration"):
        yield
    else:
        with patch("remind.query_ollama", return_value=MOCK_OLLAMA_RESPONSE):
            yield


@pytest.fixture(autouse=True)
def block_telegram():
    with patch("remind.send_telegram") as mock_send:
        yield mock_send


@pytest.fixture(autouse=True)
def block_db(request):
    if request.node.get_closest_marker("integration"):
        yield
    else:
        with patch("db.init_db"), \
             patch("db.save_session"), \
             patch("db.save_daily_plan"), \
             patch("db.update_plan_feedback"), \
             patch("db.get_recent_workouts", return_value=[]), \
             patch("db.get_today_plan", return_value=None):
            yield
