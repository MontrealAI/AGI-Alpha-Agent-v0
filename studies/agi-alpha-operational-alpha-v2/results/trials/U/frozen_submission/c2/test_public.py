import unittest
from engine import Scheduler

class Smoke(unittest.TestCase):
    def test_delivery(self):
        queue = Scheduler(5)
        queue.add("alpha", "a", 3, [])
        queue.add("alpha", "b", 2, ["a"])
        queue.claim("alpha", "a", "l1")
        queue.finish("alpha", "a", "l1", True)
        queue.claim("alpha", "b", "l2")
        self.assertEqual(queue.snapshot()["used"], 2)

if __name__ == "__main__":
    unittest.main()
