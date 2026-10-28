# SPDX-License-Identifier: Apache-2.0
import copy
import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from typing import Any, cast
from unittest.mock import patch

from contrib.enterprise_campaign.catalog_product import (
    CAPABILITY_GENERATION,
    apply_patch,
    reconcile,
    rollback,
    verify_package,
)
from contrib.enterprise_campaign.catalog_product import _read as read_input


class CatalogProductTests(unittest.TestCase):
    def test_patch_and_exact_rollback(self) -> None:
        before = '\ufeffsku,title,price\r\nA,"Thé, vert",2.00\r\nB,Café,3.50\r\n'
        after = 'sku,title,price\nA,"Thé, vert",2.50\nC,Chocolat,4.00\n'
        package = reconcile(before, after, ["sku"])
        self.assertEqual([item["kind"] for item in package["changes"]], ["update", "delete", "insert"])
        self.assertEqual(package["changes"][0]["fields"], ["price"])
        self.assertTrue(verify_package(package, before))
        output = apply_patch(before, package, authorized=True)
        self.assertEqual(output, after)
        self.assertEqual(rollback(output, package, authorized=True), before)

    def test_stale_sources_and_revoked_authority(self) -> None:
        before = "sku,title\nA,Thé\n"
        package = reconcile(before, "sku,title\nA,Café\n", ["sku"])
        with self.assertRaises(PermissionError):
            apply_patch(before, package)
        with self.assertRaises(PermissionError):
            apply_patch(before, package, authorized=cast(Any, 1))
        with self.assertRaises(ValueError):
            apply_patch(before + "\n", package, authorized=True)
        with self.assertRaises(ValueError):
            rollback("sku,title\nA,Autre\n", package, authorized=True)

    def test_tamper_refusal_even_after_digest_recalculation(self) -> None:
        before = "sku,title\nA,Thé\n"
        package = reconcile(before, "sku,title\nA,Café\n", ["sku"])
        for field, value in [("changes", []), ("output_csv", "sku,title\nA,WRONG\n"), ("generation", 99)]:
            altered = copy.deepcopy(package)
            altered[field] = value
            with self.assertRaises(ValueError):
                verify_package(altered, before)
            payload = {key: item for key, item in altered.items() if key != "proof_digest"}
            raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
            altered["proof_digest"] = hashlib.sha256(raw.encode()).hexdigest()
            with self.assertRaises(ValueError):
                verify_package(altered, before)

    def test_duplicate_and_malformed_inputs_refuse(self) -> None:
        cases = ["sku,title\nA,x\nA,y\n", "sku,sku\nA,B\n", "sku,title\n,x\n", "sku,title\nA\n",
                 'sku,title\nA,x"y\n', 'sku,title\nA,"x"junk\n', 'sku,title\nA,"unclosed\n', "sku,title\nA,x\0\n"]
        for bad in cases:
            with self.subTest(csv=bad), self.assertRaises(ValueError):
                reconcile(bad, "sku,title\nA,x\n", ["sku"])

    def test_formula_text_preserved_and_preview_escaped(self) -> None:
        package = reconcile("sku,title\nA,x\n", "sku,title\nA,=2+2\n", ["sku"])
        self.assertIn("A,=2+2", package["output_csv"])
        self.assertIn("A,'=2+2", package["safe_preview_csv"])
        self.assertEqual(rollback(package["output_csv"], package, authorized=True), "sku,title\nA,x\n")

    def test_bounds_and_future_capabilities_refuse(self) -> None:
        valid = "sku,title\nA,x\n"
        for generation in (-1, CAPABILITY_GENERATION + 1, True, 4):
            with self.subTest(generation=generation), self.assertRaises(ValueError):
                reconcile(valid, valid, ["sku"], generation)
        for bad in ["a,b\n" + "x,y\n" * 1501, "sku,title\nA," + "x" * 4097 + "\n", "x" * 200001]:
            with self.assertRaises(ValueError):
                reconcile(bad, valid, ["sku"])
        with self.assertRaises(ValueError):
            reconcile(valid, valid, ["sku", "title"])

    def test_composite_identity_preserves_distinct_locales(self) -> None:
        before = "sku,locale,title\nA,fr,Thé\nA,en,Tea\n"
        after = "sku,locale,title\nA,en,Black tea\nA,fr,Thé noir\nB,fr,Café\n"
        with self.assertRaises(ValueError):
            reconcile(before, after, ["sku"])
        package = reconcile(before, after, ["sku", "locale"], 1)
        self.assertEqual([change["key"] for change in package["changes"]], [["A", "en"], ["A", "fr"], ["B", "fr"]])
        self.assertEqual(apply_patch(before, package, authorized=True), after)
        self.assertEqual(rollback(after, package, authorized=True), before)
        with self.assertRaises(ValueError):
            reconcile(before, after, ["sku", "sku"], 1)

    def test_decimal_equivalence_and_explicit_aliases(self) -> None:
        before = "sku,locale,price,title\nA,fr,2.00,Thé\nA,en,3.00,Tea\n"
        after = "prix,code,locale,title\n2.0,A,fr,Thé\n3.50,A,en,Black tea\n"
        options = {"decimal_columns": ["price"], "aliases": {"code": "sku", "prix": "price"}}
        with self.assertRaises(ValueError):
            reconcile(before, after, ["sku", "locale"], 1, **cast(Any, options))
        package = reconcile(before, after, ["sku", "locale"], 2, **cast(Any, options))
        expected = "sku,locale,price,title\nA,fr,2.00,Thé\nA,en,3.50,Black tea\n"
        self.assertEqual(apply_patch(before, package, authorized=True), expected)
        self.assertEqual([change["key"] for change in package["changes"]], [["A", "en"]])
        self.assertEqual(rollback(expected, package, authorized=True), before)
        self.assertTrue(verify_package(package, before))

    def test_decimal_and_alias_ambiguity_refuse(self) -> None:
        before = "sku,price\nA,2.00\n"
        for number in ["NaN", "Infinity", "text", ""]:
            with self.subTest(value=number), self.assertRaises(ValueError):
                reconcile(before, "sku,price\nA," + number + "\n", ["sku"], 2, decimal_columns=["price"])
        for aliases in [{"missing": "price"}, {"sku": "price"}, {"price": "unknown"}]:
            with self.subTest(aliases=aliases), self.assertRaises(ValueError):
                reconcile(before, before, ["sku"], 2, aliases=aliases)
        with self.assertRaises(ValueError):
            reconcile(before, before, ["sku"], 2, decimal_columns=["sku"])

    def test_descriptor_read_refuses_symlink_swap_and_nonregular_input(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.csv"
            target = Path(directory) / "target.csv"
            source.write_text("sku,title\nA,x\n")
            target.write_text("sku,title\nA,y\n")
            self.assertEqual(read_input(str(source)), "sku,title\nA,x\n")
            with self.assertRaises(ValueError):
                read_input(str(source), 2)
            actual_open = os.open

            def swap_after_open(path: Any, flags: int) -> int:
                descriptor = actual_open(path, flags)
                source.unlink()
                source.symlink_to(target)
                return descriptor

            with patch("contrib.enterprise_campaign.catalog_product.os.open", side_effect=swap_after_open):
                with self.assertRaises((OSError, ValueError)):
                    read_input(str(source))
            with self.assertRaises((OSError, ValueError)):
                read_input(str(source))
            if hasattr(os, "mkfifo"):
                fifo = Path(directory) / "input.fifo"
                os.mkfifo(fifo)
                with self.assertRaises(ValueError):
                    read_input(str(fifo))

    def test_selective_updates_preserve_local_fields_and_target_membership(self) -> None:
        before = "sku,locale,price,note\nA,fr,2.00,Note locale\nC,fr,5.00,Retirer\n"
        after = "prix,code,locale,note\n2.50,A,fr,Remplacement fournisseur\n3.00,B,en,Nouveau produit\n"
        package = reconcile(
            before, after, ["sku", "locale"], 3,
            decimal_columns=["price"], aliases={"code": "sku", "prix": "price"}, update_fields=["price"],
        )
        expected = "sku,locale,price,note\nA,fr,2.50,Note locale\nB,en,3.00,Nouveau produit\n"
        self.assertEqual(apply_patch(before, package, authorized=True), expected)
        self.assertEqual(package["changes"][0]["fields"], ["price"])
        self.assertEqual([change["kind"] for change in package["changes"]], ["update", "insert", "delete"])
        self.assertEqual(rollback(expected, package, authorized=True), before)
        empty = reconcile(before, after, ["sku", "locale"], 3, aliases={"code": "sku", "prix": "price"},
                          update_fields=[])
        self.assertIn("A,fr,2.00,Note locale", empty["output_csv"])

    def test_selective_update_policy_validation(self) -> None:
        before, after = "sku,price,note\nA,2.00,Local\n", "sku,price,note\nA,2.50,Supplier\n"
        for fields in [["sku"], ["missing"], ["price", "price"], cast(Any, "price"), [cast(Any, 3)]]:
            with self.subTest(fields=fields), self.assertRaises(ValueError):
                reconcile(before, after, ["sku"], 3, update_fields=fields)
        with self.assertRaises(ValueError):
            reconcile(before, after, ["sku"], 2, update_fields=["price"])
        full = reconcile(before, after, ["sku"], 3, update_fields=None)
        self.assertEqual(full["output_csv"], after)
        fields = ["price"]
        package = reconcile(before, after, ["sku"], 3, update_fields=fields)
        fields.append("note")
        self.assertEqual(package["options"]["update_fields"], ["price"])
        self.assertTrue(verify_package(package, before))


if __name__ == "__main__":
    unittest.main()
