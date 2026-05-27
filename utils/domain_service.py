import json
import re
import whois
from pathlib import Path

from utils.config_loader import CONFIG, ROOT_DIR
from utils.namecheap_api import check_domain_namecheap

DOMAIN_RE = re.compile(r"^[a-z0-9]([a-z0-9\-]{0,61}[a-z0-9])?(\.[a-z]{2,})+$", re.I)


def _whois_lookup(domain: str) -> dict:
    try:
        w = whois.whois(domain)
        if w.domain_name:
            return {"available": False, "error": None}
        return {"available": True, "error": None}
    except Exception as e:
        err_msg = str(e).lower()
        if "no match" in err_msg or "not found" in err_msg or "not registered" in err_msg or "no data found" in err_msg:
            return {"available": True, "error": None}
        return {"available": None, "error": str(e)}


def is_valid_domain(domain: str) -> bool:
    return bool(DOMAIN_RE.match(domain.strip().lower()))


def check_domain(domain: str) -> str:
    domain = domain.strip().lower()
    if not is_valid_domain(domain):
        return "❌ Некорректное имя домена. Пример: <code>example.com</code>"

    whois_res = _whois_lookup(domain)
    nc = check_domain_namecheap(domain)

    res_text = f"🔍 <b>{domain}</b>\n\n"

    if whois_res["error"]:
        res_text = res_text + f"WHOIS: ⚠️ {whois_res['error']}\n"
    elif whois_res["available"] is True:
        res_text = res_text + "WHOIS: ✅ <b>Свободен</b>\n"
    elif whois_res["available"] is False:
        res_text = res_text + "WHOIS: 🔒 <b>Занят</b>\n"
    else:
        res_text = res_text + "WHOIS API: ❓ статус неизвестен\n"

    if nc["error"]:
        res_text = res_text + f"Namecheap (sandbox): ⚠️ {nc['error']}\n"
    elif nc["available"] is True:
        res_text = res_text + "Namecheap (sandbox): ✅ <b>Свободен</b>\n"
    elif nc["available"] is False:
        res_text = res_text + "Namecheap (sandbox): 🔒 <b>Занят</b>\n"

    return res_text


def generate_similar_names(keyword: str) -> list[str]:
    keyword = re.sub(r"[^a-z0-9\-]", "", keyword.lower())
    if not keyword:
        return []

    tlds = CONFIG.get("similar_tlds", [".com", ".net", ".org", ".io", ".ru"])
    prefixes = CONFIG.get("search_prefixes", ["", "get", "my"])
    suffixes = CONFIG.get("search_suffixes", ["", "online", "web"])

    names = []
    for p in prefixes:
        for s in suffixes:
            base = f"{p}{keyword}{s}".strip("-")
            if not base:
                continue
            for tld in tlds:
                tld = tld if tld.startswith(".") else f".{tld}"
                names.append(f"{base}{tld}")
    return names[:30]  # не перегружаем API


def search_available(keyword: str) -> str:
    domains = generate_similar_names(keyword)
    if not domains:
        return "❌ Укажите ключевое слово: <code>/search myshop</code>"

    free = []
    for d in domains:
        r = _whois_lookup(d)
        if r.get("available") is True:
            free.append(d)
        if len(free) >= 10:
            break

    if not free:
        return f"😔 Свободных доменов по запросу «{keyword}» не найдено (проверено {len(domains)})."

    res = f"🎯 Свободные домены для «<b>{keyword}</b>»:\n\n"
    for f in free:
        res = res + f"✅ <code>{f}</code>\n"
    return res


def _watchlist_path() -> Path:
    return ROOT_DIR / CONFIG["watchlist_file"]


def load_watchlist() -> dict:
    path = _watchlist_path()
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        res = json.load(f)
    return res


def save_watchlist(data: dict) -> None:
    path = _watchlist_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def add_watch(chat_id: int, domain: str) -> str:
    domain = domain.strip().lower()
    if not is_valid_domain(domain):
        return "❌ Некорректный домен"

    data = load_watchlist()
    key = str(chat_id)
    if key not in data:
        data[key] = []
    
    if domain in data[key]:
        return f"ℹ️ Домен <code>{domain}</code> уже в списке отслеживания"

    data[key].append(domain)
    save_watchlist(data)
    return f"👀 Добавлен в отслеживание: <code>{domain}</code>\nУведомлю, когда домен станет свободным."


def remove_watch(chat_id: int, domain: str) -> str:
    # Удаляем домен из списка
    domain = domain.strip().lower()
    data = load_watchlist()
    key = str(chat_id)
    if key not in data or domain not in data[key]:
        return "Домен не найден в вашем списке"

    data[key].remove(domain)
    save_watchlist(data)
    return f"🗑 Убран из отслеживания: <code>{domain}</code>"


def get_user_watchlist(chat_id: int) -> list:
    """Получить список отслеживаемых доменов пользователя."""
    data = load_watchlist()
    return data.get(str(chat_id), [])


def check_all_watchlist_and_notify(send_fn) -> int:
    """
    Проверяет все домены из watchlist.
    send_fn(chat_id, text) — функция отправки сообщения.
    Возвращает число отправленных уведомлений.
    """
    data = load_watchlist()
    notified = 0

    for chat_id, domains in list(data.items()):
        still_watching = []
        for domain in domains:
            r = _whois_lookup(domain)
            if r.get("available") is True:
                send_fn(
                    int(chat_id),
                    f"🎉 Домен <code>{domain}</code> стал <b>свободным</b>!",
                )
                notified += 1
            else:
                still_watching.append(domain)
        data[chat_id] = still_watching

    save_watchlist(data)
    return notified
