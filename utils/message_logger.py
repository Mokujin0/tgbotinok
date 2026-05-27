"""История сообщений — отдельный .log файл на каждого пользователя."""

from datetime import datetime, timezone
from pathlib import Path

from utils.config_loader import CONFIG, ROOT_DIR


def _user_log_path(chat_id: int) -> Path:
    logs_dir = ROOT_DIR / CONFIG["logs_dir"]
    logs_dir.mkdir(parents=True, exist_ok=True)
    return logs_dir / f"user_{chat_id}.log"


def log_message(chat_id: int, text: str, direction: str = "in") -> None:
    """direction: in — от пользователя, out — от бота."""
    path = _user_log_path(chat_id)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    line = f"[{ts}] [{direction}] {text}\n"
    with open(path, "a", encoding="utf-8") as f:
        f.write(line)
