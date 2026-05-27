"""Работа с Telegram Bot API через requests (без aiogram)."""

import requests

from utils.config_loader import CONFIG, TELEGRAM_TOKEN

API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"
PARSE_MODE = CONFIG.get("parse_mode", "HTML")


def _post(method: str, data: dict = None, files: dict = None) -> dict:
    url = f"{API_URL}/{method}"
    if files:
        resp = requests.post(url, data=data or {}, files=files, timeout=60)
    else:
        resp = requests.post(url, json=data or {}, timeout=60)
    resp.raise_for_status()
    return resp.json()


def get_updates(offset: int = 0, timeout: int = 30) -> list:
    result = _post("getUpdates", {"offset": offset, "timeout": timeout, "allowed_updates": []})
    return result.get("result", [])


def send_message(chat_id, text: str, parse_mode: str = None, reply_markup: dict = None) -> dict:
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode or PARSE_MODE,
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    return _post("sendMessage", payload)


def send_document(chat_id, file_path: str, caption: str = "") -> dict:
    with open(file_path, "rb") as f:
        return _post(
            "sendDocument",
            data={"chat_id": chat_id, "caption": caption},
            files={"document": f},
        )


def make_inline_button(text: str, callback_data: str) -> dict:
    """Создать inline кнопку."""
    return {"text": text, "callback_data": callback_data}


def make_inline_keyboard(buttons: list) -> dict:
    """Создать inline клавиатуру из списка списков кнопок.

    buttons: [[button1, button2], [button3]]
    """
    return {"inline_keyboard": buttons}


def answer_callback(callback_query_id: str, text: str = "", show_alert: bool = False) -> dict:
    """Ответить на callback_query (нажатие кнопки)."""
    payload = {
        "callback_query_id": callback_query_id,
        "text": text,
        "show_alert": show_alert,
    }
    return _post("answerCallbackQuery", payload)


def edit_message_text(chat_id: int, message_id: int, text: str, reply_markup: dict = None) -> dict:
    """Отредактировать текст существующего сообщения."""
    payload = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": text,
        "parse_mode": PARSE_MODE,
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    return _post("editMessageText", payload)

