# SPDX-License-Identifier: Apache-2.0
"""Seeded benchmark harness for Repo-Healer v1."""

from __future__ import annotations

import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass

from .candidate_generation import generate_candidates
from .engine import EngineOptions, RepoHealerEngine
from .models import FailureBundle, SupportMode, ValidatorClass

PYTHON = sys.executable


@dataclass(frozen=True)
class SeedCase:
    """A reproducible benchmark case."""

    name: str
    target_file: str
    before: str
    after: str
    bundle: FailureBundle
    baseline_cmd: list[str]


def _run(cmd: list[str], cwd: pathlib.Path) -> int:
    try:
        return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True).returncode
    except FileNotFoundError:
        return 127


def _replace_once(text: str, old: str, new: str) -> str:
    if old not in text:
        raise ValueError(f"Seed marker not found: {old!r}")
    return text.replace(old, new, 1)


def _build_cases() -> list[SeedCase]:
    return [
        SeedCase(
            name="ruff_failure",
            target_file="alpha_factory_v1/demos/self_healing_repo/repo_healer_v1/triage.py",
            before='DRAFT_ONLY_MARKERS = ("actionlint", "docker build", "windows", "macos", "workflow", "lint workflows")\n',
            after=(
                "DRAFT_ONLY_MARKERS = "
                '("actionlint", "docker build", "windows", "macos", "workflow", "lint workflows")\n'
                "UNDEFINED_RUFF_SENTINEL = undefined_repo_healer_symbol\n"
            ),
            bundle=FailureBundle(
                workflow="✅ PR CI",
                job="lint",
                step="Ruff check",
                run_id="seed-ruff",
                sha="deadbeef",
                failure_class="ruff",
                validator_class=ValidatorClass.RUFF,
                logs="ruff F821 undefined name 'undefined_repo_healer_symbol'",
                support_mode=SupportMode.AUTOPATCH_SAFE,
                reproduction_command=[
                    "ruff",
                    "check",
                    "alpha_factory_v1/demos/self_healing_repo/repo_healer_v1/triage.py",
                ],
            ),
            baseline_cmd=["ruff", "check", "alpha_factory_v1/demos/self_healing_repo/repo_healer_v1/triage.py"],
        ),
        SeedCase(
            name="mypy_failure",
            target_file="alpha_factory_v1/demos/self_healing_repo/repo_healer_v1/models.py",
            before="    sha: str\n",
            after="    sha: str = 1\n",
            bundle=FailureBundle(
                workflow="🚀 Integration CI — Insight Demo",
                job="lint-type",
                step="Mypy type-check",
                run_id="seed-mypy",
                sha="deadbeef",
                failure_class="mypy",
                validator_class=ValidatorClass.MYPY,
                logs="mypy: Argument 'sha' to 'FailureBundle' has incompatible type 'str'; expected 'str'",
                support_mode=SupportMode.AUTOPATCH_SAFE,
                reproduction_command=[
                    PYTHON,
                    "-m",
                    "mypy",
                    "--config-file",
                    "mypy.ini",
                    "alpha_factory_v1/demos/self_healing_repo/repo_healer_v1/models.py",
                ],
            ),
            baseline_cmd=[
                PYTHON,
                "-m",
                "mypy",
                "--config-file",
                "mypy.ini",
                "alpha_factory_v1/demos/self_healing_repo/repo_healer_v1/models.py",
            ],
        ),
        SeedCase(
            name="broken_import",
            target_file="tests/test_imports.py",
            before="import unittest\n",
            after="import unittest\nimport definitely_missing_module\n",
            bundle=FailureBundle(
                workflow="✅ PR CI",
                job="smoke",
                step="imports",
                run_id="seed-import",
                sha="deadbeef",
                failure_class="import",
                validator_class=ValidatorClass.IMPORT,
                logs="ModuleNotFoundError: No module named 'definitely_missing_module'",
                support_mode=SupportMode.AUTOPATCH_SAFE,
            ),
            baseline_cmd=[PYTHON, "-m", "pytest", "tests/test_imports.py", "-q"],
        ),
        SeedCase(
            name="pytest_failure",
            target_file="tests/test_ping_agent.py",
            before='        self.assertEqual(topic, "agent.ping")\n',
            after='        self.assertEqual(topic, "agent.pong")\n',
            bundle=FailureBundle(
                workflow="✅ PR CI",
                job="smoke",
                step="Smoke tests",
                run_id="seed-pytest",
                sha="deadbeef",
                failure_class="pytest",
                validator_class=ValidatorClass.PYTEST,
                logs="AssertionError in tests/test_ping_agent.py",
                support_mode=SupportMode.AUTOPATCH_SAFE,
            ),
            baseline_cmd=[PYTHON, "-m", "pytest", "tests/test_ping_agent.py", "-q"],
        ),
        SeedCase(
            name="mkdocs_failure",
            target_file="mkdocs.yml",
            before="site_name: Alpha-Factory Docs\n",
            after="site_name: Alpha-Factory Docs\nthis_is_not_valid_yaml: [\n",
            bundle=FailureBundle(
                workflow="📚 Docs",
                job="build-deploy",
                step="mkdocs build --strict",
                run_id="seed-docs",
                sha="deadbeef",
                failure_class="mkdocs",
                validator_class=ValidatorClass.MKDOCS,
                logs="mkdocs build --strict failed",
                support_mode=SupportMode.AUTOPATCH_SAFE,
            ),
            baseline_cmd=["mkdocs", "build", "--strict"],
        ),
        SeedCase(
            name="non_autofix_permissions",
            target_file="README.md",
            before="### Security Note\n",
            after="### Security Note\n",
            bundle=FailureBundle(
                workflow="🚀 Integration CI — Insight Demo",
                job="owner-check",
                step="Verify owner",
                run_id="seed-perm",
                sha="deadbeef",
                failure_class="permission",
                logs="resource not accessible by integration",
                support_mode=SupportMode.REPORT_ONLY,
            ),
            baseline_cmd=[PYTHON, "-c", "print('permission context')"],
        ),
    ]


def run_seeded_benchmark(repo_root: pathlib.Path) -> dict[str, object]:
    """Run seeded cases in isolated workspace and return machine-readable result."""
    results: list[dict[str, object]] = []

    with tempfile.TemporaryDirectory(prefix="repo-healer-bench-") as tmp:
        work_repo = pathlib.Path(tmp) / "repo"
        shutil.copytree(
            repo_root, work_repo, ignore=shutil.ignore_patterns(".git", "__pycache__", ".pytest_cache", ".mypy_cache")
        )

        for case in _build_cases():
            case_path = work_repo / case.target_file
            original = case_path.read_text(encoding="utf-8")
            broken = _replace_once(original, case.before, case.after)
            case_path.write_text(broken, encoding="utf-8")
            baseline_rc = _run(case.baseline_cmd, cwd=work_repo)
            reproducible = baseline_rc not in {127}

            engine = RepoHealerEngine(
                work_repo,
                EngineOptions(dry_run=False, max_attempts=1, run_broader_validation=False),
            )
            candidates = generate_candidates(work_repo, case.bundle)
            report = engine.run(case.bundle, candidates)

            healed_rc = _run(case.baseline_cmd, cwd=work_repo)
            if not reproducible:
                status = "SKIPPED_MISSING_VALIDATOR"
            elif report.support_mode in {SupportMode.REPORT_ONLY, SupportMode.DRAFT_PR_ONLY}:
                status = "REFUSED_SAFE"
            elif report.success and healed_rc == 0:
                status = "HEALED"
            else:
                status = "NOT_HEALED"
            results.append(
                {
                    "case": case.name,
                    "baseline_exit_code": baseline_rc,
                    "healed_exit_code": healed_rc,
                    "status": status,
                    "reproducible": reproducible,
                    "healed": report.success,
                    "candidate_count": len(candidates),
                    "classification": report.classification.value,
                    "support_mode": report.support_mode.value,
                    "reason": report.reason,
                }
            )

    healed = sum(1 for row in results if row["healed"])
    return {"total": len(results), "healed": healed, "results": results}


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
