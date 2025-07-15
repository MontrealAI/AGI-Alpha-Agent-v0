# SPDX-License-Identifier: Apache-2.0
"""Verify that CI docs match the workflow configuration."""

from __future__ import annotations

import pathlib
import sys
from typing import List

import yaml


def extract_lockfiles(ci_yaml: pathlib.Path) -> List[str]:
    """Return NODE_LOCKFILES from the workflow file."""
    data = yaml.safe_load(ci_yaml.read_text())
    env = data.get("env", {})
    lockfiles_str = env.get("NODE_LOCKFILES", "")
    return [line.strip() for line in str(lockfiles_str).splitlines() if line.strip()]


def owner_check_defined(ci_yaml: pathlib.Path) -> bool:
    """Return True if the workflow defines an owner-check job."""
    data = yaml.safe_load(ci_yaml.read_text())
    return "owner-check" in data.get("jobs", {})


def verify_docs(lockfiles: List[str], docs_text: str, has_owner_job: bool) -> List[str]:
    """Return a list of mismatches between docs and workflow."""
    errors: List[str] = []
    for path in lockfiles:
        if path not in docs_text:
            errors.append(f"Lockfile path missing from docs: {path}")

    if has_owner_job and "owner-check" not in docs_text:
        errors.append("Docs missing description of 'owner-check' job")
    if not has_owner_job:
        errors.append("Workflow missing required 'owner-check' job")
    return errors


def main() -> int:
    repo_root = pathlib.Path(__file__).resolve().parents[1]
    ci_path = repo_root / ".github" / "workflows" / "ci.yml"
    docs_path = repo_root / "docs" / "CI_WORKFLOW.md"

    lockfiles = extract_lockfiles(ci_path)
    has_owner = owner_check_defined(ci_path)
    docs_text = docs_path.read_text()

    errors = verify_docs(lockfiles, docs_text, has_owner)
    if errors:
        print("CI docs verification failed:\n" + "\n".join(f"- {e}" for e in errors))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
