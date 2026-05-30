from datetime import date
from pathlib import Path

from utils import storage
from utils.config_loader import CONFIG, ROOT_DIR


def _stats_path() -> Path:
    return ROOT_DIR / CONFIG["stats_file"]


def _default_stats() -> dict:
    return {
        "date": str(date.today()),
        "messages": 0,
        "commands": 0,
        "domains_checked": 0,
        "users_new": 0,
    }


def _normalize(data) -> dict:
    if not data:
        return _default_stats()
    if data.get("date") != str(date.today()):
        return _default_stats()
    return data


def inc(field: str, amount: int = 1) -> None:
    def mutator(data):
        data = _normalize(data)
        data[field] = data.get(field, 0) + amount
        data["date"] = str(date.today())
        return data

    storage.update_json(_stats_path(), mutator, default=None)


def get_today_stats() -> dict:
    return _normalize(storage.read_json(_stats_path(), default=None))


def build_report_text() -> str:
    s = get_today_stats()
    txt = f"Отчёт бота за {s['date']}\n"
    txt = txt + "========================================\n"
    txt = txt + f"Сообщений обработано: {s.get('messages', 0)}\n"
    txt = txt + f"Команд выполнено: {s.get('commands', 0)}\n"
    txt = txt + f"Доменов проверено: {s.get('domains_checked', 0)}\n"
    txt = txt + f"Новых пользователей: {s.get('users_new', 0)}\n"
    return txt
