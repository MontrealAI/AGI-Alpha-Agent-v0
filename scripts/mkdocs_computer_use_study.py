# SPDX-License-Identifier: Apache-2.0
"""Keep the study's raw downloads beside MkDocs-rendered Markdown pages."""
from pathlib import Path
from shutil import copyfile

from mkdocs.config.defaults import MkDocsConfig


def on_post_build(config: MkDocsConfig) -> None:
    """Copy only the two advertised Markdown downloads; never alter other assets."""
    relative = Path("reports/computer-use-study")
    source = Path(config.docs_dir) / relative
    destination = Path(config.site_dir) / relative
    destination.mkdir(parents=True, exist_ok=True)
    for name in ("REPORT.md", "PUBLICATION.md"):
        original = source / name
        target = destination / name
        if not original.is_file():
            raise ValueError(f"Missing study download: {name}")
        copyfile(original, target)
        if target.read_bytes() != original.read_bytes():
            raise ValueError(f"Study download copy differs: {name}")
