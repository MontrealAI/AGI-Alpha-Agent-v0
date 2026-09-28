# SPDX-License-Identifier: Apache-2.0
"""Ordinary main commits must never replace an already published version."""

from __future__ import annotations

import json
import hashlib
from html.parser import HTMLParser
from pathlib import Path
import re
import subprocess
import sys
import tomllib
from urllib.parse import urlsplit
import zipfile

import pytest

from scripts import finalize_pages_release, publish_agent_release, release_context
from scripts import ascension_protocol_evidence, package_agent_release, business3_evidence, governance_evidence


def test_source_version_and_catalog_match_the_release_without_installed_metadata(monkeypatch) -> None:
    import importlib.metadata
    import runpy
    import tomllib

    root = Path(__file__).resolve().parents[1]
    version = tomllib.loads((root / "pyproject.toml").read_text())["project"]["version"]

    def missing_distribution(_name: str) -> str:
        raise importlib.metadata.PackageNotFoundError

    monkeypatch.setattr(importlib.metadata, "version", missing_distribution)
    package = runpy.run_path(str(root / "alpha_factory_v1/__init__.py"))
    assert package["__version__"] == version
    assert json.loads((root / "alpha_factory_v1/demos/catalog.json").read_text())["release"] == version


def test_every_current_workspace_uses_the_release_version() -> None:
    root = Path(__file__).resolve().parents[1]
    version = tomllib.loads((root / "pyproject.toml").read_text())["project"]["version"]

    class VersionParser(HTMLParser):
        def __init__(self) -> None:
            super().__init__()
            self.versions: list[str | None] = []

        def handle_starttag(self, tag, attrs) -> None:
            values = dict(attrs)
            if tag == "meta" and values.get("name") == "application-version":
                self.versions.append(values.get("content"))

    for name in (
        "",
        "studio/",
        "ascension/",
        "ascension-protocol/",
        "insight/",
        "bloom/",
        "compounding/",
        "alpha_agi_business_3_v1/",
        "solving_agi_governance/",
        "alpha_factory_v1/demos/solving_agi_governance/",
        "alpha_factory_v1/demos/ascension-protocol/",
        "alpha_factory_v1/demos/alpha_agi_business_3_v1/",
    ):
        page = root / "docs" / name / "index.html"
        parser = VersionParser()
        parser.feed(page.read_text())
        assert parser.versions == [version], f"Stale release metadata in {page}"


@pytest.mark.parametrize("head,kind", [("a" * 40, "commit"), ("b" * 40, "commit"), ("a" * 40, "tag")])
def test_remote_main_must_still_match_before_publication(monkeypatch, head, kind) -> None:
    monkeypatch.setenv("GITHUB_REPOSITORY", release_context.REPOSITORY)
    monkeypatch.setenv("GITHUB_REF", "refs/heads/main")
    monkeypatch.setenv("GITHUB_SHA", "a" * 40)
    monkeypatch.setattr(
        release_context.subprocess,
        "check_output",
        lambda *args, **kwargs: json.dumps({"ref": "refs/heads/main", "object": {"sha": head, "type": kind}}),
    )
    if head == "a" * 40 and kind == "commit":
        assert release_context.require_current_main() == head
    else:
        with pytest.raises(RuntimeError, match="Superseded"):
            release_context.require_current_main()


@pytest.mark.parametrize(
    "variable,value", [("GITHUB_REPOSITORY", "other/repo"), ("GITHUB_REF", "refs/tags/v1.5.1"), ("GITHUB_SHA", "bad")]
)
def test_unauthorized_context_fails_before_network(monkeypatch, variable, value) -> None:
    monkeypatch.setenv("GITHUB_REPOSITORY", release_context.REPOSITORY)
    monkeypatch.setenv("GITHUB_REF", "refs/heads/main")
    monkeypatch.setenv("GITHUB_SHA", "a" * 40)
    monkeypatch.setenv(variable, value)
    monkeypatch.setattr(
        release_context.subprocess, "check_output", lambda *args, **kwargs: pytest.fail("network access")
    )
    with pytest.raises(ValueError):
        release_context.require_current_main()


@pytest.mark.parametrize("superseded_at", [1, 2])
def test_superseded_run_cannot_publish_even_if_main_moves_during_upload(tmp_path, monkeypatch, superseded_at) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GITHUB_REPOSITORY", release_context.REPOSITORY)
    monkeypatch.setenv("GITHUB_REF", "refs/heads/main")
    monkeypatch.setenv("GITHUB_SHA", "a" * 40)
    folder = tmp_path / "release"
    folder.mkdir()
    (folder / "release-manifest.json").write_text(json.dumps({"commit": "a" * 40, "version": "1.5.1"}))
    (folder / "RELEASE_NOTES_1.5.1.md").write_text("Verified fixture")
    (tmp_path / "pyproject.toml").write_text('[project]\nversion = "1.5.1"\n')
    calls = []
    checks = []

    def context():
        checks.append(True)
        if len(checks) == superseded_at:
            raise RuntimeError("Superseded release run")
        return "a" * 40

    def github(*args):
        calls.append(args)
        if args[:2] == ("release", "download"):
            dest = Path(args[-1])
            for path in folder.iterdir():
                (dest / path.name).write_bytes(path.read_bytes())
            return ""
        if args[0] == "api":
            assert len(args) == 2 and "/releases?" in args[1], "Unexpected API mutation"
            return json.dumps(
                [{"id": 1, "tag_name": "v1.5.1", "draft": True, "assets": [{"name": p.name} for p in folder.iterdir()]}]
            )
        assert args[:2] == ("release", "upload")
        return ""

    monkeypatch.setattr(publish_agent_release, "require_current_main", context)
    monkeypatch.setattr(publish_agent_release, "gh", github)
    monkeypatch.setattr(
        publish_agent_release.subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            [], 0, json.dumps({"object": {"type": "commit", "sha": "a" * 40}})
        ),
    )
    with pytest.raises(RuntimeError, match="Superseded"):
        publish_agent_release.main()
    assert len(checks) == superseded_at
    assert not any("PATCH" in call for call in calls)
    if superseded_at == 1:
        assert len(calls) == 1


@pytest.mark.parametrize("version", ["1.2.0", "1.2.1"])
def test_public_version_is_left_unchanged(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, version: str) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GITHUB_REPOSITORY", "MontrealAI/AGI-Alpha-Agent-v0")
    monkeypatch.setenv("GITHUB_REF", "refs/heads/main")
    monkeypatch.setenv("GITHUB_SHA", "a" * 40)
    release = tmp_path / "release"
    release.mkdir()
    (release / "release-manifest.json").write_text(json.dumps({"commit": "a" * 40, "version": version}))
    (tmp_path / "pyproject.toml").write_text(f'[project]\nversion = "{version}"\n')
    calls = []

    def read_public_release(*args: str) -> str:
        calls.append(args)
        assert args == ("api", "repos/MontrealAI/AGI-Alpha-Agent-v0/releases?per_page=100")
        return json.dumps([{"tag_name": f"v{version}", "draft": False, "html_url": "https://example.test/release"}])

    def no_mutation(*args: object, **kwargs: object) -> None:
        raise AssertionError("An existing public version must not invoke any mutation")

    monkeypatch.setattr(publish_agent_release, "gh", read_public_release)
    monkeypatch.setattr(publish_agent_release.subprocess, "run", no_mutation)
    publish_agent_release.main()
    assert len(calls) == 1


@pytest.mark.parametrize("version", ["1.2.0", "../../other-tag", 121])
def test_invalid_package_version_cannot_publish(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, version: object
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GITHUB_REPOSITORY", "MontrealAI/AGI-Alpha-Agent-v0")
    monkeypatch.setenv("GITHUB_REF", "refs/heads/main")
    monkeypatch.setenv("GITHUB_SHA", "a" * 40)
    release = tmp_path / "release"
    release.mkdir()
    (release / "release-manifest.json").write_text(json.dumps({"commit": "a" * 40, "version": version}))
    (tmp_path / "pyproject.toml").write_text('[project]\nversion = "1.2.1"\n')

    def no_github_access(*args: object, **kwargs: object) -> None:
        raise AssertionError("An invalid package must be rejected before any GitHub access")

    monkeypatch.setattr(publish_agent_release, "gh", no_github_access)
    monkeypatch.setattr(publish_agent_release.subprocess, "run", no_github_access)
    with pytest.raises(ValueError, match="package version differs"):
        publish_agent_release.main()


@pytest.mark.parametrize(
    "version,problem",
    [
        ("1.4.0", None),
        ("1.4.0", "commit"),
        ("1.4.0", "asset"),
        ("1.5.0", None),
        ("1.5.0", "commit"),
        ("1.5.0", "asset"),
        ("1.5.0", "ascension"),
        ("1.5.0", "paper"),
        ("1.5.0", "origin"),
        ("1.6.0", None),
        ("1.7.0", None),
        *[
            ("1.8.0", problem)
            for problem in (
                None,
                "transfer-failed",
                "transfer-origin",
                "transfer-check",
                "transfer-scenario",
                "transfer-browser",
                "transfer-schema",
                "transfer-manuscript",
            )
        ],
        *[
            ("1.10.0", problem)
            for problem in (
                None,
                "studio-failed",
                "studio-origin",
                "studio-check",
                "studio-case",
                "studio-browser",
                "studio-http",
                "studio-schema",
                "studio-commit",
                "studio-version",
                "studio-calculation",
            )
        ],
        ("1.7.0", "bloom-failed"),
        *[
            ("1.12.1", problem)
            for problem in (
                None,
                "protocol-failed",
                "protocol-boolean",
                "protocol-origin",
                "protocol-commit",
                "protocol-version",
                "protocol-schema",
                "protocol-check",
                "protocol-asset",
                "protocol-browser",
                "protocol-http",
            )
        ],
        *[
            ("1.13.0", problem)
            for problem in (None, "business3-failed", "business3-check", "business3-asset", "business3-cases")
        ],
        *[
            ("1.14.0", problem)
            for problem in (None, "governance-failed", "governance-check", "governance-asset", "governance-cases")
        ],
        ("1.7.0", "bloom-origin"),
        ("1.7.0", "bloom-check"),
        ("1.7.0", "bloom-experience"),
        ("1.7.0", "bloom-browser"),
        ("1.7.0", "bloom-schema"),
        ("1.6.0", "atlas-failed"),
        ("1.6.0", "atlas-origin"),
        ("1.6.0", "atlas-check"),
        ("1.6.0", "atlas-scenario"),
        ("1.6.0", "atlas-browser"),
        ("1.6.0", "atlas-schema"),
    ],
)
def test_public_evidence_requires_same_commit_and_intact_package(
    tmp_path: Path, problem: str | None, version: str
) -> None:
    folder = tmp_path / "release"
    evidence = tmp_path / "evidence"
    folder.mkdir()
    (evidence / "public-pages").mkdir(parents=True)
    manifest = {"version": version, "commit": "a" * 40, "release_gates": []}
    (folder / "release-manifest.json").write_text(json.dumps(manifest))
    archive_path = folder / f"alpha-agent-v{version}-validation.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("existing.txt", "existing evidence")
    (folder / "source.zip").write_bytes(b"immutable source fixture")
    checksums = [f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}" for p in sorted(folder.iterdir())]
    (folder / "SHA256SUMS").write_text("\n".join(checksums) + "\n")
    url = "https://montrealai.github.io/AGI-Alpha-Agent-v0/"
    public = {**manifest, "url": url}
    if problem == "commit":
        public["commit"] = "b" * 40
    if problem == "asset":
        (folder / "source.zip").write_bytes(b"corrupted source fixture")
    (evidence / "public-pages" / "release.json").write_text(json.dumps(public))
    (evidence / "public-pages" / "workspace.json").write_text(json.dumps({"origin": url, "model_required": True}))
    if tuple(map(int, version.split("."))) >= (1, 5, 0):
        ascension_dir = evidence / "public-pages" / "ascension"
        ascension_dir.mkdir()
        (ascension_dir / "ascension.json").write_text(
            json.dumps(
                {
                    "origin": "https://example.test/" if problem == "origin" else url,
                    "passed": problem != "ascension",
                    "paper_sha256": (
                        "altered"
                        if problem == "paper"
                        else "fd14d444d51e9f6ebaec13387fc8d2170615d1bbfab13edc7e84ea1f655d20aa"
                    ),
                }
            )
        )
    if tuple(map(int, version.split("."))) >= (1, 6, 0):
        atlas_dir = evidence / "public-pages" / "insight-atlas"
        atlas_dir.mkdir()
        atlas = {
            "schema": "agialpha.insight.acceptance.v1",
            "origin": url,
            "passed": True,
            "scenarios": [{"id": name} for name in ("energy", "science", "enterprise")],
            "browser_errors": [],
            "checks": [
                "all-three-scenarios",
                "stale-proof-rejected",
                "tampered-proof-rejected",
                "unsafe-quorum-blocked",
                "native-mission-schema",
                "native-research-execution-and-signed-export",
                "reviewed-design-reuse-requires-fresh-evidence",
                "recovery-replays-promotions",
                "tampered-history-rejected",
                "revocation-survives-recovery",
                "mirrored-page",
                "offline-reload-recovery-and-replay",
                "axe-wcag-a-aa-no-violations",
                "keyboard-selection-retains-focus",
            ],
        }
        if problem == "atlas-failed":
            atlas["passed"] = False
        elif problem == "atlas-origin":
            atlas["origin"] = "https://example.test/"
        elif problem == "atlas-check":
            atlas["checks"].remove("tampered-proof-rejected")
        elif problem == "atlas-scenario":
            atlas["scenarios"].pop()
        elif problem == "atlas-browser":
            atlas["browser_errors"] = ["uncaught error"]
        elif problem == "atlas-schema":
            atlas["schema"] = "declared-pass-only"
        (atlas_dir / "insight-atlas.json").write_text(json.dumps(atlas))
    if tuple(map(int, version.split("."))) >= (1, 7, 0):
        bloom_dir = evidence / "public-pages" / "proof-bloom"
        bloom_dir.mkdir()
        bloom = {
            "schema": "agialpha.bloom.acceptance.v1",
            "origin": url,
            "passed": True,
            "experiences": [{"id": name} for name in ("nova", "sovereign", "omega", "invention", "proof")],
            "browser_errors": [],
            "checks": [
                "all-five-experiences",
                "original-gallery-preserved",
                "baseline-and-stress-computed",
                "native-missions-executed-and-signed-returns",
                "signature-key-and-input-binding",
                "self-declared-verdict-rejected",
                "tampered-and-stale-return-rejected",
                "reviewed-failure-remains-hold",
                "exact-benchmark-reuse-needs-fresh-probes",
                "transitive-revocation",
                "unchanged-recovery-roundtrip",
                "tampered-history-rejected-atomically",
                "jobspec-download-sha256",
                "keyboard-focus-preserved",
                "input-text-escaped",
                "mirrored-page",
                "offline-recovery-and-execution",
                "mobile-no-overflow",
                "axe-wcag-a-aa-no-violations",
            ],
        }
        if problem == "bloom-failed":
            bloom["passed"] = False
        elif problem == "bloom-origin":
            bloom["origin"] = "https://example.test/"
        elif problem == "bloom-check":
            bloom["checks"].remove("signature-key-and-input-binding")
        elif problem == "bloom-experience":
            bloom["experiences"].pop()
        elif problem == "bloom-browser":
            bloom["browser_errors"] = ["uncaught error"]
        elif problem == "bloom-schema":
            bloom["schema"] = "self-declared-pass"
        (bloom_dir / "proof-bloom.json").write_text(json.dumps(bloom))
    if tuple(map(int, version.split("."))) >= (1, 8, 0):
        target = evidence / "public-pages" / "compounding"
        target.mkdir()
        transfer = {
            "schema": "agialpha.transfer.acceptance.v1",
            "origin": url,
            "passed": True,
            "scenarios": [{"id": name} for name in ("seasonal", "shift", "ablation")],
            "browser_errors": [],
            "manuscript_sha256": "4b290d5a8232364b8808c0af8a96e7c9b152afd7ac3f5ba05668a538e073791a",
            "checks": [
                "exact-198-page-manuscript",
                "all-three-scenarios",
                "python-javascript-exact-replay",
                "complete-docket-zip-replay",
                "review-does-not-override-loss",
                "archive-ablation-zero-gain",
                "eci-e2-no-independent-claim",
                "native-cli-browser-handoff",
                "imported-review-keeps-timing-provenance",
                "tampered-and-stale-import-rejected-atomically",
                "cost-overhead-closes-gate",
                "changed-inputs-clear-review",
                "keyboard-focus-preserved",
                "axe-wcag-a-aa-no-violations",
                "mobile-no-overflow",
                "offline-recovery-and-execution",
                "mirrored-page",
            ],
        }
        if problem == "transfer-failed":
            transfer["passed"] = False
        elif problem == "transfer-origin":
            transfer["origin"] = "https://example.test/"
        elif problem == "transfer-check":
            transfer["checks"].remove("complete-docket-zip-replay")
        elif problem == "transfer-scenario":
            transfer["scenarios"].pop()
        elif problem == "transfer-browser":
            transfer["browser_errors"] = ["uncaught error"]
        elif problem == "transfer-schema":
            transfer["schema"] = "declared-pass"
        elif problem == "transfer-manuscript":
            transfer["manuscript_sha256"] = "0" * 64
        (target / "compounding.json").write_text(json.dumps(transfer))
    if tuple(map(int, version.split("."))) >= (1, 10, 0):
        target = evidence / "public-pages" / "decision-studio"
        target.mkdir()
        studio = {
            "schema": "agialpha.decision.acceptance.v1",
            "origin": url,
            "passed": True,
            "commit": manifest["commit"],
            "version": version,
            "calculation_version": "1.10.0",
            "browser_errors": [],
            "http_failures": [],
            "cases": [
                {"id": name}
                for name in (
                    "capital",
                    "invention",
                    "supply",
                    "delivery",
                    "launch",
                    "inventory",
                    "service",
                    "energy",
                    "proof",
                    "nova",
                    "agency",
                )
            ],
            "checks": [
                "all-case-calculations",
                "downloaded-dossier-cli-replay",
                "edited-input-invalidation",
                "worker-cancellation",
                "forgery-rejection",
                "csv-import-infeasibility",
                "explicit-save-restore-clear",
                "all-artifact-downloads",
                "mobile-no-overflow",
                "accessible-controls",
                "practical-catalog-search",
                "legacy-route-bridge",
                "offline-recalculation",
                "public-current-assets",
                "staffing-cap-and-backlog-hold",
                "editable-table-keyboard-focus",
                "archived-dossier-replay",
            ],
        }
        changes = {
            "studio-failed": ("passed", False),
            "studio-origin": ("origin", "https://example.test/"),
            "studio-check": ("checks", []),
            "studio-case": ("cases", []),
            "studio-browser": ("browser_errors", ["uncaught"]),
            "studio-http": ("http_failures", ["404"]),
            "studio-schema": ("schema", "unverified"),
            "studio-commit": ("commit", "b" * 40),
            "studio-version": ("version", "1.9.0"),
            "studio-calculation": ("calculation_version", "1.9.0"),
        }
        if problem in changes:
            key, value = changes[problem]
            studio[key] = value
        (target / "decision-studio.json").write_text(json.dumps(studio))
    if tuple(map(int, version.split("."))) >= (1, 12, 1):
        target = evidence / "public-pages" / "ascension-protocol"
        target.mkdir()
        protocol = {
            "schema": ascension_protocol_evidence.SCHEMA,
            "passed": True,
            "origin": url,
            "commit": manifest["commit"],
            "version": version,
            "checks": sorted(ascension_protocol_evidence.CHECKS),
            "asset_sha256": ascension_protocol_evidence.asset_hashes(),
            "browser_errors": [],
            "http_failures": [],
        }
        changes = {
            "protocol-failed": ("passed", False),
            "protocol-boolean": ("passed", 1),
            "protocol-origin": ("origin", "https://example.test/"),
            "protocol-commit": ("commit", "b" * 40),
            "protocol-version": ("version", "1.12.0"),
            "protocol-schema": ("schema", "unverified"),
            "protocol-check": ("checks", []),
            "protocol-asset": ("asset_sha256", {}),
            "protocol-browser": ("browser_errors", ["uncaught"]),
            "protocol-http": ("http_failures", ["404"]),
        }
        if problem in changes:
            key, value = changes[problem]
            protocol[key] = value
        (target / "report.json").write_text(json.dumps(protocol))
    if tuple(map(int, version.split("."))) >= (1, 13, 0):
        target = evidence / "public-pages" / "business3"
        target.mkdir()
        business3 = {
            "schema": business3_evidence.SCHEMA,
            "passed": True,
            "origin": url,
            "commit": manifest["commit"],
            "version": version,
            "checks": sorted(business3_evidence.CHECKS),
            "assets": business3_evidence.asset_hashes(),
            "cases": business3_evidence.expected_cases(),
            "browser_errors": [],
            "http_failures": [],
        }
        changes = {
            "business3-failed": ("passed", False),
            "business3-check": ("checks", []),
            "business3-asset": ("assets", {}),
            "business3-cases": ("cases", []),
        }
        if problem in changes:
            key, value = changes[problem]
            business3[key] = value
        (target / "business3.json").write_text(json.dumps(business3))
    if tuple(map(int, version.split("."))) >= (1, 14, 0):
        target = evidence / "public-pages" / "governance"
        target.mkdir()
        governance = {
            "schema": governance_evidence.SCHEMA,
            "passed": True,
            "origin": url,
            "commit": manifest["commit"],
            "version": version,
            "checks": sorted(governance_evidence.CHECKS),
            "assets": governance_evidence.asset_hashes(),
            "cases": governance_evidence.expected_cases(),
            "browser_errors": [],
            "http_failures": [],
        }
        changes = {
            "governance-failed": ("passed", False),
            "governance-check": ("checks", []),
            "governance-asset": ("assets", {}),
            "governance-cases": ("cases", []),
        }
        if problem in changes:
            key, value = changes[problem]
            governance[key] = value
        (target / "governance.json").write_text(json.dumps(governance))
    before = {p.name: p.read_bytes() for p in folder.iterdir()}
    if problem:
        with pytest.raises(ValueError):
            finalize_pages_release.finalize(folder, evidence)
        assert {p.name: p.read_bytes() for p in folder.iterdir()} == before
        return
    finalize_pages_release.finalize(folder, evidence)
    if tuple(map(int, version.split("."))) >= (1, 6, 0):
        assert json.loads((folder / "release-manifest.json").read_text())["public_insight_atlas"]["passed"]
    if tuple(map(int, version.split("."))) >= (1, 7, 0):
        assert json.loads((folder / "release-manifest.json").read_text())["public_proof_bloom"]["passed"]
    if tuple(map(int, version.split("."))) >= (1, 10, 0):
        assert (
            json.loads((folder / "release-manifest.json").read_text())["public_decision_studio"]["commit"]
            == manifest["commit"]
        )
    if tuple(map(int, version.split("."))) >= (1, 12, 1):
        assert json.loads((folder / "release-manifest.json").read_text())["public_ascension_protocol"] == protocol
    if tuple(map(int, version.split("."))) >= (1, 13, 0):
        assert json.loads((folder / "release-manifest.json").read_text())["public_business3"] == business3
    if tuple(map(int, version.split("."))) >= (1, 14, 0):
        assert json.loads((folder / "release-manifest.json").read_text())["public_governance"] == governance
    assert (folder / "source.zip").read_bytes() == before["source.zip"]
    with zipfile.ZipFile(archive_path) as archive:
        assert archive.read("existing.txt") == b"existing evidence"
        assert json.loads(archive.read("public-pages/release.json"))["commit"] == manifest["commit"]
    for line in (folder / "SHA256SUMS").read_text().splitlines():
        digest, name = line.split("  ", 1)
        assert hashlib.sha256((folder / name).read_bytes()).hexdigest() == digest


def test_release_guides_have_working_flattened_links_and_preserve_the_manuscript(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    version = tomllib.loads((root / "pyproject.toml").read_text())["project"]["version"]
    package_agent_release.copy_release_documents(root, tmp_path, version, "a" * 40)
    assert {"START_HERE.md", "FACTORY_GUIDE.md", "DEMOS.md", "ASCENSION_PROTOCOL.md"}.issubset(
        {p.name for p in tmp_path.iterdir()}
    )
    for name in ("AGI_ALPHA_Unified_Publication_Final.md", "AGI_ALPHA_Unified_Publication_Final.pdf"):
        assert (tmp_path / name).read_bytes() == (root / "docs/manuscript" / name).read_bytes()
    for source in root.joinpath("docs/agent").glob("*.md"):
        copied = tmp_path / source.name
        if not copied.exists():
            continue
        text = re.sub(r"```.*?```", "", copied.read_text(), flags=re.S)
        for link in re.findall(r"\]\(([^\s)]+)\)", text):
            parsed = urlsplit(link)
            if not parsed.scheme and parsed.path:
                assert (tmp_path / parsed.path).is_file(), (source.name, link)
    release_notes = (tmp_path / f"RELEASE_NOTES_{version}.md").read_text()
    assert f"/blob/{'a' * 40}/docs/agent/START_HERE.md" in release_notes
    paper_guide = (tmp_path / "WHITEPAPER_IMPLEMENTATION.md").read_text()
    assert f"/blob/{'a' * 40}/whitepaper_v0.1.0-alphav15.pdf" in paper_guide
    assert "../assets/whitepaper_v0.1.0-alphav15.pdf" not in paper_guide


@pytest.mark.parametrize("staged", [False, True])
def test_release_packaging_refuses_dirty_source_before_creating_assets(
    tmp_path: Path, monkeypatch, staged: bool
) -> None:
    monkeypatch.chdir(tmp_path)
    subprocess.run(["git", "init", "-q"], check=True)
    source = tmp_path / "source.txt"
    source.write_text("committed version")
    subprocess.run(["git", "add", "source.txt"], check=True)
    subprocess.run(
        ["git", "-c", "user.name=Release Fixture", "-c", "user.email=fixture@example.test", "commit", "-qm", "Fixture"],
        check=True,
    )
    source.write_text("uncommitted version")
    if staged:
        subprocess.run(["git", "add", "source.txt"], check=True)
    monkeypatch.setattr(sys, "argv", ["package", "--output", "release", "--evidence", "evidence"])
    with pytest.raises(subprocess.CalledProcessError):
        package_agent_release.main()
    assert not (tmp_path / "release").exists()
