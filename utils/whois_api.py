import requests

from utils.config_loader import WHOIS_API_KEY, WHOIS_AVAILABILITY_URL


def check_domain_whoisxml(domain: str) -> dict:
    domain = domain.strip().lower()
    if not WHOIS_API_KEY:
        return {"available": None, "source": "whoisxml", "error": "WhoisXML: заполните WHOIS_API_KEY в .env"}

    params = {
        "apiKey": WHOIS_API_KEY,
        "domainName": domain,
        "mode": "DNS_AND_WHOIS",
        "credits": "DA",
        "outputFormat": "JSON",
    }

    try:
        resp = requests.get(WHOIS_AVAILABILITY_URL, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
    except (requests.RequestException, ValueError) as e:
        return {"available": None, "source": "whoisxml", "error": str(e)}

    if "ErrorMessage" in data:
        return {"available": None, "source": "whoisxml", "error": data["ErrorMessage"].get("msg", "WhoisXML error")}

    domain_info = data.get("DomainInfo") or {}
    availability = str(domain_info.get("domainAvailability", "")).upper()
    if availability == "AVAILABLE":
        return {"available": True, "source": "whoisxml", "error": None}
    if availability == "UNAVAILABLE":
        return {"available": False, "source": "whoisxml", "error": None}

    return {
        "available": None,
        "source": "whoisxml",
        "error": f"Неизвестный статус WhoisXML: {availability or 'empty'}",
    }
