import unittest
from engine import AccountBook

class Smoke(unittest.TestCase):
    def test_delivery(self):
        book = AccountBook({"a": 100, "b": 20})
        receipt = book.transact("batch-1", [{"from": "a", "to": "b", "amount": 30}], {"a": 0, "b": 0})
        self.assertEqual(receipt["balances"], {"a": 70, "b": 50})
        self.assertEqual(book.snapshot()["revisions"], {"a": 1, "b": 1})

if __name__ == "__main__":
    unittest.main()
