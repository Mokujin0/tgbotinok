import threading
import time

import requests

from utils.config_loader import CONFIG

_NOMINATIM_MIN_INTERVAL = float(CONFIG.get("nominatim_min_interval", 1.0))
_throttle_lock = threading.Lock()
_last_request_ts = 0.0


def _throttle() -> None:
    global _last_request_ts
    with _throttle_lock:
        now = time.monotonic()
        wait = _NOMINATIM_MIN_INTERVAL - (now - _last_request_ts)
        if wait > 0:
            time.sleep(wait)
        _last_request_ts = time.monotonic()


def get_address(latitude: float, longitude: float) -> str:
    url = "https://nominatim.openstreetmap.org/reverse"
    params = {
        "lat": latitude,
        "lon": longitude,
        "format": "json",
        "accept-language": "ru",
    }
    headers = {"User-Agent": "DomainCheckerBot/1.0"}
    try:
        _throttle()
        resp = requests.get(url, params=params, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        return data.get("display_name", "Адрес не найден")
    except requests.RequestException:
        return f"Координаты: {latitude}, {longitude} (адрес получить не удалось)"
