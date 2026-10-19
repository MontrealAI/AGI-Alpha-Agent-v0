# SPDX-License-Identifier: Apache-2.0
"""Check the downloaded gallery layout using inert acceptance metadata only."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
import yaml

from scripts import package_agent_release as packaging
from scripts import successor_alpha_evidence
from scripts import transformational_evidence as evidence

ROOT = Path(__file__).resolve().parents[1]
COMMIT, VERSION = "a" * 40, "1.36.0"
IDENTITY = {"pageSha256": "b" * 64, "manifestSha256": "c" * 64, "sourcesChecked": 4}


@pytest.fixture
def gallery_reports(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, dict[str, dict[str, Any]]]:
    """Represent the action's named artifact directories without running a browser."""

    def identity(root: Path = evidence.ROOT) -> dict[str, Any]:
        return dict(IDENTITY)

    monkeypatch.setattr(evidence, "asset_identity", identity)
    folder = tmp_path / "evidence"
    reports: dict[str, dict[str, Any]] = {}
    for kind in ("minimal", "full"):
        report = {
            "schema": "agialpha.transformational.acceptance.v1",
            "commit": COMMIT,
            "version": VERSION,
            "mode": "local",
            "origin": f"file:///gallery-{kind}/transformational-intelligence/index.html",
            "passed": True,
            "sourceIdentity": dict(IDENTITY),
            "checks": sorted(evidence.CHECKS),
            "public": None,
        }
        path = folder / f"gallery-{kind}" / "transformational-intelligence" / "report.json"
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps(report), encoding="utf-8")
        reports[kind] = report
    return folder, reports


def configure_preflight(monkeypatch: pytest.MonkeyPatch, folder: Path, output: Path) -> None:
    """Reach only the real report preflight, with build and unrelated gates stubbed."""
    monkeypatch.chdir(folder.parent)
    Path("pyproject.toml").write_text(f'[project]\nversion = "{VERSION}"\n', encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["package", "--output", str(output), "--evidence", str(folder)])
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: None)
    monkeypatch.setattr(subprocess, "check_output", lambda *args, **kwargs: COMMIT)
    monkeypatch.setattr(packaging, "require_historical_evidence", lambda *args: {})
    monkeypatch.setattr(successor_alpha_evidence, "require_local_reports", lambda *args: {"fixture": True})


def test_both_named_gallery_reports_are_verified(gallery_reports: tuple[Path, dict[str, dict[str, Any]]]) -> None:
    folder, reports = gallery_reports
    accepted = evidence.require_local_reports(folder, COMMIT, VERSION)
    assert accepted == reports
    assert accepted["minimal"]["origin"] != accepted["full"]["origin"]


@pytest.mark.parametrize("missing", ["minimal", "full"])
def test_flat_report_cannot_replace_a_missing_gallery_report(
    gallery_reports: tuple[Path, dict[str, dict[str, Any]]], missing: str
) -> None:
    folder, reports = gallery_reports
    (folder / f"gallery-{missing}/transformational-intelligence/report.json").unlink()
    flat = folder / "transformational-intelligence/report.json"
    flat.parent.mkdir()
    flat.write_text(json.dumps(reports[missing]), encoding="utf-8")
    with pytest.raises(ValueError, match="ordinary file"):
        evidence.require_local_reports(folder, COMMIT, VERSION)


@pytest.mark.parametrize("kind", ["minimal", "full"])
@pytest.mark.parametrize("field,value", [("commit", "d" * 40), ("version", "1.35.0"), ("sourceIdentity", {})])
def test_each_gallery_report_must_match_the_requested_source(
    gallery_reports: tuple[Path, dict[str, dict[str, Any]]], kind: str, field: str, value: object
) -> None:
    folder, reports = gallery_reports
    changed = dict(reports[kind], **{field: value})
    (folder / f"gallery-{kind}/transformational-intelligence/report.json").write_text(
        json.dumps(changed), encoding="utf-8"
    )
    with pytest.raises(ValueError, match="stale complete"):
        evidence.require_local_reports(folder, COMMIT, VERSION)


def test_package_preflight_consumes_named_reports_before_creating_assets(
    gallery_reports: tuple[Path, dict[str, dict[str, Any]]], monkeypatch: pytest.MonkeyPatch
) -> None:
    folder, _ = gallery_reports
    output = folder.parent / "release"
    configure_preflight(monkeypatch, folder, output)

    class ReachedOutputCreation(Exception):
        pass

    def stop_before_creation(path: Path, *args: Any, **kwargs: Any) -> None:
        assert path == output
        raise ReachedOutputCreation

    with monkeypatch.context() as context:
        context.setattr(Path, "mkdir", stop_before_creation)
        with pytest.raises(ReachedOutputCreation):
            packaging.main()
    assert not output.exists()


@pytest.mark.parametrize("missing", ["minimal", "full"])
def test_package_preflight_requires_each_gallery_report_before_output(
    gallery_reports: tuple[Path, dict[str, dict[str, Any]]], monkeypatch: pytest.MonkeyPatch, missing: str
) -> None:
    folder, _ = gallery_reports
    (folder / f"gallery-{missing}/transformational-intelligence/report.json").unlink()
    output = folder.parent / "release"
    configure_preflight(monkeypatch, folder, output)
    with pytest.raises(ValueError, match="ordinary file"):
        packaging.main()
    assert not output.exists()


def test_gallery_upload_and_bulk_download_keep_named_directories() -> None:
    workflow = yaml.load((ROOT / ".github/workflows/agent-release.yml").read_text(), Loader=yaml.BaseLoader)
    gallery = workflow["jobs"]["gallery"]
    assert gallery["strategy"]["matrix"]["assets"] == ["minimal", "full"]
    upload = next(step for step in gallery["steps"] if "upload-artifact@" in step.get("uses", ""))
    assert upload["with"]["name"] == "gallery-${{ matrix.assets }}"
    assert upload["with"]["path"] == "evidence/"
    download = next(
        step for step in workflow["jobs"]["package"]["steps"] if step.get("with", {}).get("path") == "evidence"
    )
    assert "name" not in download["with"] and "pattern" in download["with"]
    assert download["with"].get("merge-multiple", "false") == "false"
