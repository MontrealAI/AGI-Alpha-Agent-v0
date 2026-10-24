# SPDX-License-Identifier: Apache-2.0
"""Keep the existing raw research-notice destination available after MkDocs."""

import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest

SOURCE = Path(__file__).resolve().parents[1] / "scripts/mkdocs_assets.py"
SPEC = importlib.util.spec_from_file_location("notice_hook", SOURCE)
assert SPEC is not None and SPEC.loader is not None
HOOK = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(HOOK)


def test_post_build_preserves_the_raw_notice_destination(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    site = tmp_path / "site"
    docs.mkdir()
    site.mkdir()
    raw = "Research notice · Avis de recherche\r\nOriginal source bytes.\n".encode()
    (docs / "DISCLAIMER_SNIPPET.md").write_bytes(raw)
    config = SimpleNamespace(docs_dir=str(docs), site_dir=str(site))
    HOOK.on_post_build(config)
    assert (site / "DISCLAIMER_SNIPPET.md").read_bytes() == raw
    HOOK.on_post_build(config)
    assert (site / "DISCLAIMER_SNIPPET.md").read_bytes() == raw


def test_missing_notice_fails_instead_of_publishing_a_dead_link(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    site = tmp_path / "site"
    docs.mkdir()
    site.mkdir()
    with pytest.raises(FileNotFoundError):
        HOOK.on_post_build(SimpleNamespace(docs_dir=str(docs), site_dir=str(site)))
    assert not (site / "DISCLAIMER_SNIPPET.md").exists()
