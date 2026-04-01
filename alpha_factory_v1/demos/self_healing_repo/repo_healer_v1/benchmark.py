# SPDX-License-Identifier: Apache-2.0
"""Seeded benchmark harness for Repo-Healer v1."""

from __future__ import annotations

import json
import pathlib
import shutil
import subprocess
import sys
import tempfile

from .engine import EngineOptions, RepoHealerEngine
from .models import FailureBundle, PatchCandidate

PYTHON = sys.executable


def _run(cmd: list[str], cwd: pathlib.Path) -> int:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True).returncode


def run_seeded_benchmark(repo_root: pathlib.Path) -> dict[str, object]:
    """Run seeded cases in a temp copy and return machine-readable results."""
    cases = [
        {"name": "ruff_failure", "bundle": FailureBundle("🚀 CI — Insight Demo", "lint-type", "Ruff lint", "seed-1", "deadbeef", logs="ruff F401"), "baseline": [PYTHON, "-m", "pytest", "tests/test_ping_agent.py", "-q"]},
        {"name": "mypy_failure", "bundle": FailureBundle("🚀 CI — Insight Demo", "lint-type", "Mypy", "seed-2", "deadbeef", logs="mypy: error"), "baseline": [PYTHON, "-m", "pytest", "tests/test_ping_agent.py", "-q"]},
        {"name": "broken_import", "bundle": FailureBundle("✅ PR CI", "tests", "pytest", "seed-3", "deadbeef", logs="ModuleNotFoundError"), "baseline": [PYTHON, "-m", "pytest", "tests/test_imports.py", "-q"]},
        {"name": "smoke_failure", "bundle": FailureBundle("🔥 Smoke Test", "smoke", "smoke", "seed-4", "deadbeef", logs="assert 1 == 2"), "baseline": [PYTHON, "scripts/check_python_deps.py"]},
        {"name": "mkdocs_failure", "bundle": FailureBundle("📚 Docs", "docs", "mkdocs", "seed-5", "deadbeef", logs="mkdocs build --strict failed"), "baseline": [PYTHON, "-m", "pytest", "tests/test_notebooks.py", "-q"]},
        {"name": "tier2_windows", "bundle": FailureBundle("🚀 CI — Insight Demo", "windows-smoke", "pytest", "seed-6", "deadbeef", platform="windows", logs="path issue"), "baseline": [PYTHON, "-c", "print('tier2')"]},
    ]

    results: list[dict[str, object]] = []
    with tempfile.TemporaryDirectory(prefix="repo-healer-bench-") as tmp:
        work_repo = pathlib.Path(tmp) / "repo"
        shutil.copytree(repo_root, work_repo)
        engine = RepoHealerEngine(work_repo, EngineOptions(dry_run=True))
        for case in cases:
            baseline_rc = _run(case["baseline"], cwd=work_repo)
            patch = PatchCandidate(
                diff="--- a/README.md\n+++ b/README.md\n@@ -1,1 +1,1 @@\n-[See docs/DISCLAIMER_SNIPPET.md](docs/DISCLAIMER_SNIPPET.md)\n+[See docs/DISCLAIMER_SNIPPET.md](docs/DISCLAIMER_SNIPPET.md)\n",
                summary=f"seeded candidate for {case['name']}",
                score=0.9,
            )
            report = engine.run(case["bundle"], [patch])
            results.append({"case": case["name"], "baseline_exit_code": baseline_rc, "healed": report.success, "policy": report.policy.value, "reason": report.reason})

    return {"total": len(results), "healed": sum(1 for row in results if row["healed"]), "results": results}


def main() -> int:
    """CLI for seeded benchmark."""
    import argparse

    parser = argparse.ArgumentParser(description="Run Repo-Healer v1 seeded benchmark")
    parser.add_argument("--repo", default=".")
    parser.add_argument("--out", default="repo_healer_benchmark.json")
    args = parser.parse_args()
    payload = run_seeded_benchmark(pathlib.Path(args.repo).resolve())
    pathlib.Path(args.out).write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
