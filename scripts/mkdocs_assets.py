# SPDX-License-Identifier: Apache-2.0
"""Include the canonical research paper in every documentation build."""

from __future__ import annotations

from pathlib import Path
from shutil import copyfile
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mkdocs.config.defaults import MkDocsConfig


def on_pre_build(config: MkDocsConfig) -> None:
    """Prepare the unchanged paper before MkDocs validates local links."""
    source = Path(__file__).resolve().parents[1] / "whitepaper_v0.1.0-alphav15.pdf"
    destination = Path(config.docs_dir) / "assets" / source.name
    destination.parent.mkdir(parents=True, exist_ok=True)
    copyfile(source, destination)

    # Add the exact archived wallet profile; the paper and local demo are unchanged.
    from runpy import run_path

    build = run_path(str(Path(__file__).with_name("build_mark_wallet.py")))["build"]
    build(Path(__file__).resolve().parents[1], Path(config.docs_dir))


def on_post_build(config: MkDocsConfig) -> None:
    """Preserve the raw notice URL already linked by the exact research guides."""
    source = Path(config.docs_dir) / "DISCLAIMER_SNIPPET.md"
    destination = Path(config.site_dir) / source.name
    copyfile(source, destination)
    if destination.read_bytes() != source.read_bytes():
        raise ValueError("Published raw research notice differs from its source")
