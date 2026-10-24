from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import sys

import pytest
import yaml


def test_ci_health_workflow_run_is_rerun_only_and_context_aware() -> None:
    workflow = Path(".github/workflows/ci-health.yml").read_text(encoding="utf-8")

    assert 'workflows:\n      - "🚀 Integration CI — Insight Demo"\n      - "✅ PR CI"' in workflow
    assert 'HARD_WORKFLOW="pr-ci.yml"' in workflow

    workflow_run_block = """
          if [[ "${{ github.event_name }}" == "workflow_run" ]]; then
            source_workflow=$(jq -r '.workflow_run.name // empty' "$GITHUB_EVENT_PATH")
            if [[ "$source_workflow" == "🚀 Integration CI — Insight Demo" ]]; then
              HARD_WORKFLOW="ci.yml"
            fi
            # A completed workflow_run already guarantees a concrete run exists.
            # Avoid extra dispatches in this context and only rerun failed runs.
            DISPATCH_ARGS=()
            # Repo-Healer marks run_attempt<2 as report-only; keep one automatic rerun
            # path for failed workflow_run contexts so AUTOPATCH_SAFE can activate.
            RERUN_ARGS+=("--rerun-failed")
          fi
    """.strip()
    assert workflow_run_block in workflow
    assert "DISPATCH_ARGS=(--dispatch-missing)" in workflow


@pytest.mark.parametrize(
    ("event_name", "upstream_event", "apply_expected"),
    [
        ("workflow_run", "pull_request", False),
        ("workflow_run", "push", True),
        ("workflow_run", "workflow_dispatch", True),
        ("schedule", "", True),
        ("workflow_dispatch", "", True),
    ],
)
def test_ci_health_uses_apply_only_for_existing_non_pr_contexts(
    tmp_path: Path, event_name: str, upstream_event: str, apply_expected: bool
) -> None:
    workflow = Path(".github/workflows/ci-health.yml").read_text(encoding="utf-8")
    steps = yaml.safe_load(workflow)["jobs"]["ci-health"]["steps"]
    verify_step = next(step for step in steps if step.get("name") == "Verify branch protection on main")
    assert verify_step["if"] == "${{ env.ADMIN_GITHUB_TOKEN != '' }}"
    script = verify_step["run"]
    assert '--branch "${CI_POLICY_BRANCH}"' in script
    assert "--required-checks-file scripts/required_checks.json" in script

    # Only this owned executable receives argv. It never loads the named verifier,
    # reads a token, contacts an API or changes repository settings.
    capture = tmp_path / "argv.json"
    fake_python = tmp_path / "python"
    fake_python.write_text(
        f"#!{sys.executable}\n"
        "import json, os, pathlib, sys\n"
        "pathlib.Path(os.environ['CI_HEALTH_ARGV_CAPTURE']).write_text(json.dumps(sys.argv[1:]))\n",
        encoding="utf-8",
    )
    fake_python.chmod(0o700)
    bash = shutil.which("bash")
    assert bash is not None
    script = script.replace("${{ github.event_name }}", event_name).replace(
        "${{ github.event.workflow_run.event }}", upstream_event
    )
    assert "${{" not in script
    result = subprocess.run(
        [bash, "-e", "-o", "pipefail", "-c", script],
        cwd=tmp_path,
        env={
            "PATH": str(tmp_path),
            "CI_POLICY_BRANCH": "main",
            "CI_HEALTH_ARGV_CAPTURE": str(capture),
        },
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    expected = ["scripts/verify_branch_protection.py", "--branch", "main"]
    if apply_expected:
        expected.append("--apply")
    expected.extend(["--required-checks-file", "scripts/required_checks.json"])
    assert json.loads(capture.read_text(encoding="utf-8")) == expected


def test_ci_health_scheduled_runs_hard_monitor_integration_ci() -> None:
    workflow = Path(".github/workflows/ci-health.yml").read_text(encoding="utf-8")

    assert "- name: Check merge-surface integration CI health" in workflow
    assert "--workflow ci.yml" in workflow
    assert "--dispatch-missing" in workflow
    assert "informational" not in workflow
