# SPDX-License-Identifier: Apache-2.0
"""Fast release policy keeps real acceptance failures blocking."""

from __future__ import annotations

import itertools
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[1]


def workflow(name: str) -> dict:
    return yaml.safe_load((ROOT / ".github/workflows" / name).read_text())


def needs(job: dict) -> set[str]:
    value = job.get("needs", [])
    return {value} if isinstance(value, str) else set(value)


class FastReleasePolicyTests(unittest.TestCase):
    def test_preview_is_not_in_the_qualification_dependency_graph(self):
        self.assertEqual(set(workflow("paper-scope.yml")["jobs"]), {"classify"})
        preview = workflow("paper-preview.yml")
        self.assertEqual(set(preview.get("on", preview.get(True))), {"pull_request"})
        self.assertEqual(preview["permissions"], {"contents": "read"})
        self.assertTrue(preview["jobs"]["web-preview"]["continue-on-error"])
        for name in ("ci.yml", "pr-ci.yml", "smoke.yml", "agent-release.yml"):
            self.assertNotIn("web-preview", workflow(name)["jobs"])

    def test_lint_and_smoke_are_parallel_but_both_verdicts_remain_required(self):
        jobs = workflow("pr-ci.yml")["jobs"]
        self.assertEqual(needs(jobs["smoke"]), {"paper-scope"})
        self.assertEqual(needs(jobs["lint"]), {"paper-scope"})
        self.assertEqual(needs(jobs["lint-result"]), {"paper-scope", "lint"})
        self.assertEqual(needs(jobs["smoke-result"]), {"paper-scope", "smoke"})
        for key in ("lint", "smoke", "lint-result", "smoke-result"):
            self.assertIn(key, needs(jobs["full-software-qualification"]))

    def test_representative_matrix_is_exact_and_same_on_pr_main_manual(self):
        smoke = workflow("smoke.yml")
        self.assertEqual(set(smoke.get("on", smoke.get(True))), {"push", "pull_request", "workflow_dispatch"})
        matrix = smoke["jobs"]["smoke"]["strategy"]["matrix"]
        actual = set(itertools.product(matrix["os"], matrix["python-version"]))
        actual -= {(item["os"], item["python-version"]) for item in matrix["exclude"]}
        self.assertEqual(
            actual,
            {
                ("ubuntu-latest", "3.11"),
                ("ubuntu-latest", "3.12"),
                ("ubuntu-latest", "3.13"),
                ("windows-latest", "3.12"),
                ("macos-latest", "3.12"),
            },
        )
        job = smoke["jobs"]["smoke"]
        self.assertFalse(job.get("continue-on-error", False))
        commands = "\n".join(step.get("run", "") for step in job["steps"])
        self.assertIn("alpha-agent --version", commands)
        self.assertNotIn("python -m pytest tests/runtime", commands)
        for required in (
            "test_macro_simulation_boundaries.py",
            "test_openai_bridge_integration.py",
            "test_cross_alpha_discovery.py",
            "test_business_submission_http.py",
        ):
            self.assertIn(required, commands)

    def test_one_primary_full_coverage_and_three_python_runtime_suites_remain(self):
        release = workflow("agent-release.yml")["jobs"]
        regression = release["regression"]
        primary = [step for step in regression["steps"] if "--cov-fail-under=80" in step.get("run", "")]
        self.assertEqual(len(primary), 1)
        self.assertFalse(primary[0].get("continue-on-error", False))
        self.assertIn("regression", needs(release["package"]))
        self.assertEqual(set(release["runtime"]["strategy"]["matrix"]["python"]), {"3.11", "3.12", "3.13"})
        integration = workflow("ci.yml")["jobs"]["tests"]
        self.assertEqual(integration["strategy"]["matrix"]["python-version"], ["3.12"])
        self.assertFalse(any("--cov" in step.get("run", "") for step in integration["steps"]))

    def test_only_cosmetic_hooks_are_advisory_and_cannot_modify_release_source(self):
        jobs = workflow("agent-release.yml")["jobs"]
        advisory = jobs["style-advisory"]
        self.assertTrue(advisory["continue-on-error"])
        self.assertNotIn("style-advisory", needs(jobs["package"]))
        checkout = next(step for step in advisory["steps"] if step.get("uses", "").startswith("actions/checkout@"))
        self.assertFalse(checkout["with"]["persist-credentials"])
        hooks = [step for step in jobs["quality"]["steps"] if step.get("env", {}).get("SKIP")]
        self.assertEqual(len(hooks), 2)
        for step in hooks:
            self.assertEqual(set(step["env"]["SKIP"].split(",")), {"black", "ruff-format", "flake8", "update-actions"})
            self.assertFalse(step.get("continue-on-error", False))
        self.assertFalse(jobs["quality"].get("continue-on-error", False))
        for key in ("quality", "dependency-audit", "mark-wallet", "browser-contracts", "runtime", "regression"):
            self.assertIn(key, needs(jobs["package"]))
            self.assertFalse(jobs[key].get("continue-on-error", False))

    def test_actual_qualification_scripts_fail_closed_for_every_required_result(self):
        with tempfile.TemporaryDirectory() as directory:
            for name in ("ci.yml", "pr-ci.yml", "smoke.yml"):
                marker = workflow(name)["jobs"]["full-software-qualification"]
                script = next(step["run"] for step in marker["steps"] if "run" in step)
                for key in needs(marker):
                    for result in ("success", "failure", "cancelled", "skipped"):
                        rows = {item: {"result": "success"} for item in needs(marker)}
                        rows[key]["result"] = result
                        process = subprocess.run(
                            ["bash", "-eu", "-o", "pipefail", "-c", script],
                            cwd=directory,
                            env={**os.environ, "RESULTS": json.dumps(rows)},
                            capture_output=True,
                            text=True,
                        )
                        self.assertEqual(process.returncode == 0, result == "success", (name, key, result))

    def test_security_and_financial_acceptance_is_not_advisory(self):
        jobs = workflow("agent-release.yml")["jobs"]
        for name in (
            "dependency-audit",
            "mark-wallet",
            "browser-contracts",
            "finance-lab",
            "package",
            "pages",
            "publish",
        ):
            self.assertFalse(jobs[name].get("continue-on-error", False))
            self.assertFalse(any(step.get("continue-on-error", False) for step in jobs[name].get("steps", [])))


if __name__ == "__main__":
    unittest.main()
