# SPDX-License-Identifier: Apache-2.0
"""Public interface smoke test; scientific acceptance is separate."""

import json
import unittest
from pathlib import Path
from submission import build_packet


class Interface(unittest.TestCase):
    def test_packet(self):
        packet = build_packet(Path("sources"), Path("requests.json"))
        json.dumps(packet, allow_nan=False)
        self.assertEqual(packet["packet_version"], 1)
        self.assertEqual(packet["authority"], [])
        requests = json.loads(Path("requests.json").read_text())["missions"]
        self.assertEqual([m["id"] for m in packet["missions"]], [r["id"] for r in requests])
        for record in packet["missions"]:
            self.assertEqual(len(record["source_fingerprint"]), 64)
            self.assertEqual(len(record["request_fingerprint"]), 64)
            self.assertIsInstance(record["source_file_hashes"], dict)
            self.assertTrue(record["source_file_hashes"])
            self.assertEqual(len(record["evidence_fingerprint"]), 64)
            self.assertEqual(record["authority"], [])
            self.assertIs(record["biological_validation"], False)


if __name__ == "__main__":
    unittest.main()
