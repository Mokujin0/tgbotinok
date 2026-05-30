import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from utils import domain_service, stats, user_state, users


class PersistenceTestBase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)


class UsersTests(PersistenceTestBase):
    def test_save_user_new_then_existing(self):
        cfg = {"users_csv": "users.csv"}
        with patch.object(users, "ROOT_DIR", self.tmp), patch.object(users, "CONFIG", cfg):
            self.assertTrue(users.save_user(1, "alice", "Alice"))
            self.assertFalse(users.save_user(1, "alice", "Alice"))
            self.assertTrue(users.save_user(2, "bob"))
            self.assertEqual(users.count_users(), 2)

    def test_count_users_empty(self):
        cfg = {"users_csv": "users.csv"}
        with patch.object(users, "ROOT_DIR", self.tmp), patch.object(users, "CONFIG", cfg):
            self.assertEqual(users.count_users(), 0)


class StatsTests(PersistenceTestBase):
    def test_inc_accumulates(self):
        cfg = {"stats_file": "stats.json"}
        with patch.object(stats, "ROOT_DIR", self.tmp), patch.object(stats, "CONFIG", cfg):
            stats.inc("messages")
            stats.inc("messages", 2)
            stats.inc("commands")
            s = stats.get_today_stats()
            self.assertEqual(s["messages"], 3)
            self.assertEqual(s["commands"], 1)
            self.assertEqual(s["date"], str(date.today()))

    def test_inc_resets_on_new_day(self):
        cfg = {"stats_file": "stats.json"}
        with patch.object(stats, "ROOT_DIR", self.tmp), patch.object(stats, "CONFIG", cfg):
            stats.inc("messages", 5)
            from utils import storage
            path = self.tmp / "stats.json"
            data = storage.read_json(path)
            data["date"] = "2000-01-01"
            storage.write_json(path, data)

            stats.inc("messages")
            s = stats.get_today_stats()
            self.assertEqual(s["messages"], 1)


class WatchlistTests(PersistenceTestBase):
    def _ctx(self):
        cfg = {"watchlist_file": "watchlist.json"}
        return patch.object(domain_service, "ROOT_DIR", self.tmp), patch.object(domain_service, "CONFIG", cfg)

    def test_add_remove_watch(self):
        c1, c2 = self._ctx()
        with c1, c2:
            domain_service.add_watch(10, "example.com")
            self.assertEqual(domain_service.get_user_watchlist(10), ["example.com"])
            domain_service.add_watch(10, "example.com")
            self.assertEqual(domain_service.get_user_watchlist(10), ["example.com"])
            domain_service.remove_watch(10, "example.com")
            self.assertEqual(domain_service.get_user_watchlist(10), [])

    def test_add_watch_invalid_domain(self):
        c1, c2 = self._ctx()
        with c1, c2:
            res = domain_service.add_watch(10, "not a domain")
            self.assertIn("Некорректный", res)
            self.assertEqual(domain_service.get_user_watchlist(10), [])

    def test_check_all_watchlist_and_notify(self):
        c1, c2 = self._ctx()
        with c1, c2:
            domain_service.add_watch(10, "free.com")
            domain_service.add_watch(10, "taken.com")

            availability = {"free.com": True, "taken.com": False}
            sent = []

            def fake_send(chat_id, text):
                sent.append((chat_id, text))

            with patch.object(domain_service, "_check_domains_for_watchlist", return_value=availability):
                n = domain_service.check_all_watchlist_and_notify(fake_send)

            self.assertEqual(n, 1)
            self.assertEqual(sent[0][0], 10)
            self.assertIn("free.com", sent[0][1])
            self.assertEqual(domain_service.get_user_watchlist(10), ["taken.com"])


class ValidationTests(unittest.TestCase):
    def test_valid_domains(self):
        for d in ["example.com", "my-shop.io", "a.co", "sub.domain.org"]:
            self.assertTrue(domain_service.is_valid_domain(d), d)

    def test_invalid_domains(self):
        for d in ["", "no tld", "-bad.com", "bad-.com", "x.c", "пример.рф"]:
            self.assertFalse(domain_service.is_valid_domain(d), d)


class UserStateTests(PersistenceTestBase):
    def test_set_get_clear(self):
        cfg = {"user_states_file": "states.json"}
        with patch.object(user_state, "ROOT_DIR", self.tmp), patch.object(user_state, "CONFIG", cfg):
            self.assertEqual(user_state.get_state(5), (None, {}))
            user_state.set_state(5, "waiting_domain_check")
            self.assertEqual(user_state.get_state(5), ("waiting_domain_check", {}))
            user_state.clear_state(5)
            self.assertEqual(user_state.get_state(5), (None, {}))


if __name__ == "__main__":
    unittest.main()
