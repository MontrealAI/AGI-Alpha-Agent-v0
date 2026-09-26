# SPDX-License-Identifier: Apache-2.0
"""Audit every package in the supported operator lock; retain dated evidence."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
from importlib.metadata import version
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Any

from alpha_factory_v1.utils.disclaimer import DISCLAIMER  # noqa: F401


def validate_report(lock: str, report: dict[str, Any]) -> int:
    """Require complete, unskipped, matching package coverage and zero advisories."""
    normalize = lambda name: re.sub(r"[-_.]+", "-", name).lower()  # noqa: E731
    expected = {
        normalize(name): pinned for name, pinned in re.findall(r"^([A-Za-z0-9_.-]+)==([^\s;\\]+)", lock, re.MULTILINE)
    }
    dependencies = report.get("dependencies", [])
    actual = {normalize(item["name"]): item.get("version") for item in dependencies}
    if not expected or actual != expected or len(actual) != len(dependencies):
        raise ValueError("Dependency audit must cover every exact locked package once")
    if any(item.get("skip_reason") or "vulns" not in item or item["vulns"] for item in dependencies):
        raise ValueError("Dependency audit contains advisories, skipped packages or incomplete results")
    return len(expected)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lock", type=Path, default=Path("requirements-agent.lock"))
    parser.add_argument("--output", type=Path, default=Path("evidence/python-dependencies"))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    report_path = args.output / "pip-audit.json"
    command = [
        sys.executable,
        "-m",
        "pip_audit",
        "--disable-pip",
        "--require-hashes",
        "--progress-spinner=off",
        "-r",
        str(args.lock),
        "--format=json",
        "--output",
        str(report_path),
    ]
    completed = subprocess.run(command, check=False, timeout=600)
    metadata = {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "commit": os.environ.get("GITHUB_SHA"),
        "lock": str(args.lock),
        "lock_sha256": hashlib.sha256(args.lock.read_bytes()).hexdigest(),
        "tool": "pip-audit",
        "tool_version": version("pip-audit"),
        "service": "PyPI",
        "exit_code": completed.returncode,
        "passed": False,
    }
    try:
        metadata["packages"] = validate_report(args.lock.read_text(), json.loads(report_path.read_bytes()))
        if completed.returncode != 0:
            raise RuntimeError("Dependency scanner failed; inspect pip-audit.json and the job log")
        metadata["passed"] = True
    finally:
        (args.output / "summary.json").write_text(json.dumps(metadata, indent=2) + "\n")
    print(json.dumps(metadata))


if __name__ == "__main__":
    main()
