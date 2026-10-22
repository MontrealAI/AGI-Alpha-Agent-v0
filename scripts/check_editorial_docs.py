# SPDX-License-Identifier: Apache-2.0
"""Validate the proved editorial page with MkDocs, without building/publishing a site."""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
import tempfile

from scripts.paper_changes import git, prove_paper_descendants
from scripts.release_plan import EDITORIAL_PATH


class StrictWarnings(logging.Handler):
    def __init__(self) -> None:
        super().__init__(logging.WARNING)
        self.messages: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.messages.append(record.getMessage())


def validate_page(root: Path) -> None:
    """Use the same config, file inventory, Markdown and warning levels as MkDocs."""
    from mkdocs.commands.build import _populate_page
    from mkdocs.config import load_config
    from mkdocs.structure.files import get_files, set_exclusions
    from mkdocs.structure.pages import Page

    warnings = StrictWarnings()
    logger = logging.getLogger("mkdocs")
    previous_level = logger.level
    logger.setLevel(logging.INFO)
    logger.addHandler(warnings)
    try:
        with tempfile.TemporaryDirectory(prefix="editorial-mkdocs-") as output:
            config = load_config(config_file=str(root / "mkdocs.yml"), site_dir=output)
            config.plugins.on_startup(command="build", dirty=False)
            try:
                config = config.plugins.on_config(config)
                # Preserve generated link targets from the repository's normal hooks.
                # This does not build templates, copy the site or publish anything.
                config.plugins.on_pre_build(config=config)
                files = get_files(config)
                files.add_files_from_theme(config.theme.get_env(), config)
                files = config.plugins.on_files(files, config=config)
                set_exclusions(files, config)
                target = files.get_file_from_path("CHANGELOG.md")
                if target is None or not target.inclusion.is_included():
                    raise ValueError("Editorial page is missing or excluded from MkDocs")
                page = Page(None, target, config)
                _populate_page(page, config, files)
                # Match MkDocs anchor warning severity. Render only referenced Markdown
                # targets when anchor validation is enabled, not unrelated pages.
                level = config.validation.links.anchors
                if level > logging.DEBUG:
                    for linked in page.links_to_anchors or {}:
                        if linked is not target and linked.is_documentation_page():
                            other = linked.page or Page(None, linked, config)
                            _populate_page(other, config, files)
                    page.validate_anchor_links(files=files, log_level=level)
                if warnings.messages:
                    raise ValueError(
                        "Strict editorial documentation validation failed:\n" + "\n".join(warnings.messages)
                    )
            finally:
                config.plugins.on_shutdown()
    finally:
        logger.removeHandler(warnings)
        logger.setLevel(previous_level)


def check(root: Path, scope: dict) -> bool:
    # Reprove before importing MkDocs or loading any checkout configuration/hooks.
    proof = prove_paper_descendants(root, scope["software_commit"], scope["paper_commit"])
    if proof != scope or scope.get("mode") != "paper":
        raise ValueError("Editorial validation requires the exact trusted scope proof")
    if git(root, "rev-parse", "HEAD").decode().strip() != scope["paper_commit"]:
        raise ValueError("Editorial checkout does not match the proved source")
    if git(root, "status", "--porcelain", "--untracked-files=no"):
        raise ValueError("Editorial checkout has modified tracked inputs")
    if not any(EDITORIAL_PATH in row["paths"] for row in scope["transitions"]):
        return False
    validate_page(root)
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--scope", type=Path, required=True)
    args = parser.parse_args()
    performed = check(args.root.resolve(), json.loads(args.scope.read_text(encoding="utf-8")))
    print("Strict editorial MkDocs page check passed" if performed else "Editorial page check not applicable")


if __name__ == "__main__":
    main()
