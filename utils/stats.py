import json
from datetime import date
from pathlib import Path

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


def _load() -> dict:
    path = _stats_path()
    if not path.exists():
        return _default_stats()
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    today = str(date.today())
    if data.get("date") != today:
        return _default_stats()
    return data


def _save(data: dict) -> None:
    path = _stats_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def inc(field: str, amount: int = 1) -> None:
    data = _load()
    data[field] = data.get(field, 0) + amount
    data["date"] = str(date.today())
    _save(data)


def get_today_stats() -> dict:
    return _load()


def build_report_text() -> str:
    s = get_today_stats()
    txt = f"Отчёт бота за {s['date']}\n"
    txt = txt + "========================================\n"
    txt = txt + f"Сообщений обработано: {s.get('messages', 0)}\n"
    txt = txt + f"Команд выполнено: {s.get('commands', 0)}\n"
    txt = txt + f"Доменов проверено: {s.get('domains_checked', 0)}\n"
    txt = txt + f"Новых пользователей: {s.get('users_new', 0)}\n"
    return txt
