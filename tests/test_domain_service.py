import datetime
import unittest
from unittest.mock import patch

from utils import domain_service


class DomainServiceTests(unittest.TestCase):
    def test_generate_similar_names_deduplicates_and_skips_keyword_suffix(self):
        with patch.dict(
            domain_service.CONFIG,
            {
                "similar_tlds": [".com", "com", ".net"],
                "search_prefixes": ["", "get"],
                "search_suffixes": ["", "shop", "hub"],
                "search_candidates_limit": 50,
            },
        ):
            names = domain_service.generate_similar_names("shop")

        self.assertEqual(len(names), len(set(names)))
        self.assertIn("shop.com", names)
        self.assertIn("shophub.com", names)
        self.assertNotIn("shopshop.com", names)

    def test_search_available_ignores_namecheap_sandbox_for_decisions(self):
        calls = []

        def fake_lookup(domain):
            calls.append(domain)
            return {"available": domain == "free-example.com", "source": "whoisxml", "error": None}

        with patch.object(domain_service, "generate_similar_names", return_value=["taken-example.com", "free-example.com"]):
            with patch.object(domain_service, "is_namecheap_sandbox", return_value=True):
                with patch.object(domain_service, "check_domains_namecheap_bulk") as bulk_check:
                    with patch.object(domain_service, "_real_availability_lookup", side_effect=fake_lookup):
                        with patch.object(domain_service.time, "sleep"):
                            result = domain_service.search_available("example")

        bulk_check.assert_not_called()
        self.assertEqual(calls, ["taken-example.com", "free-example.com"])
        self.assertIn("free-example.com", result)
        self.assertNotIn("taken-example.com", result)


class ExpiryAndBulkTests(unittest.TestCase):
    def test_parse_expiry_handles_list_and_none(self):
        d = datetime.datetime(2027, 3, 15)
        self.assertEqual(domain_service._parse_expiry(d), "15.03.2027")
        self.assertEqual(domain_service._parse_expiry([d, d]), "15.03.2027")
        self.assertEqual(domain_service._parse_expiry(None), "")

    def test_bulk_check_summary(self):
        def fake_lookup(domain):
            if domain == "free.com":
                return {"available": True, "source": "rdap", "error": None}
            return {"available": False, "source": "rdap", "error": None, "expires": "01.01.2030"}

        with patch.object(domain_service, "_real_availability_lookup", side_effect=fake_lookup):
            with patch.object(domain_service.time, "sleep"):
                res = domain_service.check_domains_bulk(["free.com", "taken.com"])

        self.assertIn("free.com", res)
        self.assertIn("свободен", res)
        self.assertIn("taken.com", res)
        self.assertIn("занят", res)

    def test_bulk_check_respects_limit(self):
        domains = [f"d{i}.com" for i in range(20)]
        seen = []

        def fake_lookup(domain):
            seen.append(domain)
            return {"available": True, "source": "rdap", "error": None}

        with patch.dict(domain_service.CONFIG, {"bulk_check_limit": 5}):
            with patch.object(domain_service, "_real_availability_lookup", side_effect=fake_lookup):
                with patch.object(domain_service.time, "sleep"):
                    res = domain_service.check_domains_bulk(domains)

        self.assertEqual(len(seen), 5)
        self.assertIn("пропущено", res)


if __name__ == "__main__":
    unittest.main()
