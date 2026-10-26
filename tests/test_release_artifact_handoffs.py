# SPDX-License-Identifier: Apache-2.0
"""Release retries must consume the successful producer's evidence, not older IDs."""

from __future__ import annotations

import fnmatch
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml

WORKFLOW = Path(__file__).resolve().parents[1] / ".github/workflows/agent-release.yml"


def jobs() -> dict[str, Any]:
    """Load the real release handoffs rather than a copied workflow fixture."""
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))["jobs"]


def producer_name(
    job: dict[str, Any], attempt: int, temporary: Path, output_key: str = "artifact-name", assets: str | None = None
) -> str:
    """Execute the actual producer naming step with GitHub's output-file contract."""
    expression = job["outputs"][output_key]
    match = re.fullmatch(r"\$\{\{ steps\.([\w-]+)\.outputs\.([\w-]+) }}", expression)
    assert match, "The artifact name must be saved by its producing job"
    step = next(step for step in job["steps"] if step.get("id") == match[1])
    output = temporary / f"output-{output_key}-{assets or 'single'}-{attempt}.txt"
    environment = dict(
        os.environ, GITHUB_RUN_ID="37836936731", GITHUB_RUN_ATTEMPT=str(attempt), GITHUB_OUTPUT=str(output)
    )
    if assets is not None:
        assert step["env"] == {"ASSETS": "${{ matrix.assets }}"}
        environment["ASSETS"] = assets
    subprocess.run(["bash", "-eu", "-o", "pipefail", "-c", step["run"]], env=environment, check=True, cwd=temporary)
    values = dict(line.split("=", 1) for line in output.read_text(encoding="utf-8").splitlines())
    upload = next(step for step in job["steps"] if step.get("uses", "").startswith("actions/upload-artifact@"))
    assert upload["with"]["name"] == "${{ steps." + match[1] + ".outputs.name }}"
    assert values[match[2]] == values["name"]
    assert step.get("if", "success()") == upload.get("if", "success()")
    return values[match[2]]


@pytest.mark.skipif(shutil.which("bash") is None, reason="The release workflow runs its naming steps with Bash")
@pytest.mark.parametrize(
    ("producer", "consumer", "destination"),
    [
        ("historical-ci", "package", "evidence/historical-ci"),
        ("regression", "package", "evidence/regression"),
        ("package", "publish", "release"),
        ("pages", "publish", "public-evidence"),
    ],
)
def test_retry_downloads_successful_producer_even_when_its_artifact_id_is_lower(
    tmp_path: Path, producer: str, consumer: str, destination: str
) -> None:
    workflow_jobs = jobs()
    first = producer_name(workflow_jobs[producer], 1, tmp_path)
    successful = producer_name(workflow_jobs[producer], 2, tmp_path)
    assert first != successful
    # These IDs reproduce the observed non-monotonic historical artifact order.
    artifacts = [
        {"id": 11579020890, "name": first, "evidence": "older failed attempt"},
        {"id": 11578747603, "name": successful, "evidence": "successful producer"},
    ]
    download = next(
        step
        for step in workflow_jobs[consumer]["steps"]
        if step.get("uses", "").startswith("actions/download-artifact@")
        and step.get("with", {}).get("path") == destination
    )
    # A dependent-only third retry must retain attempt two's job output, rather
    # than recompute a nonexistent attempt-three artifact or choose the largest ID.
    assert download["with"]["name"] == "${{ needs." + producer + ".outputs.artifact-name }}"
    assert download["with"]["digest-mismatch"] == "error"
    assert producer in workflow_jobs[consumer]["needs"]
    selected = [artifact for artifact in artifacts if artifact["name"] == successful]
    assert len(selected) == 1
    assert selected[0]["evidence"] == "successful producer"
    assert selected[0]["id"] < max(artifact["id"] for artifact in artifacts)


def test_bulk_download_excludes_failed_history_and_previous_release_outputs() -> None:
    download = next(step for step in jobs()["package"]["steps"] if step.get("with", {}).get("path") == "evidence")
    pattern = download["with"]["pattern"]
    # The action uses Minimatch with default leading-! negation and brace expansion.
    match = re.fullmatch(r"!\{([\w,-]+)}\*", pattern)
    assert match, "Bulk evidence must exclude prior attempts' downstream artifacts"
    exclusions = [prefix + "*" for prefix in match[1].split(",")]

    def retained(name: str) -> bool:
        return not any(fnmatch.fnmatchcase(name, exclusion) for exclusion in exclusions)

    for prefix in ("historical-ci", "release-package", "public-pages", "github-pages", "regression", "gallery-"):
        assert not retained(prefix)
        assert not retained(prefix + "-37836936731-1")
        assert not retained(prefix + "-37836936731-2")
    for name in ("runtime-3.12", "browser-contracts", "browser-distribution", "pages-distribution"):
        assert retained(name)
    assert download["with"]["digest-mismatch"] == "error"


@pytest.mark.skipif(shutil.which("bash") is None, reason="The release workflow uses Bash")
def test_matrix_retry_keeps_both_successful_profiles_without_selecting_failed_higher_ids(tmp_path: Path) -> None:
    workflow_jobs = jobs()
    gallery = workflow_jobs["gallery"]
    outputs = {}
    for assets, successful_attempt in (("full", 1), ("minimal", 3)):
        key = assets + "-artifact-name"
        successful = producer_name(gallery, successful_attempt, tmp_path, key, assets)
        failed = producer_name(gallery, 2, tmp_path, key, assets)
        assert successful != failed
        outputs[key] = successful
        artifacts = [
            {"id": 12689498426, "name": failed, "files": {"historical-fixture.json"}},
            {"id": 12688624907, "name": successful, "files": {"successor-alpha/report.json"}},
        ]
        download = next(
            step
            for step in workflow_jobs["package"]["steps"]
            if step.get("with", {}).get("path") == "evidence/gallery-" + assets
        )
        assert download["with"]["name"] == "${{ needs.gallery.outputs." + key + " }}"
        assert download["with"]["digest-mismatch"] == "error"
        assert "gallery" in workflow_jobs["package"]["needs"]
        selected = [artifact for artifact in artifacts if artifact["name"] == outputs[key]]
        assert len(selected) == 1 and "successor-alpha/report.json" in selected[0]["files"]
        assert selected[0]["id"] < artifacts[0]["id"]
    assert outputs["full-artifact-name"].endswith("-1")
    assert outputs["minimal-artifact-name"].endswith("-3")


@pytest.mark.skipif(shutil.which("bash") is None, reason="The release workflow uses Bash")
@pytest.mark.parametrize(
    ("key", "value", "accepted"),
    [
        ("MINIMAL_GALLERY_ARTIFACT", "gallery-minimal-37836936731-3", True),
        ("REGRESSION_ARTIFACT", "", False),
        ("FULL_GALLERY_ARTIFACT", "", False),
        ("MINIMAL_GALLERY_ARTIFACT", "", False),
        ("MINIMAL_GALLERY_ARTIFACT", "gallery-full-37836936731-3", False),
        ("MINIMAL_GALLERY_ARTIFACT", "gallery-minimal-999-3", False),
        ("MINIMAL_GALLERY_ARTIFACT", "gallery-minimal-37836936731-0", False),
        ("REGRESSION_ARTIFACT", "regression-37836936731-2/untrusted", False),
    ],
)
def test_missing_or_cross_run_producer_output_cannot_fall_back_to_bulk_download(
    tmp_path: Path, key: str, value: str, accepted: bool
) -> None:
    sequence = jobs()["package"]["steps"]
    guard = next(step for step in sequence if step.get("name") == "Require successful producer artifact names")
    assert sequence.index(guard) < next(
        index for index, step in enumerate(sequence) if step.get("uses", "").startswith("actions/download-artifact@")
    )
    assert guard["env"] == {
        "REGRESSION_ARTIFACT": "${{ needs.regression.outputs.artifact-name }}",
        "FULL_GALLERY_ARTIFACT": "${{ needs.gallery.outputs.full-artifact-name }}",
        "MINIMAL_GALLERY_ARTIFACT": "${{ needs.gallery.outputs.minimal-artifact-name }}",
    }
    environment = dict(
        os.environ,
        GITHUB_RUN_ID="37836936731",
        GITHUB_RUN_ATTEMPT="4",
        REGRESSION_ARTIFACT="regression-37836936731-2",
        FULL_GALLERY_ARTIFACT="gallery-full-37836936731-1",
        MINIMAL_GALLERY_ARTIFACT="gallery-minimal-37836936731-3",
    )
    environment[key] = value
    result = subprocess.run(
        ["bash", "-eu", "-o", "pipefail", "-c", guard["run"]], env=environment, check=False, cwd=tmp_path, timeout=5
    )
    assert (result.returncode == 0) is accepted


def test_pages_deploys_the_unique_artifact_uploaded_in_its_own_attempt() -> None:
    steps = jobs()["pages"]["steps"]
    upload = next(step for step in steps if step.get("uses", "").startswith("actions/upload-pages-artifact@"))
    deploy = next(step for step in steps if step.get("uses", "").startswith("actions/deploy-pages@"))
    name = upload["with"]["name"]
    assert name == deploy["with"]["artifact_name"]
    assert "${{ github.run_id }}" in name
    assert "${{ github.run_attempt }}" in name
