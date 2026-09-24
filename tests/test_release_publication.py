# SPDX-License-Identifier: Apache-2.0
"""Ordinary main commits must never replace an already published version."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import publish_agent_release


def test_public_version_is_left_unchanged(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GITHUB_REPOSITORY", "MontrealAI/AGI-Alpha-Agent-v0")
    monkeypatch.setenv("GITHUB_REF", "refs/heads/main")
    monkeypatch.setenv("GITHUB_SHA", "a" * 40)
    release = tmp_path / "release"
    release.mkdir()
    (release / "release-manifest.json").write_text(json.dumps({"commit": "a" * 40}))
    calls = []

    def read_public_release(*args: str) -> str:
        calls.append(args)
        assert args == ("api", "repos/MontrealAI/AGI-Alpha-Agent-v0/releases?per_page=100")
        return json.dumps([{"tag_name": "v1.2.0", "draft": False, "html_url": "https://example.test/release"}])

    def no_mutation(*args: object, **kwargs: object) -> None:
        raise AssertionError("An existing public version must not invoke any mutation")

    monkeypatch.setattr(publish_agent_release, "gh", read_public_release)
    monkeypatch.setattr(publish_agent_release.subprocess, "run", no_mutation)
    publish_agent_release.main()
    assert len(calls) == 1
