# SPDX-License-Identifier: Apache-2.0
"""Seeded benchmark harness for Repo-Healer v1."""

from __future__ import annotations

import difflib
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass

from .engine import EngineOptions, RepoHealerEngine
from .models import FailureBundle, FailureClass, PatchCandidate, ValidatorClass

PYTHON = sys.executable
TARGET_ROOT = pathlib.Path("alpha_factory_v1/demos/self_healing_repo/repo_healer_v1/bench_targets")


@dataclass(frozen=True)
class SeedCase:
    name: str
    failure_class: FailureClass
    validator_class: ValidatorClass
    file_path: pathlib.Path
    broken_text: str
    fixed_text: str
    command: list[str]
    workflow: str


def _run(cmd: list[str], cwd: pathlib.Path) -> int:
    if shutil.which(cmd[0]) is None:
        return 127
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True).returncode


def _diff_for(file_path: pathlib.Path, broken: str, fixed: str) -> str:
    return "".join(
        difflib.unified_diff(
            broken.splitlines(keepends=True),
            fixed.splitlines(keepends=True),
            fromfile=f"a/{file_path.as_posix()}",
            tofile=f"b/{file_path.as_posix()}",
        )
    )


def _seed_cases() -> list[SeedCase]:
    return [
        SeedCase(
            "ruff_failure",
            FailureClass.RUFF,
            ValidatorClass.RUFF,
            TARGET_ROOT / "ruff_case.py",
            "# SPDX-License-Identifier: Apache-2.0\n\n\ndef keep() -> int\n    return 1\n",
            "# SPDX-License-Identifier: Apache-2.0\n\n\ndef keep() -> int:\n    return 1\n",
            ["ruff", "check", str(TARGET_ROOT / "ruff_case.py")],
            "✅ PR CI",
        ),
        SeedCase(
            "mypy_failure",
            FailureClass.MYPY,
            ValidatorClass.MYPY,
            TARGET_ROOT / "mypy_case.py",
            '# SPDX-License-Identifier: Apache-2.0\n\n\ndef typed_value() -> int:\n    return "broken"\n',
            "# SPDX-License-Identifier: Apache-2.0\n\n\ndef typed_value() -> int:\n    return 7\n",
            ["mypy", str(TARGET_ROOT / "mypy_case.py")],
            "🚀 CI — Insight Demo",
        ),
        SeedCase(
            "broken_import",
            FailureClass.IMPORT,
            ValidatorClass.PYTEST,
            TARGET_ROOT / "test_import_case.py",
            '# SPDX-License-Identifier: Apache-2.0\n\nfrom alpha_factory_v1.demos.self_healing_repo.repo_healer_v1.bench_targets.missing_import import ping\n\n\ndef test_ping() -> None:\n    assert ping() == "pong"\n',
            '# SPDX-License-Identifier: Apache-2.0\n\nfrom alpha_factory_v1.demos.self_healing_repo.repo_healer_v1.bench_targets.import_case import ping\n\n\ndef test_ping() -> None:\n    assert ping() == "pong"\n',
            [PYTHON, "-m", "pytest", str(TARGET_ROOT / "test_import_case.py"), "-q"],
            "✅ PR CI",
        ),
        SeedCase(
            "smoke_failure",
            FailureClass.SMOKE,
            ValidatorClass.SMOKE,
            TARGET_ROOT / "test_smoke_case.py",
            "# SPDX-License-Identifier: Apache-2.0\n\nimport pytest\n\n\n@pytest.mark.smoke\ndef test_smoke_marker() -> None:\n    assert False\n",
            "# SPDX-License-Identifier: Apache-2.0\n\nimport pytest\n\n\n@pytest.mark.smoke\ndef test_smoke_marker() -> None:\n    assert True\n",
            [PYTHON, "-m", "pytest", str(TARGET_ROOT / "test_smoke_case.py"), "-q"],
            "🔥 Smoke Test",
        ),
        SeedCase(
            "docs_failure",
            FailureClass.DOCS,
            ValidatorClass.DOCS,
            TARGET_ROOT / "docs_case/docs/index.md",
            "# Repo Healer Bench\n\n[broken](missing.md)\n",
            "# Repo Healer Bench\n\nThis docs seed should build.\n",
            ["mkdocs", "build", "--strict", "-f", str(TARGET_ROOT / "docs_case/mkdocs.yml")],
            "🚀 CI — Insight Demo",
        ),
    ]


def run_seeded_benchmark(repo_root: pathlib.Path) -> dict[str, object]:
    """Run seeded cases in a temp copy and return machine-readable results."""
    cases = _seed_cases()
    results: list[dict[str, object]] = []

    with tempfile.TemporaryDirectory(prefix="repo-healer-bench-") as tmp:
        work_repo = pathlib.Path(tmp) / "repo"
        shutil.copytree(repo_root, work_repo)
        engine = RepoHealerEngine(work_repo, EngineOptions(dry_run=False, max_attempts=1))

        for case in cases:
            file_path = work_repo / case.file_path
            file_path.write_text(case.broken_text, encoding="utf-8")
            baseline_rc = _run(case.command, cwd=work_repo)

            bundle = FailureBundle(
                workflow=case.workflow,
                job="seeded",
                step=case.name,
                run_id=f"seed-{case.name}",
                sha="seeded",
                failure_class=case.failure_class,
                validator_class=case.validator_class,
                candidate_files=[str(case.file_path)],
                reproduction_command=case.command,
                logs=f"seeded {case.failure_class.value} failure",
            )
            patch = PatchCandidate(
                diff=_diff_for(case.file_path, case.broken_text, case.fixed_text),
                summary=f"restore {case.name}",
                score=1.0,
            )
            if baseline_rc == 127:
                results.append(
                    {
                        "case": case.name,
                        "baseline_exit_code": baseline_rc,
                        "healed_exit_code": 127,
                        "healed": False,
                        "decision": "DIAGNOSE_ONLY",
                        "support_mode": "REPORT_ONLY",
                    }
                )
                continue
            report = engine.run(bundle, [patch])
            healed_rc = _run(case.command, cwd=work_repo)
            results.append(
                {
                    "case": case.name,
                    "baseline_exit_code": baseline_rc,
                    "healed_exit_code": healed_rc,
                    "healed": report.success,
                    "decision": report.decision.value,
                    "support_mode": report.support_mode.value,
                }
            )

        unsupported = FailureBundle(
            workflow="🚀 CI — Insight Demo",
            job="docker",
            step="publish",
            run_id="seed-tier3",
            sha="seeded",
            platform="linux",
            failure_class=FailureClass.DOCKER,
            logs="publish requires signing secret",
        )
        diagnosis = engine.run(
            unsupported,
            [PatchCandidate(diff="--- a/README.md\n+++ b/README.md\n", summary="blocked", score=0.1)],
        )
        results.append(
            {
                "case": "non_autofix_refusal",
                "baseline_exit_code": 1,
                "healed_exit_code": 1,
                "healed": diagnosis.success,
                "decision": diagnosis.decision.value,
                "support_mode": diagnosis.support_mode.value,
            }
        )

    return {
        "total": len(results),
        "healed": sum(1 for row in results if row["healed"]),
        "results": results,
    }


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
