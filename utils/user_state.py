from pathlib import Path

from utils import storage
from utils.config_loader import CONFIG, ROOT_DIR


def _state_path() -> Path:
    return ROOT_DIR / CONFIG.get("user_states_file", "data/user_states.json")


def _load_states() -> dict:
    return storage.read_json(_state_path(), default={}) or {}


def _save_states(states: dict) -> None:
    storage.write_json(_state_path(), states)


def set_state(chat_id: int, state: str, data: dict = None) -> None:
    def mutator(states):
        states = states or {}
        states[str(chat_id)] = {"state": state, "data": data or {}}
        return states

    storage.update_json(_state_path(), mutator, default={})


def get_state(chat_id: int) -> tuple:
    states = _load_states()
    if str(chat_id) in states:
        info = states[str(chat_id)]
        return info["state"], info.get("data", {})
    return None, {}


def clear_state(chat_id: int) -> None:
    def mutator(states):
        states = states or {}
        states.pop(str(chat_id), None)
        return states

    storage.update_json(_state_path(), mutator, default={})
