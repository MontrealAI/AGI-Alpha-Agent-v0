from __future__ import annotations

import yaml
from pathlib import Path


def test_semgrep_hook_includes_setuptools_for_python312_pkg_resources() -> None:
    config = yaml.safe_load(Path(".pre-commit-config.yaml").read_text(encoding="utf-8"))
    semgrep_repo = next(repo for repo in config["repos"] if "semgrep/semgrep" in repo["repo"])
    semgrep_hook = next(hook for hook in semgrep_repo["hooks"] if hook["id"] == "semgrep")
    additional_deps = semgrep_hook.get("additional_dependencies", [])
    assert "setuptools<81" in additional_deps
