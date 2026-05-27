"""Адрес по координатам (для сообщений type=location)."""

import requests


def get_address(latitude: float, longitude: float) -> str:
    """Обратное геокодирование через OpenStreetMap Nominatim (бесплатно)."""
    url = "https://nominatim.openstreetmap.org/reverse"
    params = {
        "lat": latitude,
        "lon": longitude,
        "format": "json",
        "accept-language": "ru",
    }
    headers = {"User-Agent": "DomainCheckerBot/1.0"}
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        return data.get("display_name", "Адрес не найден")
    except requests.RequestException:
        return f"Координаты: {latitude}, {longitude} (адрес получить не удалось)"
