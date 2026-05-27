"""Управление состояниями пользователей (ожидание ввода)."""

import json
from pathlib import Path

STATE_FILE = Path("data/user_states.json")


def _load_states() -> dict:
    """Загрузить состояния из файла."""
    if STATE_FILE.exists():
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save_states(states: dict) -> None:
    """Сохранить состояния в файл."""
    STATE_FILE.parent.mkdir(exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(states, f, ensure_ascii=False, indent=2)


def set_state(chat_id: int, state: str, data: dict = None) -> None:
    """Установить состояние пользователя."""
    states = _load_states()
    states[str(chat_id)] = {
        "state": state,
        "data": data or {}
    }
    _save_states(states)


def get_state(chat_id: int) -> tuple:
    """Получить состояние пользователя. Возвращает (state, data)."""
    states = _load_states()
    if str(chat_id) in states:
        info = states[str(chat_id)]
        return info["state"], info.get("data", {})
    return None, {}


def clear_state(chat_id: int) -> None:
    """Очистить состояние пользователя."""
    states = _load_states()
    states.pop(str(chat_id), None)
    _save_states(states)
