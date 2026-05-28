import xml.etree.ElementTree as ET

import requests

from utils.config_loader import (
    NAMECHEAP_API_KEY,
    NAMECHEAP_API_URL,
    NAMECHEAP_API_USER,
    NAMECHEAP_CLIENT_IP,
)


def check_domain_namecheap(domain: str) -> dict:
    """Возвращает available (bool|None), error (str|None)."""
    domain = domain.strip().lower()
    if not all([NAMECHEAP_API_USER, NAMECHEAP_API_KEY, NAMECHEAP_CLIENT_IP]):
        return {"available": None, "error": "Namecheap: заполните переменные в .env"}

    # example.com -> sld=example, tld=com
    parts = domain.split(".")
    if len(parts) < 2:
        return {"available": None, "error": "Некорректное имя домена"}

    sld = parts[0]
    tld = ".".join(parts[1:])

    url = NAMECHEAP_API_URL
    params = {
        "ApiUser": NAMECHEAP_API_USER,
        "ApiKey": NAMECHEAP_API_KEY,
        "UserName": NAMECHEAP_API_USER,
        "ClientIp": NAMECHEAP_CLIENT_IP,
        "Command": "namecheap.domains.check",
        "DomainList": domain,
    }

    try:
        resp = requests.get(url, params=params, timeout=30)
        resp.raise_for_status()
        root = ET.fromstring(resp.text)
    except (requests.RequestException, ET.ParseError) as e:
        return {"available": None, "error": str(e)}

    ns = {"nc": "http://api.namecheap.com/xml.response"}
    attr = root.find(".//nc:DomainCheckResult", ns)
    if attr is None:
        err = root.find(".//nc:Errors/nc:Error", ns)
        msg = err.text if err is not None else "Неизвестный ответ Namecheap"
        return {"available": None, "error": msg}

    available_str = attr.get("Available", "")
    available = available_str.lower() == "true"
    return {"available": available, "error": None}


def check_domains_namecheap_bulk(domains: list[str]) -> dict:
    """
    Массовая проверка списка доменов (до 50 шт) через Sandbox API.
    Возвращает словарь {domain: available_bool} или {'error': msg}.
    """
    if not domains:
        return {}
    if not all([NAMECHEAP_API_USER, NAMECHEAP_API_KEY, NAMECHEAP_CLIENT_IP]):
        return {"error": "Namecheap: заполните переменные в .env"}

    url = NAMECHEAP_API_URL
    params = {
        "ApiUser": NAMECHEAP_API_USER,
        "ApiKey": NAMECHEAP_API_KEY,
        "UserName": NAMECHEAP_API_USER,
        "ClientIp": NAMECHEAP_CLIENT_IP,
        "Command": "namecheap.domains.check",
        "DomainList": ",".join(domains),
    }

    try:
        resp = requests.get(url, params=params, timeout=30)
        resp.raise_for_status()
        root = ET.fromstring(resp.text)
    except (requests.RequestException, ET.ParseError) as e:
        return {"error": str(e)}

    ns = {"nc": "http://api.namecheap.com/xml.response"}
    results = {}

    check_nodes = root.findall(".//nc:DomainCheckResult", ns)
    if not check_nodes:
        return {"error": "Отсутствуют результаты проверки"}

    for node in check_nodes:
        domain_name = node.get("Domain", "").lower()
        results[domain_name] = node.get("Available", "").lower() == "true"

    return results
