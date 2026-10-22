# SPDX-License-Identifier: Apache-2.0
"""Legacy URL evidence is mandatory in the existing software publication path."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from scripts import finalize_pages_release, package_agent_release

ROOT = Path(__file__).resolve().parents[1]
COMMIT = "a" * 40
VERSION = "1.37.1"


def test_historical_release_compatibility_is_not_retroactively_requalified(tmp_path: Path) -> None:
    assert package_agent_release.qualify_legacy_site(tmp_path, tmp_path / "absent", COMMIT, "1.37.0", tmp_path) is None
    assert finalize_pages_release.verify_legacy_evidence(tmp_path, tmp_path, {"version": "1.36.0"}) is None


def test_packaging_runs_and_verifies_exact_distribution_before_retaining_report(tmp_path: Path, monkeypatch) -> None:
    from scripts import legacy_public_urls

    report = {"commit": COMMIT, "version": VERSION, "mode": "local"}
    calls = []
    packs = tmp_path / "site-packs.json"
    site = tmp_path / "site"
    monkeypatch.setattr(legacy_public_urls, "check_site", lambda *args: calls.append(("check", args)) or report)
    monkeypatch.setattr(
        legacy_public_urls, "verify_report", lambda *args, **kwargs: calls.append(("verify", args, kwargs))
    )
    assert package_agent_release.qualify_legacy_site(site, packs, COMMIT, VERSION, tmp_path) == report
    assert calls == [
        ("check", (site, packs, COMMIT, VERSION)),
        ("verify", (report, COMMIT, VERSION, packs), {"mode": "local"}),
    ]
    assert json.loads((tmp_path / "legacy-public-urls.json").read_text()) == report


def test_packaging_cannot_retain_unverified_compatibility(tmp_path: Path, monkeypatch) -> None:
    from scripts import legacy_public_urls

    monkeypatch.setattr(legacy_public_urls, "check_site", lambda *args: {"passed": True})

    def reject(*args, **kwargs):
        raise ValueError("unbound report")

    monkeypatch.setattr(legacy_public_urls, "verify_report", reject)
    with pytest.raises(ValueError, match="unbound report"):
        package_agent_release.qualify_legacy_site(tmp_path, tmp_path / "packs", COMMIT, VERSION, tmp_path)
    assert not (tmp_path / "legacy-public-urls.json").exists()


def test_finalization_requires_local_and_public_reports_bound_to_same_pack(tmp_path: Path, monkeypatch) -> None:
    from scripts import legacy_public_urls

    local = {"mode": "local"}
    public = {"mode": "public"}
    folder = tmp_path / "release"
    evidence = tmp_path / "evidence"
    (evidence / "public-pages").mkdir(parents=True)
    (evidence / "public-pages/legacy-public-urls.json").write_text(json.dumps(public))
    manifest = {"commit": COMMIT, "version": VERSION, "legacy_public_urls": local}
    calls = []
    monkeypatch.setattr(legacy_public_urls, "verify_report", lambda *a, **k: calls.append((a, k)))
    assert finalize_pages_release.verify_legacy_evidence(folder, evidence, manifest) == public
    assert calls == [
        ((local, COMMIT, VERSION, folder / "site-packs.json"), {"mode": "local"}),
        ((public, COMMIT, VERSION, folder / "site-packs.json"), {"mode": "public"}),
    ]


@pytest.mark.parametrize("damage", ["missing-local", "missing-public", "rejected-local", "rejected-public"])
def test_finalization_cannot_omit_or_ignore_either_verification(tmp_path: Path, monkeypatch, damage: str) -> None:
    from scripts import legacy_public_urls

    manifest = {"commit": COMMIT, "version": VERSION, "legacy_public_urls": {"mode": "local"}}
    evidence = tmp_path / "evidence"
    (evidence / "public-pages").mkdir(parents=True)
    if damage != "missing-public":
        (evidence / "public-pages/legacy-public-urls.json").write_text('{"mode":"public"}')
    if damage == "missing-local":
        manifest.pop("legacy_public_urls")

    def reject(*args, mode: str):
        if damage == f"rejected-{mode}":
            raise ValueError("incomplete or stale")

    monkeypatch.setattr(legacy_public_urls, "verify_report", reject)
    with pytest.raises((ValueError, FileNotFoundError)):
        finalize_pages_release.verify_legacy_evidence(tmp_path, evidence, manifest)


def test_actual_finalizer_calls_legacy_gate_before_accepting_new_release(tmp_path: Path, monkeypatch) -> None:
    release = tmp_path / "release"
    evidence = tmp_path / "evidence"
    release.mkdir()
    (evidence / "public-pages").mkdir(parents=True)
    origin = "https://montrealai.github.io/AGI-Alpha-Agent-v0/"
    identity = {"commit": COMMIT, "version": VERSION, "url": origin}
    (release / "release-manifest.json").write_text(json.dumps(identity))
    (evidence / "public-pages/release.json").write_text(json.dumps(identity))
    (evidence / "public-pages/workspace.json").write_text(json.dumps({"origin": origin, "model_required": True}))

    def reject(*args):
        raise ValueError("legacy gate executed")

    monkeypatch.setattr(finalize_pages_release, "verify_legacy_evidence", reject)
    with pytest.raises(ValueError, match="legacy gate executed"):
        finalize_pages_release.finalize(release, evidence)


def test_existing_release_workflow_executes_compatibility_not_a_separate_optional_job() -> None:
    workflow = yaml.safe_load((ROOT / ".github/workflows/agent-release.yml").read_text())
    steps = workflow["jobs"]["pages"]["steps"]
    matching = [step for step in steps if "scripts.legacy_public_urls" in step.get("run", "")]
    assert len(matching) == 1
    step = matching[0]
    assert "continue-on-error" not in step and "if" not in step
    command = step["run"]
    assert "--site site --pack-manifest pages-distribution/site-packs.json" in command
    assert '--commit "$GITHUB_SHA"' in command
    assert "--output evidence/public-pages/legacy-public-urls.json --public" in command
    assert command.index("scripts.wait_for_pages_release") < command.index("scripts.legacy_public_urls")
    all_runs = "\n".join(step.get("run", "") for job in workflow["jobs"].values() for step in job.get("steps", []))
    assert "tests/test_legacy_public_urls.py tests/test_legacy_public_url_release.py" in all_runs


def test_historical_repair_receipt_is_an_exact_copy_not_current_release_identity() -> None:
    from scripts.repair_paper_links import receipt_bytes

    assert (ROOT / "docs/paper-link-repair-20261021.json").read_bytes() == receipt_bytes(
        "0cd35c0dc3f7ca901073aedc97316260949b5987"
    )
