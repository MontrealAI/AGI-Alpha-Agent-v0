# SPDX-License-Identifier: Apache-2.0
"""Prevent publication bypass or accidental upload of native private journal state."""

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_release_package_requires_real_transformational_acceptance():
    release = yaml.load((ROOT / ".github/workflows/agent-release.yml").read_text(), Loader=yaml.BaseLoader)
    jobs = release["jobs"]
    assert "transformational-intelligence" in jobs["package"]["needs"]
    assert jobs["transformational-intelligence"]["uses"] == "./.github/workflows/transformational-intelligence.yml"
    acceptance = yaml.load(
        (ROOT / ".github/workflows/transformational-intelligence.yml").read_text(), Loader=yaml.BaseLoader
    )
    steps = acceptance["jobs"]["bounded-discovery"]["steps"]
    required = [
        "tests.test_transformational_paper",
        "scripts/reproduce_transformational_paper.py",
        "test_transformation.py",
        "test_transformation_review.py",
        "test_transformation_source_audit.py",
        "test_transformation_library.py",
        "test_measurement.py",
        "test_measurement_review.py",
        "inspector.test.mjs",
        "transformational_intelligence.test.mjs",
        "test_transformational_intelligence_browser.py",
        "transformation_source_audit_cli",
    ]
    for command in required:
        step = next(step for step in steps if command in step.get("run", ""))
        assert "if" not in step and "continue-on-error" not in step


def test_workflow_artifacts_exclude_private_native_state():
    source = (ROOT / ".github/workflows/transformational-intelligence.yml").read_text()
    assert '--home "$RUNNER_TEMP/ti-local-agent"' in source
    assert "--home evidence/" not in source
    workflow = yaml.load(source, Loader=yaml.BaseLoader)
    artifacts = [
        step for step in workflow["jobs"]["bounded-discovery"]["steps"] if "upload-artifact" in step.get("uses", "")
    ]
    assert len(artifacts) == 1 and artifacts[0]["with"]["path"] == "evidence/"


def test_release_requires_full_ti_packaged_and_public_browser_readback():
    workflow = yaml.load((ROOT / ".github/workflows/agent-release.yml").read_text(), Loader=yaml.BaseLoader)
    steps = [step for job in workflow["jobs"].values() for step in job.get("steps", [])]
    validators = [step for step in steps if "scripts.validate_transformational_intelligence" in step.get("run", "")]
    assert len(validators) == 2
    assert any("--url https://montrealai.github.io/AGI-Alpha-Agent-v0/" in step["run"] for step in validators)
    assert any("--output evidence/transformational-intelligence" in step["run"] for step in validators)
    assert all("continue-on-error" not in step and "if" not in step for step in validators)
