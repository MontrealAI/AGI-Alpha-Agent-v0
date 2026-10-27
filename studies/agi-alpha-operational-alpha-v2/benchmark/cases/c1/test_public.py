import unittest
from engine import Journal

class Smoke(unittest.TestCase):
    def test_delivery(self):
        journal = Journal({"alpha": 100})
        journal.append(dict(id="e1", job="j1", owner="alpha", kind="reserve", amount=40))
        journal.append(dict(id="e2", job="j1", owner="alpha", kind="settle", amount=25))
        self.assertEqual(journal.snapshot()["wallets"]["alpha"]["available"], 75)
        self.assertEqual(Journal.replay({"alpha": 100}, journal.export_log()).snapshot(), journal.snapshot())

if __name__ == "__main__":
    unittest.main()
