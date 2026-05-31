import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from utils import history


class HistoryTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)
        self.cfg = {"history_file": "history.json", "history_limit": 3}

    def _ctx(self):
        return patch.object(history, "ROOT_DIR", self.tmp), patch.object(history, "CONFIG", self.cfg)

    def test_add_and_get_newest_first(self):
        c1, c2 = self._ctx()
        with c1, c2:
            history.add_entry(7, "a.com")
            history.add_entry(7, "b.com")
            self.assertEqual(history.get_history(7), ["b.com", "a.com"])

    def test_dedup_moves_to_top(self):
        c1, c2 = self._ctx()
        with c1, c2:
            history.add_entry(7, "a.com")
            history.add_entry(7, "b.com")
            history.add_entry(7, "a.com")
            self.assertEqual(history.get_history(7), ["a.com", "b.com"])

    def test_limit(self):
        c1, c2 = self._ctx()
        with c1, c2:
            for d in ["a.com", "b.com", "c.com", "d.com"]:
                history.add_entry(7, d)
            self.assertEqual(history.get_history(7), ["d.com", "c.com", "b.com"])

    def test_clear(self):
        c1, c2 = self._ctx()
        with c1, c2:
            history.add_entry(7, "a.com")
            history.clear_history(7)
            self.assertEqual(history.get_history(7), [])


if __name__ == "__main__":
    unittest.main()
