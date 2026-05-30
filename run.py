import sys
import time
from concurrent.futures import ThreadPoolExecutor

from utils.config_loader import CONFIG, TELEGRAM_TOKEN
from utils.handlers import handle_update
from utils.scheduler_tasks import start_scheduler
from utils import telegram_api


def _safe_handle(update: dict) -> None:
    try:
        handle_update(update)
    except Exception as e:
        print(f"[handler] ошибка: {e}")


def main() -> None:
    if not TELEGRAM_TOKEN:
        print("Ошибка: задайте TELEGRAM_BOT_TOKEN в файле .env")
        sys.exit(1)

    interval = CONFIG.get("poll_interval_seconds", 1)
    workers = int(CONFIG.get("handler_workers", 8))
    scheduler = start_scheduler()
    executor = ThreadPoolExecutor(max_workers=workers, thread_name_prefix="handler")

    print("Бот запущен. Ожидание сообщений...")
    offset = 0

    try:
        while True:
            start = time.time()
            try:
                updates = telegram_api.get_updates(offset=offset, timeout=25)
                for update in updates:
                    offset = update["update_id"] + 1
                    executor.submit(_safe_handle, update)
            except Exception as e:
                print(f"[poll] ошибка getUpdates: {e}")

            elapsed = time.time() - start
            if elapsed < interval:
                time.sleep(interval - elapsed)
    except KeyboardInterrupt:
        print("\nОстановка бота...")
        scheduler.shutdown(wait=False)
        executor.shutdown(wait=False, cancel_futures=True)


if __name__ == "__main__":
    main()
