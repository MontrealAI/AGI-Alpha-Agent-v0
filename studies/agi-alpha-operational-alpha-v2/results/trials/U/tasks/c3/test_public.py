import hashlib
import unittest
from engine import ArtifactStore

class Smoke(unittest.TestCase):
    def test_delivery(self):
        store = ArtifactStore()
        data = b"useful artifact"
        store.begin("alpha", "report", len(data), hashlib.sha256(data).hexdigest())
        store.put("alpha", "report", 0, data)
        self.assertEqual(store.commit("alpha", "report"), data)
        self.assertEqual(ArtifactStore.restore(store.snapshot()).commit("alpha", "report"), data)

if __name__ == "__main__":
    unittest.main()
