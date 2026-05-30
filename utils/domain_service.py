import html
import re
import time
from pathlib import Path

from utils import storage
from utils.config_loader import CONFIG, ROOT_DIR
from utils.namecheap_api import (
    check_domain_namecheap,
    check_domains_namecheap_bulk,
    is_namecheap_sandbox,
)
from utils.rdap_api import check_domain_rdap
from utils.whois_api import check_domain_whoisxml

try:
    import whois
except ImportError:
    whois = None

WHOIS_DELAY = 1.2
DEFAULT_SEARCH_RESULTS_LIMIT = 10
DEFAULT_SEARCH_CANDIDATES_LIMIT = 50

FALLBACK_TLDS = [".com", ".net", ".org", ".io", ".ru"]
FALLBACK_PREFIXES = ["", "get", "my", "go", "try"]
FALLBACK_SUFFIXES = ["", "app", "hub", "online", "shop"]

DOMAIN_RE = re.compile(r"^[a-z0-9]([a-z0-9\-]{0,61}[a-z0-9])?(\.[a-z]{2,})+$", re.I)


def _typographic_variations(keyword: str) -> list[str]:
    variations: list[str] = []
    if not keyword:
        return variations

    last = keyword[-1]
    candidates = [
        keyword + last,
        keyword + "y",
        keyword + "z",
        keyword + "i",
        "e" + keyword,
    ]
    for c in candidates:
        c = c.strip("-")
        if c and c != keyword and c not in variations and len(c) <= 63:
            variations.append(c)
    return variations


def _generate_bases(keyword: str) -> list[str]:
    prefixes = CONFIG.get("search_prefixes") or FALLBACK_PREFIXES
    suffixes = CONFIG.get("search_suffixes") or FALLBACK_SUFFIXES
    use_hyphen = bool(CONFIG.get("search_use_hyphen", False))

    scored: list[tuple[tuple, str]] = []
    seen: set[str] = set()

    def add(base: str, affix_count: int, typo: int = 0) -> None:
        base = base.strip("-")
        if not base or len(base) > 63 or base in seen:
            return
        seen.add(base)
        scored.append(((affix_count + typo, len(base), base), base))

    add(keyword, affix_count=0)

    for typo in _typographic_variations(keyword):
        add(typo, affix_count=0, typo=1)

    for p in prefixes:
        for s in suffixes:
            if s and s == keyword:
                continue
            if p and p == keyword:
                continue
            affix_count = (1 if p else 0) + (1 if s else 0)
            if affix_count == 0:
                continue
            add(f"{p}{keyword}{s}", affix_count)
            if use_hyphen:
                parts = [x for x in (p, keyword, s) if x]
                add("-".join(parts), affix_count)

    scored.sort(key=lambda x: x[0])
    return [base for _, base in scored]


def generate_similar_names(keyword: str) -> list[str]:
    keyword = re.sub(r"[^a-z0-9\-]", "", keyword.lower())
    keyword = keyword.strip("-")
    if not keyword:
        return []

    tlds_raw = CONFIG.get("similar_tlds") or FALLBACK_TLDS
    tlds = [t if t.startswith(".") else f".{t}" for t in tlds_raw]
    tlds = list(dict.fromkeys(tlds))
    limit = int(CONFIG.get("search_candidates_limit", DEFAULT_SEARCH_CANDIDATES_LIMIT))

    bases = _generate_bases(keyword)

    names: list[str] = []
    seen: set[str] = set()
    for tld in tlds:
        for base in bases:
            domain = f"{base}{tld}".lower()
            if domain not in seen and is_valid_domain(domain):
                seen.add(domain)
                names.append(domain)
                if len(names) >= limit:
                    return names
    return names


def _local_whois_lookup(domain: str) -> dict:
    if whois is None:
        return {
            "available": None,
            "source": "local whois",
            "error": "python-whois не установлен",
        }

    timeout = int(CONFIG.get("whois_timeout", 8))
    try:
        w = whois.whois(domain, timeout=timeout)
        if w.domain_name:
            return {"available": False, "source": "local whois", "error": None}
        return {"available": True, "source": "local whois", "error": None}
    except Exception as e:
        err_msg = str(e).lower()
        if "no match" in err_msg or "not found" in err_msg or "not registered" in err_msg or "no data found" in err_msg:
            return {"available": True, "source": "local whois", "error": None}
        if (
            "no address associated with hostname" in err_msg
            or "connection refused" in err_msg
            or "timed out" in err_msg
            or "timeout" in err_msg
        ):
            return {"available": None, "source": "local whois", "error": "WHOIS timeout/rate limit"}
        return {"available": None, "source": "local whois", "error": str(e)}


def _real_availability_lookup(domain: str) -> dict:
    sources = [
        check_domain_rdap,
        check_domain_whoisxml,
    ]
    if not is_namecheap_sandbox():
        sources.append(check_domain_namecheap)
    sources.append(_local_whois_lookup)

    errors = []
    for source_fn in sources:
        res = source_fn(domain)
        if res.get("available") is True or res.get("available") is False:
            return res
        if res.get("error"):
            errors.append(f"{res.get('source', 'source')}: {res['error']}")

    return {
        "available": None,
        "source": "availability",
        "error": "; ".join(errors) or "статус неизвестен",
    }


def _format_status(prefix: str, result: dict) -> str:
    error = result.get("error")
    available = result.get("available")
    if error:
        return f"{prefix}: ⚠️ {html.escape(str(error))}\n"
    if available is True:
        return f"{prefix}: ✅ <b>Свободен</b>\n"
    if available is False:
        return f"{prefix}: 🔒 <b>Занят</b>\n"
    return f"{prefix}: ❓ статус неизвестен\n"


def is_valid_domain(domain: str) -> bool:
    return bool(DOMAIN_RE.match(domain.strip().lower()))


def check_domain(domain: str) -> str:
    domain = domain.strip().lower()
    if not is_valid_domain(domain):
        return "❌ Некорректное имя домена. Пример: <code>example.com</code>"

    rdap_res = check_domain_rdap(domain)
    whoisxml_res = check_domain_whoisxml(domain)
    local_whois_res = _local_whois_lookup(domain)
    nc = check_domain_namecheap(domain)

    res_text = f"🔍 <b>{html.escape(domain)}</b>\n\n"
    res_text += _format_status("RDAP", rdap_res)
    res_text += _format_status("WhoisXML", whoisxml_res)
    res_text += _format_status("Local WHOIS", local_whois_res)
    nc_label = "Namecheap sandbox" if is_namecheap_sandbox() else "Namecheap"
    res_text += _format_status(nc_label, nc)
    if is_namecheap_sandbox():
        res_text += "\nℹ️ Sandbox не отражает реальные регистрации и используется только для диагностики API.\n"

    return res_text


def search_available(keyword: str) -> str:
    domains = generate_similar_names(keyword)
    if not domains:
        return "❌ Укажите ключевое слово: <code>/search myshop</code>"

    free = []
    skipped_sandbox = is_namecheap_sandbox()
    results_limit = int(CONFIG.get("search_results_limit", DEFAULT_SEARCH_RESULTS_LIMIT))
    max_lookups = int(CONFIG.get("search_max_lookups", 15))
    checked = 0

    candidates = domains
    if not skipped_sandbox:
        nc_results = check_domains_namecheap_bulk(domains[:50])
        if "error" not in nc_results:
            candidates = [d for d in domains if nc_results.get(d) is not False]

    for i, d in enumerate(candidates):
        if checked >= max_lookups:
            break
        if i > 0:
            time.sleep(WHOIS_DELAY)
        checked += 1
        r = _real_availability_lookup(d)
        if r.get("available") is True:
            free.append((d, r.get("source", "availability")))
        if len(free) >= results_limit:
            break

    if not free:
        return f"😔 Свободных доменов по запросу «{html.escape(keyword)}» не найдено (проверено {checked} из {len(domains)})."

    res = f"🎯 Свободные домены для «<b>{html.escape(keyword)}</b>»:\n\n"
    for domain, source in free:
        res = res + f"✅ <code>{html.escape(domain)}</code> <i>({html.escape(source)})</i>\n"
    if skipped_sandbox:
        res += "\nℹ️ Namecheap sandbox пропущен при поиске, чтобы не показывать занятые домены как свободные.\n"
    return res


def _check_domains_real(domains: list[str]) -> dict:
    results = {}
    for i, domain in enumerate(domains):
        if i > 0:
            time.sleep(WHOIS_DELAY)
        results[domain] = _real_availability_lookup(domain).get("available")
    return results


def _check_domains_for_watchlist(domains: list[str]) -> dict:
    if not domains:
        return {}

    if is_namecheap_sandbox():
        return _check_domains_real(domains)

    nc_results = {}
    for i in range(0, len(domains), 50):
        batch = domains[i:i + 50]
        res = check_domains_namecheap_bulk(batch)
        if "error" not in res:
            nc_results.update(res)

    final_results = {}
    for domain in domains:
        is_available = nc_results.get(domain)
        if is_available is True or is_available is None:
            is_available = _real_availability_lookup(domain).get("available")
        final_results[domain] = is_available
    return final_results


def _watchlist_path() -> Path:
    return ROOT_DIR / CONFIG["watchlist_file"]


def load_watchlist() -> dict:
    return storage.read_json(_watchlist_path(), default={}) or {}


def save_watchlist(data: dict) -> None:
    storage.write_json(_watchlist_path(), data)


def add_watch(chat_id: int, domain: str) -> str:
    domain = domain.strip().lower()
    if not is_valid_domain(domain):
        return "❌ Некорректный домен"

    already = {"v": False}

    def mutator(data):
        data = data or {}
        key = str(chat_id)
        data.setdefault(key, [])
        if domain in data[key]:
            already["v"] = True
        else:
            data[key].append(domain)
        return data

    storage.update_json(_watchlist_path(), mutator, default={})

    if already["v"]:
        return f"ℹ️ Домен <code>{html.escape(domain)}</code> уже в списке отслеживания"
    return f"👀 Добавлен в отслеживание: <code>{html.escape(domain)}</code>\nУведомлю, когда домен станет свободным."


def remove_watch(chat_id: int, domain: str) -> str:
    domain = domain.strip().lower()
    found = {"v": False}

    def mutator(data):
        data = data or {}
        key = str(chat_id)
        if key in data and domain in data[key]:
            data[key].remove(domain)
            found["v"] = True
        return data

    storage.update_json(_watchlist_path(), mutator, default={})

    if not found["v"]:
        return "Домен не найден в вашем списке"
    return f"🗑 Убран из отслеживания: <code>{html.escape(domain)}</code>"


def get_user_watchlist(chat_id: int) -> list:
    data = load_watchlist()
    return data.get(str(chat_id), [])


def check_all_watchlist_and_notify(send_fn) -> int:
    data = load_watchlist()
    notified = 0

    all_domains = set()
    for domains in data.values():
        all_domains.update(domains)

    availability = _check_domains_for_watchlist(sorted(all_domains))

    freed = {d for d, avail in availability.items() if avail is True}
    if not freed:
        return 0

    notified_domains: list[tuple[int, str]] = []

    def mutator(current):
        current = current or {}
        for chat_id, domains in list(current.items()):
            still_watching = []
            for domain in domains:
                if domain in freed:
                    notified_domains.append((int(chat_id), domain))
                else:
                    still_watching.append(domain)
            current[chat_id] = still_watching
        return current

    storage.update_json(_watchlist_path(), mutator, default={})

    for chat_id, domain in notified_domains:
        send_fn(
            chat_id,
            f"🎉 Домен <code>{html.escape(domain)}</code> стал <b>свободным</b>!",
        )
        notified += 1

    return notified
