"""Сохранение пользователей в CSV."""

import csv
from datetime import datetime, timezone
from pathlib import Path

from utils.config_loader import CONFIG, ROOT_DIR


def _users_path() -> Path:
    return ROOT_DIR / CONFIG["users_csv"]


def save_user(chat_id: int, username: str = "", first_name: str = "", last_name: str = "") -> bool:
    """
    Добавляет пользователя, если его ещё нет.
    Возвращает True, если пользователь новый.
    """
    path = _users_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    rows = []
    exists = False
    if path.exists() and path.stat().st_size > 0:
        with open(path, "r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames or ["chat_id", "username", "first_name", "last_name", "registered_at"]
            for row in reader:
                if str(row.get("chat_id")) == str(chat_id):
                    exists = True
                rows.append(row)
    else:
        fieldnames = ["chat_id", "username", "first_name", "last_name", "registered_at"]

    if exists:
        return False

    rows.append({
        "chat_id": chat_id,
        "username": username or "",
        "first_name": first_name or "",
        "last_name": last_name or "",
        "registered_at": datetime.now(timezone.utc).isoformat(),
    })

    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    return True


def count_users() -> int:
    path = _users_path()
    if not path.exists():
        return 0
    with open(path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        return sum(1 for _ in reader)
