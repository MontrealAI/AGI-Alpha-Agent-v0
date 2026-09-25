# SPDX-License-Identifier: Apache-2.0
"""Ordinary main commits must never replace an already published version."""

from __future__ import annotations

import json
import hashlib
from pathlib import Path
import zipfile

import pytest

from scripts import finalize_pages_release, publish_agent_release


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


@pytest.mark.parametrize("problem", [None, "commit", "asset"])
def test_public_evidence_requires_same_commit_and_intact_package(tmp_path: Path, problem: str | None) -> None:
    folder = tmp_path / "release"
    evidence = tmp_path / "evidence"
    folder.mkdir()
    (evidence / "public-pages").mkdir(parents=True)
    manifest = {"version": "1.4.0", "commit": "a" * 40, "release_gates": []}
    (folder / "release-manifest.json").write_text(json.dumps(manifest))
    archive_path = folder / "alpha-agent-v1.4.0-validation.zip"
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
