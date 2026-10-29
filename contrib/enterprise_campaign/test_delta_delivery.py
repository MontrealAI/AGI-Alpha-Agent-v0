# SPDX-License-Identifier: Apache-2.0
"""Executable acceptance, negative controls, and engineering regression cases."""
from __future__ import annotations

import copy
import csv
import io
import json
import random
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from contrib.enterprise_campaign import catalog_product as native
from contrib.enterprise_campaign.delta_acceptance import conventional_delta, verify_delta
from contrib.enterprise_campaign.delta_delivery import _digest, assert_upstream_identity, build_delta, make_request

ROOT = Path(__file__).resolve().parents[2]
BEFORE = "sku,name,price,note\r\nA,Alpha,10.00,local-a\r\nB,Beta,20.00,local-b\r\nC,Gamma,30.00,local-c\r\n"
DELTA = "sku,price\nA,12.50\n"


def emit(headers: list[str], rows: list[list[str]]) -> str:
    out = io.StringIO(newline="")
    writer = csv.writer(out, lineterminator="\n")
    writer.writerows([headers, *rows])
    return out.getvalue()


class DeltaTests(unittest.TestCase):
    def setUp(self) -> None:
        self.request = make_request(["sku"], ["price"], ["price"])

    def test_upstream_exact_source(self) -> None:
        assert_upstream_identity()

    def test_sparse_updates_preserve_other_rows(self) -> None:
        package = build_delta(BEFORE, DELTA, self.request)
        self.assertEqual(package["native_package"]["trace"]["after_rows"], 3)
        self.assertEqual(verify_delta(BEFORE, DELTA, package, self.request)["verdict"], "PASS_IN_SCOPE")
        self.assertIn("B,Beta,20.00,local-b", package["native_package"]["output_csv"])

    def test_exact_rollback(self) -> None:
        p = build_delta(BEFORE, DELTA, self.request)["native_package"]
        changed = native.apply_patch(BEFORE, p, authorized=True)
        self.assertEqual(native.rollback(changed, p, authorized=True), BEFORE)

    def test_source_not_implicitly_authorized(self) -> None:
        p = build_delta(BEFORE, DELTA, self.request)["native_package"]
        with self.assertRaises(PermissionError):
            native.apply_patch(BEFORE, p)
        with self.assertRaises(PermissionError):
            native.rollback(p["output_csv"], p)

    def test_protected_column_refused(self) -> None:
        with self.assertRaises(ValueError):
            build_delta(BEFORE, "sku,price,note\nA,12.50,replace-local-note\n", self.request)

    def test_insert_refused(self) -> None:
        with self.assertRaises(ValueError):
            build_delta(BEFORE, "sku,price\nNEW,12.50\n", self.request)

    def test_duplicate_delta_refused(self) -> None:
        with self.assertRaises(ValueError):
            build_delta(BEFORE, "sku,price\nA,12\nA,13\n", self.request)

    def test_duplicate_source_refused(self) -> None:
        with self.assertRaises(ValueError):
            build_delta(BEFORE + "A,Duplicate,12,x\r\n", DELTA, self.request)

    def test_equivalent_decimal_format_retained(self) -> None:
        p = build_delta(BEFORE, "sku,price\nA,10.000\n", self.request)["native_package"]
        self.assertEqual(p["changes"], [])
        self.assertIn("10.00", p["output_csv"])

    def test_nonfinite_and_invalid_numbers_refused(self) -> None:
        for number in ("NaN", "Infinity", "-Infinity", "", "twelve"):
            with self.subTest(number=number), self.assertRaises(ValueError):
                build_delta(BEFORE, f"sku,price\nA,{number}\n", self.request)

    def test_composite_identifiers(self) -> None:
        req = make_request(["warehouse", "sku"], ["quantity"], ["quantity"])
        before = "warehouse,sku,quantity,note\nE,A,1,one\nW,A,2,two\n"
        delta = "sku,warehouse,quantity\nA,W,7\n"
        p = build_delta(before, delta, req)
        self.assertEqual(verify_delta(before, delta, p, req)["verdict"], "PASS_IN_SCOPE")
        self.assertIn("E,A,1,one", p["native_package"]["output_csv"])

    def test_explicit_aliases(self) -> None:
        req = make_request(["sku"], ["price"], ["price"], {"code": "sku", "cost": "price"})
        delta = "cost,code\n14.25,B\n"
        p = build_delta(BEFORE, delta, req)
        self.assertEqual(verify_delta(BEFORE, delta, p, req)["verdict"], "PASS_IN_SCOPE")

    def test_alias_collisions_and_unused_alias_refused(self) -> None:
        cases = [("sku,code,price\nA,A,12\n", {"code": "sku"}),
                 (DELTA, {"nonexistent": "sku"})]
        for delta, aliases in cases:
            with self.subTest(aliases=aliases), self.assertRaises(ValueError):
                build_delta(BEFORE, delta, make_request(["sku"], ["price"], ["price"], aliases))

    def test_no_key_mutation(self) -> None:
        with self.assertRaises(ValueError):
            make_request(["sku"], ["sku"])

    def test_blank_and_nonunique_key_refused(self) -> None:
        for delta in ("sku,price\n,12\n", "sku,sku,price\nA,A,12\n"):
            with self.subTest(delta=delta), self.assertRaises(ValueError):
                build_delta(BEFORE, delta, self.request)

    def test_malformed_and_oversized_refused(self) -> None:
        for delta in ('sku,price\nA,"12\n', "sku,price\nA,12,extra\n", "x" * 200001,
                      "sku,price\nA,12\x00\n"):
            with self.subTest(length=len(delta)), self.assertRaises(ValueError):
                build_delta(BEFORE, delta, self.request)

    def test_wrong_full_snapshot_is_not_delta(self) -> None:
        partial = "sku,name,price,note\nA,Alpha,12.50,local-a\n"
        old = native.reconcile(BEFORE, partial, ["sku"], 3, decimal_columns=["price"], update_fields=["price"])
        self.assertEqual(old["trace"]["after_rows"], 1)
        p = build_delta(BEFORE, DELTA, self.request)
        p["native_package"] = old
        p["digest"] = _digest({k: v for k, v in p.items() if k != "digest"})
        self.assertEqual(verify_delta(BEFORE, DELTA, p, self.request)["verdict"], "REJECTED")

    def test_rehashed_tamper_is_rejected(self) -> None:
        p = build_delta(BEFORE, DELTA, self.request)
        p["native_package"]["output_csv"] = p["native_package"]["output_csv"].replace("local-b", "corrupted")
        p["native_package"]["output_sha256"] = native.digest(p["native_package"]["output_csv"])
        p["digest"] = _digest({k: v for k, v in p.items() if k != "digest"})
        self.assertEqual(verify_delta(BEFORE, DELTA, p, self.request)["verdict"], "REJECTED")

    def test_stale_sources_and_feed_refused(self) -> None:
        p = build_delta(BEFORE, DELTA, self.request)
        self.assertEqual(verify_delta(BEFORE.replace("10.00", "9.00"), DELTA, p, self.request)["verdict"], "REJECTED")
        self.assertEqual(verify_delta(BEFORE, DELTA.replace("12.50", "1.00"), p, self.request)["verdict"], "REJECTED")
        with self.assertRaises(ValueError):
            native.apply_patch(BEFORE + "\n", p["native_package"], authorized=True)

    def test_no_rows_is_explicit_noop(self) -> None:
        p = build_delta(BEFORE, "sku,price\n", self.request)
        self.assertEqual(p["native_package"]["changes"], [])

    def test_unicode_quotes_newlines_and_formula_preview(self) -> None:
        before = emit(["sku", "name"], [["A", 'é, "quoted"\nline'], ["B", "keep"]])
        delta = emit(["sku", "name"], [["A", "=1+1"]])
        req = make_request(["sku"], ["name"])
        p = build_delta(before, delta, req)
        self.assertEqual(verify_delta(before, delta, p, req)["verdict"], "PASS_IN_SCOPE")
        self.assertIn("'=1+1", p["native_package"]["safe_preview_csv"])
        self.assertIn("=1+1", p["native_package"]["output_csv"])

    def test_mode_cannot_change_silently(self) -> None:
        req = copy.deepcopy(self.request)
        req["membership"] = "delete_missing"
        with self.assertRaises(ValueError):
            build_delta(BEFORE, DELTA, req)

    def test_checker_rejects_changed_contract(self) -> None:
        p = build_delta(BEFORE, DELTA, self.request)
        altered = copy.deepcopy(self.request)
        altered["membership"] = "delete_missing"
        p["request"] = altered
        p["digest"] = _digest({k: v for k, v in p.items() if k != "digest"})
        self.assertEqual(verify_delta(BEFORE, DELTA, p, altered)["verdict"], "REJECTED")

    def test_bom(self) -> None:
        p = build_delta("\ufeff" + BEFORE, "\ufeff" + DELTA, self.request)
        self.assertEqual(verify_delta("\ufeff" + BEFORE, "\ufeff" + DELTA, p, self.request)["verdict"], "PASS_IN_SCOPE")

    def test_64_generated_development_cases(self) -> None:
        evidence = []
        for seed in range(64):
            with self.subTest(seed=seed):
                rng = random.Random(seed)
                size = rng.randint(4, 80)
                rows = [[f"K{i}", f"item-{i}-é", f"{rng.randint(1,999)}.00", f"local-{i}"] for i in range(size)]
                selected = rng.sample(range(size), rng.randint(1, size - 1))
                feed = [[rows[i][0], f"{rng.randint(1000,1999)}.25"] for i in selected]
                before = emit(["sku", "name", "price", "note"], rows)
                delta = emit(["sku", "price"], feed)
                p = build_delta(before, delta, self.request)
                expected = conventional_delta(before, delta, self.request)
                verdict = verify_delta(before, delta, p, self.request)
                self.assertEqual(verdict["verdict"], "PASS_IN_SCOPE")
                self.assertEqual(p["native_package"]["output_csv"], expected)
                self.assertEqual(native.rollback(expected, p["native_package"], authorized=True), before)
                self.assertEqual(len(p["native_package"]["changes"]), len(selected))
                evidence.append({"seed": seed, "rows": size, "updates": len(selected), "before": before,
                                 "delta": delta, "request": self.request, "candidate": p,
                                 "conventional_output": expected, "acceptance": verdict})
        self.assertEqual(len(evidence), 64)

    def test_cli_delivers_and_refuses_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            before, delta, out = Path(temp) / "before.csv", Path(temp) / "delta.csv", Path(temp) / "out"
            before.write_bytes(BEFORE.encode())
            delta.write_text(DELTA)
            command = [sys.executable, "-m", "contrib.enterprise_campaign.delta_delivery", "--before", str(before),
                       "--delta", str(delta), "--keys", "sku", "--write-fields", "price", "--decimal-fields", "price",
                       "--output", str(out)]
            first = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=20)
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual((out / "rollback.csv").read_bytes(), BEFORE.encode())
            self.assertEqual(before.read_bytes(), BEFORE.encode())
            second = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=20)
            self.assertEqual(second.returncode, 2)
            self.assertIn("previous evidence is never overwritten", second.stderr)


if __name__ == "__main__":
    unittest.main()
