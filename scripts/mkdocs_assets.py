# SPDX-License-Identifier: Apache-2.0
"""Include the canonical research paper in every documentation build."""

from pathlib import Path
from shutil import copyfile

from mkdocs.config.defaults import MkDocsConfig


def on_pre_build(config: MkDocsConfig) -> None:
    """Prepare the unchanged paper before MkDocs validates local links."""
    source = Path(__file__).resolve().parents[1] / "whitepaper_v0.1.0-alphav15.pdf"
    destination = Path(config.docs_dir) / "assets" / source.name
    destination.parent.mkdir(parents=True, exist_ok=True)
    copyfile(source, destination)
