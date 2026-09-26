# SPDX-License-Identifier: Apache-2.0
"""Ordinary main commits must never replace an already published version."""

from __future__ import annotations

import json
import hashlib
from pathlib import Path
import subprocess
import zipfile

import pytest

from scripts import finalize_pages_release, publish_agent_release, release_context


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
    if version == "1.5.0":
        ascension_dir = evidence / "public-pages" / "ascension"
        ascension_dir.mkdir()
        (ascension_dir / "ascension.json").write_text(
            json.dumps(
                {
                    "origin": "https://example.test/" if problem == "origin" else url,
                    "passed": problem != "ascension",
                    "paper_sha256": "altered"
                    if problem == "paper"
                    else "fd14d444d51e9f6ebaec13387fc8d2170615d1bbfab13edc7e84ea1f655d20aa",
                }
            )
        )
    before = {p.name: p.read_bytes() for p in folder.iterdir()}
    if problem:
        with pytest.raises(ValueError):
            finalize_pages_release.finalize(folder, evidence)
        assert {p.name: p.read_bytes() for p in folder.iterdir()} == before
        return
    finalize_pages_release.finalize(folder, evidence)
    assert (folder / "source.zip").read_bytes() == before["source.zip"]
    with zipfile.ZipFile(archive_path) as archive:
        assert archive.read("existing.txt") == b"existing evidence"
        assert json.loads(archive.read("public-pages/release.json"))["commit"] == manifest["commit"]
    for line in (folder / "SHA256SUMS").read_text().splitlines():
        digest, name = line.split("  ", 1)
        assert hashlib.sha256((folder / name).read_bytes()).hexdigest() == digest
