# SPDX-License-Identifier: Apache-2.0
"""Bounded synthetic integrity controls; never build the real evidence companion."""

from __future__ import annotations

import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from typing import Any

import package_evidence as package


class PackageTests(unittest.TestCase):
    """Check extraction safety, immutable source binding and complete archive membership."""

    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.policy = package.load(package.STUDY / "publication/package-policy.json")

    def synthetic_plan(self) -> tuple[Path, Path, dict[str, Any]]:
        prefix = "studies/synthetic"
        entries = []
        for name, content in [
            ("paper/main.pdf", b"SYNTHETIC PDF FIXTURE"),
            ("demo/index.html", b"<p>SYNTHETIC TEST</p>"),
            ("src/tool.js", b"// synthetic\n"),
        ]:
            source = self.root / name
            source.parent.mkdir(parents=True, exist_ok=True)
            source.write_bytes(content)
            entries.append(package.entry_for(source, f"{prefix}/{name}", self.root, prefix, "synthetic-test"))
        link = self.root / "src/tool-link.js"
        link.symlink_to("tool.js")
        entries.append(package.entry_for(link, f"{prefix}/src/tool-link.js", self.root, prefix, "synthetic-test"))
        plan = {
            "schema": "agi-alpha.work-discovery.companion-manifest.v1",
            "study_path": prefix,
            "entries": entries,
            "payload_files": len(entries),
            "payload_bytes": sum(x["bytes"] for x in entries),
            "limits": {"maximum_payload_files": 20, "maximum_uncompressed_bytes": 10000},
        }
        plan_path = self.root / "synthetic-plan.json"
        plan_path.write_bytes(package.encode(plan))
        release = {
            "schema": "agi-alpha.work-discovery.companion-release.v1",
            "status": "ROOT_RELEASED_FOR_ARCHIVE_BUILD",
            "unit_test_fixture_only": True,
            "plan_sha256": package.sha256(plan_path.read_bytes()),
            "final_artifacts": [{"path": item["archive_path"], "sha256": item["sha256"]} for item in entries[:2]],
        }
        release_path = self.root / "synthetic-release.json"
        release_path.write_bytes(package.encode(release))
        return plan_path, release_path, plan

    def test_safe_relative_archive_paths(self) -> None:
        for path in ["/absolute", "../escape", "a/../escape", "a//b", "C:/drive", "a\\b", "a\nb"]:
            with self.assertRaises(ValueError):
                package.safe_archive_path(path)
        self.assertEqual(package.safe_archive_path("studies/example/source.mjs"), "studies/example/source.mjs")

    def test_internal_qa_exclusions_keep_publication_figures_and_json(self) -> None:
        self.assertIsNotNone(package.exclusion("demo/evidence/mobile-fr.png", False, self.policy))
        self.assertIsNotNone(package.exclusion("paper/main.aux", False, self.policy))
        self.assertIsNotNone(package.exclusion(".mypy_cache", True, self.policy))
        self.assertIsNone(package.exclusion("demo/evidence/browser-check.json", False, self.policy))
        self.assertIsNone(package.exclusion("paper/figures/economic-cells.png", False, self.policy))
        self.assertIsNone(package.exclusion("discovery/gtfs/evidence/executed-source.tar.gz", False, self.policy))

    def test_symlinks_cannot_escape_dependency_tree(self) -> None:
        self.assertEqual(
            package.safe_link_target(
                "external-tools/x/node_modules/.bin/cli", "../x/cli.js", "external-tools/x/node_modules"
            ),
            "external-tools/x/node_modules/x/cli.js",
        )
        with self.assertRaises(ValueError):
            package.safe_link_target(
                "external-tools/x/node_modules/.bin/cli", "../../../../../outside", "external-tools/x/node_modules"
            )

    def test_missing_or_changed_source_refuses_before_archive_creation(self) -> None:
        plan, release, _ = self.synthetic_plan()
        (self.root / "paper/main.pdf").write_bytes(b"changed")
        output = self.root / "synthetic.zip"
        with self.assertRaises(ValueError):
            package.build_package(plan, release, output)
        self.assertFalse(output.exists())

    def test_release_must_bind_exact_plan_pdf_and_demo(self) -> None:
        plan, release, _ = self.synthetic_plan()
        record = package.load(release)
        record["final_artifacts"][0]["sha256"] = "0" * 64
        release.write_bytes(package.encode(record))
        with self.assertRaises(ValueError):
            package.build_package(plan, release, self.root / "synthetic.zip")

    def test_synthetic_archive_roundtrip_and_no_overwrite(self) -> None:
        plan, release, expected = self.synthetic_plan()
        output = self.root / "synthetic.zip"
        result = package.build_package(plan, release, output)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["payload_files"], expected["payload_files"])
        self.assertEqual(package.verify_package(output)["status"], "PASS")
        with self.assertRaises(FileExistsError):
            package.build_package(plan, release, output)

    def test_unmanifested_zip_payload_is_rejected(self) -> None:
        plan, release, _ = self.synthetic_plan()
        output = self.root / "synthetic.zip"
        package.build_package(plan, release, output)
        with zipfile.ZipFile(output, "a") as archive:
            archive.writestr("unmanifested.txt", "unapproved fixture data")
        with self.assertRaises(ValueError):
            package.verify_package(output)

    def test_a_frozen_dependency_cannot_be_silently_missing(self) -> None:
        study = self.root / "studies/synthetic"
        study.mkdir(parents=True)
        record = {"files": [{"path": "missing.mjs", "bytes": 1, "sha256": "0" * 64}]}
        (study / "freeze.json").write_text(json.dumps(record))
        policy = {"primary_freeze": "freeze.json", "additional_active_freezes": []}
        with self.assertRaises((OSError, ValueError)):
            package.validate_frozen_files(study, self.root, policy)


if __name__ == "__main__":
    unittest.main(verbosity=2)
