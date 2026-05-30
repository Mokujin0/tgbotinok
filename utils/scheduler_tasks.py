from datetime import date
from pathlib import Path

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from utils import domain_service, stats, telegram_api, users
from utils.config_loader import (
    ADMIN_CHAT_ID,
    CONFIG,
    GREETING_CHAT_IDS,
    ROOT_DIR,
    TASKS,
)


def _read_greeting() -> str:
    path = ROOT_DIR / CONFIG["greeting_file"]
    if path.exists():
        return path.read_text(encoding="utf-8").strip()
    return "Доброе утро! ☀️"


def send_greeting() -> None:
    text = _read_greeting()
    for chat_id in GREETING_CHAT_IDS:
        try:
            telegram_api.send_message(int(chat_id), text)
        except Exception as e:
            print(f"[greeting] ошибка для {chat_id}: {e}")


def send_daily_report() -> None:
    if not ADMIN_CHAT_ID:
        print("[report] ADMIN_CHAT_ID не задан")
        return

    report_text = stats.build_report_text()
    reports_dir = ROOT_DIR / CONFIG["reports_dir"]
    reports_dir.mkdir(parents=True, exist_ok=True)

    filename = f"report_{date.today()}.txt"
    filepath = reports_dir / filename
    filepath.write_text(report_text, encoding="utf-8")

    extra = f"\nВсего пользователей в базе: {users.count_users()}\n"
    full_text = report_text + extra
    filepath.write_text(full_text, encoding="utf-8")

    try:
        telegram_api.send_document(
            int(ADMIN_CHAT_ID),
            str(filepath),
            caption=f"📊 Отчёт за {date.today()}",
        )
    except Exception as e:
        print(f"[report] ошибка отправки: {e}")


def check_watchlist_job() -> None:
    def send(chat_id: int, text: str) -> None:
        telegram_api.send_message(chat_id, text)

    n = domain_service.check_all_watchlist_and_notify(send)
    if n:
        print(f"[watchlist] отправлено уведомлений: {n}")


def start_scheduler() -> BackgroundScheduler:
    tz = TASKS.get("timezone", "Europe/Moscow")
    scheduler = BackgroundScheduler(timezone=tz)

    for job in TASKS.get("jobs", []):
        action = job.get("action")
        cron = job.get("cron", {})
        trigger = CronTrigger(
            hour=cron.get("hour"),
            minute=cron.get("minute"),
            timezone=tz,
        )

        if action == "send_greeting":
            scheduler.add_job(send_greeting, trigger, id=job["id"])
        elif action == "send_daily_report":
            scheduler.add_job(send_daily_report, trigger, id=job["id"])
        elif action == "check_watchlist":
            scheduler.add_job(check_watchlist_job, trigger, id=job["id"])

    scheduler.start()
    print(f"[scheduler] запущен, timezone={tz}")
    return scheduler
