import hashlib
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from conventional_v2 import extract


def task(consumer, before, after=None):
    sources = {"consumer": {"path": "service.py", "text": consumer}}
    sides = {}
    for side, mapping in [("before", before), ("after", after if after is not None else before)]:
        sides[side] = []
        for index, (path, text) in enumerate(mapping.items()):
            ident = side[0] + str(index)
            sources[ident] = {"path": path, "text": text}
            sides[side].append(ident)
    for source in sources.values():
        source.update(repository="synthetic/development", commit="1" * 40,
                      sha256=hashlib.sha256(source["text"].encode()).hexdigest())
    return {"schema": "alpha-transfer-raw-task/v1", "id": "c2-development", "title": "Synthetic development",
            "purpose": "Separate comparator construction controls, not primary missions",
            "dependency": {"package": "tinydep", "importRoots": ["tinydep"],
                           "before": {"version": "1"}, "after": {"version": "2"}},
            "consumer": {"source": "consumer", "scopeSymbols": ["run"]},
            "sources": sources, "providerSides": sides, "licenseRecords": []}


class Controls(unittest.TestCase):
    def test_all_exports(self):
        raw = task("from tinydep import operate\ndef run():\n    return operate(2)\n",
                   {"tinydep/__init__.py": "from ._ops import *\n",
                    "tinydep/_ops.py": "__all__ = ['operate']\ndef operate(x): pass\ndef hidden(x): pass\n"})
        result = extract(raw)
        self.assertEqual(result["claims"][0]["before"], {"source": "b1", "symbol": "operate"})

    def test_all_exclusion_is_not_overruled_by_unique_name(self):
        raw = task("from tinydep import hidden\ndef run():\n    return hidden(2)\n",
                   {"tinydep/__init__.py": "from ._ops import *\n",
                    "tinydep/_ops.py": "__all__ = ['operate']\ndef operate(x): pass\ndef hidden(x): pass\n"})
        result = extract(raw)
        self.assertFalse(result["claims"])
        self.assertEqual(len(result["unresolved"]), 1)

    def test_unique_source_conditional_target(self):
        raw = task("from tinydep import operate\ndef run():\n    return operate(2)\n",
                   {"tinydep/_ops.py": "def operate(x): pass\n"})
        result = extract(raw)
        self.assertEqual(result["claims"][0]["before"]["symbol"], "operate")
        self.assertIn("conditional", result["claims"][0]["explanation"])

    def test_ambiguous_two_sources(self):
        raw = task("from tinydep import operate\ndef run():\n    return operate(2)\n",
                   {"tinydep/one.py": "def operate(x): pass\n",
                    "tinydep/two.py": "def operate(x, y=0): pass\n"})
        result = extract(raw)
        self.assertFalse(result["claims"])
        self.assertEqual(len(result["unresolved"]), 1)

    def test_duplicate_definitions(self):
        raw = task("from tinydep import operate\ndef run():\n    return operate(2)\n",
                   {"tinydep/one.py": "def operate(x): pass\ndef operate(x, y=0): pass\n"})
        self.assertFalse(extract(raw)["claims"])

    def test_nested_export_alias(self):
        raw = task("from tinydep import public\ndef run():\n    return public(2)\n",
                   {"tinydep/__init__.py": "from .surface import public\n",
                    "tinydep/surface.py": "from ._ops import operate as public\n",
                    "tinydep/_ops.py": "def operate(x): pass\n"})
        self.assertEqual(extract(raw)["claims"][0]["before"], {"source": "b2", "symbol": "operate"})

    def test_available_import_wins_over_fallback(self):
        consumer = "try:\n    from tinydep import modern as operate\nexcept ImportError:\n    from tinydep import legacy as operate\ndef run():\n    return operate(2)\n"
        mapping = {"tinydep/__init__.py": "from ._ops import *\n",
                   "tinydep/_ops.py": "__all__ = ['modern', 'legacy']\ndef modern(x): pass\ndef legacy(x): pass\n"}
        result = extract(task(consumer, mapping))
        self.assertEqual(result["claims"][0]["before"]["symbol"], "modern")
        self.assertEqual(result["claims"][0]["after"]["symbol"], "modern")

    def test_version_specific_fallback(self):
        consumer = "try:\n    from tinydep import modern as operate\nexcept ImportError:\n    from tinydep import legacy as operate\ndef run():\n    return operate(2)\n"
        before = {"tinydep/__init__.py": "from ._ops import *\n",
                  "tinydep/_ops.py": "__all__ = ['legacy']\ndef legacy(x): pass\n"}
        after = {"tinydep/__init__.py": "from ._ops import *\n",
                 "tinydep/_ops.py": "__all__ = ['modern', 'legacy']\ndef modern(x): pass\ndef legacy(x): pass\n"}
        result = extract(task(consumer, before, after))
        self.assertEqual(result["claims"][0]["before"]["symbol"], "legacy")
        self.assertEqual(result["claims"][0]["after"]["symbol"], "modern")

    def test_unknown_runtime_condition_remains_unresolved(self):
        consumer = "if runtime_flag:\n    from tinydep import modern as operate\nelse:\n    from tinydep import legacy as operate\ndef run():\n    return operate(2)\n"
        mapping = {"tinydep/_ops.py": "def modern(x): pass\ndef legacy(x): pass\n"}
        result = extract(task(consumer, mapping))
        self.assertFalse(result["claims"])
        self.assertEqual(len(result["unresolved"]), 1)

    def test_expansion_and_decorators_remain_unresolved(self):
        raw = task("from tinydep import operate\ndef run(**options):\n    return operate(**options)\n",
                   {"tinydep/_ops.py": "@wrapped\ndef operate(x): pass\n"})
        result = extract(raw)
        self.assertFalse(result["claims"])
        self.assertEqual(len(result["unresolved"]), 1)

    def test_constructor_target_does_not_claim_runtime_proof(self):
        raw = task("from tinydep import Client\ndef run():\n    client = Client()\n    return client.send(2)\n",
                   {"tinydep/_client.py": "class Client:\n    def __init__(self): pass\n    def send(self, x): pass\n"})
        result = extract(raw)
        self.assertEqual([c["before"]["symbol"] for c in result["claims"]], ["Client.__init__", "Client.send"])
        self.assertTrue(all("unproved" in c["explanation"] for c in result["claims"]))


if __name__ == "__main__":
    unittest.main()

