import unittest
from unittest.mock import MagicMock, patch

from utils import rdap_api
from utils import domain_service


class RdapClientTests(unittest.TestCase):
    def _resp(self, status_code):
        m = MagicMock()
        m.status_code = status_code
        return m

    def test_404_means_available(self):
        with patch.object(rdap_api.requests, "get", return_value=self._resp(404)):
            res = rdap_api.check_domain_rdap("free.com")
        self.assertIs(res["available"], True)
        self.assertEqual(res["source"], "rdap")

    def test_200_means_taken(self):
        with patch.object(rdap_api.requests, "get", return_value=self._resp(200)):
            res = rdap_api.check_domain_rdap("taken.com")
        self.assertIs(res["available"], False)

    def test_429_unknown(self):
        with patch.object(rdap_api.requests, "get", return_value=self._resp(429)):
            res = rdap_api.check_domain_rdap("x.com")
        self.assertIsNone(res["available"])
        self.assertIn("rate limit", res["error"])

    def test_network_error_unknown(self):
        with patch.object(rdap_api.requests, "get", side_effect=rdap_api.requests.RequestException("boom")):
            res = rdap_api.check_domain_rdap("x.com")
        self.assertIsNone(res["available"])
        self.assertIn("boom", res["error"])


class RealAvailabilityOrderTests(unittest.TestCase):
    def test_rdap_short_circuits_before_local_whois(self):
        with patch.object(domain_service, "check_domain_rdap",
                          return_value={"available": True, "source": "rdap", "error": None}), \
             patch.object(domain_service, "check_domain_whoisxml") as wx, \
             patch.object(domain_service, "_local_whois_lookup") as lw, \
             patch.object(domain_service, "is_namecheap_sandbox", return_value=True):
            res = domain_service._real_availability_lookup("example.com")

        self.assertIs(res["available"], True)
        self.assertEqual(res["source"], "rdap")
        wx.assert_not_called()
        lw.assert_not_called()

    def test_falls_through_to_next_source_when_unknown(self):
        with patch.object(domain_service, "check_domain_rdap",
                          return_value={"available": None, "source": "rdap", "error": "zone unsupported"}), \
             patch.object(domain_service, "check_domain_whoisxml",
                          return_value={"available": False, "source": "whoisxml", "error": None}), \
             patch.object(domain_service, "_local_whois_lookup") as lw, \
             patch.object(domain_service, "is_namecheap_sandbox", return_value=True):
            res = domain_service._real_availability_lookup("example.com")

        self.assertIs(res["available"], False)
        self.assertEqual(res["source"], "whoisxml")
        lw.assert_not_called()


if __name__ == "__main__":
    unittest.main()
