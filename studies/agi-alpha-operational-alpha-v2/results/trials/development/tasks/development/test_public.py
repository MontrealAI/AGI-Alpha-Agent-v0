import unittest
from engine import Ledger

class Smoke(unittest.TestCase):
    def test_delivery(self):
        ledger = Ledger({"alpha": 100})
        ledger.reserve("alpha", "job-1", 40)
        ledger.settle("alpha", "job-1", 25)
        self.assertEqual(ledger.snapshot()["wallets"]["alpha"],
                         {"available": 75, "reserved": 0, "spent": 25})

if __name__ == "__main__":
    unittest.main()
