# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from pathlib import Path

import yaml


def test_semgrep_hook_declares_setuptools_for_py312_pkg_resources() -> None:
    """Semgrep hook env must vendor pkg_resources via setuptools on Python 3.12."""
    cfg = yaml.safe_load(Path(".pre-commit-config.yaml").read_text(encoding="utf-8"))
    repos = cfg.get("repos", []) if isinstance(cfg, dict) else []
    semgrep_hooks = []
    for repo in repos:
        if not isinstance(repo, dict):
            continue
        if repo.get("repo") != "https://github.com/semgrep/semgrep":
            continue
        hooks = repo.get("hooks", [])
        for hook in hooks:
            if isinstance(hook, dict) and hook.get("id") == "semgrep":
                semgrep_hooks.append(hook)

    assert semgrep_hooks, "semgrep hook must be configured"
    semgrep_hook = semgrep_hooks[0]
    deps = semgrep_hook.get("additional_dependencies", [])
    assert isinstance(deps, list)
    assert any(
        str(dep).startswith("setuptools") for dep in deps
    ), "semgrep hook must include setuptools so pkg_resources is available in isolated Python 3.12 envs"
