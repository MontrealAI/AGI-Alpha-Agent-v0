# SPDX-License-Identifier: Apache-2.0
"""Fail-closed flagship packaging and final-publication acceptance regression checks."""

from __future__ import annotations

import hashlib
import json
import sys
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

import pytest

from scripts import finalize_pages_release, package_agent_release, successor_alpha_evidence as evidence

COMMIT = "a" * 40
VERSION = "1.34.0"


def source_fixture(root: Path) -> dict[str, object]:
    sources = {}
    for name in evidence.MODULE_ROOTS:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        source = "export const VERSION = 'fixture';\n"
        path.write_text(source, encoding="utf-8")
        sources[name] = hashlib.sha256(source.encode()).hexdigest()
    template = root / "scripts/templates/successor-alpha/index.html"
    template.parent.mkdir(parents=True)
    template.write_text("template\n", encoding="utf-8")
    sources[template.relative_to(root).as_posix()] = hashlib.sha256(template.read_bytes()).hexdigest()
    implementation = {name: sources[name] for name in evidence.MODULE_ROOTS}
    source_hash = hashlib.sha256(json.dumps(implementation, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    page = root / "docs/successor/alpha/index.html"
    page.parent.mkdir(parents=True)
    page.write_bytes(b"<!doctype html><html lang=en>Exact standalone flagship</html>\n")
    manifest = {
        "schema": "successor-alpha-source/v1",
        "sources": sources,
        "engineSourceHash": source_hash,
        "pageSha256": hashlib.sha256(page.read_bytes()).hexdigest(),
    }
    page.with_name("sources.json").write_text(json.dumps(manifest), encoding="utf-8")
    return evidence.asset_identity(root)


def report_fixture(root: Path, mode: str = "local") -> dict[str, object]:
    origin = evidence.PUBLIC_ORIGIN if mode == "public" else "file:///accepted/site/successor/alpha/index.html"
    return {
        "schema": evidence.SCHEMA,
        "passed": True,
        "commit": COMMIT,
        "version": VERSION,
        "mode": mode,
        "origin": origin,
        "sourceIdentity": evidence.asset_identity(root),
        "public": (
            {"url": origin, "httpsVerified": True, "exactPackagedBytes": True, "assets": ["index.html", "sources.json"]}
            if mode == "public"
            else None
        ),
        "journey": {
            "passed": True,
            "entryUrl": origin,
            "accessibilityAudited": True,
            "languages": ["en", "fr"],
            "viewports": [1440, 390, 320],
            "checks": sorted(evidence.REQUIRED_CHECKS),
            "errors": [],
            "browser_errors": [],
            "http_failures": [],
        },
    }


@pytest.mark.parametrize("mode", ["local", "public"])
def test_exact_source_complete_journey_acceptance_is_required(tmp_path: Path, mode: str) -> None:
    source_fixture(tmp_path)
    report = report_fixture(tmp_path, mode)
    evidence.verify_report(report, COMMIT, VERSION, mode=mode, root=tmp_path)
    for name, replacement in (("commit", "b" * 40), ("version", "1.33.0"), ("passed", False), ("mode", "other")):
        changed = deepcopy(report)
        changed[name] = replacement
        with pytest.raises(ValueError):
            evidence.verify_report(changed, COMMIT, VERSION, mode=mode, root=tmp_path)
    for check in evidence.REQUIRED_CHECKS:
        changed = deepcopy(report)
        changed["journey"]["checks"].remove(check)
        with pytest.raises(ValueError):
            evidence.verify_report(changed, COMMIT, VERSION, mode=mode, root=tmp_path)


def test_wrong_origin_partial_accessibility_and_false_public_byte_claims_are_rejected(tmp_path: Path) -> None:
    source_fixture(tmp_path)
    report = report_fixture(tmp_path, "public")
    for origin in (
        "http://montrealai.github.io/AGI-Alpha-Agent-v0/successor/alpha/",
        "https://example.test/successor/alpha/",
        evidence.PUBLIC_ORIGIN + "?stale=1",
        evidence.PUBLIC_ORIGIN + "index.html",
    ):
        changed = deepcopy(report)
        changed["origin"] = origin
        changed["journey"]["entryUrl"] = origin
        with pytest.raises(ValueError):
            evidence.verify_report(changed, COMMIT, VERSION, mode="public", root=tmp_path)
    for key, value in (
        ("accessibilityAudited", False),
        ("languages", ["en"]),
        ("viewports", [1440, 390]),
        ("errors", ["failed"]),
        ("browser_errors", ["CSP violation"]),
        ("http_failures", [404]),
    ):
        changed = deepcopy(report)
        changed["journey"][key] = value
        with pytest.raises(ValueError):
            evidence.verify_report(changed, COMMIT, VERSION, mode="public", root=tmp_path)
    for key in ("httpsVerified", "exactPackagedBytes"):
        changed = deepcopy(report)
        changed["public"][key] = False
        with pytest.raises(ValueError):
            evidence.verify_report(changed, COMMIT, VERSION, mode="public", root=tmp_path)
    with pytest.raises(ValueError):
        evidence.verify_report(report, COMMIT, VERSION, mode="local", root=tmp_path)


def test_stale_generated_page_module_and_template_are_each_rejected(tmp_path: Path) -> None:
    source_fixture(tmp_path)
    report = report_fixture(tmp_path)
    for name in (
        "docs/successor/alpha/index.html",
        evidence.MODULE_ROOTS[0],
        "scripts/templates/successor-alpha/index.html",
    ):
        path = tmp_path / name
        raw = path.read_bytes()
        path.write_bytes(raw + b"changed\n")
        with pytest.raises(ValueError):
            evidence.verify_report(report, COMMIT, VERSION, mode="local", root=tmp_path)
        path.write_bytes(raw)
    evidence.verify_report(report, COMMIT, VERSION, mode="local", root=tmp_path)


def test_source_inventory_cannot_omit_a_reviewed_module_even_when_rehashed(tmp_path: Path) -> None:
    source_fixture(tmp_path)
    manifest_path = tmp_path / "docs/successor/alpha/sources.json"
    manifest = json.loads(manifest_path.read_text())
    del manifest["sources"][evidence.MODULE_ROOTS[0]]
    manifest_path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="omits"):
        evidence.asset_identity(tmp_path)


def test_both_gallery_matrix_reports_are_required(tmp_path: Path) -> None:
    source_fixture(tmp_path)
    report = report_fixture(tmp_path)
    folder = tmp_path / "evidence"
    for kind in ("minimal", "full"):
        target = folder / f"gallery-{kind}/successor-alpha/report.json"
        target.parent.mkdir(parents=True)
        target.write_text(json.dumps(report))
    accepted = evidence.require_local_reports(folder, COMMIT, VERSION, root=tmp_path)
    assert set(accepted) == {"minimal", "full"}
    (folder / "gallery-minimal/successor-alpha/report.json").unlink()
    with pytest.raises(ValueError):
        evidence.require_local_reports(folder, COMMIT, VERSION, root=tmp_path)


def test_missing_duplicate_or_symlinked_reports_do_not_satisfy_the_gate(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        evidence.load_report(tmp_path / "missing.json")
    target = tmp_path / "report.json"
    target.write_text('{"passed":true,"passed":false}')
    with pytest.raises(ValueError, match="duplicate"):
        evidence.load_report(target)
    link = tmp_path / "link.json"
    link.symlink_to(target)
    with pytest.raises(ValueError):
        evidence.load_report(link)


def test_standalone_asset_is_byte_exact_and_cannot_overwrite_an_existing_file(tmp_path: Path) -> None:
    source = tmp_path / "source"
    identity = source_fixture(source)
    output = tmp_path / "release"
    output.mkdir()
    result = package_agent_release.package_successor_alpha_workspace(source, output)
    raw = (output / "successor-alpha-workspace.html").read_bytes()
    assert raw == (source / "docs/successor/alpha/index.html").read_bytes()
    assert result == {"name": "successor-alpha-workspace.html", "bytes": len(raw), "sha256": identity["pageSha256"]}
    with pytest.raises(FileExistsError):
        package_agent_release.package_successor_alpha_workspace(source, output)
    assert (output / "successor-alpha-workspace.html").read_bytes() == raw


def test_packaged_workspace_requires_both_local_acceptances_and_the_exact_page(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source_fixture(source)
    output = tmp_path / "release"
    output.mkdir()
    asset = package_agent_release.package_successor_alpha_workspace(source, output)
    local = report_fixture(source)
    record = {"workspace": asset, "local_acceptance": {"minimal": local, "full": local}}
    evidence.verify_release_workspace(record, output, COMMIT, VERSION, root=source)
    incomplete = deepcopy(record)
    del incomplete["local_acceptance"]["full"]
    with pytest.raises(ValueError):
        evidence.verify_release_workspace(incomplete, output, COMMIT, VERSION, root=source)
    (output / "successor-alpha-workspace.html").write_bytes(b"other workspace")
    with pytest.raises(ValueError):
        evidence.verify_release_workspace(record, output, COMMIT, VERSION, root=source)


def test_new_release_packaging_refuses_missing_flagship_evidence_before_creating_assets(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text('[project]\nversion = "1.34.0"\n')
    args = ["package", "--output", str(tmp_path / "release"), "--evidence", str(tmp_path / "evidence")]
    with (
        patch.object(sys, "argv", args),
        patch("os.getcwd", return_value=str(tmp_path)),
        patch.object(package_agent_release.subprocess, "run"),
        patch.object(package_agent_release.subprocess, "check_output", return_value=COMMIT),
        patch.object(package_agent_release, "require_historical_evidence", return_value={}),
        patch.object(package_agent_release.tomllib, "loads", return_value={"project": {"version": VERSION}}),
    ):
        with pytest.raises(ValueError):
            package_agent_release.main()
    assert not (tmp_path / "release").exists()


def test_public_finalization_refuses_missing_flagship_evidence_without_changing_assets(tmp_path: Path) -> None:
    folder, public = tmp_path / "release", tmp_path / "evidence/public-pages"
    folder.mkdir()
    public.mkdir(parents=True)
    manifest = {"commit": COMMIT, "version": VERSION, "release_gates": []}
    (folder / "release-manifest.json").write_text(json.dumps(manifest))
    (folder / "keep.txt").write_bytes(b"existing package")
    site = "https://montrealai.github.io/AGI-Alpha-Agent-v0/"
    (public / "release.json").write_text(json.dumps({"commit": COMMIT, "version": VERSION, "url": site}))
    (public / "workspace.json").write_text(json.dumps({"origin": site, "model_required": True}))
    before = {path.name: path.read_bytes() for path in folder.iterdir()}
    with pytest.raises(ValueError):
        finalize_pages_release.finalize(folder, tmp_path / "evidence")
    assert {path.name: path.read_bytes() for path in folder.iterdir()} == before


def test_three_flagship_guides_are_in_the_operator_release_documents() -> None:
    documents = set(package_agent_release.release_documents(VERSION))
    assert {
        "docs/agent/SUCCESSOR_ALPHA.md",
        "docs/agent/SUCCESSOR_ALPHA_DEPLOYMENT.md",
        "docs/agent/SUCCESSOR_ALPHA_CONTINUITY.md",
    } <= documents


@pytest.mark.parametrize("problem", ["missing", "stale", "partial", "wrong-origin", "workspace-missing"])
def test_new_publication_refuses_missing_or_incomplete_finalized_flagship_before_external_writes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, problem: str
) -> None:
    from scripts import publish_agent_release

    source = tmp_path / "source"
    identity = source_fixture(source)
    report = report_fixture(source, "public")
    manifest = {"commit": COMMIT, "version": VERSION}
    if problem != "missing":
        if problem == "stale":
            report["commit"] = "b" * 40
        elif problem == "partial":
            report["journey"]["checks"].remove("native-sdk-and-node-host-return-import")
        elif problem == "wrong-origin":
            report["origin"] = "https://example.test/successor/alpha/"
        manifest["public_successor_alpha"] = report
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GITHUB_REPOSITORY", "MontrealAI/AGI-Alpha-Agent-v0")
    monkeypatch.setenv("GITHUB_REF", "refs/heads/main")
    monkeypatch.setenv("GITHUB_SHA", COMMIT)
    (tmp_path / "pyproject.toml").write_text('[project]\nversion = "1.34.0"\n')
    folder = tmp_path / "release"
    folder.mkdir()
    (folder / "release-manifest.json").write_text(json.dumps(manifest))
    before = {path.name: path.read_bytes() for path in folder.iterdir()}
    calls = []

    def read_only_github(*args: str) -> str:
        calls.append(args)
        assert args == ("api", "repos/MontrealAI/AGI-Alpha-Agent-v0/releases?per_page=100")
        return "[]"

    monkeypatch.setattr(publish_agent_release, "gh", read_only_github)
    monkeypatch.setattr(evidence, "asset_identity", lambda root=evidence.ROOT: identity)

    def no_external_command(*args: object, **kwargs: object) -> None:
        raise AssertionError("Missing flagship proof must fail before any tag, draft, upload or external command")

    monkeypatch.setattr(publish_agent_release.subprocess, "run", no_external_command)
    with pytest.raises(ValueError):
        publish_agent_release.main()
    assert len(calls) == 1
    assert {path.name: path.read_bytes() for path in folder.iterdir()} == before


def test_already_public_new_version_remains_a_read_only_idempotent_return(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from scripts import publish_agent_release

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GITHUB_REPOSITORY", "MontrealAI/AGI-Alpha-Agent-v0")
    monkeypatch.setenv("GITHUB_REF", "refs/heads/main")
    monkeypatch.setenv("GITHUB_SHA", COMMIT)
    (tmp_path / "pyproject.toml").write_text('[project]\nversion = "1.34.0"\n')
    folder = tmp_path / "release"
    folder.mkdir()
    (folder / "release-manifest.json").write_text(json.dumps({"commit": COMMIT, "version": VERSION}))
    calls = []

    def read_only_github(*args: str) -> str:
        calls.append(args)
        assert args[0] == "api" and len(args) == 2
        if args[1].endswith("releases?per_page=100"):
            return json.dumps([{"tag_name": "v1.34.0", "draft": False, "html_url": "https://example.test/release"}])
        assert args[1].endswith("/git/ref/tags/v1.34.0")
        return json.dumps({"object": {"type": "commit", "sha": COMMIT}})

    monkeypatch.setattr(publish_agent_release, "gh", read_only_github)
    publish_agent_release.main()
    assert len(calls) == 2
