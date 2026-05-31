from pathlib import Path

from utils import storage
from utils.config_loader import CONFIG, ROOT_DIR


def _history_path() -> Path:
    return ROOT_DIR / CONFIG.get("history_file", "data/history.json")


def add_entry(chat_id: int, domain: str) -> None:
    domain = domain.strip().lower()
    if not domain:
        return
    limit = int(CONFIG.get("history_limit", 10))

    def mutator(data):
        data = data or {}
        key = str(chat_id)
        items = data.get(key, [])
        items = [d for d in items if d != domain]
        items.insert(0, domain)
        data[key] = items[:limit]
        return data

    storage.update_json(_history_path(), mutator, default={})


def get_history(chat_id: int) -> list:
    data = storage.read_json(_history_path(), default={}) or {}
    return data.get(str(chat_id), [])


def clear_history(chat_id: int) -> None:
    def mutator(data):
        data = data or {}
        data.pop(str(chat_id), None)
        return data

    storage.update_json(_history_path(), mutator, default={})
