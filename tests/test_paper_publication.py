# SPDX-License-Identifier: Apache-2.0
"""Paper publication is a narrow, monotonic overlay, not software acceptance."""

from __future__ import annotations

import copy
import json
from pathlib import Path
import subprocess
import sys
import types
from typing import Any

import pytest
import yaml

from scripts import publish_paper_site as papers
from scripts.release_packs import digest, pack


def commit(root: Path, message: str) -> str:
    subprocess.run(["git", "-C", str(root), "add", "."], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(root), "commit", "-m", message], check=True, capture_output=True)
    return papers.git(root, "rev-parse", "HEAD").decode().strip()


def write(root: Path, name: str, data: bytes) -> None:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


@pytest.fixture
def source(tmp_path: Path) -> tuple[Path, str, str]:
    root = tmp_path / "source"
    root.mkdir()
    subprocess.run(["git", "init", str(root)], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(root), "config", "user.name", "Paper Test"], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.email", "paper@example.invalid"], check=True)
    for name in papers.GENERATED:
        write(root, "docs/" + name, ("baseline " + name).encode())
    write(root, "docs/research/original.pdf", b"original PDF bytes")
    write(root, "runtime.py", b"unchanged software")
    write(root, "docs/research-papers.json", b'{"papers": ["original"]}\n')
    first = commit(root, "software")
    write(root, "docs/research/fresh.pdf", b"fresh PDF bytes")
    write(root, "docs/research/fresh.tex", b"fresh TEX bytes")
    for name in papers.GENERATED:
        write(root, "docs/" + name, ("paper " + name).encode())
    write(root, "docs/research-papers.json", b'{"papers": ["original", "fresh"]}\n')
    second = commit(root, "papers")
    return root, first, second


def staged(source: tuple[Path, str, str], site: Path) -> tuple[dict[str, Any], dict[str, str], dict[str, str]]:
    root, software, _ = source
    for name in papers.SOURCE_OVERLAY:
        write(site, name, papers.source_bytes(root, software, "docs/" + name))
    write(site, "research/original.pdf", b"original PDF bytes")
    write(site, "successor/work/worker.js", b"runtime unchanged")
    write(site, "models/weights.bin", b"model unchanged")
    write(site, "release.json", papers.canonical({"schema": 1, "version": "1.2.3", "commit": software}))
    old = {"docs/research/original.pdf": papers.sha256(b"original PDF bytes")}
    new = {
        **old,
        "docs/research/fresh.pdf": papers.sha256(b"fresh PDF bytes"),
        "docs/research/fresh.tex": papers.sha256(b"fresh TEX bytes"),
    }
    return papers.inventory(site), old, new


def test_overlay_preserves_complete_software_inventory(source: tuple[Path, str, str], tmp_path: Path) -> None:
    root, software, _ = source
    write(root, "docs/CHANGELOG.md", b"<details>Ordinary editorial HTML must not be published.</details>")
    site = tmp_path / "site"
    before, old, new = staged(source, site)
    delta = papers.compose_site(root, site, software_commit=software, baseline=before, old_assets=old, new_assets=new)
    after = papers.inventory(site)
    assert "CHANGELOG.md" not in after
    assert "CHANGELOG.md" not in papers.SOURCE_OVERLAY
    assert {row["path"] for row in delta["files"]} == set(papers.SOURCE_OVERLAY) | {
        "research/fresh.pdf",
        "research/fresh.tex",
    }
    assert delta["removed"] == []
    assert (site / "research-papers.json").read_bytes() == (root / "docs/research-papers.json").read_bytes()
    assert after["research-papers.json"] != before["research-papers.json"]
    assert after["release.json"] == before["release.json"]
    for name in set(before) - set(papers.SOURCE_OVERLAY):
        assert after[name] == before[name]
    expected = {
        name: before[name]
        for name in sorted(before)
        if name not in set(papers.SOURCE_OVERLAY) | set(papers.site_assets(new))
    }
    assert delta["unchanged_inventory_sha256"] == papers.sha256(papers.canonical(expected))


@pytest.mark.parametrize("target", ["service-worker.js", "assets/service-worker.js", papers.WORKERS[2], "index.html"])
def test_unsupported_generated_baseline_is_not_rebuilt(
    source: tuple[Path, str, str], tmp_path: Path, target: str
) -> None:
    root, software, _ = source
    site = tmp_path / "site"
    _, old, new = staged(source, site)
    write(site, target, b"different built cache policy")
    before = papers.inventory(site)
    with pytest.raises(papers.Deferred, match="differs from source"):
        papers.compose_site(root, site, software_commit=software, baseline=before, old_assets=old, new_assets=new)
    assert papers.inventory(site) == before


@pytest.mark.parametrize("mutation", ["delete", "replace", "unrelated", "tampered-paper"])
def test_overlay_rejects_unsafe_changes(source: tuple[Path, str, str], tmp_path: Path, mutation: str) -> None:
    root, software, _ = source
    site = tmp_path / "site"
    before, old, new = staged(source, site)
    if mutation == "delete":
        new.pop("docs/research/original.pdf")
    elif mutation == "replace":
        new["docs/research/original.pdf"] = "f" * 64
    elif mutation == "unrelated":
        write(site, "models/weights.bin", b"changed")
    else:
        write(root, "docs/research/fresh.pdf", b"changed")
    with pytest.raises(ValueError):
        papers.compose_site(root, site, software_commit=software, baseline=before, old_assets=old, new_assets=new)


def test_fresh_paper_cannot_overwrite_unrelated_site_file(source: tuple[Path, str, str], tmp_path: Path) -> None:
    root, software, _ = source
    site = tmp_path / "site"
    _, old, new = staged(source, site)
    write(site, "research/fresh.pdf", b"unrelated existing asset")
    with pytest.raises(ValueError, match="overwrite an unrelated"):
        papers.compose_site(
            root, site, software_commit=software, baseline=papers.inventory(site), old_assets=old, new_assets=new
        )


def test_delta_rejects_extra_files_and_removals() -> None:
    before = {"runtime.js": {"sha256": "a", "bytes": 1}, "paper.pdf": {"sha256": "b", "bytes": 1}}
    with pytest.raises(ValueError, match="unrelated"):
        papers.verify_delta(before, {**before, "evil.js": {"sha256": "c", "bytes": 1}}, {"paper.pdf"})
    with pytest.raises(ValueError, match="cannot remove"):
        papers.verify_delta(before, {"runtime.js": before["runtime.js"]}, {"paper.pdf"})


def test_catalog_mapping_rejects_nonpaper_paths() -> None:
    for name in ("runtime.py", "docs/runtime.js", "docs/../paper.pdf", "/docs/paper.pdf"):
        with pytest.raises(ValueError):
            papers.site_assets({name: "a" * 64})


def test_source_checkout_must_be_exact_and_clean(source: tuple[Path, str, str]) -> None:
    root, software, paper = source
    papers.require_clean_source(root, paper)
    with pytest.raises(ValueError):
        papers.require_clean_source(root, software)
    write(root, "runtime.py", b"uncommitted code")
    with pytest.raises(ValueError):
        papers.require_clean_source(root, paper)


def plan_for(source: tuple[Path, str, str]) -> dict[str, Any]:
    _, software, paper = source
    return {
        "schema": papers.PLAN_SCHEMA,
        "status": "ready",
        "sealed": True,
        "software": {"commit": software, "version": "1.2.3", "release_id": 123},
        "paper": {"commit": paper, "catalog_sha256": "a" * 64},
    }


def test_monotonic_publication_never_rolls_back(source: tuple[Path, str, str]) -> None:
    root, software, paper = source
    plan = plan_for(source)
    live: dict[str, Any] = {"commit": software, "version": "1.2.3"}
    assert papers.require_live_order(root, plan, live)
    live["paper_publication"] = {"paper_commit": paper, "catalog_sha256": "a" * 64}
    assert not papers.require_live_order(root, plan, live)
    live["paper_publication"]["catalog_sha256"] = "b" * 64
    with pytest.raises(ValueError, match="conflicting"):
        papers.require_live_order(root, plan, live)
    write(root, "docs/research/newer.pdf", b"newer")
    newer = commit(root, "newer paper")
    live["paper_publication"] = {"paper_commit": newer, "catalog_sha256": "b" * 64}
    with pytest.raises(papers.Deferred, match="newer or divergent"):
        papers.require_live_order(root, plan, live)
    live["commit"] = newer
    with pytest.raises(papers.Deferred, match="Live software differs"):
        papers.require_live_order(root, plan, live)


def test_superseded_main_defers_under_lock_before_other_reads(
    source: tuple[Path, str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    root, software, _ = source
    module = types.ModuleType("scripts.paper_changes")
    module.prove_paper_descendants = (  # type: ignore[attr-defined]
        lambda *_: pytest.fail("must not prove after current-main rejection")
    )
    monkeypatch.setitem(sys.modules, "scripts.paper_changes", module)
    monkeypatch.setattr(papers, "current_main", lambda: software)
    monkeypatch.setattr(papers, "public_release", lambda *_: pytest.fail("must not inspect release after stale main"))
    with pytest.raises(papers.Deferred, match="Main advanced"):
        papers.guard(root, plan_for(source))


def test_editorial_only_preparation_defers_before_downloading_or_changing_site(
    source: tuple[Path, str, str], monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from scripts.release_plan import plan_for_proved_scope

    root, software, head = source
    write(root, "pyproject.toml", b'[project]\nversion = "1.2.3"\n')
    head = commit(root, "Fixture version")
    module = types.ModuleType("scripts.paper_changes")
    module.prove_paper_descendants = lambda *_: {  # type: ignore[attr-defined]
        "mode": "paper",
        "release_plan": plan_for_proved_scope(software, head, has_paper_changes=False).to_dict(),
    }
    monkeypatch.setitem(sys.modules, "scripts.paper_changes", module)
    monkeypatch.setattr(papers, "current_main", lambda: head)
    monkeypatch.setattr(papers, "public_release", lambda *_: ({"id": 123}, software))
    monkeypatch.setattr(papers, "download_release_assets", lambda *_: pytest.fail("editorial is not site publication"))
    site = tmp_path / "site"
    with pytest.raises(papers.Deferred, match="Editorial-only"):
        papers.prepare(root, tmp_path / "downloads", site)
    assert not site.exists()


def trusted_event() -> tuple[dict[str, Any], dict[str, str]]:
    repo = {"full_name": papers.REPOSITORY}
    return {
        "action": "completed",
        "workflow_run": {
            "name": "Agent release acceptance",
            "conclusion": "success",
            "head_branch": "main",
            "repository": repo,
            "head_repository": repo,
            "event": "push",
            "head_sha": "a" * 40,
        },
    }, {"GITHUB_REPOSITORY": papers.REPOSITORY, "GITHUB_EVENT_NAME": "workflow_run"}


@pytest.mark.parametrize(
    "key,value",
    [
        ("conclusion", "failure"),
        ("head_branch", "untrusted"),
        ("event", "pull_request"),
        ("name", "Other workflow"),
        ("head_sha", "main"),
        ("head_repository", {"full_name": "attacker/fork"}),
        ("repository", {"full_name": "attacker/fork"}),
    ],
)
def test_completion_trigger_rejects_untrusted_context(key: str, value: Any) -> None:
    event, env = trusted_event()
    papers.require_context(event, env)
    event["workflow_run"][key] = value
    with pytest.raises(ValueError, match="Untrusted"):
        papers.require_context(event, env)


def test_direct_trigger_requires_authorized_main() -> None:
    event, env = trusted_event()
    for trigger in ("push", "workflow_dispatch"):
        env.update(GITHUB_EVENT_NAME=trigger, GITHUB_REF="refs/heads/main")
        papers.require_context(event, env)
        env["GITHUB_REF"] = "refs/heads/paper"
        with pytest.raises(ValueError):
            papers.require_context(event, env)


def test_public_metadata_is_bound_to_source_and_checksums(tmp_path: Path) -> None:
    site = tmp_path / "site"
    write(site, "index.html", b"tested site")
    release = tmp_path / "release"
    pack(site, release, "site", commit="a" * 40, version="1.2.3", limit=8192)
    assets = [{"name": p.name, "bytes": p.stat().st_size, "sha256": digest(p)} for p in sorted(release.iterdir())]
    manifest = {
        "repository": papers.REPOSITORY,
        "commit": "a" * 40,
        "version": "1.2.3",
        "assets": assets,
        "distributions": {"site": {"manifest": "site-packs.json"}},
    }
    write(release, "release-manifest.json", papers.canonical(manifest))
    write(release, "SHA256SUMS", "".join(f"{digest(p)}  {p.name}\n" for p in sorted(release.iterdir())).encode())
    result = papers.verify_distribution(release, "a" * 40, "1.2.3")
    assert result["commit"] == "a" * 40
    with pytest.raises(ValueError, match="identities differ"):
        papers.verify_distribution(release, "b" * 40, "1.2.3")
    write(release, result["packs"][0]["name"], b"tampered")
    with pytest.raises(ValueError, match="checksum differs"):
        papers.verify_distribution(release, "a" * 40, "1.2.3")


def test_separate_provenance_keeps_software_identity(
    source: tuple[Path, str, str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, software, paper = source
    site = tmp_path / "site"
    before, old, new = staged(source, site)
    delta = papers.compose_site(root, site, software_commit=software, baseline=before, old_assets=old, new_assets=new)
    report = tmp_path / "homepage.json"
    report.write_text('{"narrow": true}')
    module = types.ModuleType("scripts.homepage_evidence")
    calls = []
    module.verify_report = lambda *args: calls.append(args)  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "scripts.homepage_evidence", module)
    original = papers.read_json(site / "release.json")
    plan = {
        **plan_for(source),
        "baseline_inventory": before,
        "delta": delta,
        "original_release": original,
        "proof": {"mode": "paper"},
        "run_url": "https://github.com/example/actions/runs/1",
    }
    plan["paper"]["files"] = papers.site_assets(new)
    plan["paper"]["catalog_sha256"] = digest(root / "docs/research-papers.json")
    sealed = papers.seal(site, plan, report)
    assert calls == [({"narrow": True}, paper, "1.2.3", "local project subpath")]
    live = papers.read_json(site / "release.json")
    assert {key: value for key, value in live.items() if key != "paper_publication"} == original
    publication = papers.read_json(site / "paper-publication.json")
    assert publication["software"]["commit"] == software
    assert publication["paper"]["commit"] == paper
    assert publication["evidence"]["scope"] == "paper-site-only"
    assert publication["evidence"]["homepage"]["sha256"] == digest(report)
    assert sealed["publication"] == live["paper_publication"]
    assert live["paper_publication"]["sha256"] == digest(site / "paper-publication.json")
    assert all(digest(site / name) == checksum for name, checksum in sealed["served_files"].items())
    assert sealed["served_files"]["research-papers.json"] == plan["paper"]["catalog_sha256"]
    monkeypatch.setattr(papers, "fetch_public", lambda name: (site / name).read_bytes())
    assert papers.verify_live(sealed)["passed"] is True
    # Matching release/sidecar metadata is insufficient when the CDN serves the old catalog.
    stale_catalog = papers.source_bytes(root, software, "docs/research-papers.json")
    write(site, "research-papers.json", stale_catalog)
    monkeypatch.setattr("scripts.publish_paper_site.time.sleep", lambda _: None)
    with pytest.raises(TimeoutError, match="public edge"):
        papers.verify_live(sealed)


def test_workflow_lock_scope_permissions_and_retry_artifacts() -> None:
    path = Path(__file__).resolve().parents[1] / ".github/workflows/paper-publication.yml"
    workflow = yaml.safe_load(path.read_text())
    jobs = workflow["jobs"]
    assert workflow["permissions"] == {"contents": "read"}
    assert "concurrency" not in jobs["prepare"] and "concurrency" not in jobs["verify-public"]
    deploy = jobs["deploy"]
    assert deploy["permissions"] == {"contents": "read", "pages": "write", "id-token": "write"}
    assert deploy["concurrency"] == {"group": "github-pages", "cancel-in-progress": False}
    steps = deploy["steps"]
    assert steps[-2]["run"] == "python -m scripts.publish_paper_site guard"
    assert steps[-1]["if"] == "steps.guard.outputs.ready == 'true'"
    assert all("sleep" not in step.get("run", "") for step in steps)
    assert all("finalize_pages_release" not in step.get("run", "") for job in jobs.values() for step in job["steps"])
    assert jobs["prepare"]["outputs"]["plan-name"] == "${{ steps.names.outputs.plan }}"
    assert jobs["prepare"]["outputs"]["pages-name"] == "${{ steps.names.outputs.pages }}"
    assert steps[-1]["with"]["artifact_name"] == "${{ needs.prepare.outputs.pages-name }}"
    for job in (jobs["deploy"], jobs["verify-public"]):
        download = next(step for step in job["steps"] if step.get("uses", "").startswith("actions/download-artifact@"))
        assert download["with"]["name"] == "${{ needs.prepare.outputs.plan-name }}"
        assert download["with"]["digest-mismatch"] == "error"
        assert "run-id" not in download["with"]
    assert jobs["prepare"]["steps"][0]["with"]["ref"] == "refs/heads/main"


@pytest.mark.parametrize(
    "draft,prerelease,published", [(True, False, "now"), (False, True, "now"), (False, False, None)]
)
def test_unpublished_or_prerelease_software_never_qualifies(
    monkeypatch: pytest.MonkeyPatch, draft: bool, prerelease: bool, published: str | None
) -> None:
    monkeypatch.setattr(
        papers, "api", lambda *args, **kwargs: {"draft": draft, "prerelease": prerelease, "published_at": published}
    )
    with pytest.raises(papers.Deferred, match="not fully public"):
        papers.public_release("1.2.3")


@pytest.mark.parametrize("change", ["none", "tag", "release-id", "metadata", "proof", "live-software", "already-live"])
def test_locked_guard_revalidates_every_publication_boundary(
    source: tuple[Path, str, str], monkeypatch: pytest.MonkeyPatch, change: str
) -> None:
    root, software, paper = source
    plan = plan_for(source)
    plan["software"].update(release_manifest_sha256="b" * 64, site_packs_sha256="b" * 64)
    plan["proof"] = {"mode": "paper", "software_commit": software, "paper_commit": paper}
    module = types.ModuleType("scripts.paper_changes")
    module.prove_paper_descendants = (  # type: ignore[attr-defined]
        lambda *_: ({} if change == "proof" else plan["proof"])
    )
    monkeypatch.setitem(sys.modules, "scripts.paper_changes", module)
    monkeypatch.setattr(papers, "current_main", lambda: paper)
    monkeypatch.setattr(
        papers,
        "public_release",
        lambda _: ({"id": 456 if change == "release-id" else 123}, "c" * 40 if change == "tag" else software),
    )
    monkeypatch.setattr(papers, "remote_metadata_digest", lambda *_: ("c" if change == "metadata" else "b") * 64)
    live: dict[str, Any] = {"commit": paper if change == "live-software" else software, "version": "1.2.3"}
    if change == "already-live":
        live["paper_publication"] = {"paper_commit": paper, "catalog_sha256": "a" * 64}
    monkeypatch.setattr(papers, "live_release", lambda: live)
    if change == "none":
        assert papers.guard(root, plan)
    elif change == "already-live":
        assert not papers.guard(root, plan)
    else:
        with pytest.raises(ValueError):
            papers.guard(root, plan)


def test_live_provenance_requires_the_exact_sidecar_bytes(monkeypatch: pytest.MonkeyPatch) -> None:
    publication = {
        "schema": papers.SCHEMA,
        "software": {"commit": "a" * 40, "version": "1.2.3"},
        "paper": {"commit": "b" * 40, "catalog_sha256": "c" * 64},
    }
    raw = papers.canonical(publication)
    pointer = {
        "path": "paper-publication.json",
        "sha256": papers.sha256(raw),
        "paper_commit": "b" * 40,
        "catalog_sha256": "c" * 64,
    }
    release = {"commit": "a" * 40, "version": "1.2.3", "paper_publication": pointer}
    monkeypatch.setattr(
        papers, "fetch_public", lambda name: papers.canonical(release) if name == "release.json" else raw
    )
    assert papers.live_release() == release
    pointer["sha256"] = "d" * 64
    with pytest.raises(papers.Deferred, match="inconsistent"):
        papers.live_release()


@pytest.mark.parametrize("target", ["index.html", "research-papers.json"])
def test_seal_rejects_tampering_after_validation(
    source: tuple[Path, str, str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch, target: str
) -> None:
    root, software, _ = source
    site = tmp_path / "site"
    before, old, new = staged(source, site)
    delta = papers.compose_site(root, site, software_commit=software, baseline=before, old_assets=old, new_assets=new)
    plan = {**plan_for(source), "baseline_inventory": before, "delta": delta}
    plan["paper"]["files"] = papers.site_assets(new)
    module = types.ModuleType("scripts.homepage_evidence")
    module.verify_report = lambda *_: None  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "scripts.homepage_evidence", module)
    report = tmp_path / "homepage.json"
    report.write_text("{}")
    write(site, target, b"changed after validation")
    with pytest.raises(ValueError, match="changed after"):
        papers.seal(site, plan, report)


def test_seal_rejects_stale_catalog_plan_before_metadata_write(
    source: tuple[Path, str, str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, software, _ = source
    site = tmp_path / "site"
    before, old, new = staged(source, site)
    delta = papers.compose_site(root, site, software_commit=software, baseline=before, old_assets=old, new_assets=new)
    plan = {
        **plan_for(source),
        "sealed": False,
        "baseline_inventory": before,
        "delta": delta,
        "original_release": papers.read_json(site / "release.json"),
        "proof": {"mode": "paper"},
        "run_url": "https://github.com/example/actions/runs/1",
    }
    plan["paper"]["files"] = papers.site_assets(new)
    plan["paper"]["catalog_sha256"] = papers.sha256(papers.source_bytes(root, software, "docs/research-papers.json"))
    original_release = (site / "release.json").read_bytes()
    assert digest(site / "research-papers.json") != plan["paper"]["catalog_sha256"]
    module = types.ModuleType("scripts.homepage_evidence")
    module.verify_report = lambda *_: None  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "scripts.homepage_evidence", module)
    report = tmp_path / "homepage.json"
    report.write_text("{}")

    with pytest.raises(ValueError, match="catalog.*source-bound"):
        papers.seal(site, plan, report)

    assert not (site / "paper-publication.json").exists()
    assert (site / "release.json").read_bytes() == original_release
