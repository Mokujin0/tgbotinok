from datetime import datetime, timezone
from pathlib import Path

from utils import storage
from utils.config_loader import CONFIG, ROOT_DIR

FIELDNAMES = ["chat_id", "username", "first_name", "last_name", "registered_at"]


def _users_path() -> Path:
    return ROOT_DIR / CONFIG["users_csv"]


def save_user(chat_id: int, username: str = "", first_name: str = "", last_name: str = "") -> bool:
    def mutator(rows, fieldnames):
        exists = any(str(r.get("chat_id")) == str(chat_id) for r in rows)
        if exists:
            return None, fieldnames, False

        rows.append({
            "chat_id": chat_id,
            "username": username or "",
            "first_name": first_name or "",
            "last_name": last_name or "",
            "registered_at": datetime.now(timezone.utc).isoformat(),
        })
        return rows, FIELDNAMES, True

    return storage.update_csv(_users_path(), mutator, FIELDNAMES)


def count_users() -> int:
    rows, _ = storage.read_csv_rows(_users_path())
    return len(rows)
