# SPDX-License-Identifier: Apache-2.0
import copy
import hashlib
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from intake import assess_extraction, compile_extraction, digest


def fixture():
    texts = {
        "consumer": (
            "consumer.py",
            "from provider.api import work as execute\ndef mission():\n    return execute(3, flag=True)\ndef outside():\n    return execute(4)\n",
        ),
        "before": ("provider/api.py", "def work(x, flag=False):\n    return x\n"),
        "after": ("provider/api.py", "def work(x):\n    return x\n"),
    }
    sources = {
        k: {
            "repository": "test-fixture/structural-input",
            "commit": "0" * 40,
            "path": p,
            "text": s,
            "sha256": hashlib.sha256(s.encode()).hexdigest(),
        }
        for k, (p, s) in texts.items()
    }
    raw = {
        "schema": "alpha-transfer-raw-task/v1",
        "id": "synthetic-control",
        "title": "Synthetic development control",
        "purpose": "Synthetic development fixture; no public production source or customer.",
        "dependency": {
            "package": "provider",
            "importRoots": ["provider"],
            "before": {"version": "1"},
            "after": {"version": "2"},
        },
        "consumer": {"source": "consumer", "scopeSymbols": ["mission"]},
        "sources": sources,
        "providerSides": {"before": ["before"], "after": ["after"]},
        "licenseRecords": [],
    }
    ex = {
        "schema": "alpha-transfer-extraction/v1",
        "inputSha256": digest(raw),
        "claims": [
            {
                "line": 3,
                "column": 11,
                "callee": "execute",
                "before": {"source": "before", "symbol": "work"},
                "after": {"source": "after", "symbol": "work"},
                "explanation": "Direct imported alias in synthetic fixture.",
            }
        ],
        "unresolved": [],
        "provenance": {"mode": "synthetic-development"},
    }
    return raw, ex


class Controls(unittest.TestCase):
    def test_exact_conflict(self):
        r, e = fixture()
        out = assess_extraction(r, e)
        self.assertEqual(out["nextAction"], "HOLD_UPDATE_AND_TEST")
        self.assertEqual(out["coreRecord"]["calls"][0]["status"], "BINDING_CONFLICT")
        self.assertIsNone(out["completeScopeAccepted"])

    def test_wrong_identity(self):
        r, e = fixture()
        e["inputSha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "exact raw"):
            compile_extraction(r, e)

    def test_changed_source(self):
        r, e = fixture()
        r["sources"]["consumer"]["text"] += "\n"
        with self.assertRaisesRegex(ValueError, "identity"):
            compile_extraction(r, e)

    def test_hallucinated_line(self):
        r, e = fixture()
        e["claims"][0]["line"] = 99
        with self.assertRaisesRegex(ValueError, "not present"):
            compile_extraction(r, e)

    def test_outside_scope(self):
        r, e = fixture()
        e["claims"][0]["line"] = 5
        with self.assertRaisesRegex(ValueError, "not present"):
            compile_extraction(r, e)

    def test_hallucinated_target(self):
        r, e = fixture()
        e["claims"][0]["after"]["symbol"] = "invented"
        with self.assertRaisesRegex(ValueError, "absent"):
            compile_extraction(r, e)

    def test_wrong_side(self):
        r, e = fixture()
        e["claims"][0]["after"]["source"] = "before"
        with self.assertRaisesRegex(ValueError, "provider side"):
            compile_extraction(r, e)

    def test_duplicate_call(self):
        r, e = fixture()
        e["claims"].append(copy.deepcopy(e["claims"][0]))
        with self.assertRaisesRegex(ValueError, "duplicate"):
            compile_extraction(r, e)

    def test_explicit_unresolved(self):
        r, e = fixture()
        e["unresolved"] = [{k: v for k, v in e["claims"][0].items() if k in ["line", "column", "callee"]}]
        e["unresolved"][0]["reason"] = "Synthetic missing export evidence"
        e["claims"] = []
        out = assess_extraction(r, e)
        self.assertEqual(out["nextAction"], "REVIEW_UNRESOLVED_SCOPE")
        self.assertIsNone(out["coreRecord"])
        self.assertIsNone(out["completeScopeAccepted"])

    def test_nested_call_location(self):
        r, e = fixture()
        text = "from provider.api import work\nclass Child:\n    def mission(self):\n        super().__init__(3)\n"
        r["sources"]["consumer"]["text"] = text
        r["sources"]["consumer"]["sha256"] = hashlib.sha256(text.encode()).hexdigest()
        r["consumer"]["scopeSymbols"] = ["Child.mission"]
        e["inputSha256"] = digest(r)
        e["claims"] = []
        e["unresolved"] = [
            {"line": 4, "column": 8, "callee": "super().__init__", "reason": "Synthetic missing class identity"}
        ]
        out = assess_extraction(r, e)
        self.assertEqual(out["unresolvedIntake"][0]["callee"], "super().__init__")


if __name__ == "__main__":
    unittest.main()
