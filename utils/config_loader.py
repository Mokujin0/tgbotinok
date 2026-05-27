"""Загрузка config.json, tasks.json и переменных из .env."""

import json
from pathlib import Path

from decouple import config
from dotenv import load_dotenv

# Корень проекта — папка на уровень выше utils/
ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")


def load_json(filename: str) -> dict:
    path = ROOT_DIR / filename
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


CONFIG = load_json("config.json")
TASKS = load_json("tasks.json")

TELEGRAM_TOKEN = config("TELEGRAM_BOT_TOKEN", default="")
ADMIN_CHAT_ID = config("ADMIN_CHAT_ID", default="")
WHOIS_API_KEY = config("WHOIS_API_KEY", default="")
WHOIS_AVAILABILITY_URL = config(
    "WHOIS_AVAILABILITY_URL",
    default="https://domain-availability.whoisxmlapi.com/api/v1",
)
NAMECHEAP_API_USER = config("NAMECHEAP_API_USER", default="")
NAMECHEAP_API_KEY = config("NAMECHEAP_API_KEY", default="")
NAMECHEAP_CLIENT_IP = config("NAMECHEAP_CLIENT_IP", default="")
NAMECHEAP_API_URL = config(
    "NAMECHEAP_API_URL",
    default="https://api.sandbox.namecheap.com/xml.response",
)

GREETING_CHAT_IDS = [
    x.strip()
    for x in config("GREETING_CHAT_IDS", default="").split(",")
    if x.strip()
]
