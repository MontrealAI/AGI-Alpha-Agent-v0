# SPDX-License-Identifier: Apache-2.0
"""Validate proved editorial changes with an isolated strict documentation build."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import tempfile

from scripts.paper_changes import git, prove_paper_descendants
from scripts.release_plan import EDITORIAL_PATH


def validate_docs(root: Path) -> None:
    """Run the existing complete strict MkDocs build in disposable output."""
    from mkdocs.commands.build import build
    from mkdocs.config import load_config

    with tempfile.TemporaryDirectory(prefix="editorial-mkdocs-") as output:
        config = load_config(config_file=str(root / "mkdocs.yml"), site_dir=output, strict=True)
        config.plugins.on_startup(command="build", dirty=False)
        try:
            # Delegate all Markdown, template, navigation, plugin and final-output
            # semantics to MkDocs instead of reconstructing a partial build.
            build(config)
        finally:
            config.plugins.on_shutdown()


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
    validate_docs(root)
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--scope", type=Path, required=True)
    args = parser.parse_args()
    performed = check(args.root.resolve(), json.loads(args.scope.read_text(encoding="utf-8")))
    print("Strict editorial MkDocs build passed" if performed else "Editorial page check not applicable")


if __name__ == "__main__":
    main()
