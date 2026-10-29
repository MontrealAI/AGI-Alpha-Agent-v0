# SPDX-License-Identifier: Apache-2.0
"""Independent integration regression cases; not commercial or scientific trials."""
from __future__ import annotations

import unittest
import copy
import tempfile
import subprocess
import sys
from pathlib import Path

from contrib.enterprise_campaign import catalog_product as native
from contrib.enterprise_campaign.delta_acceptance import verify_delta
from contrib.enterprise_campaign.delta_delivery import _digest, build_delta, make_request


def rehash(package: dict) -> None:
    inner = package["native_package"]
    inner["proof_digest"] = _digest({k: v for k, v in inner.items() if k != "proof_digest"})
    package["digest"] = _digest({k: v for k, v in package.items() if k != "digest"})


class QualificationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.before = "sku,note\r\nA,old\r\nB,retained\r\n"
        self.delta = "sku,note\nA,=1+1\n"
        self.request = make_request(["sku"], ["note"])
        self.package = build_delta(self.before, self.delta, self.request)

    def test_rehashed_preview_is_independently_rejected(self) -> None:
        self.package["native_package"]["safe_preview_csv"] = self.package["native_package"]["output_csv"]
        rehash(self.package)
        verdict = verify_delta(self.before, self.delta, self.package, self.request)
        self.assertIn("review_preview", verdict["failures"])
        with self.assertRaises(ValueError):
            native.apply_patch(self.before, self.package["native_package"], authorized=True)

    def test_rehashed_false_summary_is_rejected(self) -> None:
        self.package["native_package"]["changes"] = []
        rehash(self.package)
        self.assertIn("change_summary", verify_delta(self.before, self.delta, self.package, self.request)["failures"])

    def test_missing_native_integrity_is_rejected(self) -> None:
        self.package["native_package"].pop("proof_digest")
        self.package["digest"] = _digest({k: v for k, v in self.package.items() if k != "digest"})
        self.assertIn("native_integrity", verify_delta(self.before, self.delta, self.package, self.request)["failures"])

    def test_wrong_producer_identity_is_rejected(self) -> None:
        self.package["source_git_blob"] = "0" * 40
        rehash(self.package)
        self.assertIn("source_identity", verify_delta(self.before, self.delta, self.package, self.request)["failures"])

    def test_native_contract_metadata_rehashed_tampering(self) -> None:
        mutations = {
            "keys": ["MISSING"],
            "options": {},
            "schema": "wrong",
            "generation": 2,
            "after_csv": "sku,note\nA,wrong\n",
            "trace": {},
        }
        for field, value in mutations.items():
            with self.subTest(field=field):
                package = copy.deepcopy(self.package)
                package["native_package"][field] = value
                rehash(package)
                self.assertIn(
                    "native_contract", verify_delta(self.before, self.delta, package, self.request)["failures"]
                )

    def test_unquoted_quote_forged_source_refused(self) -> None:
        before = 'id,note\na,"ab""cd"\n'
        malformed = 'id,note\na,ab"cd\n'
        delta = "id,note\na,new\n"
        request = make_request(["id"], ["note"])
        package = build_delta(before, delta, request)
        package["before_sha256"] = native.digest(malformed)
        package["native_package"]["before_sha256"] = native.digest(malformed)
        package["native_package"]["rollback_csv"] = malformed
        rehash(package)
        self.assertEqual(verify_delta(malformed, delta, package, request)["verdict"], "REJECTED")

    def test_untouched_invalid_decimal_and_long_header_refused(self) -> None:
        from contrib.enterprise_campaign.delta_acceptance import conventional_delta
        from decimal import InvalidOperation

        request = make_request(["sku"], ["v"], ["v"])
        with self.assertRaises((ValueError, InvalidOperation)):
            conventional_delta("sku,v\nA,1\nB,invalid\n", "sku,v\nA,2\n", request)
        huge = "x" * 4097
        with self.assertRaises(ValueError):
            conventional_delta(f"sku,{huge}\nA,x\n", f"sku,{huge}\nA,y\n", make_request(["sku"], [huge]))

    def test_non_object_native_package_refused(self) -> None:
        self.package["native_package"] = []
        self.assertEqual(verify_delta(self.before, self.delta, self.package, self.request)["verdict"], "REJECTED")

    def test_documented_bundled_example_cli(self) -> None:
        root = Path(__file__).resolve().parents[1]
        examples = root / "contrib/enterprise_campaign/examples"
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "delivery"
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "contrib.enterprise_campaign.delta_delivery",
                    "--before",
                    str(examples / "catalogue.csv"),
                    "--delta",
                    str(examples / "supplier_delta.csv"),
                    "--keys",
                    "sku",
                    "--write-fields",
                    "price",
                    "--decimal-fields",
                    "price",
                    "--aliases",
                    '{"product_code":"sku","new_price":"price"}',
                    "--output",
                    str(output),
                ],
                cwd=root,
                capture_output=True,
                text=True,
                timeout=20,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual((output / "rollback.csv").read_bytes(), (examples / "catalogue.csv").read_bytes())
            self.assertIn("A,Montréal Widget,12.50,Preserve buyer approval", (output / "updated.csv").read_text())

    def test_non_object_change_entries_refused(self) -> None:
        for changes in ([None], ["update"], [1], None, {}, "update"):
            with self.subTest(changes=changes):
                package = copy.deepcopy(self.package)
                package["native_package"]["changes"] = changes
                self.assertEqual(verify_delta(self.before, self.delta, package, self.request)["verdict"], "REJECTED")

    def test_stale_rollback_refuses(self) -> None:
        with self.assertRaises(ValueError):
            native.rollback("sku,note\nA,different\n", self.package["native_package"], authorized=True)

    def test_fresh_contract_matrix(self) -> None:
        # Fixed before this run: alias, composite identity, blank text, Unicode,
        # formula text, equivalent decimals, header-only delta and CRLF/BOM.
        cases = [
            ("sku,v,n\nA,1,local\nB,2,keep\n", "id,v\nB,3\n", make_request(["sku"], ["v"], [], {"id": "sku"})),
            ("site,sku,v\nE,A,1\nW,A,2\n", "sku,site,v\nA,W,9\n", make_request(["site", "sku"], ["v"])),
            ("sku,v\nA,old\n", "sku,v\nA,\n", make_request(["sku"], ["v"])),
            ("sku,v\nα,old\n", "sku,v\nα,été\n", make_request(["sku"], ["v"])),
            ("sku,v\nA,old\n", "sku,v\nA, @SUM(A1)\n", make_request(["sku"], ["v"])),
            ("sku,v\nA,1.00\n", "sku,v\nA,1.000\n", make_request(["sku"], ["v"], ["v"])),
            ("sku,v\nA,old\n", "sku,v\n", make_request(["sku"], ["v"])),
            ("\ufeffsku,v\r\nA,old\r\n", "\ufeffsku,v\r\nA,new\r\n", make_request(["sku"], ["v"])),
        ]
        for before, delta, request in cases:
            with self.subTest(before=before, delta=delta):
                package = build_delta(before, delta, request)
                self.assertEqual(verify_delta(before, delta, package, request)["verdict"], "PASS_IN_SCOPE")
                output = native.apply_patch(before, package["native_package"], authorized=True)
                self.assertEqual(native.rollback(output, package["native_package"], authorized=True), before)


if __name__ == "__main__":
    unittest.main()
