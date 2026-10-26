# SPDX-License-Identifier: Apache-2.0
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from consumer import assess_consumers
from dossier import compare_sources


def assess(source, old="def get(url, *, timeout=None): pass\n", new="def get(url): pass\n", extra=None):
    before = {"pkg/api.py": old, "pkg/__init__.py": "from .api import get\n"}
    after = {"pkg/api.py": new, "pkg/__init__.py": "from .api import get\n"}
    if extra:
        before.update(extra)
        after.update(extra)
    reports = [compare_sources(before[path], after[path], path) for path in before]
    return assess_consumers([{"path": "consumer.py", "source": source}], before, after, reports)


class ConsumerTests(unittest.TestCase):
    def test_explicit_reexport_alias_changed_actual_call(self):
        result = assess("from pkg import get as fetch\nfetch('url', timeout=3)\n")
        row = result["findings"][0]
        self.assertEqual(row["before_accepts"], True)
        self.assertEqual(row["after_accepts"], False)
        self.assertEqual(row["before"]["target"]["module"], "pkg.api")
        self.assertEqual(row["snippet"], "fetch('url', timeout=3)")
        self.assertEqual(row["line"], 2)

    def test_module_import_and_local_import(self):
        result = assess("import pkg\ndef run():\n from pkg.api import get as local\n local('u', timeout=1)\n pkg.get('u')\n")
        self.assertEqual(result["coverage"]["potential_break"], 1)
        self.assertEqual(result["coverage"]["preserved_binding"], 1)

    def test_explicit_submodule_import(self):
        result = assess("import pkg.api\npkg.api.get('u', timeout=1)\n")
        self.assertEqual(result["coverage"]["potential_break"], 1)
        missing = assess("import pkg\npkg.api.get('u', timeout=1)\n")
        self.assertEqual(missing["coverage"]["potential_break"], 0)
        self.assertEqual(missing["coverage"]["unresolved"], 1)

    def test_constructor_and_single_base_super(self):
        before = {"pkg/client.py": "class Client:\n def __init__(self, *, app=None): pass\n", "pkg/__init__.py": "from .client import Client\n"}
        after = {"pkg/client.py": "class Client:\n def __init__(self): pass\n", "pkg/__init__.py": "from .client import Client\n"}
        reports = [compare_sources(before[p], after[p], p) for p in before]
        source = "import pkg\npkg.Client(app=1)\nclass TestClient(pkg.Client):\n def __init__(self):\n  super().__init__(app=self.app)\n"
        result = assess_consumers([{"path": "use.py", "source": source}], before, after, reports)
        self.assertEqual(result["coverage"]["potential_break"], 2)
        self.assertTrue(all(r["before"]["target"]["implicit_receiver"] == 1 for r in result["findings"]))
        self.assertEqual(result["findings"][1]["before"]["target"]["name"], "Client.__init__")

    def test_missing_or_wildcard_exports_do_not_guess(self):
        for init in ("", "from .api import *\n__all__ = ['get']\n"):
            result = assess("import pkg\npkg.get('u', timeout=1)\n", extra={"pkg/__init__.py": init})
            self.assertEqual(result["coverage"]["potential_break"], 0)
            self.assertEqual(result["coverage"]["unresolved"], 1)

    def test_shadowing_conditional_import_and_preimport(self):
        cases = ["from pkg import get\ndef run(get):\n get('u', timeout=1)\n",
                 "from pkg import get\nget = other\nget('u', timeout=1)\n",
                 "if True:\n from pkg import get\nget('u', timeout=1)\n",
                 "def run():\n get('u', timeout=1)\n from pkg import get\n",
                 "from pkg import get\ndef run():\n get('u', timeout=1)\n get = other\n"]
        for source in cases:
            result = assess(source)
            self.assertEqual(result["coverage"]["potential_break"], 0)
            self.assertEqual(result["coverage"]["unresolved"], 1)

    def test_literal_and_dynamic_expansions(self):
        result = assess("from pkg import get\nget(*['u'], **{'timeout': 2})\nget(*args, timeout=2)\nget('u', **kwargs)\nget('u', timeout=2, **{'timeout':3})\n")
        self.assertEqual(result["coverage"]["potential_break"], 1)
        self.assertEqual(result["coverage"]["unresolved"], 3)

    def test_relative_chain_and_no_source_execution(self):
        extra = {"pkg/__init__.py": "from .bridge import get\n", "pkg/bridge.py": "from .api import get\nraise RuntimeError('must never execute')\n"}
        result = assess("from pkg import get\nget('u', timeout=1)\nraise RuntimeError('consumer must never execute')\n", extra=extra)
        self.assertEqual(result["coverage"]["potential_break"], 1)
        self.assertFalse(result["meter"]["source_execution"])

    def test_source_mismatch_rejected(self):
        before, after = {"pkg/api.py": "def get(url, timeout=None): pass\n"}, {"pkg/api.py": "def get(url): pass\n"}
        report = compare_sources(before["pkg/api.py"], after["pkg/api.py"], "pkg.api")
        report["source_ids"][0] = "bad"
        result = assess_consumers([{"path": "use.py", "source": "from pkg.api import get\nget('u', timeout=1)\n"}], before, after, [report])
        self.assertEqual(result["coverage"]["potential_break"], 0)
        self.assertEqual(len(result["producer_errors"]["reports"]), 1)

    def test_before_invalid_call_is_not_new_break(self):
        result = assess("from pkg import get\nget(timeout=1)\n")
        self.assertEqual(result["calls"][0]["status"], "unresolved")
        self.assertFalse(result["calls"][0]["before_accepts"])

    def test_comprehension_parameter_does_not_resolve_as_import(self):
        result = assess("from pkg import get\n[get('u', timeout=1) for get in functions]\n")
        self.assertEqual(result["coverage"]["potential_break"], 0)
        self.assertEqual(result["coverage"]["unresolved"], 1)

    def test_reexport_relocation_is_not_old_target_comparison(self):
        before = {"pkg/__init__.py": "from .a import get\n", "pkg/a.py": "def get(url, timeout=None): pass\n", "pkg/b.py": "def get(url, timeout=None): pass\n"}
        after = {"pkg/__init__.py": "from .b import get\n", "pkg/a.py": "def get(url): pass\n", "pkg/b.py": "def get(url, timeout=None): pass\n"}
        reports = [compare_sources(before[p], after[p], p) for p in before]
        result = assess_consumers([{"path": "use.py", "source": "from pkg import get\nget('u', timeout=1)\n"}], before, after, reports)
        self.assertEqual(result["calls"][0]["status"], "preserved_binding")
        self.assertEqual(result["calls"][0]["after"]["target"]["module"], "pkg.b")

    def test_closed_literal_wildcard_is_separate_candidate(self):
        old = "__all__ = ['get']\ndef get(url, timeout=None): pass\n"
        new = "__all__ = ['get']\ndef get(url): pass\n"
        result = assess("import pkg\npkg.get('u', timeout=1)\n", old, new, {"pkg/__init__.py": "from .api import *\n__all__ = ['get']\n"})
        self.assertEqual(result["coverage"]["potential_break"], 0)
        self.assertEqual(result["coverage"]["unresolved"], 1)
        self.assertEqual(len(result["syntactic_candidate_findings"]), 1)
        self.assertIn("runtime-unproved", result["syntactic_candidate_findings"][0]["qualification"])

    def test_wildcard_collision_and_missing_source_remain_unresolved(self):
        old = "__all__ = ['get']\ndef get(url, timeout=None): pass\n"
        new = "__all__ = ['get']\ndef get(url): pass\n"
        for extra in ({"pkg/__init__.py": "from .api import *\nfrom .missing import *\n__all__=['get']\n"},
                      {"pkg/__init__.py": "from .api import *\nfrom .other import *\n__all__=['get']\n", "pkg/other.py": "__all__=['get']\ndef get(*args, **kwargs):pass\n"}):
            result = assess("import pkg\npkg.get('u', timeout=1)\n", old, new, extra)
            self.assertEqual(result["syntactic_candidate_findings"], [])

    def test_guarded_import_candidate_requires_raise_on_every_handler(self):
        for ending, expected in (("raise RuntimeError('missing')", 1), ("pass", 0)):
            source = "try:\n import pkg\nexcept ImportError:\n " + ending + "\npkg.get('u', timeout=1)\n"
            result = assess(source)
            self.assertEqual(result["coverage"]["potential_break"], 0)
            self.assertEqual(len(result["syntactic_candidate_findings"]), expected)

    def test_class_local_import_is_not_method_lambda_or_comprehension_global(self):
        source = "class Consumer:\n from pkg import get\n def run(self):\n  get('u', timeout=1)\n func = lambda: get('u', timeout=1)\n results = [get('u', timeout=1) for x in values]\n"
        result = assess(source)
        self.assertEqual(result["coverage"]["potential_break"], 0)
        self.assertEqual(result["coverage"]["unresolved"], 3)

    def test_annotations_and_lambda_defaults_are_counted_as_source_sites(self):
        source = "from pkg import get\ndef f(x: get('u', timeout=1)): pass\ng = lambda x=get('u', timeout=1): x\n"
        result = assess(source)
        self.assertEqual(result["coverage"]["inspected_calls"], 2)
        self.assertEqual(result["coverage"]["potential_break"], 2)

    def test_export_list_mutations_and_aliases_are_not_closed(self):
        for suffix in ("__all__.append('extra')\n", "alias=__all__\n", "del __all__[0]\n"):
            old = "__all__=['get']\ndef get(url, timeout=None): pass\n" + suffix
            new = "__all__=['get']\ndef get(url): pass\n" + suffix
            result = assess("import pkg\npkg.get('u', timeout=1)\n", old, new, {"pkg/__init__.py": "from .api import *\n__all__=['get']\n"})
            self.assertEqual(result["syntactic_candidate_findings"], [])

    def test_src_package_paths_are_normalized(self):
        before = {"src/pkg/api.py": "def get(url, timeout=None): pass\n", "src/pkg/__init__.py": "from .api import get\n"}
        after = {"src/pkg/api.py": "def get(url): pass\n", "src/pkg/__init__.py": "from .api import get\n"}
        reports = [compare_sources(before[p], after[p], p) for p in before]
        result = assess_consumers([{"path": "use.py", "source": "import pkg\npkg.get('u', timeout=1)\n"}], before, after, reports)
        self.assertEqual(result["coverage"]["potential_break"], 1)

    def test_scope_triage_separates_dependency_references_from_other_calls(self):
        result = assess("import pkg\nimport unrelated\npkg.get('u', timeout=1)\nunrelated.run()\nlocal()\n")
        self.assertEqual(result["coverage"]["scope_triage"], {"dependency-import-reference": 1, "other-import-reference": 1, "unattributed-call": 1})


if __name__ == "__main__":
    unittest.main()
