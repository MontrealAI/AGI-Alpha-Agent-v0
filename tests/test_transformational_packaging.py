# SPDX-License-Identifier: Apache-2.0
"""Exact offline TI delivery and fail-closed new-release evidence gates."""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
import zipfile
from copy import deepcopy
from pathlib import Path

import pytest

from scripts import package_agent_release as packaging
from scripts import transformational_evidence as evidence
from scripts import validate_transformational_intelligence as validation
from scripts import finalize_pages_release, publish_agent_release, successor_alpha_evidence

ROOT = Path(__file__).resolve().parents[1]
COMMIT, VERSION = "a" * 40, "1.36.0"


def report() -> dict:
    return {
        "schema": "agialpha.transformational.acceptance.v1",
        "commit": COMMIT,
        "version": VERSION,
        "mode": "local",
        "origin": (ROOT / "docs/transformational-intelligence/index.html").as_uri(),
        "passed": True,
        "sourceIdentity": evidence.asset_identity(),
        "checks": sorted(evidence.CHECKS),
        "public": None,
    }


def test_exact_standalone_workspace_and_report_are_required(tmp_path: Path) -> None:
    asset = evidence.package_workspace(ROOT, tmp_path)
    raw = (tmp_path / asset["name"]).read_bytes()
    assert raw == (ROOT / "docs/transformational-intelligence/index.html").read_bytes()
    assert asset["sha256"] == hashlib.sha256(raw).hexdigest()
    record = {"local_acceptance": report(), "workspace": asset}
    evidence.verify_release_workspace(record, tmp_path, COMMIT, VERSION)
    with pytest.raises(FileExistsError):
        evidence.package_workspace(ROOT, tmp_path)
    (tmp_path / asset["name"]).write_bytes(raw + b"changed")
    with pytest.raises(ValueError):
        evidence.verify_release_workspace(record, tmp_path, COMMIT, VERSION)


@pytest.mark.parametrize("field,value", [("commit", "b" * 40), ("passed", 1), ("checks", []), ("sourceIdentity", {})])
def test_partial_or_stale_acceptance_cannot_qualify(field: str, value: object) -> None:
    changed = report()
    changed[field] = value
    with pytest.raises(ValueError):
        evidence.verify_report(changed, COMMIT, VERSION, mode="local")


def test_public_acceptance_requires_exact_canonical_https_readback() -> None:
    current = report()
    current.update(
        mode="public",
        origin="https://montrealai.github.io/AGI-Alpha-Agent-v0/transformational-intelligence/",
        public={"httpsVerified": True, "exactPackagedBytes": True, "savedOfflineJourney": True},
    )
    evidence.verify_report(current, COMMIT, VERSION, mode="public")
    for field, value in (("origin", "https://example.org/transformational-intelligence/"), ("public", {})):
        changed = deepcopy(current)
        changed[field] = value
        with pytest.raises(ValueError):
            evidence.verify_report(changed, COMMIT, VERSION, mode="public")
    for name in current["public"]:
        changed = deepcopy(current)
        changed["public"][name] = 1
        with pytest.raises(ValueError):
            evidence.verify_report(changed, COMMIT, VERSION, mode="public")


@pytest.mark.parametrize("problem", ["page", "source", "link"])
def test_source_closure_and_page_tampering_are_refused(tmp_path: Path, problem: str) -> None:
    manifest = json.loads((ROOT / "docs/transformational-intelligence/sources.json").read_text())
    for name in [
        *manifest["sources"],
        "docs/transformational-intelligence/index.html",
        "docs/transformational-intelligence/sources.json",
    ]:
        destination = tmp_path / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, destination)
    evidence.asset_identity(tmp_path)
    target = tmp_path / (
        "docs/transformational-intelligence/index.html" if problem == "page" else next(iter(manifest["sources"]))
    )
    if problem == "link":
        target.unlink()
        target.symlink_to(ROOT / next(iter(manifest["sources"])))
    else:
        target.write_bytes(target.read_bytes() + b"altered")
    with pytest.raises(ValueError):
        evidence.asset_identity(tmp_path)


def test_operator_bundle_contains_all_guides_exact_page_and_public_examples(tmp_path: Path) -> None:
    packaging.copy_release_documents(ROOT, tmp_path, VERSION, COMMIT)
    evidence.package_workspace(ROOT, tmp_path)
    archive_path = packaging.package_operator_guide(ROOT, tmp_path, VERSION)
    with zipfile.ZipFile(archive_path) as archive:
        assert {
            "TRANSFORMATIONAL_IMPLEMENTATION.md",
            "TRANSFORMATIONAL_DISCOVERY.md",
            "TRANSFORMATIONAL_LOCAL_MODEL.md",
            "TRANSFORMATIONAL_POLICY_STUDY.md",
            "TRANSFORMATIONAL_MATH.md",
            "TRANSFORMATIONAL_PUBLIC_PILOT.md",
            "TRANSFORMATIONAL_SOURCE_AUDIT.md",
            "transformational-intelligence-workspace.html",
            "transformational-examples/transformational-intelligence/public-preparation/input.json",
            "transformational-examples/transformational-intelligence/public-preparation/retained-run.json",
            "transformational-examples/transformational-intelligence/public-preparation/direct-origination-profile.md",
            "transformational-examples/transformational-intelligence/public-preparation/ubuntu-ephemeral-creator.md",
            "transformational-examples/transformational-intelligence/public-preparation/LICENSE.Manager",
            "transformational-examples/transformational-source-audit/fixture.json",
            "transformational-examples/transformational-source-audit/expected-results.json",
        } <= set(archive.namelist())
        assert (
            archive.read("transformational-intelligence-workspace.html")
            == (ROOT / "docs/transformational-intelligence/index.html").read_bytes()
        )
        for name in packaging.TI_PUBLIC_EXAMPLES:
            assert (
                archive.read("transformational-examples/" + name.removeprefix("examples/"))
                == (ROOT / name).read_bytes()
            )
        assert "](TRANSFORMATIONAL_DISCOVERY.md)" in archive.read("START_HERE.md").decode()
        assert "](transformational-intelligence-workspace.html)" in archive.read("START_HERE.md").decode()
        assert not any(name.endswith((".key", "journal.sqlite", "api.token")) for name in archive.namelist())


def test_omitted_source_cannot_self_declare_a_smaller_closure(tmp_path: Path) -> None:
    manifest = json.loads((ROOT / "docs/transformational-intelligence/sources.json").read_text())
    names = [
        *manifest["sources"],
        "docs/transformational-intelligence/index.html",
        "docs/transformational-intelligence/sources.json",
    ]
    for name in names:
        destination = tmp_path / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, destination)
    omitted = "examples/transformational-intelligence/vendor/fleet/LICENSE"
    assert manifest["sources"].pop(omitted)
    (tmp_path / "docs/transformational-intelligence/sources.json").write_text(json.dumps(manifest))
    with pytest.raises(ValueError):
        evidence.asset_identity(tmp_path)


def test_public_received_bytes_cannot_be_substituted() -> None:
    directory = ROOT / "docs/transformational-intelligence"
    page, manifest = (directory / "index.html").read_bytes(), (directory / "sources.json").read_bytes()
    validation.verify_received(page, manifest, ROOT / "docs")
    with pytest.raises(ValueError):
        validation.verify_received(page + b"changed", manifest, ROOT / "docs")


def test_duplicate_or_linked_report_is_refused(tmp_path: Path) -> None:
    target = tmp_path / "report.json"
    target.write_text('{"passed":true,"passed":false}')
    with pytest.raises(ValueError, match="Duplicate"):
        evidence.load_report(target)
    link = tmp_path / "linked.json"
    link.symlink_to(target)
    with pytest.raises(ValueError):
        evidence.load_report(link)


def test_missing_ti_report_blocks_packaging_before_creating_assets(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "pyproject.toml").write_text('[project]\nversion = "1.36.0"\n')
    output = tmp_path / "release"
    monkeypatch.setattr(sys, "argv", ["package", "--output", str(output), "--evidence", str(tmp_path / "evidence")])
    monkeypatch.setattr(packaging.subprocess, "run", lambda *args, **kwargs: None)
    monkeypatch.setattr(packaging.subprocess, "check_output", lambda *args, **kwargs: COMMIT)
    monkeypatch.setattr(packaging, "require_historical_evidence", lambda *args: {})
    monkeypatch.setattr(successor_alpha_evidence, "require_local_reports", lambda *args: {"fixture": True})
    with pytest.raises(ValueError):
        packaging.main()
    assert not output.exists()


def test_missing_ti_public_report_blocks_finalization_without_mutation(tmp_path: Path, monkeypatch) -> None:
    folder, public = tmp_path / "release", tmp_path / "evidence/public-pages"
    folder.mkdir()
    public.mkdir(parents=True)
    (folder / "release-manifest.json").write_text(json.dumps({"commit": COMMIT, "version": VERSION}))
    url = "https://montrealai.github.io/AGI-Alpha-Agent-v0/"
    (public / "release.json").write_text(json.dumps({"commit": COMMIT, "version": VERSION, "url": url}))
    (public / "workspace.json").write_text(json.dumps({"origin": url, "model_required": True}))
    monkeypatch.setattr(successor_alpha_evidence, "load_report", lambda *args: {})
    monkeypatch.setattr(successor_alpha_evidence, "verify_report", lambda *args, **kwargs: None)
    monkeypatch.setattr(successor_alpha_evidence, "verify_release_workspace", lambda *args: None)
    before = {path.name: path.read_bytes() for path in folder.iterdir()}
    with pytest.raises(ValueError):
        finalize_pages_release.finalize(folder, tmp_path / "evidence")
    assert before == {path.name: path.read_bytes() for path in folder.iterdir()}


def test_missing_ti_public_report_blocks_external_release_writes(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GITHUB_REPOSITORY", "MontrealAI/AGI-Alpha-Agent-v0")
    monkeypatch.setenv("GITHUB_REF", "refs/heads/main")
    monkeypatch.setenv("GITHUB_SHA", COMMIT)
    (tmp_path / "pyproject.toml").write_text('[project]\nversion = "1.36.0"\n')
    (tmp_path / "release").mkdir()
    (tmp_path / "release/release-manifest.json").write_text(json.dumps({"commit": COMMIT, "version": VERSION}))
    monkeypatch.setattr(successor_alpha_evidence, "verify_report", lambda *args, **kwargs: None)
    monkeypatch.setattr(successor_alpha_evidence, "verify_release_workspace", lambda *args: None)
    calls = []
    monkeypatch.setattr(publish_agent_release, "gh", lambda *args: calls.append(args) or "[]")
    with pytest.raises(ValueError):
        publish_agent_release.main()
    assert calls == [("api", "repos/MontrealAI/AGI-Alpha-Agent-v0/releases?per_page=100")]
