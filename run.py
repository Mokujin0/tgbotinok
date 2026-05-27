import sys
import time

from utils.config_loader import CONFIG, TELEGRAM_TOKEN
from utils.handlers import handle_update
from utils.scheduler_tasks import start_scheduler
from utils import telegram_api


def main() -> None:
    if not TELEGRAM_TOKEN:
        print("Ошибка: задайте TELEGRAM_BOT_TOKEN в файле .env")
        sys.exit(1)

    interval = CONFIG.get("poll_interval_seconds", 1)
    scheduler = start_scheduler()

    print("Бот запущен. Ожидание сообщений...")
    offset = 0

    try:
        while True:
            start = time.time()
            try:
                updates = telegram_api.get_updates(offset=offset, timeout=25)
                for update in updates:
                    offset = update["update_id"] + 1
                    try:
                        handle_update(update)
                    except Exception as e:
                        print(f"[handler] ошибка: {e}")
            except Exception as e:
                print(f"[poll] ошибка getUpdates: {e}")

            elapsed = time.time() - start
            if elapsed < interval:
                time.sleep(interval - elapsed)
    except KeyboardInterrupt:
        print("\nОстановка бота...")
        scheduler.shutdown(wait=False)


if __name__ == "__main__":
    main()
