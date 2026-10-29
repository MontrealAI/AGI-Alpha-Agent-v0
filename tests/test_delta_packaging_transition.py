# SPDX-License-Identifier: Apache-2.0
"""Exact additive wheel closure; prior packaging identities remain immutable."""
import hashlib
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
PROFILE = "scripts/strategy_research_e721_compatibility_v2.json"
GUARD = "scripts/check_strategy_research_compatibility_v2.py"


class DeltaPackagingTransition(unittest.TestCase):
    def test_exact_namespace_addition_and_only_corresponding_identity_changes(self):
        raw = (ROOT / "tests/fixtures/fast-delivery-packaging-147-metadata.json").read_bytes()
        self.assertEqual(
            hashlib.sha256(raw).hexdigest(), "527ea6953de0d6cbefa919cd1ecedf33ea497ab78a411ab71c19420538715ffe"
        )
        snapshot = json.loads(raw)
        self.assertEqual(snapshot["sourceCommit"], "a6b2d869a7736e7c414d7d615d86c616c2f82615")
        old = snapshot["files"]
        self.assertEqual(set(old), {"pyproject.toml", PROFILE, GUARD})
        before = b'"contrib.invention_automation*"]'
        after = b'"contrib.invention_automation*", "contrib.enterprise_campaign"]'
        project = old["pyproject.toml"].encode().replace(before, after, 1)
        self.assertEqual(old["pyproject.toml"].encode().count(before), 1)
        self.assertEqual((ROOT / "pyproject.toml").read_bytes(), project)
        previous = old[PROFILE].encode()
        entry = json.loads(previous)["files"]["pyproject.toml"]
        expected = previous.replace(
            ('"bytes": ' + str(entry["bytes"])).encode(), ('"bytes": ' + str(len(project))).encode(), 1
        ).replace(entry["sha256"].encode(), hashlib.sha256(project).hexdigest().encode(), 1)
        self.assertEqual((ROOT / PROFILE).read_bytes(), expected)
        old_hash = hashlib.sha256(previous).hexdigest().encode()
        new_hash = hashlib.sha256(expected).hexdigest().encode()
        self.assertEqual(old[GUARD].encode().count(old_hash), 1)
        self.assertEqual((ROOT / GUARD).read_bytes(), old[GUARD].encode().replace(old_hash, new_hash, 1))


if __name__ == "__main__":
    unittest.main()
