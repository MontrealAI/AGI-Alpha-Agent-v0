# SPDX-License-Identifier: Apache-2.0
"""Offline, stdlib-only tests for the deliberately bounded public PDF repair."""

from __future__ import annotations

import copy
import io
import json
import os
import tempfile
import unittest
import urllib.error
from email.message import Message
from pathlib import Path
from unittest.mock import patch

from scripts import repair_paper_links as repair

SOURCE = "1" * 40
ROOT = Path(__file__).resolve().parents[1]


class PaperLinkRepairTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.site = self.root / "site"
        self.docs = self.root / "docs"
        self.site.mkdir()
        self.docs.mkdir()
        self.pdf_data = {name: b"%PDF-1.7\n" + name.encode() for name in repair.PDFS}
        self.pdfs = {name: (len(data), repair.sha256(data)) for name, data in self.pdf_data.items()}
        self.baseline = {
            "release.json": b'{"version":"1.36.0","commit":"unchanged"}\n',
            "index.html": b"unchanged homepage",
            "runtime/model.bin": b"unchanged model",
        }
        self.baseline.update({name: data for name, data in self.pdf_data.items() if name not in repair.ADDITIONS})
        for name, data in self.baseline.items():
            path = self.site / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        for name, data in self.pdf_data.items():
            (self.docs / name).write_bytes(data)
        self.index = {
            "files": [
                {"path": name, "bytes": len(data), "sha256": repair.sha256(data)}
                for name, data in self.baseline.items()
            ]
        }
        self.addCleanup(patch.stopall)
        patch.object(repair, "PDFS", self.pdfs).start()

    def test_overlay_adds_only_five_pdfs_and_distinct_receipt(self) -> None:
        repair.overlay(self.site, self.docs, self.index, SOURCE)
        repair.verify_inventory(self.site, self.index, SOURCE, repaired=True)
        self.assertEqual(
            {p.relative_to(self.site).as_posix() for p in self.site.rglob("*") if p.is_file()},
            set(self.baseline) | set(repair.ADDITIONS) | {repair.RECEIPT},
        )
        for name, data in self.baseline.items():
            self.assertEqual((self.site / name).read_bytes(), data)
        receipt = json.loads((self.site / repair.RECEIPT).read_text())
        self.assertEqual(receipt["software"], {"version": "1.36.0", "commit": repair.BASELINE_COMMIT})
        self.assertEqual(receipt["repair_source_commit"], SOURCE)
        self.assertEqual(len(receipt["added"]), 5)

    def test_repeated_overlay_refuses_instead_of_overwriting(self) -> None:
        repair.overlay(self.site, self.docs, self.index, SOURCE)
        before = (self.site / repair.RECEIPT).read_bytes()
        with self.assertRaises(ValueError):
            repair.overlay(self.site, self.docs, self.index, SOURCE)
        self.assertEqual((self.site / repair.RECEIPT).read_bytes(), before)

    def test_every_baseline_mutation_is_rejected(self) -> None:
        for name in self.baseline:
            with self.subTest(name=name):
                path = self.site / name
                data = path.read_bytes()
                path.write_bytes(data + b"changed")
                with self.assertRaises(ValueError):
                    repair.overlay(self.site, self.docs, self.index, SOURCE)
                path.write_bytes(data)
        self.assertFalse((self.site / repair.RECEIPT).exists())

    def test_missing_extra_symlink_and_special_paths_fail(self) -> None:
        target = self.site / "index.html"
        target.unlink()
        with self.assertRaises(ValueError):
            repair.verify_inventory(self.site, self.index, SOURCE, repaired=False)
        target.write_bytes(self.baseline["index.html"])
        extra = self.site / "unknown.html"
        extra.write_bytes(b"not disposable")
        with self.assertRaises(ValueError):
            repair.verify_inventory(self.site, self.index, SOURCE, repaired=False)
        extra.unlink()
        extra.symlink_to(target)
        with self.assertRaises(ValueError):
            repair.verify_inventory(self.site, self.index, SOURCE, repaired=False)

    def test_corrupt_original_rejected_before_any_overlay(self) -> None:
        for name in self.pdfs:
            with self.subTest(name=name):
                path = self.docs / name
                path.write_bytes(b"not the original")
                with self.assertRaises(ValueError):
                    repair.overlay(self.site, self.docs, self.index, SOURCE)
                self.assertFalse(any((self.site / name).exists() for name in repair.ADDITIONS))
                path.write_bytes(self.pdf_data[name])

    def test_baseline_pdf_or_receipt_collision_fails(self) -> None:
        for name in (*repair.ADDITIONS, repair.RECEIPT):
            index = copy.deepcopy(self.index)
            index["files"].append({"path": name, "bytes": 1, "sha256": repair.sha256(b"x")})
            with self.assertRaises(ValueError):
                repair.verify_inventory(self.site, index, SOURCE, repaired=False)

    def test_duplicate_inventory_rejected(self) -> None:
        self.index["files"].append(self.index["files"][0])
        with self.assertRaises(ValueError):
            repair.verify_inventory(self.site, self.index, SOURCE, repaired=False)

    def test_partial_result_cannot_pass_final_inventory(self) -> None:
        (self.site / repair.ADDITIONS[0]).write_bytes(self.pdf_data[repair.ADDITIONS[0]])
        with self.assertRaises(ValueError):
            repair.verify_inventory(self.site, self.index, SOURCE, repaired=True)

    def test_receipt_identity_is_strict(self) -> None:
        for source in ("main", "", "1" * 39, "G" * 40):
            with self.assertRaises(ValueError):
                repair.repair_receipt(source)
        self.assertEqual(repair.receipt_bytes(SOURCE), repair.receipt_bytes(SOURCE))

    def test_wrong_index_digest_rejected(self) -> None:
        path = self.root / "index.json"
        path.write_text(json.dumps(self.index))
        with self.assertRaises(ValueError):
            repair.load_index(path)

    def test_index_semantics_rejected_even_with_test_digest_binding(self) -> None:
        index = {
            "schema": "wrong",
            "commit": repair.BASELINE_COMMIT,
            "version": "1.36.0",
            "files": [None] * 991,
            "packs": [None] * 5,
        }
        data = json.dumps(index).encode()
        path = self.root / "index.json"
        path.write_bytes(data)
        with patch.object(repair, "INDEX_BYTES", len(data)), patch.object(repair, "INDEX_SHA256", repair.sha256(data)):
            with self.assertRaises(ValueError):
                repair.load_index(path)

    def test_existing_download_must_match_exact_bytes(self) -> None:
        path = self.root / "asset.zip"
        path.write_bytes(b"exact")
        repair.download_exact("https://example.invalid", path, 5, repair.sha256(b"exact"))
        with self.assertRaises(ValueError):
            repair.download_exact("https://example.invalid", path, 5, "0" * 64)

    def test_corrupt_download_retains_partial_not_promoted(self) -> None:
        path = self.root / "asset.zip"
        response = io.BytesIO(b"corrupt")
        response.status = 200
        with patch.object(repair.urllib.request, "urlopen", return_value=response):
            with self.assertRaises(ValueError):
                repair.download_exact("https://example.invalid", path, 7, "0" * 64)
        self.assertFalse(path.exists())
        self.assertTrue(path.with_suffix(".zip.partial").exists())

    def test_interrupted_download_does_not_overwrite_partial(self) -> None:
        path = self.root / "asset.zip"
        path.with_suffix(".zip.partial").write_bytes(b"preserve")
        with self.assertRaises(ValueError):
            repair.download_exact("https://example.invalid", path, 1, "0" * 64)

    def test_only_404_proves_absence(self) -> None:
        for code in (403, 429, 500):
            with patch.object(repair, "live", side_effect=urllib.error.HTTPError("url", code, "error", {}, None)):
                with self.assertRaises(urllib.error.HTTPError):
                    repair.absent("paper-publication.json")
        with patch.object(repair, "live", side_effect=urllib.error.HTTPError("url", 404, "absent", {}, None)):
            repair.absent("paper-publication.json")
        with patch.object(repair, "live", return_value=(b"existing", {})):
            with self.assertRaises(ValueError):
                repair.absent("paper-publication.json")

    def test_context_requires_current_main(self) -> None:
        env = {"GITHUB_REPOSITORY": repair.REPOSITORY, "GITHUB_REF": "refs/heads/main", "GITHUB_SHA": SOURCE}
        ref = {"ref": "refs/heads/main", "object": {"sha": SOURCE}}
        with patch.dict(os.environ, env), patch.object(repair, "api", return_value=ref):
            self.assertEqual(repair.require_context(), SOURCE)
            for key, value in (
                ("GITHUB_REPOSITORY", "fork/repo"),
                ("GITHUB_REF", "refs/pull/1/merge"),
                ("GITHUB_SHA", "2" * 40),
            ):
                with patch.dict(os.environ, {key: value}):
                    with self.assertRaises(ValueError):
                        repair.require_context()

    def deployment_api(self, *, pending: dict | None = None, state: str = "success"):
        base = {"id": repair.BASELINE_DEPLOYMENT, "sha": repair.BASELINE_COMMIT}
        status = {
            "state": state,
            "log_url": (
                f"https://github.com/{repair.REPOSITORY}/actions/runs/{repair.BASELINE_RUN}"
                f"/job/{repair.BASELINE_JOB}"
            ),
            "environment_url": repair.SITE,
        }

        def read(path):
            if path.startswith("deployments?"):
                return ([pending] if pending else []) + [base]
            if path.startswith(f"deployments/{repair.BASELINE_DEPLOYMENT}/"):
                return [status]
            return [pending["status"]]

        return read

    def test_exact_successful_deployment_required(self) -> None:
        with patch.object(repair, "api", side_effect=self.deployment_api()):
            repair.require_baseline_deployment(SOURCE)
        for state in ("failure", "inactive", "pending"):
            with patch.object(repair, "api", side_effect=self.deployment_api(state=state)):
                with self.assertRaises(ValueError):
                    repair.require_baseline_deployment(SOURCE)

    def test_only_current_run_pending_deployment_allowed(self) -> None:
        pending = {
            "id": 99,
            "sha": SOURCE,
            "status": {
                "state": "in_progress",
                "log_url": f"https://github.com/{repair.REPOSITORY}/actions/runs/123/job/456",
            },
        }
        with patch.dict(os.environ, {"GITHUB_RUN_ID": "123"}):
            with patch.object(repair, "api", side_effect=self.deployment_api(pending=pending)):
                repair.require_baseline_deployment(SOURCE)
            for changed in (
                {"sha": "2" * 40},
                {"status": {"state": "success"}},
                {"status": {"state": "queued", "log_url": "unrelated"}},
            ):
                item = copy.deepcopy(pending)
                item.update(changed)
                with patch.object(repair, "api", side_effect=self.deployment_api(pending=item)):
                    with self.assertRaises(ValueError):
                        repair.require_baseline_deployment(SOURCE)

    def test_guard_rechecks_after_live_probes(self) -> None:
        calls = []
        with (
            patch.object(repair, "require_context", side_effect=lambda: calls.append("main") or SOURCE),
            patch.object(repair, "require_baseline_deployment", side_effect=lambda _: calls.append("deployment")),
            patch.object(repair, "verify_live_baseline", side_effect=lambda _: calls.append("live")),
            patch.object(repair, "absent", side_effect=lambda _: calls.append("absence")),
            patch.object(repair, "live", side_effect=lambda name: (self.pdf_data[name], {})),
        ):
            repair.guard(self.index)
        self.assertEqual(calls[:3], ["main", "deployment", "live"])
        self.assertEqual(calls[-2:], ["main", "deployment"])

    def test_all_seven_live_pdf_checks_are_exact_and_inline(self) -> None:
        headers = Message()
        headers["Content-Type"] = "application/pdf"

        def live(name):
            return (repair.receipt_bytes(SOURCE) if name == repair.RECEIPT else self.pdf_data[name], headers)

        with patch.object(repair, "verify_live_baseline"), patch.object(repair, "live", side_effect=live):
            report = repair.verify_live(self.index, SOURCE)
            self.assertEqual([x["path"] for x in report["papers"]], list(self.pdfs))
            headers.replace_header("Content-Type", "text/html")
            with self.assertRaises(ValueError):
                repair.verify_live(self.index, SOURCE)
            headers.replace_header("Content-Type", "application/pdf")
            headers["Content-Disposition"] = "attachment; filename=paper.pdf"
            with self.assertRaises(ValueError):
                repair.verify_live(self.index, SOURCE)


class WorkflowPolicyTests(unittest.TestCase):
    def test_workflow_is_separate_fail_closed_and_uses_existing_pages_authority(self) -> None:
        workflow = (ROOT / ".github/workflows/paper-links-repair.yml").read_text()
        self.assertIn("group: github-pages\n      cancel-in-progress: false", workflow)
        self.assertIn("contents: read\n      pages: write\n      id-token: write", workflow)
        self.assertEqual(workflow.count("persist-credentials: false"), 4)
        self.assertEqual(workflow.count("github.event_name != 'pull_request'"), 3)
        self.assertNotIn("configure-pages", workflow)
        self.assertNotIn("ADMIN_GITHUB_TOKEN", workflow)
        self.assertNotIn("continue-on-error", workflow)
        self.assertNotIn("contents: write", workflow)
        self.assertNotIn("secrets:", workflow)
        guard = workflow.index("scripts.repair_paper_links guard")
        deploy = workflow.index("actions/deploy-pages@")
        verify = workflow.index("scripts.repair_paper_links verify-live")
        self.assertLess(guard, deploy)
        self.assertLess(deploy, verify)
        self.assertIn("needs: prepare", workflow)
        self.assertIn("artifact_name: pdf-link-repair-${{ github.run_id }}-${{ github.run_attempt }}", workflow)
        self.assertIn("actions/deploy-pages@d6db90164ac5ed86f2b6aed7e0febac5b3c0c03e", workflow)

    def test_failed_live_verification_can_retry_without_pages_authority(self) -> None:
        workflow = (ROOT / ".github/workflows/paper-links-repair.yml").read_text()
        deployment, verification = workflow.split("\n  verify-live:\n", 1)
        self.assertIn("needs: deploy", verification)
        self.assertIn("permissions:\n      contents: read", verification)
        self.assertIn("scripts.repair_paper_links verify-live", verification)
        self.assertIn("REPAIR_SOURCE: ${{ github.sha }}", verification)
        self.assertIn("if: ${{ always() }}", verification)
        for forbidden in (
            "pages: write",
            "id-token:",
            "environment:",
            "actions/deploy-pages@",
            "scripts.repair_paper_links prepare",
            "scripts.repair_paper_links guard",
        ):
            self.assertNotIn(forbidden, verification)
        self.assertNotIn("scripts.repair_paper_links verify-live", deployment)


if __name__ == "__main__":
    unittest.main()
