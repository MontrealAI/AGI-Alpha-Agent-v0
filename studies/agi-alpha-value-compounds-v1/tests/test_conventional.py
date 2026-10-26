# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import copy
import inspect
from pathlib import Path
import random
import tempfile
import unittest

from conventional import clear_cache, compare_sources
from validate_dossier import validate_dossier


class ConventionalDevelopmentTests(unittest.TestCase):
    def setUp(self) -> None:
        clear_cache()

    def check(self, before: str, after: str, expected: str, name: str = "f") -> dict:
        report = compare_sources(before, after, "development")
        actual = {row["name"]: row for row in report["functions"]}
        self.assertEqual(actual[name]["status"], expected, report)
        verdict = validate_dossier(before, after, "development", report)
        self.assertTrue(verdict["accepted"], verdict)
        return report

    def test_optional_becomes_required(self) -> None:
        self.check("def f(a=1): pass", "def f(a): pass", "call_loss")

    def test_keyword_rename(self) -> None:
        self.check("def f(a): pass", "def f(b): pass", "call_loss")

    def test_positional_to_keyword_only(self) -> None:
        self.check("def f(a): pass", "def f(*,a): pass", "call_loss")

    def test_keyword_to_positional_only(self) -> None:
        self.check("def f(a): pass", "def f(a,/): pass", "call_loss")

    def test_variadic_removed(self) -> None:
        self.check("def f(*args,**kwargs): pass", "def f(a=1): pass", "call_loss")

    def test_positional_only_name_enters_kwargs(self) -> None:
        report = self.check("def f(a,/,**kwargs): pass", "def f(a,**kwargs): pass", "call_loss")
        row = report["functions"][0]
        self.assertEqual(row["witness"], {"positional_count": 1, "keyword_names": ["a"]})

    def test_optional_positional_only_keyword_is_not_binding(self) -> None:
        self.check("def f(a=1,/,**kwargs): pass", "def f(b=1,/,**kwargs): pass", "no_call_loss")

    def test_permitted_expansion(self) -> None:
        self.check("def f(a,/): pass", "def f(a=1,*args,**kwargs): pass", "no_call_loss")

    def test_new_optional_keyword(self) -> None:
        self.check("def f(a): pass", "def f(a,*,b=1): pass", "no_call_loss")

    def test_removed_definition(self) -> None:
        self.check("def f(a): pass", "", "call_loss")

    def test_added_definition(self) -> None:
        self.check("", "def f(a): pass", "added")

    def test_decorated_definition(self) -> None:
        self.check("@deco\ndef f(a): pass", "def f(a): pass", "unresolved")

    def test_duplicate_definition(self) -> None:
        self.check("def f(a): pass\ndef f(b): pass", "def f(a): pass", "unresolved")

    def test_assigned_definition(self) -> None:
        self.check("def f(a): pass\nf = replacement", "def f(a): pass", "unresolved")

    def test_reimported_definition(self) -> None:
        self.check("def f(a): pass\nfrom elsewhere import f", "def f(a): pass", "unresolved")

    def test_conditional_redefinition(self) -> None:
        self.check("def f(a): pass\nif flag:\n def f(b): pass", "def f(a): pass", "unresolved")

    def test_conditional_only_after(self) -> None:
        self.check("def f(a): pass", "if flag:\n def f(a): pass", "unresolved")

    def test_dynamic_module(self) -> None:
        self.check("def f(a): pass\nglobals().update({})", "def f(a): pass", "unresolved")

    def test_dynamic_function_body_not_executed(self) -> None:
        self.check("def f(a=1):\n globals().update({})", "def f(a): pass", "call_loss")

    def test_unrelated_lambda_body(self) -> None:
        self.check("g=lambda: globals()\ndef f(a=1): pass", "def f(a): pass", "call_loss")

    def test_star_import(self) -> None:
        self.check("from x import *\ndef f(a): pass", "def f(a): pass", "unresolved")

    def test_removed_to_alias(self) -> None:
        self.check("def f(a): pass", "from somewhere import f", "unresolved")

    def test_default_expression_and_body_are_inert(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            marker = Path(directory) / "must-not-exist"
            expression = "__import__('pathlib').Path(" + repr(str(marker)) + ").write_text('unsafe')"
            self.check("def f(a=" + expression + "):\n raise RuntimeError('must not run')", "def f(a): pass", "call_loss")
            self.assertFalse(marker.exists())

    def test_griffe_broader_alerts_are_retained(self) -> None:
        report = self.check("def f(a=1): pass", "def f(a=2): pass", "no_call_loss")
        self.assertEqual(report["griffe_status"], "complete")
        self.assertTrue(any("default" in alert["kind"].lower() for alert in report["griffe_alerts"]))
        self.assertIn("members", report["griffe"]["snapshots"]["before"])

    def test_exact_content_reuse_and_mutation_isolation(self) -> None:
        before, after = "def f(a=1): pass", "def f(a): pass"
        report = self.check(before, after, "call_loss")
        self.assertEqual(report["meter"]["capture_cache_misses"], 2)
        report["griffe"]["snapshots"]["before"]["members"].clear()
        second = self.check(before, after, "call_loss")
        self.assertEqual(second["meter"]["capture_cache_hits"], 2)
        self.assertIn("f", second["griffe"]["snapshots"]["before"]["members"])

    def test_changed_source_invalidates_reuse(self) -> None:
        compare_sources("def f(a=1): pass", "def f(a): pass", "development")
        report = compare_sources("def f(a): pass", "def f(a,b): pass", "development")
        self.assertEqual(report["meter"]["capture_cache_hits"], 1)
        self.assertEqual(report["meter"]["capture_cache_misses"], 1)

    def test_tampered_witness_refused(self) -> None:
        before, after = "def f(a=1): pass", "def f(a): pass"
        report = self.check(before, after, "call_loss")
        report["functions"][0]["witness"] = {"positional_count": 1, "keyword_names": []}
        self.assertFalse(validate_dossier(before, after, "development", report)["accepted"])

    def test_omitted_result_refused(self) -> None:
        before, after = "def f(a=1): pass", "def f(a): pass"
        report = self.check(before, after, "call_loss")
        report["functions"].clear()
        self.assertFalse(validate_dossier(before, after, "development", report)["accepted"])

    def test_tampered_source_refused(self) -> None:
        before, after = "def f(a=1): pass", "def f(a): pass"
        report = self.check(before, after, "call_loss")
        report["source_hashes"]["before"] = "0" * 64
        self.assertFalse(validate_dossier(before, after, "development", report)["accepted"])

    def test_consumer_signature_metadata(self) -> None:
        report = self.check("def f(a,/,b=1,*args,c,**kwargs): pass", "def f(a,/,b=1,*args,c,d,**kwargs): pass", "call_loss")
        signature = report["functions"][0]["before_signature"]
        self.assertEqual([p["kind"] for p in signature["parameters"]], ["posonly", "poskw", "varpos", "kwonly", "varkw"])
        self.assertEqual(report["source_ids"], [report["source_hashes"]["before"], report["source_hashes"]["after"]])

    def test_tampered_consumer_metadata_refused(self) -> None:
        before, after = "def f(a=1): pass", "def f(a): pass"
        report = self.check(before, after, "call_loss")
        report["functions"][0]["before_signature"]["parameters"][0]["required"] = True
        self.assertFalse(validate_dossier(before, after, "development", report)["accepted"])

    def test_constructor_required_addition(self) -> None:
        self.check("class Client:\n def __init__(self,app=None): pass", "class Client:\n def __init__(self): pass", "call_loss", "Client.__init__")

    def test_constructor_one_base(self) -> None:
        self.check("class Client(Base):\n def __init__(self,a=1): pass", "class Client(Base):\n def __init__(self,a): pass", "call_loss", "Client.__init__")

    def test_constructor_decorated_class(self) -> None:
        self.check("@wrap\nclass Client:\n def __init__(self,a=1): pass", "class Client:\n def __init__(self,a): pass", "unresolved", "Client.__init__")

    def test_constructor_decorated_method(self) -> None:
        self.check("class Client:\n @wrap\n def __init__(self,a=1): pass", "class Client:\n def __init__(self,a): pass", "unresolved", "Client.__init__")

    def test_constructor_metaclass(self) -> None:
        self.check("class Client(metaclass=Meta):\n def __init__(self,a=1): pass", "class Client:\n def __init__(self,a): pass", "unresolved", "Client.__init__")

    def test_constructor_multiple_bases(self) -> None:
        self.check("class Client(A,B):\n def __init__(self,a=1): pass", "class Client:\n def __init__(self,a): pass", "unresolved", "Client.__init__")

    def test_constructor_inherited_unknown(self) -> None:
        self.check("class Client:\n def __init__(self,a=1): pass", "class Client(Base): pass", "unresolved", "Client.__init__")

    def test_constructor_class_removed(self) -> None:
        self.check("class Client:\n def __init__(self,a=1): pass", "", "call_loss", "Client.__init__")

    def test_constructor_class_rebound(self) -> None:
        self.check("class Client:\n def __init__(self,a=1): pass\nClient=replacement", "class Client:\n def __init__(self,a): pass", "unresolved", "Client.__init__")

    def test_constructor_method_rebound(self) -> None:
        self.check("class Client:\n def __init__(self,a=1): pass\n __init__=replacement", "class Client:\n def __init__(self,a): pass", "unresolved", "Client.__init__")

    def test_constructor_conditional_method(self) -> None:
        self.check("class Client:\n def __init__(self,a=1): pass\n if flag:\n  def __init__(self,b): pass", "class Client:\n def __init__(self,a): pass", "unresolved", "Client.__init__")

    def test_constructor_async_unknown(self) -> None:
        self.check("class Client:\n def __init__(self,a=1): pass", "class Client:\n async def __init__(self,a): pass", "unresolved", "Client.__init__")

    def test_constructor_loop_binding_unknown(self) -> None:
        self.check("class Client:\n def __init__(self,a=1): pass\n for __init__ in replacements: pass", "class Client:\n def __init__(self,a): pass", "unresolved", "Client.__init__")

    def test_constructor_pattern_binding_unknown(self) -> None:
        self.check("class Client:\n def __init__(self,a=1): pass\n match candidate:\n  case {'replacement': __init__}: pass", "class Client:\n def __init__(self,a): pass", "unresolved", "Client.__init__")

    def test_malformed_findings_rejected(self) -> None:
        before, after = "def f(a=1): pass", "def f(a): pass"
        report = self.check(before, after, "call_loss")
        report["findings"] = [{"name": [], "status": "call_loss"}]
        self.assertFalse(validate_dossier(before, after, "development", report)["accepted"])

    def test_large_domain_exact_frontier_fallback(self) -> None:
        before = "def f(" + ",".join("p" + str(i) + "=None" for i in range(24)) + "): pass"
        after = before.replace("): pass", ",*,extra=None): pass")
        report = self.check(before, after, "no_call_loss")
        verdict = validate_dossier(before, after, "development", report)
        self.assertIn("frontier", verdict["checks"][0]["independent_method"])
        self.assertTrue(verdict["scope_complete"])

    def test_exhaustive_budget_unknown_is_not_pass(self) -> None:
        before, after = "def f(a=1): pass", "def f(a=1,*,extra=None): pass"
        report = self.check(before, after, "no_call_loss")
        verdict = validate_dossier(before, after, "development", report, shape_budget=1, validation_mode="exhaustive")
        self.assertFalse(verdict["accepted"])
        self.assertTrue(verdict["report_correct"])
        self.assertTrue(verdict["unknowns"])

    def test_source_bound_refusal(self) -> None:
        report = compare_sources("x" * 1_000_001, "def f(): pass", "development")
        self.assertEqual(report["status"], "partial")
        self.assertTrue(validate_dossier("x" * 1_000_001, "def f(): pass", "development", report)["accepted"])

    def test_seeded_finite_signature_crosscheck(self) -> None:
        rng = random.Random(2645)
        signatures = []
        for _ in range(80):
            positional_count = rng.randrange(4)
            positional_only = rng.randrange(positional_count + 1)
            required_count = rng.randrange(positional_count + 1)
            fields = []
            for index in range(positional_count):
                fields.append("abc"[index] + ("=None" if index >= required_count else ""))
                if index + 1 == positional_only:
                    fields.append("/")
            vararg = rng.choice([False, True])
            keyword_count = rng.randrange(3)
            if vararg:
                fields.append("*args")
            elif keyword_count:
                fields.append("*")
            for index in range(keyword_count):
                fields.append("de"[index] + rng.choice(["", "=None"]))
            if rng.choice([False, True]):
                fields.append("**kwargs")
            signatures.append("def f(" + ",".join(fields) + "): pass")
        for _ in range(150):
            before, after = rng.sample(signatures, 2)
            report = compare_sources(before, after, "development")
            verdict = validate_dossier(before, after, "development", report)
            self.assertTrue(verdict["accepted"], {"before": before, "after": after, "verdict": verdict})


if __name__ == "__main__":
    unittest.main()
