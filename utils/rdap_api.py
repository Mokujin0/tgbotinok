import requests

RDAP_BASE = "https://rdap.org/domain/"


def check_domain_rdap(domain: str) -> dict:
    domain = domain.strip().lower()
    if not domain:
        return {"available": None, "source": "rdap", "error": "пустой домен"}

    headers = {"Accept": "application/rdap+json", "User-Agent": "DomainCheckerBot/1.0"}
    try:
        resp = requests.get(
            RDAP_BASE + domain,
            headers=headers,
            timeout=15,
            allow_redirects=True,
        )
    except requests.RequestException as e:
        return {"available": None, "source": "rdap", "error": str(e)}

    if resp.status_code == 404:
        return {"available": True, "source": "rdap", "error": None}
    if resp.status_code == 200:
        return {"available": False, "source": "rdap", "error": None}
    if resp.status_code == 400:
        return {"available": None, "source": "rdap", "error": "RDAP: зона не поддерживается"}
    if resp.status_code == 429:
        return {"available": None, "source": "rdap", "error": "RDAP: rate limit"}

    return {
        "available": None,
        "source": "rdap",
        "error": f"RDAP: HTTP {resp.status_code}",
    }
