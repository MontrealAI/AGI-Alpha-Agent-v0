# SPDX-License-Identifier: Apache-2.0
"""Reproduce the exact portable bundle and protect its separate acceptance lane."""

from __future__ import annotations

import ast
import importlib.util
import hashlib
import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from types import ModuleType

import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_native_fleet_return_cannot_be_skipped_by_the_required_hosted_journey() -> None:
    """An actual immutable public checkout and mandatory mode guard the extra acceptance."""
    workflow = yaml.safe_load((ROOT / ".github/workflows/successor-capability.yml").read_text())
    steps = workflow["jobs"]["capability"]["steps"]
    checkouts = [step for step in steps if step.get("with", {}).get("repository") == "MontrealAI/AGI-Fleet-Linux"]
    assert len(checkouts) == 1
    checkout = checkouts[0]
    assert checkout["uses"] == "actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd"
    assert checkout["with"]["ref"] == "0dd352fdd2b1af00bc8358e0ac7f96682fd6f796"
    assert checkout["with"]["persist-credentials"] is False
    assert "if" not in checkout and not checkout.get("continue-on-error")
    journey = next(
        step for step in steps if "python tests/browser/test_discovery_lab_continuation.py" in step.get("run", "")
    )
    assert journey["env"]["DISCOVERY_FLEET_ROOT"].endswith("/" + checkout["with"]["path"])
    assert journey["env"]["DISCOVERY_FLEET_REQUIRED"] == "1"
    assert "if" not in journey and not journey.get("continue-on-error")
    events = workflow.get("on", workflow.get(True))
    for name in (
        "fleet_receipt_native.mjs",
        "fleet_module_boundary.mjs",
        "fleet_module_boundary.test.mjs",
        "fleet_git_metadata.mjs",
        "fleet_git_metadata.test.mjs",
    ):
        assert "tests/browser/" + name in events["pull_request"]["paths"]
    node_step = next(step["run"] for step in steps if "node --test" in step.get("run", ""))
    assert "tests/browser/fleet_module_boundary.test.mjs" in node_step
    assert "tests/browser/fleet_git_metadata.test.mjs" in node_step


def test_native_source_helper_refuses_unsafe_metadata_without_installing_or_running_commands(tmp_path: Path) -> None:
    """Inert configuration values exercise refusal before Git or source import."""
    node = shutil.which("node")
    assert node is not None
    request, mission = tmp_path / "request.json", tmp_path / "mission.json"
    request.write_text("{}")
    mission.write_text("{}")
    for name, config, expected in [
        (
            "filter",
            '[core]\n bare = false\n[filter "unavailable"]\n smudge = unavailable-value\n',
            "configuration section",
        ),
        ("include", "[core]\n bare = false\n[include]\n path = unsafe.cfg\n", "configuration section"),
        ("fsmonitor", "[core]\n bare = false\n fsmonitor = unavailable-value\n", "Git configuration is refused"),
        ("promisor", '[core]\n bare = false\n[remote "origin"]\n promisor = true\n', "Git configuration is refused"),
        ("partial", "[core]\n bare = false\n[extensions]\n partialClone = origin\n", "Git configuration is refused"),
        (
            "uploadpack",
            '[core]\n bare = false\n[remote "origin"]\n uploadpack = unavailable-value\n',
            "Git configuration is refused",
        ),
    ]:
        root = tmp_path / name
        (root / ".git").mkdir(parents=True)
        (root / ".git/config").write_text(config)
        result = subprocess.run(
            [
                node,
                str(ROOT / "tests/browser/fleet_receipt_native.mjs"),
                str(root),
                str(mission),
                str(request),
                str(tmp_path / (name + "-output")),
            ],
            text=True,
            capture_output=True,
            timeout=15,
            check=False,
        )
        assert result.returncode != 0 and expected in result.stderr


def test_native_source_helper_refuses_non_admitted_worktree_metadata(tmp_path: Path) -> None:
    """Only inert local metadata is supplied; refusal precedes any Git object read."""
    node = shutil.which("node")
    assert node is not None
    for kind, expected in [
        ("active-worktree", "worktree configuration is refused"),
        ("bare-worktree-key", "worktree configuration is refused"),
        ("commondir", "common Git directory"),
        ("worktree-directory", "metadata must be regular"),
        ("oversize-worktree", "Bounded regular file"),
    ]:
        root = tmp_path / kind
        directory = root / ".git"
        directory.mkdir(parents=True)
        config = "[core]\n bare = false\n"
        if kind == "active-worktree":
            config += "[extensions]\n worktreeConfig = false\n worktreeConfig = true\n"
        elif kind == "bare-worktree-key":
            config += "[extensions]\n worktreeConfig\n"
        (directory / "config").write_text(config)
        if kind == "commondir":
            (directory / "commondir").write_text("../unavailable\n")
        elif kind == "worktree-directory":
            (directory / "config.worktree").mkdir()
        else:
            (directory / "config.worktree").write_text(
                "#" + "x" * 128000 if kind == "oversize-worktree" else "[core]\n sparseCheckout = false\n"
            )
        mission, request = tmp_path / "mission.json", tmp_path / "request.json"
        mission.write_text("{}")
        request.write_text("{}")
        result = subprocess.run(
            [
                node,
                str(ROOT / "tests/browser/fleet_receipt_native.mjs"),
                str(root),
                str(mission),
                str(request),
                str(root / "absent-output"),
            ],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        assert result.returncode != 0 and expected in result.stderr, kind


def test_native_browser_attack_bank_is_predeclared_and_not_selected_by_the_producer() -> None:
    """Inspect the fixed acceptance inventory as inert syntax, without loading browser code."""
    tree = ast.parse((ROOT / "tests/browser/test_discovery_lab_continuation.py").read_text())
    declaration = next(
        node
        for node in tree.body
        if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "FLEET_VARIANTS" for target in node.targets)
    )
    assert ast.literal_eval(declaration.value) == (
        "executor",
        "runtime",
        "elapsed",
        "memory",
        "outcome",
        "raw-framing",
        "receipt-framing",
        "request-framing",
        "source-repository",
        "forged-authority",
        "swapped-mission",
    )
    acceptance = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "fleet_return")
    loops = [node for node in ast.walk(acceptance) if isinstance(node, ast.For)]
    assert any(isinstance(node.iter, ast.Name) and node.iter.id == "FLEET_VARIANTS" for node in loops)


def test_both_native_requests_are_actual_ui_downloads_with_one_pre_fleet_history() -> None:
    """Protect the two alternatives consumed from one authenticated browser artifact."""
    source = (ROOT / "tests/browser/test_discovery_lab_continuation.py").read_text()
    tree = ast.parse(source)
    function = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "fleet_return")
    downloads = [
        node
        for node in ast.walk(function)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "download_request"
    ]
    assert [ast.literal_eval(node.args[2]) for node in downloads] == ["USDC", "AGIALPHA"]
    journal = next(
        node.value
        for node in ast.walk(function)
        if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "request_exports" for target in node.targets)
    )

    def fields(node: ast.expr) -> dict[str, ast.expr]:
        assert isinstance(node, ast.Dict)
        result = {}
        for key, value in zip(node.keys, node.values):
            assert key is not None
            name = ast.literal_eval(key)
            assert isinstance(name, str) and name not in result
            result[name] = value
        return result

    entries = fields(journal)
    assert {"missionId", "campaignDigest", "sourceHash", "pageSha256", "workspace", "requests"} <= entries.keys()
    assert fields(entries["requests"]).keys() == {"manager-usdc", "jobs-agialpha"}
    assert {"file", "sha256", "jobsFile", "jobsSha256", "revision", "eventPrefix", "head"} <= fields(
        entries["workspace"]
    ).keys()
    assert "jobs_workspace_path.read_bytes() == workspace_path.read_bytes()" in source
    assert '"browser-native-requests.json"' in source and '"jobs-browser-request.json"' in source


def load_script(name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_portable_bundle_reproduces_and_gallery_preserves_exact_bytes() -> None:
    manifest = json.loads((ROOT / "docs/successor/capabilities/sources.json").read_text())
    with tempfile.TemporaryDirectory(prefix="capability-delivery-") as directory:
        isolated = Path(directory)
        for name in manifest["sources"]:
            target = isolated / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, target)
        load_script("generate_successor_capability").build(isolated)
        for name in ("index.html", "sources.json"):
            assert (isolated / "docs/successor/capabilities" / name).read_bytes() == (
                ROOT / "docs/successor/capabilities" / name
            ).read_bytes(), name
        page = isolated / "docs/successor/capabilities/index.html"
        original = page.read_bytes()
        load_script("generate_gallery_html").insert_back_link([page])
        assert page.read_bytes() == original


def test_acceptance_is_mandatory_read_only_and_retains_evidence() -> None:
    workflow = yaml.safe_load((ROOT / ".github/workflows/successor-capability.yml").read_text())
    assert workflow["permissions"] == {"contents": "read"}
    assert workflow["concurrency"]["group"].startswith("capability-")
    # Standalone and reusable release invocations must not cancel one another.
    assert "${{ github.workflow }}" in workflow["concurrency"]["group"]
    job = workflow["jobs"]["capability"]
    assert job["if"] == "${{ !cancelled() && success() && needs.paper-scope.outputs.mode == 'full' }}"
    assert job["needs"] == "paper-scope"
    assert workflow["jobs"]["paper-scope"]["uses"] == "./.github/workflows/paper-scope.yml"
    assert not job.get("continue-on-error")
    steps = job["steps"]
    for step in steps:
        if "uses" in step:
            assert re.fullmatch(r"[^@]+@[0-9a-f]{40}", step["uses"])
    commands = [
        "node --test examples/successor-capability/*.test.mjs",
        "python scripts/generate_successor_capability.py",
        "git diff --exit-code -- docs/successor/capabilities",
        "python tests/browser/test_successor_capability_browser.py",
    ]
    for command in commands:
        matches = [step for step in steps if command in step.get("run", "")]
        assert len(matches) == 1
        assert "if" not in matches[0] and not matches[0].get("continue-on-error")
    browser = next(step for step in steps if commands[-1] in step.get("run", ""))
    assert browser["env"]["AXE_SCRIPT"].endswith("/tests/browser/node_modules/axe-core/axe.min.js")
    retained = {
        commands[0]: "node.log",
        "tests/test_successor_capability_delivery.py -q": "delivery.log",
        "python -m mypy --strict": "typing.log",
        commands[-1]: "v1-browser.log",
        "python tests/browser/test_out_evolve_browser.py": "out-evolve-browser.log",
        "python tests/browser/test_out_execute_browser.py": "out-execute-browser.log",
        "node examples/successor-capability/out-execute/reproduce.mjs": "out-execute-study.log",
        "python tests/browser/test_successor_capability_accessibility.py": "accessibility-review.log",
    }
    for command, log in retained.items():
        step = next(step for step in steps if command in step.get("run", ""))
        assert "set -o pipefail" in step["run"]
        assert f"tee capability-evidence/logs/{log}" in step["run"]
        assert "if" not in step and not step.get("continue-on-error")
    typing = next(step["run"] for step in steps if "python -m mypy --strict" in step.get("run", ""))
    assert "tests/browser/out_evolve_recovery.py" in typing
    assert "tests/browser/test_out_execute_browser.py" in typing
    events = workflow.get("on", workflow.get(True))
    assert "tests/browser/out_evolve_recovery.py" in events["pull_request"]["paths"]
    assert "tests/browser/test_out_execute_browser.py" in events["pull_request"]["paths"]
    # This data file is consumed executable input in the generated browser bundle.
    assert "docs/discovery-lab/DEPLOYMENT_COMPATIBILITY.json" in events["pull_request"]["paths"]
    assert "workflow_call" in events
    node_step = next(step["run"] for step in steps if "node --test" in step.get("run", ""))
    assert "examples/successor-capability/out-execute/*.test.mjs" in node_step
    uploader = next(step for step in steps if step.get("uses", "").startswith("actions/upload-artifact@"))
    assert uploader["if"] == "always()"
    assert uploader["with"]["if-no-files-found"] == "error"


def test_release_packaging_requires_the_same_complete_capability_gate() -> None:
    workflow = yaml.safe_load((ROOT / ".github/workflows/agent-release.yml").read_text())
    assert workflow["permissions"] == {"contents": "read"}
    job = workflow["jobs"]["successor-capability"]
    assert job == {
        "if": "${{ !cancelled() && success() && needs.paper-scope.outputs.mode == 'full' }}",
        "needs": ["paper-scope", "publication-preflight"],
        "uses": "./.github/workflows/successor-capability.yml",
    }
    package = workflow["jobs"]["package"]
    assert "successor-capability" in package["needs"]
    assert package["if"] == "${{ !cancelled() && success() && needs.paper-scope.outputs.mode == 'full' }}"
    assert not package.get("continue-on-error")
    download = next(step for step in package["steps"] if step.get("uses", "").startswith("actions/download-artifact@"))
    assert download["with"]["pattern"] == "!{historical-ci,release-package,public-pages,github-pages}*"
    assert download["with"]["digest-mismatch"] == "error"


def test_retained_authored_study_is_bound_to_installed_source_and_keeps_counterbaselines() -> None:
    record = json.loads((ROOT / "docs/agent/release-evidence/out-execute-authored-study-20261021.json").read_text())
    summary = record["summary"]
    assert record["scope"] == "local-authored-finite-study-not-release-acceptance"
    assert summary["manuscriptCompanionReproduced"] is False
    for group in ("compilerSources", "checkerSources"):
        for path, expected in summary["source"][group].items():
            assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == expected, path
    for path, expected in record["studyHarnessSources"].items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == expected, path
    assert summary["snapshots"] == summary["matches"] == 576
    assert summary["semanticStops"] == 160 != summary["manuscriptClaimCounts"]["semanticStops"]
    assert summary["executionWork"] == summary["matchedIncrementalWork"]
    assert summary["identicalInputControl"]["fixedSecond"] < summary["identicalInputControl"]["boundarySecond"]
    assert summary["localArchiveReopenAudit"]["profileComparisons"] > 0
    assert len(record["retainedFixtureSha256"]) == summary["fixtures"] == 64
