# SPDX-License-Identifier: Apache-2.0
"""Challenge exact generated/public Discovery Lab custody without a simulated browser pass."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from typing import Any
from unittest import mock

from scripts import validate_discovery_lab as validation

GENERATOR = """import hashlib,json
from pathlib import Path
def build(root):
 root=Path(root)
 names=['source.mjs','scripts/generate_successor_capability.py']
 sources={n:hashlib.sha256((root/n).read_bytes()).hexdigest() for n in names}
 digest=hashlib.sha256(json.dumps(sources,sort_keys=True,separators=(',',':')).encode()).hexdigest()
 destination=root/'docs/successor/capabilities';destination.mkdir(parents=True,exist_ok=True)
 (destination/'index.html').write_bytes(('<!doctype html><title>Finite lab</title>'+digest).encode())
 manifest={'schema':'successor-capability-source/v1','sourceHash':digest,'sources':sources}
 (destination/'sources.json').write_text(json.dumps(manifest,sort_keys=True,indent=2)+'\\n')
if __name__=='__main__':build(Path(__file__).resolve().parents[1])
"""


class DiscoveryValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="discovery-validator-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        (self.root / "scripts").mkdir()
        (self.root / validation.GENERATOR).write_text(GENERATOR)
        (self.root / "source.mjs").write_text("export const finite = 1;\n")
        subprocess.run([sys.executable, str(self.root / validation.GENERATOR)], check=True, timeout=15)
        self.generated = self.root / "docs" / validation.ASSET
        self.site = self.root / "site"
        self.page = self.site / validation.ASSET
        self.page.parent.mkdir(parents=True)
        self.page.write_bytes(self.generated.read_bytes())
        self.page.with_name("sources.json").write_bytes(self.generated.with_name("sources.json").read_bytes())
        self.expected = validation.verify_packaged(self.site, self.root)

    def manifest(self) -> dict[str, Any]:
        result: dict[str, Any] = json.loads(self.expected["manifest"])
        return result

    def test_exact_generated_package_and_public_bytes_pass(self) -> None:
        validation.verify_received(self.expected["page"], self.expected["manifest"], self.expected)
        self.assertEqual(self.expected["sourcesChecked"], 2)

    def test_self_consistent_older_public_page_is_refused(self) -> None:
        changed = self.manifest()
        changed["sources"]["source.mjs"] = "1" * 64
        changed["sourceHash"] = validation.sha256(
            json.dumps(changed["sources"], sort_keys=True, separators=(",", ":")).encode()
        )
        with self.assertRaisesRegex(ValueError, "exact packaged/generated"):
            validation.verify_received(b"<title>Old page</title>", json.dumps(changed).encode(), self.expected)

    def test_changed_page_and_byte_different_manifest_are_refused(self) -> None:
        for page, manifest in (
            (self.expected["page"] + b" ", self.expected["manifest"]),
            (self.expected["page"], json.dumps(self.manifest()).encode()),
        ):
            with self.subTest(page=page[:30]), self.assertRaises(ValueError):
                validation.verify_received(page, manifest, self.expected)

    def test_modified_checkout_source_or_forged_generated_page_is_refused(self) -> None:
        (self.root / "source.mjs").write_text("export const finite = 2;\n")
        with self.assertRaisesRegex(ValueError, "differs from checkout"):
            validation.verify_packaged(self.site, self.root)
        (self.root / "source.mjs").write_text("export const finite = 1;\n")
        for file in (self.page, self.generated):
            file.write_bytes(b"<title>Forged generated output</title>")
        with self.assertRaisesRegex(ValueError, "exact generated checkout bytes"):
            validation.verify_packaged(self.site, self.root)

    def test_manifest_paths_cannot_escape_or_hide_duplicate_keys(self) -> None:
        for name in ("../outside", "/absolute", "a/../b", "a\\b", ".", "a//b"):
            value = self.manifest()
            value["sources"] = {name: "1" * 64}
            with self.subTest(name=name), self.assertRaises(ValueError):
                validation.manifest_data(json.dumps(value).encode())
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            validation.manifest_data(b'{"schema":1,"schema":2}')

    def test_source_commitment_size_and_missing_generator_are_refused(self) -> None:
        value = self.manifest()
        value["sourceHash"] = "f" * 64
        with self.assertRaisesRegex(ValueError, "source hash"):
            validation.manifest_data(json.dumps(value).encode())
        with self.assertRaisesRegex(ValueError, "byte cap"):
            validation.manifest_data(b" " * (validation.MAX_MANIFEST_BYTES + 1))
        value = self.manifest()
        del value["sources"][validation.GENERATOR]
        value["sourceHash"] = validation.sha256(
            json.dumps(value["sources"], sort_keys=True, separators=(",", ":")).encode()
        )
        self.page.with_name("sources.json").write_text(json.dumps(value))
        with self.assertRaisesRegex(ValueError, "omits.*generator"):
            validation.verify_packaged(self.site, self.root)

    def test_source_symlink_cannot_escape_checkout(self) -> None:
        outside = self.root.parent / (self.root.name + "-outside.mjs")
        outside.write_text("export const finite = 1;\n")
        self.addCleanup(outside.unlink)
        source = self.root / "source.mjs"
        source.unlink()
        source.symlink_to(outside)
        with self.assertRaisesRegex(ValueError, "escapes"):
            validation.verify_packaged(self.site, self.root)

    def test_public_entry_requires_exact_https_without_credential_or_query_variants(self) -> None:
        base = "https://montrealai.github.io/AGI-Alpha-Agent-v0/"
        target = base + "successor/capabilities/"
        for source in (base, target, target + "index.html", target.rstrip("/")):
            self.assertEqual(validation.discovery_url(source), target)
        for value in (
            base.replace("https:", "http:"),
            "https://user:secret@example.com/",
            "https://@example.com/",
            base + "?old=1",
            base + "?",
            base + "#",
            base + "#old",
            "https://example.com:bad/",
            "https://example.com /",
            base + "\\bad",
        ):
            with self.subTest(value=value), self.assertRaises(ValueError):
                validation.discovery_url(value)

    def test_browser_loader_requires_full_suite_success_and_preserves_absolute_output(self) -> None:
        browser = self.root / "tests/browser/test_discovery_lab_browser.py"
        browser.parent.mkdir(parents=True)
        browser.write_text(
            "def run_acceptance(entry, output, *, expected_page_sha256):\n    return {'passed': False}\n"
        )
        with mock.patch.object(validation, "ROOT", self.root), self.assertRaisesRegex(ValueError, "did not pass"):
            validation.browser_acceptance(self.page.as_uri(), self.root / "evidence", self.expected["pageSha256"])
        browser.write_text(
            "def run_acceptance(entry, output, *, expected_page_sha256):\n"
            "    return {'passed': True, 'entryUrl': entry, 'output': str(output),\n"
            "            'pageSha256': expected_page_sha256,\n"
            "            'campaigns': 4, 'checks': ['budget-inconclusive','six-stage-accepted',\n"
            "            'both-zero-cap-drafts',\n"
            "            'edited-constraint-rejected','stronger-successor','history-reload','resolved-accessibility',\n"
            "            'responsive-390-320','keyboard','no-external-requests','exact-page-before-and-after']}\n"
        )
        with mock.patch.object(validation, "ROOT", self.root):
            result = validation.browser_acceptance(
                self.page.as_uri(), self.root / "evidence", self.expected["pageSha256"]
            )
        self.assertEqual(result["output"], str((self.root / "evidence").resolve()))

    def test_dirty_or_untracked_acceptance_inputs_cannot_claim_the_head_identity(self) -> None:
        for name in (
            "scripts/validate_discovery_lab.py",
            "tests/browser/test_discovery_lab_browser.py",
            "tests/browser/test_successor_capability_accessibility.py",
        ):
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("# immutable acceptance fixture\n")
        (self.root / "tests/browser/package.json").write_text("{}")
        (self.root / "tests/browser/package-lock.json").write_text("{}")
        (self.root / "pyproject.toml").write_text('[project]\nversion="1.0.0"\n')
        captured = {
            path.relative_to(self.root).as_posix(): path.read_bytes() for path in self.root.rglob("*") if path.is_file()
        }

        def git(command: list[str], **kwargs: Any) -> str | bytes:
            if command[1] == "rev-parse":
                return ("1" if command[2] == "HEAD" else "2") * 40 + "\n"
            return captured[command[2].split(":", 1)[1]]

        with (
            mock.patch.object(validation, "ROOT", self.root),
            mock.patch("scripts.validate_discovery_lab.subprocess.check_output", side_effect=git),
            mock.patch.dict(os.environ, {}, clear=True),
        ):
            self.assertEqual(validation.checkout_identity(), ("1" * 40, "2" * 40, "1.0.0"))
            (self.root / "tests/browser/test_discovery_lab_browser.py").write_text("# changed runner\n")
            with self.assertRaisesRegex(ValueError, "differs from the exact checkout commit"):
                validation.checkout_identity()
            (self.root / "tests/browser/test_discovery_lab_browser.py").write_bytes(
                captured["tests/browser/test_discovery_lab_browser.py"]
            )

            def missing(command: list[str], **kwargs: Any) -> str | bytes:
                if command[1] == "show":
                    raise subprocess.CalledProcessError(128, "git")
                return git(command, **kwargs)

            with mock.patch("scripts.validate_discovery_lab.subprocess.check_output", side_effect=missing):
                with self.assertRaisesRegex(ValueError, "absent from the exact checkout commit"):
                    validation.checkout_identity()

    def test_auditor_stub_or_altered_lock_cannot_establish_accessibility_acceptance(self) -> None:
        folder = self.root / "tests/browser"
        folder.mkdir(parents=True)
        lock = {
            "packages": {
                "node_modules/axe-core": {
                    "version": validation.AXE_VERSION,
                    "integrity": validation.AXE_INTEGRITY,
                    "resolved": "https://registry.npmjs.org/axe-core/-/axe-core-4.10.3.tgz",
                }
            }
        }
        (folder / "package-lock.json").write_text(json.dumps(lock))
        script = self.root / "axe-stub.js"
        script.write_text("window.axe={run:async()=>({violations:[],incomplete:[]})};")
        with self.assertRaisesRegex(ValueError, "auditor bytes"):
            validation.validate_auditor(script, self.root)
        with mock.patch.object(validation, "AXE_SHA256", validation.sha256(script.read_bytes())):
            self.assertEqual(validation.validate_auditor(script, self.root)["version"], "4.10.3")
            lock["packages"]["node_modules/axe-core"]["integrity"] = "unreviewed"
            (folder / "package-lock.json").write_text(json.dumps(lock))
            with self.assertRaisesRegex(ValueError, "package lock"):
                validation.validate_auditor(script, self.root)

    def test_assertion_disabled_runner_cannot_claim_full_browser_acceptance(self) -> None:
        with mock.patch("scripts.validate_discovery_lab.sys.flags", mock.Mock(optimize=1)):
            with self.assertRaisesRegex(RuntimeError, "assertion checks enabled"):
                validation.browser_acceptance(self.page.as_uri(), self.root / "evidence", self.expected["pageSha256"])

    def test_main_verifies_public_bytes_before_and_after_the_same_complete_suite(self) -> None:
        axe = self.root / "axe.js"
        axe.write_text("/* auditor fixture: no browser acceptance is established here */")
        output = self.root / "evidence"
        public = "https://example.com/gallery/successor/capabilities/"
        with (
            mock.patch.object(validation, "checkout_identity", return_value=("1" * 40, "2" * 40, "1.0.0")),
            mock.patch.object(validation, "verify_packaged", return_value=self.expected) as packaged,
            mock.patch.object(
                validation, "validate_auditor", return_value={"scriptSha256": validation.sha256(axe.read_bytes())}
            ),
            mock.patch.object(validation, "verify_public", return_value={"url": public}) as received,
            mock.patch.object(
                validation, "browser_acceptance", return_value={"passed": True, "checks": ["test-double"]}
            ) as browser,
            mock.patch.dict(os.environ),
            redirect_stdout(StringIO()),
            mock.patch(
                "sys.argv",
                [
                    "validator",
                    "--site",
                    str(self.site),
                    "--url",
                    public,
                    "--output",
                    str(output),
                    "--axe-script",
                    str(axe),
                ],
            ),
        ):
            validation.main()
        self.assertEqual(received.call_count, 2)
        self.assertEqual(packaged.call_count, 2)
        browser.assert_called_once_with(public, output / "browser", self.expected["pageSha256"])
        report = json.loads((output / "report.json").read_text())
        self.assertEqual(report["mode"], "public")
        self.assertEqual(report["tree"], "2" * 40)
        self.assertIn("broader release qualification", report["scope"])


if __name__ == "__main__":
    unittest.main()
