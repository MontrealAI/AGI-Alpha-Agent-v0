# SPDX-License-Identifier: Apache-2.0
"""Independent contracts for trusted paper scope and reviewed software gates."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
from typing import Any

import pytest
import yaml

from scripts import release_context

ROOT = Path(__file__).resolve().parents[1]
REVIEWED_BASE = "07aca9ba9e98db173de8efd69cfe51095c168a59"
GATED = (
    "agent-release.yml",
    "alpha-authority-v2.yml",
    "ci.yml",
    "pr-ci.yml",
    "smoke.yml",
    "successor-capability.yml",
    "successor-mission.yml",
    "transformational-intelligence.yml",
)


class UniqueLoader(yaml.SafeLoader):
    """Ordinary safe_load silently discards duplicate workflow mapping keys."""


def unique_mapping(loader: UniqueLoader, node: yaml.MappingNode) -> dict[str, Any]:
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node)
        if key in result:
            raise ValueError(f"Duplicate YAML key {key!r} on line {key_node.start_mark.line + 1}")
        result[key] = loader.construct_object(value_node)
    return result


UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, unique_mapping)


def workflow(name: str, *, baseline: bool = False) -> dict[str, Any]:
    path = ".github/workflows/" + name
    text = (
        subprocess.check_output(
            ["git", "--no-replace-objects", "-C", str(ROOT), "show", f"{REVIEWED_BASE}:{path}"], text=True
        )
        if baseline
        else (ROOT / path).read_text()
    )
    result = yaml.load(text, Loader=UniqueLoader)
    assert isinstance(result, dict)
    return result


def dependencies(job: dict[str, Any]) -> set[str]:
    value = job.get("needs", [])
    return {value} if isinstance(value, str) else set(value)


@pytest.mark.parametrize("name", (*GATED, "paper-scope.yml", "paper-preview.yml", "paper-publication.yml"))
def test_workflow_yaml_has_no_duplicate_mapping_keys(name: str) -> None:
    workflow(name)


@pytest.mark.parametrize("name", GATED)
def test_runtime_gates_preserve_original_permissions_dependencies_and_failure_semantics(name: str) -> None:
    old, new = workflow(name, baseline=True), workflow(name)
    assert new.get("permissions") == old.get("permissions")
    assert new["jobs"]["paper-scope"]["uses"] == "./.github/workflows/paper-scope.yml"
    for key, before in old["jobs"].items():
        after = new["jobs"][key]
        assert after.get("permissions") == before.get("permissions"), (name, key)
        added_dependencies = {"paper-scope"}
        if (name, key) == ("agent-release.yml", "package"):
            # The combined software release adds, never substitutes, its exact-source
            # capability/browser/recovery gate. The delivery test binds that call.
            added_dependencies.add("successor-capability")
        expected_dependencies = dependencies(before) | added_dependencies
        if (name, key) == ("agent-release.yml", "historical-ci"):
            # Waiting is deferred until every substantive package prerequisite completes.
            expected_dependencies |= dependencies(new["jobs"]["package"]) - {"historical-ci"}
        if (name, key) == ("pr-ci.yml", "smoke"):
            # Lint and smoke independently feed their required verdicts.
            expected_dependencies.discard("lint")
        assert dependencies(after) == expected_dependencies, (name, key)
        condition = after.get("if", "")
        assert "needs.paper-scope.outputs.mode == 'full'" in condition, (name, key)
        assert "!cancelled()" in condition, (name, key)
        if "always()" not in before.get("if", ""):
            assert "success()" in condition, (name, key)
        else:
            assert "always()" not in condition, (name, key)
        # Step-level diagnostic/cleanup always() must survive the job-level gate.
        old_cleanup = [step for step in before.get("steps", []) if "always()" in step.get("if", "")]
        for cleanup in old_cleanup:
            matches = [
                step
                for step in after.get("steps", [])
                if (step.get("name"), step.get("uses")) == (cleanup.get("name"), cleanup.get("uses"))
            ]
            assert any(step.get("if") == cleanup.get("if") for step in matches), (name, key, cleanup)
    if "concurrency" in old:
        assert "${{ github.sha }}" in new["concurrency"]["group"]
        assert new["concurrency"]["cancel-in-progress"] == old["concurrency"]["cancel-in-progress"]


@pytest.mark.parametrize("name", ("ci.yml", "pr-ci.yml", "smoke.yml"))
def test_full_software_marker_depends_on_all_main_runtime_jobs(name: str) -> None:
    jobs = workflow(name)["jobs"]
    markers = [job for job in jobs.values() if job.get("name") == "Full software qualification"]
    assert len(markers) == 1
    marker = markers[0]
    assert "needs.paper-scope.outputs.mode == 'full'" in marker["if"]
    assert "github.ref == 'refs/heads/main'" in marker["if"]
    assert "!cancelled()" in marker["if"]
    required = set(jobs) - {"full-software-qualification"}
    if name == "ci.yml":
        # The historical tag-only deploy was never part of main acceptance.
        assert "startsWith(github.ref, 'refs/tags/')" in jobs["deploy"]["if"]
        required.remove("deploy")
    assert dependencies(marker) == required


@pytest.mark.parametrize("name", ("ci.yml", "pr-ci.yml", "smoke.yml"))
@pytest.mark.parametrize("status", ("success", "failure", "cancelled", "skipped"))
def test_actual_marker_script_rejects_any_unsuccessful_dependency(name: str, status: str, tmp_path: Path) -> None:
    marker = workflow(name)["jobs"]["full-software-qualification"]
    results = {key: {"result": "success"} for key in dependencies(marker)}
    results[next(key for key in results if key != "paper-scope")]["result"] = status
    script = next(step["run"] for step in marker["steps"] if "run" in step)
    result = subprocess.run(
        ["bash", "-eu", "-o", "pipefail", "-c", script],
        cwd=tmp_path,
        env={**os.environ, "RESULTS": json.dumps(results)},
        capture_output=True,
        text=True,
    )
    assert (result.returncode == 0) == (status == "success"), result.stderr


def test_paper_scope_executes_only_extracted_prechange_policy() -> None:
    policy = workflow("paper-scope.yml")
    assert policy["permissions"] == {"contents": "read"}
    job = policy["jobs"]["classify"]
    checkout = next(step for step in job["steps"] if step.get("uses", "").startswith("actions/checkout@"))
    assert checkout["with"]["persist-credentials"] is False
    assert checkout["with"]["fetch-depth"] == 0
    step = next(step for step in job["steps"] if step.get("id") == "scope")
    script = step["run"]
    assert 'git --no-replace-objects show "$BASE:$file" > "$policy/$file"' in script
    assert 'cd "$policy"' in script
    assert script.index('cd "$policy"') < script.index("python scripts/paper_changes.py")
    extracted = script.split("for file in", 1)[1].split("; do", 1)[0]
    for required in ("scripts/release_plan.py", "scripts/check_editorial_docs.py", "requirements-editorial-docs.lock"):
        assert required in extracted
    assert script.index("python scripts/paper_changes.py") < script.index("python -m scripts.check_editorial_docs")
    assert '--root "$GITHUB_WORKSPACE" --base "$BASE" --head "$HEAD"' in script
    assert 'python -m scripts.research_papers --root "$GITHUB_WORKSPACE" check' in script
    assert "--require-hashes --only-binary=:all: -r requirements-papers.lock" in script
    assert "git checkout" not in script and "git switch" not in script


@pytest.mark.parametrize("event,base", [("workflow_dispatch", "a" * 40), ("push", "0" * 40), ("pull_request", "")])
def test_unbounded_scope_defaults_full_without_running_source(event: str, base: str, tmp_path: Path) -> None:
    step = next(step for step in workflow("paper-scope.yml")["jobs"]["classify"]["steps"] if step.get("id") == "scope")
    output = tmp_path / "output"
    result = subprocess.run(
        ["bash", "-eu", "-o", "pipefail", "-c", step["run"]],
        cwd=tmp_path,
        env={
            **os.environ,
            "RUNNER_TEMP": str(tmp_path),
            "GITHUB_OUTPUT": str(output),
            "GITHUB_WORKSPACE": str(tmp_path),
            "EVENT": event,
            "BASE": base,
            "HEAD": "b" * 40,
        },
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert output.read_text() == "mode=full\n"


def test_both_deployment_lanes_share_lock_and_recheck_immediately_before_deploy() -> None:
    software = workflow("agent-release.yml")["jobs"]["pages"]
    paper = workflow("paper-publication.yml")["jobs"]["deploy"]
    assert software["concurrency"] == paper["concurrency"] == {"group": "github-pages", "cancel-in-progress": False}
    assert (
        software["permissions"] == paper["permissions"] == {"contents": "read", "pages": "write", "id-token": "write"}
    )
    for job, command in (
        (software, "python -m scripts.release_context --before-software-deploy"),
        (paper, "python -m scripts.publish_paper_site guard"),
    ):
        steps = job["steps"]
        index = next(
            index for index, step in enumerate(steps) if step.get("uses", "").startswith("actions/deploy-pages@")
        )
        assert steps[index - 1]["run"] == command


@pytest.mark.parametrize(
    "missing", ["scripts/release_plan.py", "scripts/check_editorial_docs.py", "requirements-editorial-docs.lock"]
)
def test_missing_prechange_release_policy_falls_back_full_before_branch_code(tmp_path: Path, missing: str) -> None:
    from tests.test_paper_changes import git, save

    git(tmp_path, "init", "-b", "main")
    git(tmp_path, "config", "user.name", "Fixture")
    git(tmp_path, "config", "user.email", "fixture@example.invalid")
    (tmp_path / "scripts").mkdir()
    # Every available policy file would fail if executed; one trusted input is
    # absent even though the candidate supplies it. Installation must fall back.
    for path in (
        "scripts/paper_changes.py",
        "scripts/release_plan.py",
        "scripts/check_editorial_docs.py",
        "scripts/research_papers.py",
        "scripts/build_service_worker.py",
        "requirements-papers.lock",
        "requirements-editorial-docs.lock",
    ):
        if path != missing:
            (tmp_path / path).write_text("raise AssertionError('must not execute')\n")
    base = save(tmp_path)
    (tmp_path / missing).write_text("raise AssertionError('untrusted branch policy')\n")
    head = save(tmp_path)
    step = next(step for step in workflow("paper-scope.yml")["jobs"]["classify"]["steps"] if step.get("id") == "scope")
    output = tmp_path / "output"
    result = subprocess.run(
        ["bash", "-eu", "-o", "pipefail", "-c", step["run"]],
        cwd=tmp_path,
        env={
            **os.environ,
            "RUNNER_TEMP": str(tmp_path),
            "GITHUB_OUTPUT": str(output),
            "GITHUB_WORKSPACE": str(tmp_path),
            "EVENT": "push",
            "BASE": base,
            "HEAD": head,
        },
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert output.read_text() == "mode=full\n"


def test_descendant_check_fetches_objects_without_executing_new_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import scripts.paper_changes as classifier

    commands = []

    def run(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess:
        commands.append(command)
        return subprocess.CompletedProcess(command, 1 if "cat-file" in command else 0)

    proofs = []
    monkeypatch.setattr(release_context.subprocess, "run", run)
    monkeypatch.setattr(classifier, "prove_paper_descendants", lambda *args: proofs.append(args) or {"mode": "paper"})
    release_context.require_paper_descendant(tmp_path, "a" * 40, "b" * 40)
    assert proofs == [(tmp_path, "a" * 40, "b" * 40)]
    assert len(commands) == 2
    assert all(command[:2] == ["git", "--no-replace-objects"] for command in commands)
    assert commands[-1][-2:] == [f"https://github.com/{release_context.REPOSITORY}.git", "b" * 40]
    assert "fetch" in commands[-1] and "--no-tags" in commands[-1]
    assert not any("checkout" in command or "switch" in command for command in commands)


@pytest.mark.parametrize(
    "status,payload,error,permitted",
    [
        (1, "", "gh: Not Found (HTTP 404)", True),
        (0, {"tag_name": "v1.2.3", "draft": True}, "", True),
        (0, {"tag_name": "v1.2.3", "draft": False}, "", False),
        (0, {"tag_name": "v9.9.9", "draft": True}, "", False),
        (0, {"tag_name": "v1.2.3", "draft": 1}, "", False),
        (1, "", "gh: Forbidden (HTTP 403)", False),
        (1, "", "gh: Bad Gateway (HTTP 502)", False),
    ],
)
def test_software_lock_guard_uses_exact_tag_and_only_known_absence_allows_deploy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, status: int, payload: Any, error: str, permitted: bool
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "pyproject.toml").write_text('[project]\nversion = "1.2.3"\n')
    commands = []

    def run(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess:
        commands.append(command)
        return subprocess.CompletedProcess(command, status, json.dumps(payload), error)

    monkeypatch.setattr(release_context.subprocess, "run", run)
    if permitted:
        release_context.require_unpublished_software()
    else:
        with pytest.raises((ValueError, RuntimeError)):
            release_context.require_unpublished_software()
    assert len(commands) == 1
    assert f"repos/{release_context.REPOSITORY}/releases/tags/v1.2.3" in commands[0]
    assert not any("releases?" in part for part in commands[0])


def test_existing_required_check_names_are_unique_always_running_verdicts() -> None:
    required = json.loads((ROOT / "scripts/required_checks.json").read_text())
    assert required == ["Lint (ruff)", "Smoke tests"]
    jobs = workflow("pr-ci.yml")["jobs"]
    for name in required:
        matches = [job for job in jobs.values() if job.get("name") == name]
        assert len(matches) == 1
        verdict = matches[0]
        assert "always()" in verdict["if"] and "!cancelled()" not in verdict["if"]
        assert "paper-scope" in dependencies(verdict)
        assert len(dependencies(verdict)) >= 2
        assert not any(step.get("uses", "").startswith("actions/checkout@") for step in verdict["steps"])
    assert jobs["lint"]["name"] == "Full lint (ruff)"
    assert jobs["smoke"]["name"] == "Full smoke tests"
    assert "lint" in dependencies(next(job for job in jobs.values() if job.get("name") == "Lint (ruff)"))
    assert "smoke" in dependencies(next(job for job in jobs.values() if job.get("name") == "Smoke tests"))


@pytest.mark.parametrize("required_name", ("Lint (ruff)", "Smoke tests"))
@pytest.mark.parametrize("scope_result", ("success", "failure", "cancelled", "skipped"))
@pytest.mark.parametrize("mode", ("paper", "full", "unknown", ""))
@pytest.mark.parametrize("runtime_result", ("success", "failure", "cancelled", "skipped"))
def test_required_verdict_truth_table_cannot_accept_failed_paper_scope(
    required_name: str, scope_result: str, mode: str, runtime_result: str, tmp_path: Path
) -> None:
    jobs = workflow("pr-ci.yml")["jobs"]
    verdict = next(job for job in jobs.values() if job.get("name") == required_name)
    results = {key: {"result": runtime_result} for key in dependencies(verdict)}
    results["paper-scope"] = {"result": scope_result, "outputs": {"mode": mode}}
    environment = {**os.environ, "GITHUB_STEP_SUMMARY": str(tmp_path / "summary")}
    for step in verdict["steps"]:
        for key, value in step.get("env", {}).items():
            if value == "${{ toJSON(needs) }}":
                environment[key] = json.dumps(results)
            elif value == "${{ needs.paper-scope.result }}":
                environment[key] = scope_result
            elif value == "${{ needs.paper-scope.outputs.mode }}":
                environment[key] = mode
            elif value in {"${{ needs.lint.result }}", "${{ needs.smoke.result }}"}:
                environment[key] = runtime_result
            else:
                assert "${{" not in str(value), f"Unmodelled verdict environment: {key}={value}"
                environment[key] = str(value)
    script = "\n".join(step["run"] for step in verdict["steps"] if "run" in step)
    result = subprocess.run(
        ["bash", "-eu", "-o", "pipefail", "-c", script], cwd=tmp_path, env=environment, capture_output=True, text=True
    )
    permitted = scope_result == "success" and (mode == "paper" or (mode == "full" and runtime_result == "success"))
    assert (result.returncode == 0) == permitted, (scope_result, mode, runtime_result, result.stdout, result.stderr)


PREVIEW_FILES = {
    "README.md",
    "docs/index.html",
    "docs/service-worker.js",
    "docs/assets/service-worker.js",
    "docs/alpha_factory_v1/demos/alpha_agi_insight_v1/service-worker.js",
}


def preview_steps() -> tuple[dict[str, Any], dict[str, Any]]:
    steps = workflow("paper-preview.yml")["jobs"]["web-preview"]["steps"]
    preview = next(step for step in steps if step.get("id") == "preview")
    artifact = next(step for step in steps if step.get("uses", "").startswith("actions/upload-artifact@"))
    return preview, artifact


def test_optional_preview_never_qualifies_papers_or_blocks_full_fallback() -> None:
    policy = workflow("paper-scope.yml")
    job = policy["jobs"]["classify"]
    assert set(policy["jobs"]) == {"classify"}
    preview_policy = workflow("paper-preview.yml")
    preview_job = preview_policy["jobs"]["web-preview"]
    preview, artifact = preview_steps()
    assert policy["permissions"] == {"contents": "read"}
    assert job["outputs"] == {"mode": "${{ steps.scope.outputs.mode }}"}
    assert dependencies(preview_job) == {"paper-scope"}
    assert preview_policy["jobs"]["paper-scope"]["uses"] == "./.github/workflows/paper-scope.yml"
    assert "github.event_name == 'pull_request'" in preview_job["if"]
    assert "needs.paper-scope.outputs.mode == 'full'" in preview_job["if"]
    assert preview_job["continue-on-error"] is True
    assert "outputs" not in preview_job
    assert 0 < preview["timeout-minutes"] < preview_job["timeout-minutes"] < job["timeout-minutes"]
    assert 0 < artifact["timeout-minutes"] < preview_job["timeout-minutes"]
    assert preview["continue-on-error"] is True
    assert artifact["continue-on-error"] is True
    assert artifact["if"] == "steps.preview.outcome == 'success'"
    assert "not release evidence" in artifact["name"]
    assert "NOT acceptance" in preview["run"]
    assert "untrusted proposed changes before opening or uploading" in preview["run"]
    assert artifact["with"]["name"].startswith("paper-preview-")
    assert artifact["with"]["path"] == "${{ runner.temp }}/paper-preview/"
    assert artifact["with"]["if-no-files-found"] == "ignore"
    assert "GITHUB_OUTPUT" not in preview["run"]
    assert "GITHUB_ENV" not in preview["run"]
    assert "git commit" not in preview["run"] and "git push" not in preview["run"]
    assert "GH_TOKEN" not in preview.get("env", {})
    assert not any(step.get("uses", "").startswith("actions/deploy-pages@") for step in preview_job["steps"])


def test_preview_uses_only_trusted_policy_and_locked_wheels() -> None:
    preview, _ = preview_steps()
    script = preview["run"]
    assert preview["env"] == {"BASE": "${{ github.event.pull_request.base.sha }}"}
    assert '[[ "$BASE" =~ ^[0-9a-f]{40}$ ]]' in script
    assert 'git --no-replace-objects show "$BASE:$file" > "$policy/$file"' in script
    assert 'touch "$policy/scripts/__init__.py"' in script
    assert script.index('git --no-replace-objects show "$BASE:$file"') < script.index('cd "$policy"')
    checkout = next(
        step
        for step in workflow("paper-preview.yml")["jobs"]["web-preview"]["steps"]
        if step.get("uses", "").startswith("actions/checkout@")
    )
    assert checkout["with"]["persist-credentials"] is False
    assert checkout["with"]["fetch-depth"] == 0
    assert script.index('cd "$policy"') < script.index("python -m pip")
    assert "python -m pip install --require-hashes --only-binary=:all: -r requirements-papers.lock" in script
    assert 'python -m scripts.research_papers --root "$GITHUB_WORKSPACE" render' in script
    assert script.index("python -m scripts.research_papers") < script.index('cd "$GITHUB_WORKSPACE"')
    assert "python " not in script.split('cd "$GITHUB_WORKSPACE"', 1)[1]
    assert "npm " not in script and "latex" not in script and "playwright" not in script
    copy = next(line for line in script.splitlines() if line.startswith("cp --parents "))
    assert set(shlex.split(copy)[2:-1]) == PREVIEW_FILES


def preview_environment(tmp_path: Path) -> tuple[Path, dict[str, str]]:
    """Real trusted renderer and passive parser; pip is a no-network assertion double."""
    import pypdf

    from tests.test_research_papers import write_paper_fixture

    workspace = tmp_path / "untrusted-checkout"
    workspace.mkdir()
    write_paper_fixture(workspace)
    (workspace / "scripts").mkdir()
    for name in ("research_papers.py", "build_service_worker.py"):
        shutil.copyfile(ROOT / "scripts" / name, workspace / "scripts" / name)
    (workspace / "scripts/__init__.py").write_text("")
    shutil.copyfile(ROOT / "requirements-papers.lock", workspace / "requirements-papers.lock")
    for args in (
        ["init", "--quiet"],
        ["add", "."],
        ["-c", "user.email=test@example.invalid", "-c", "user.name=Fixture", "commit", "--quiet", "-m", "Fixture"],
    ):
        subprocess.run(["git", "-C", str(workspace), *args], check=True, capture_output=True)
    base = subprocess.check_output(["git", "-C", str(workspace), "rev-parse", "HEAD"], text=True).strip()
    # These files are deliberately executable poison, not imports the preview may use.
    poison = (
        "from pathlib import Path\n"
        "Path(__file__).parent.joinpath('SOURCE_EXECUTED').write_text('bad')\n"
        "raise RuntimeError('PR source executed')\n"
    )
    for name in (
        "scripts/__init__.py",
        "scripts/research_papers.py",
        "scripts/build_service_worker.py",
        "sitecustomize.py",
        "pypdf.py",
        "json.py",
    ):
        path = workspace / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(poison)
    (workspace / "requirements-papers.lock").write_text("UNTRUSTED WHEEL REQUIREMENT MUST NOT BE USED\n")
    binary = tmp_path / "bin"
    binary.mkdir()
    shim = binary / "python"
    shim.write_text(
        "#!/bin/bash\nset -eu\n"
        'if [[ "$1" == -m && "$2" == pip ]]; then\n'
        '  [[ "$*" == "-m pip install --require-hashes --only-binary=:all: -r requirements-papers.lock" ]]\n'
        '  [[ "$PWD" == "$RUNNER_TEMP/paper-policy" ]]\n'
        '  cmp requirements-papers.lock "$TRUSTED_LOCK"\n'
        '  echo trusted-pip >> "$RUNNER_TEMP/pip-calls"\n'
        "  exit 0\nfi\n"
        f'exec {shlex.quote(sys.executable)} "$@"\n'
    )
    shim.chmod(0o755)
    output = tmp_path / "scope-output"
    output.write_text("mode=full\n")
    environment = {
        **os.environ,
        "PATH": str(binary) + os.pathsep + os.environ["PATH"],
        # Keep the installed parser, never inherited working-checkout import paths.
        "PYTHONPATH": str(Path(pypdf.__file__).resolve().parent.parent),
        "RUNNER_TEMP": str(tmp_path),
        "BASE": base,
        "GITHUB_WORKSPACE": str(workspace),
        "GITHUB_OUTPUT": str(output),
        "GITHUB_STEP_SUMMARY": str(tmp_path / "summary"),
        "TRUSTED_LOCK": str(ROOT / "requirements-papers.lock"),
    }
    return workspace, environment


def run_preview(workspace: Path, environment: dict[str, str]) -> subprocess.CompletedProcess[str]:
    preview, _ = preview_steps()
    return subprocess.run(
        ["bash", "-eu", "-o", "pipefail", "-c", preview["run"]],
        cwd=workspace,
        env=environment,
        capture_output=True,
        text=True,
        timeout=20,
    )


def test_actual_preview_ignores_untrusted_modules_and_dependency_lock(tmp_path: Path) -> None:
    workspace, environment = preview_environment(tmp_path)
    result = run_preview(workspace, environment)
    assert result.returncode == 0, result.stderr
    artifact = tmp_path / "paper-preview"
    files = {path.relative_to(artifact).as_posix() for path in artifact.rglob("*") if path.is_file()}
    assert files == PREVIEW_FILES
    assert not any(path.is_symlink() for path in artifact.rglob("*"))
    assert all((artifact / name).read_bytes() == (workspace / name).read_bytes() for name in PREVIEW_FILES)
    assert not list(workspace.rglob("SOURCE_EXECUTED"))
    assert (tmp_path / "scope-output").read_text() == "mode=full\n"
    assert (tmp_path / "pip-calls").read_text() == "trusted-pip\n"
    assert "NOT acceptance" in (tmp_path / "summary").read_text()


@pytest.mark.parametrize("base", ["", "0" * 40, "NOT_A_SHA", "$(touch SOURCE_EXECUTED)"])
def test_actual_preview_without_exact_available_base_is_an_optional_noop(tmp_path: Path, base: str) -> None:
    workspace, environment = preview_environment(tmp_path)
    result = run_preview(workspace, {**environment, "BASE": base})
    assert result.returncode == 0, result.stderr
    assert not (tmp_path / "paper-preview").exists()
    assert not (tmp_path / "pip-calls").exists()
    assert not list(workspace.rglob("SOURCE_EXECUTED"))
    assert (tmp_path / "scope-output").read_text() == "mode=full\n"


@pytest.mark.parametrize(
    "missing", ["scripts/research_papers.py", "scripts/build_service_worker.py", "requirements-papers.lock"]
)
def test_actual_preview_first_install_without_base_policy_is_an_optional_noop(tmp_path: Path, missing: str) -> None:
    workspace, environment = preview_environment(tmp_path)
    subprocess.run(["git", "-C", str(workspace), "rm", "--cached", missing], check=True, capture_output=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(workspace),
            "-c",
            "user.email=test@example.invalid",
            "-c",
            "user.name=Fixture",
            "commit",
            "--quiet",
            "-m",
            "Before policy installation",
        ],
        check=True,
        capture_output=True,
    )
    base = subprocess.check_output(["git", "-C", str(workspace), "rev-parse", "HEAD"], text=True).strip()
    result = run_preview(workspace, {**environment, "BASE": base})
    assert result.returncode == 0, result.stderr
    assert not (tmp_path / "paper-preview").exists()
    assert not (tmp_path / "pip-calls").exists()
    assert not list(workspace.rglob("SOURCE_EXECUTED"))
    assert (tmp_path / "scope-output").read_text() == "mode=full\n"


@pytest.mark.parametrize(
    "target",
    [
        "README.md",
        "docs/index.html",
        "docs/research-papers.json",
        "docs/service-worker.js",
        "docs/assets/service-worker.js",
        "docs/alpha_factory_v1/demos/alpha_agi_insight_v1/service-worker.js",
        "alpha_factory_v1/demos/catalog.json",
        "docs/assets/secret.json",
        "docs/papers/paper-0.pdf",
        "docs/assets",
        "docs/papers",
        "alpha_factory_v1/demos",
    ],
)
def test_actual_preview_rejects_symlinks_without_uploading_or_escaping(tmp_path: Path, target: str) -> None:
    workspace, environment = preview_environment(tmp_path)
    path = workspace / target
    outside = tmp_path / "outside"
    if path.exists():
        path.rename(outside)
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        outside.write_text("PRIVATE RUNNER DATA MUST NOT ENTER ARTIFACT\n")
    before = {
        str(item): item.read_bytes()
        for item in (outside.rglob("*") if outside.is_dir() else [outside])
        if item.is_file()
    }
    path.symlink_to(outside, target_is_directory=outside.is_dir())
    result = run_preview(workspace, environment)
    assert result.returncode != 0, result.stdout
    assert "symlink" in result.stderr.lower(), result.stderr
    assert all(Path(name).read_bytes() == raw for name, raw in before.items())
    assert not (tmp_path / "paper-preview").exists()
    assert not list(workspace.rglob("SOURCE_EXECUTED"))
    assert (tmp_path / "scope-output").read_text() == "mode=full\n"
