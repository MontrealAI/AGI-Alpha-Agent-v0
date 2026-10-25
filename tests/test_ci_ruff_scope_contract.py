# SPDX-License-Identifier: Apache-2.0
"""Regression guards for explicit Ruff target selection in CI workflows."""

from __future__ import annotations

import ast
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys

import pytest
import yaml


PUBLIC_SECURITY_ARTIFACT_PATHS = [
    "evidence/semgrep-official/public/attempt-*/" + name
    for name in ("summary.json", "policy-identity.json", "finding-index.json", "source-identities.json")
]


def test_integration_ci_ruff_step_uses_target_script() -> None:
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert "name: Ruff lint" in workflow
    assert "run: python scripts/ruff_targets.py --run" in workflow
    assert "name: Ruff lint\n        run: python -m ruff check ." not in workflow


def test_pr_ci_ruff_step_uses_target_script() -> None:
    workflow = Path(".github/workflows/pr-ci.yml").read_text(encoding="utf-8")

    assert "name: Ruff check" in workflow
    assert "run: python scripts/ruff_targets.py --run" in workflow
    assert "run: python -m ruff check ." not in workflow


def test_ruff_exclude_contains_git_metadata() -> None:
    pyproject = Path("pyproject.toml").read_text(encoding="utf-8")

    assert "exclude = [" in pyproject
    assert '".git"' in pyproject


def test_pre_commit_ruff_matches_locked_ci_version_without_rule_or_fix_changes() -> None:
    config = yaml.safe_load(Path(".pre-commit-config.yaml").read_text(encoding="utf-8"))
    repo = next(item for item in config["repos"] if item["repo"] == "https://github.com/astral-sh/ruff-pre-commit")
    # This upstream immutable commit declares ruff==0.12.5 and retains the legacy
    # ruff hook alias; changing the lock requires separately checking its mirror.
    assert repo["rev"] == "73b0f6d59bbfcb75e17a4653d581c9dfaca13969"
    locked = re.search(r"(?m)^ruff==([^\s\\]+)", Path("requirements-dev.lock").read_text(encoding="utf-8"))
    assert locked is not None and locked.group(1) == "0.12.5"
    assert repo["hooks"] == [
        {"id": "ruff", "exclude": "alpha_factory_v1/backend/agent_factory.py"},
        {"id": "ruff-format", "exclude": "alpha_factory_v1/backend/agent_factory.py"},
    ]


def test_release_quality_checks_committed_delta_before_blocking_hooks() -> None:
    workflow = yaml.safe_load(Path(".github/workflows/agent-release.yml").read_text(encoding="utf-8"))
    steps = workflow["jobs"]["quality"]["steps"]
    checks = next(
        step for step in steps if step.get("name") == "Verify immutable sources and committed release evidence"
    )
    assert checks["run"].splitlines() == [
        "python scripts/check_strategy_research_source.py",
        "python scripts/check_no_binary_diff.py --base 5499495911bf8822ac0aa8c9007f00789c1132b5",
        "python scripts/dp_scrubber.py --base 5499495911bf8822ac0aa8c9007f00789c1132b5",
    ]
    assert checks.get("if") is None
    assert checks.get("continue-on-error", False) is False
    hooks = next(step for step in steps if step.get("name") == "Require the blocking repository hook report")
    assert steps.index(checks) < steps.index(hooks)


def test_security_hooks_preserve_official_policy_and_add_fixed_strategy_scope() -> None:
    config = yaml.safe_load(Path(".pre-commit-config.yaml").read_text(encoding="utf-8"))
    repo = next(item for item in config["repos"] if item["repo"] == "https://github.com/semgrep/semgrep")
    assert repo["rev"] == "2bbd0a55b3655b26991c936b92e0c0f6d6f4fa94"
    assert repo["hooks"] == [
        {
            "id": "semgrep",
            "name": "Repository Python security (official and local rules)",
            "entry": "python -I scripts/check_strategy_python_security.py --official-repository --",
            "args": [],
            "additional_dependencies": ["setuptools>=75,<81"],
            "types": ["python"],
            "pass_filenames": True,
            "require_serial": True,
            "verbose": True,
        },
        {
            "id": "semgrep",
            "name": "Additional bounded Strategy Python security",
            "entry": "python -I scripts/check_strategy_python_security.py",
            "args": [],
            "additional_dependencies": ["setuptools>=75,<81"],
            "types": ["python"],
            "pass_filenames": False,
            "always_run": True,
        },
    ]


def test_pre_commit_semgrep_selection_executes_both_named_hooks_without_aliases(tmp_path: Path) -> None:
    env = {**os.environ, "PRE_COMMIT_HOME": str(tmp_path / "cache"), "SKIP": ""}
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True, env=env)
    marker = tmp_path / "marker.py"
    marker.write_text(
        "from pathlib import Path\nimport sys\n"
        "with Path('selected.txt').open('a') as output: output.write(sys.argv[1]+'\\n')\n"
    )
    (tmp_path / "example.py").write_text("value = 1\n")
    subprocess.run(["git", "-C", str(tmp_path), "add", "example.py"], check=True, env=env)
    hooks = [
        {
            "id": "semgrep",
            "name": name,
            "entry": shlex.join([sys.executable, str(marker), role]),
            "language": "system",
            "pass_filenames": False,
            "always_run": True,
        }
        for name, role in (("Primary policy", "primary"), ("Additional bounded policy", "additional"))
    ]
    (tmp_path / ".pre-commit-config.yaml").write_text(yaml.safe_dump({"repos": [{"repo": "local", "hooks": hooks}]}))
    subprocess.run(
        [sys.executable, "-m", "pre_commit", "run", "semgrep", "--all-files"],
        cwd=tmp_path,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    assert (tmp_path / "selected.txt").read_text().splitlines() == ["primary", "additional"]


def test_pr_smoke_requires_official_and_additional_security_before_merge() -> None:
    workflow = yaml.safe_load(Path(".github/workflows/pr-ci.yml").read_text(encoding="utf-8"))
    steps = workflow["jobs"]["smoke"]["steps"]
    security = next(
        step for step in steps if step.get("name") == "Check official and additional Python security before merge"
    )
    _require_committed_context_for_ci(security)
    assert security["run"].splitlines() == [
        "mkdir -p evidence/semgrep-official",
        "set -o pipefail",
        "pre-commit run semgrep --all-files --verbose --show-diff-on-failure 2>&1 | tee evidence/semgrep-official/precommit-pr.log",
    ]
    assert security["timeout-minutes"] == 12
    assert security.get("if") is None
    assert security.get("continue-on-error", False) is False
    dependencies = next(step for step in steps if step.get("name") == "Install dependencies")
    smoke = next(step for step in steps if step.get("name") == "Run smoke tests")
    assert steps.index(dependencies) < steps.index(security) < steps.index(smoke)
    artifact = next(step for step in steps if step.get("name") == "Retain actual Python security evidence")
    assert artifact["if"] == "always()"
    assert artifact["with"]["path"].splitlines() == PUBLIC_SECURITY_ARTIFACT_PATHS
    assert artifact["with"]["if-no-files-found"] == "error"


def test_main_quality_always_retains_primary_security_reports() -> None:
    workflow = yaml.safe_load(Path(".github/workflows/agent-release.yml").read_text())
    steps = workflow["jobs"]["quality"]["steps"]
    artifact = next(step for step in steps if step.get("name") == "Retain actual repository Python security evidence")
    assert artifact["if"] == "always()"
    assert artifact["with"]["path"].splitlines() == PUBLIC_SECURITY_ARTIFACT_PATHS
    assert artifact["with"]["if-no-files-found"] == "error"
    assert "/evidence/semgrep-official/" in Path(".gitignore").read_text().splitlines()


def test_broad_release_artifacts_exclude_private_scanner_captures() -> None:
    workflow = yaml.safe_load(Path(".github/workflows/agent-release.yml").read_text())
    observed = set()
    for job, definition in workflow["jobs"].items():
        for step in definition.get("steps", []):
            if not str(step.get("uses", "")).startswith("actions/upload-artifact@"):
                continue
            paths = step["with"]["path"].splitlines()
            if "evidence/" not in paths:
                continue
            observed.add(job)
            ordinary = ["evidence/"]
            if job == "browser-contracts":
                ordinary.append("alpha_factory_v1/core/interface/web_client/test-results/")
            # This is one generated private directory, not an evidence waiver.
            assert paths == [ordinary[0], "!evidence/semgrep-official/**", *ordinary[1:]]
            assert step["if"] == "always()"
            existing_warn = {"gallery", "demo-distribution", "historical-ci", "pages"}
            assert step["with"]["if-no-files-found"] == ("warn" if job in existing_warn else "error")
    assert observed == {
        "runtime",
        "regression",
        "browser-contracts",
        "real-model",
        "quality",
        "gallery",
        "native-demos",
        "sovereign-lab",
        "finance-lab",
        "muzero-lab",
        "demo-distribution",
        "historical-ci",
        "successor-workbench",
        "pages",
    }


def test_xml_safety_dependency_is_installed_only_in_qa_and_public_verifier_bootstraps() -> None:
    strategy = yaml.safe_load(Path(".github/workflows/strategy-succession-engineering.yml").read_text())
    install = next(
        step
        for step in strategy["jobs"]["qualify"]["steps"]
        if step.get("name") == "Install the separately verified public runtime in a clean test environment"
    )
    assert "defusedxml==0.7.1" in install["run"]
    release = yaml.safe_load(Path(".github/workflows/agent-release.yml").read_text())
    public = next(
        step
        for step in release["jobs"]["public-strategy-install"]["steps"]
        if step.get("name") == "Install only the existing release-verifier dependencies"
    )
    assert public["run"] == "python -m pip install cryptography==50.0.1 packaging==25.0 defusedxml==0.7.1"
    requirements = Path("contrib/strategy_succession/requirements-qualification.txt").read_text()
    assert "defusedxml" not in requirements


def test_release_quality_requires_actual_security_regressions_after_installed_hooks() -> None:
    workflow = yaml.safe_load(Path(".github/workflows/agent-release.yml").read_text(encoding="utf-8"))
    steps = workflow["jobs"]["quality"]["steps"]
    regressions = next(
        step for step in steps if step.get("name") == "Verify scoped security hook with its installed tool"
    )
    assert regressions["run"] == (
        "STRATEGY_REQUIRE_SEMGREP=1 python -m pytest --noconftest -o addopts= "
        "-p no:cacheprovider tests/test_strategy_python_security.py -q"
    )
    assert regressions.get("if") is None
    assert regressions.get("continue-on-error", False) is False
    hooks = next(step for step in steps if step.get("name") == "Require blocking hooks on every release change")
    assert steps.index(regressions) > steps.index(hooks)


def _release_hook_steps() -> tuple[dict, dict]:
    workflow = yaml.safe_load(Path(".github/workflows/agent-release.yml").read_text(encoding="utf-8"))
    quality = workflow["jobs"]["quality"]
    assert quality["if"] == "${{ !cancelled() && success() && needs.paper-scope.outputs.mode == 'full' }}"
    assert quality.get("continue-on-error", False) is False
    steps = quality["steps"]
    first = next(step for step in steps if step.get("name") == "Require the blocking repository hook report")
    second = next(step for step in steps if step.get("name") == "Require blocking hooks on every release change")
    assert steps.index(first) < steps.index(second)
    for step in (first, second):
        assert step.get("if") is None
        assert step.get("continue-on-error", False) is False
    return first, second


def test_release_full_scope_security_remains_mandatory_before_duplicate_skip() -> None:
    first, second = _release_hook_steps()
    ordinary_skips = "black,ruff-format,flake8,update-actions"
    assert first["env"] == {"SKIP": ordinary_skips, "STRATEGY_REQUIRE_COMMITTED_CONTEXT": "1"}
    _require_committed_context_for_ci(first)
    assert second["env"] == {"SKIP": ordinary_skips + ",semgrep"}
    lines = first["run"].splitlines()
    assert lines[0:2] == ["mkdir -p evidence", "python - <<'PY'"]
    assert lines[-1] == "PY"
    tree = ast.parse("\n".join(lines[2:-1]))
    assignment = next(
        node for node in tree.body if isinstance(node, ast.Assign) and ast.unparse(node.targets[0]) == "result"
    )
    assert isinstance(assignment.value, ast.Call)
    assert ast.unparse(assignment.value.func) == "subprocess.run"
    assert [ast.literal_eval(argument) for argument in assignment.value.args] == [
        ["pre-commit", "run", "--all-files", "--show-diff-on-failure"]
    ]
    assert {keyword.arg: ast.literal_eval(keyword.value) for keyword in assignment.value.keywords} == {
        "capture_output": True,
        "text": True,
    }
    assert isinstance(tree.body[-1], ast.Raise)
    assert ast.unparse(tree.body[-1]) == "raise SystemExit(result.returncode)"
    assert not any(isinstance(node, (ast.If, ast.Try)) for node in ast.walk(tree))
    assert second["run"].splitlines() == [
        "# Semgrep (official and bounded) was already required on all files above.",
        'test "$(git rev-parse HEAD)" = "$GITHUB_SHA"',
        "git diff --exit-code HEAD",
        "git diff --cached --exit-code HEAD",
        "git diff --name-only -z d1df708e3e08ee58b7cbe74758767ddb2da2d5f9 HEAD | xargs -0 pre-commit run --files",
        'test "$(git rev-parse HEAD)" = "$GITHUB_SHA"',
        "git diff --exit-code HEAD",
        "git diff --cached --exit-code HEAD",
    ]


def _require_committed_context_for_ci(step: dict) -> None:
    """A developer-only raw pass must never select the CI qualification mode."""
    value = step.get("env", {}).get("STRATEGY_REQUIRE_COMMITTED_CONTEXT")
    assert type(value) is str and value == "1"
    assert step.get("if") is None
    assert step.get("continue-on-error", False) is False


CI_OFFICIAL_CONSUMERS = (
    ("agent-release.yml", "quality", "Require the blocking repository hook report"),
    ("pr-ci.yml", "smoke", "Check official and additional Python security before merge"),
    ("ci.yml", "lint-type", "Run pre-commit checks"),
)


@pytest.mark.parametrize(("filename", "job", "name"), CI_OFFICIAL_CONSUMERS)
def test_every_mandatory_official_consumer_requires_committed_context(filename: str, job: str, name: str) -> None:
    workflow = yaml.safe_load((Path(".github/workflows") / filename).read_text())
    step = next(step for step in workflow["jobs"][job]["steps"] if step.get("name") == name)
    _require_committed_context_for_ci(step)
    if filename == "ci.yml":
        assert step["env"] == {
            "PRE_COMMIT_HOME": ".cache/pre-commit",
            "SKIP": "eslint-insight-browser,black,ruff-format,flake8,update-actions",
            "STRATEGY_REQUIRE_COMMITTED_CONTEXT": "1",
        }
        assert step["run"].splitlines() == [
            'test "$(git rev-parse HEAD)" = "$GITHUB_SHA"',
            "git diff --exit-code HEAD",
            "git diff --cached --exit-code HEAD",
            'from_ref="${{ github.event.before }}"',
            'if [ -n "$from_ref" ] && git rev-parse --verify "$from_ref^{commit}" >/dev/null 2>&1; then',
            "  pre-commit run semgrep --all-files",
            '  test "$(git rev-parse HEAD)" = "$GITHUB_SHA"',
            "  git diff --exit-code HEAD",
            "  git diff --cached --exit-code HEAD",
            '  SKIP="${SKIP},semgrep" pre-commit run --from-ref "$from_ref" --to-ref "${{ github.sha }}"',
            "else",
            '  echo "::notice::Falling back to pre-commit --all-files (missing or unreachable from_ref)."',
            "  pre-commit run --all-files",
            "fi",
            'test "$(git rev-parse HEAD)" = "$GITHUB_SHA"',
            "git diff --exit-code HEAD",
            "git diff --cached --exit-code HEAD",
        ]


@pytest.mark.parametrize(("filename", "job", "name"), CI_OFFICIAL_CONSUMERS)
@pytest.mark.parametrize("value", [None, "0", "true", "", 1, True])
def test_missing_or_malformed_strict_ci_flag_cannot_qualify(
    filename: str, job: str, name: str, value: str | int | bool | None
) -> None:
    workflow = yaml.safe_load((Path(".github/workflows") / filename).read_text())
    original = next(step for step in workflow["jobs"][job]["steps"] if step.get("name") == name)
    changed = {**original, "env": dict(original.get("env", {}))}
    if value is None:
        changed["env"].pop("STRATEGY_REQUIRE_COMMITTED_CONTEXT", None)
    else:
        changed["env"]["STRATEGY_REQUIRE_COMMITTED_CONTEXT"] = value
    with pytest.raises(AssertionError):
        _require_committed_context_for_ci(changed)


@pytest.mark.parametrize(
    ("branch", "phase", "effect"),
    [
        ("range", "none", "none"),
        ("fallback", "none", "none"),
        *[
            (branch, phase, effect)
            for branch, phase in (("range", "full"), ("range", "range"), ("fallback", "full"))
            for effect in ("failure", "head", "index", "worktree", "masked-index")
        ],
    ],
)
def test_integration_full_security_precedes_only_duplicate_skip_and_refuses_source_mutations(
    tmp_path: Path, branch: str, phase: str, effect: str
) -> None:
    """Exercise both actual Integration shell branches using authored inert hooks."""
    workflow = yaml.safe_load(Path(".github/workflows/ci.yml").read_text())
    step = next(s for s in workflow["jobs"]["lint-type"]["steps"] if s.get("name") == "Run pre-commit checks")
    repo = tmp_path / "repository"
    repo.mkdir()
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("GIT_") and key not in {"BASH_ENV", "SKIP", "STRATEGY_REQUIRE_COMMITTED_CONTEXT"}
    }
    empty_config = tmp_path / "empty-config"
    empty_config.write_text("")
    env.update(
        GIT_CONFIG_NOSYSTEM="1",
        GIT_CONFIG_GLOBAL=str(empty_config),
        GIT_TERMINAL_PROMPT="0",
        GIT_AUTHOR_NAME="Integration fixture",
        GIT_AUTHOR_EMAIL="fixture@example.invalid",
        GIT_COMMITTER_NAME="Integration fixture",
        GIT_COMMITTER_EMAIL="fixture@example.invalid",
    )

    def git(*args: str) -> str:
        return subprocess.check_output(["git", *args], cwd=repo, env=env, text=True).strip()

    git("init", "-q")
    (repo / "tracked.txt").write_text("baseline\n")
    git("add", ".")
    git("commit", "-qm", "Baseline fixture")
    baseline = git("rev-parse", "HEAD")
    (repo / "tracked.txt").write_text("release\n")
    git("add", ".")
    git("commit", "-qm", "Release fixture")
    head = git("rev-parse", "HEAD")
    bindir = tmp_path / "bin"
    bindir.mkdir()
    hook = bindir / "pre-commit"
    hook.write_text(
        "#!" + sys.executable + "\n"
        "import json, os, subprocess, sys\nfrom pathlib import Path\n"
        "phase = 'range' if '--from-ref' in sys.argv else 'full'\n"
        "with Path('calls.jsonl').open('a') as out:\n"
        "    out.write(json.dumps({'phase':phase,'args':sys.argv[1:],'skip':os.environ['SKIP'],"
        "'strict':os.environ.get('STRATEGY_REQUIRE_COMMITTED_CONTEXT')})+'\\n')\n"
        "if phase == os.environ['FIXTURE_PHASE']:\n"
        "    effect = os.environ['FIXTURE_EFFECT']\n"
        "    if effect == 'failure': sys.exit(7)\n"
        "    if effect == 'head':\n"
        "        subprocess.run(['git','commit','--allow-empty','-qm','Unexpected fixture commit'],check=True)\n"
        "    else:\n"
        "        Path('tracked.txt').write_text('unexpected fixture change\\n')\n"
        "        if effect in ('index','masked-index'):\n"
        "            subprocess.run(['git','add','tracked.txt'],check=True)\n"
        "        if effect == 'masked-index': Path('tracked.txt').write_text('release\\n')\n"
    )
    hook.chmod(0o700)
    env.update(
        PATH=str(bindir) + os.pathsep + env.get("PATH", os.defpath),
        GITHUB_SHA=head,
        FIXTURE_PHASE=phase,
        FIXTURE_EFFECT=effect,
        **step["env"],
    )
    script = step["run"].replace("${{ github.event.before }}", baseline if branch == "range" else "missing-ref")
    script = script.replace("${{ github.sha }}", head)
    result = subprocess.run(
        ["bash", "--noprofile", "--norc", "-eo", "pipefail", "-c", script],
        cwd=repo,
        env=env,
        capture_output=True,
        text=True,
        timeout=20,
    )
    calls = [json.loads(line) for line in (repo / "calls.jsonl").read_text().splitlines()]
    ordinary = "eslint-insight-browser,black,ruff-format,flake8,update-actions"
    assert calls[0] == {
        "phase": "full",
        "args": ["run", "semgrep", "--all-files"] if branch == "range" else ["run", "--all-files"],
        "skip": ordinary,
        "strict": "1",
    }
    if branch == "range" and phase != "full":
        assert calls[1] == {
            "phase": "range",
            "args": ["run", "--from-ref", baseline, "--to-ref", head],
            "skip": ordinary + ",semgrep",
            "strict": "1",
        }
        assert len(calls) == 2
    else:
        assert len(calls) == 1
    assert (result.returncode == 0) is (effect == "none")
    if effect == "masked-index":
        assert subprocess.run(["git", "diff", "--exit-code", "HEAD"], cwd=repo, env=env).returncode == 0
        assert subprocess.run(["git", "diff", "--cached", "--exit-code", "HEAD"], cwd=repo, env=env).returncode == 1


@pytest.mark.parametrize(
    ("phase", "effect"),
    [
        ("none", "none"),
        ("first", "head"),
        ("first", "index"),
        ("first", "worktree"),
        ("first", "masked-index"),
        ("second", "head"),
        ("second", "index"),
        ("second", "worktree"),
        ("second", "masked-index"),
        ("first", "failure"),
        ("second", "failure"),
    ],
)
def test_release_hook_pair_refuses_failures_and_source_changes(tmp_path: Path, phase: str, effect: str) -> None:
    """Run the actual shell steps with an inert hook, never a policy scanner."""
    first, second = _release_hook_steps()
    repo = tmp_path / "repo"
    repo.mkdir()
    empty_config = tmp_path / "empty-git-config"
    empty_config.write_text("")
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("GIT_") and key not in {"BASH_ENV", "STRATEGY_REQUIRE_COMMITTED_CONTEXT"}
    }
    env.update(
        GIT_CONFIG_NOSYSTEM="1",
        GIT_CONFIG_GLOBAL=str(empty_config),
        GIT_TERMINAL_PROMPT="0",
        GIT_AUTHOR_NAME="Workflow fixture",
        GIT_AUTHOR_EMAIL="fixture@example.invalid",
        GIT_COMMITTER_NAME="Workflow fixture",
        GIT_COMMITTER_EMAIL="fixture@example.invalid",
    )

    def git(*arguments: str) -> str:
        return subprocess.check_output(["git", *arguments], cwd=repo, env=env, text=True).strip()

    git("init", "-q")
    tracked = repo / "tracked.txt"
    tracked.write_text("baseline\n")
    git("add", "tracked.txt")
    git("commit", "-qm", "Fixture baseline")
    baseline = git("rev-parse", "HEAD")
    tracked.write_text("release\n")
    git("add", "tracked.txt")
    git("commit", "-qm", "Fixture release")
    expected_head = git("rev-parse", "HEAD")
    bindir = tmp_path / "bin"
    bindir.mkdir()
    hook = bindir / "pre-commit"
    hook.write_text(
        "#!" + sys.executable + "\n"
        "import json, os, subprocess, sys\n"
        "from pathlib import Path\n"
        "phase = 'first' if '--all-files' in sys.argv else 'second'\n"
        "with Path('calls.jsonl').open('a') as out:\n"
        "    out.write(json.dumps({'phase': phase, 'args': sys.argv[1:], 'skip': os.environ['SKIP'], "
        "'committed_context': os.environ.get('STRATEGY_REQUIRE_COMMITTED_CONTEXT')}) + '\\n')\n"
        "if phase == os.environ['FIXTURE_PHASE']:\n"
        "    effect = os.environ['FIXTURE_EFFECT']\n"
        "    if effect == 'failure': sys.exit(7)\n"
        "    if effect == 'head':\n"
        "        subprocess.run(['git', 'commit', '--allow-empty', '-qm', 'Unexpected fixture commit'], check=True)\n"
        "    else:\n"
        "        Path('tracked.txt').write_text('unexpected fixture edit\\n')\n"
        "        if effect in ('index', 'masked-index'):\n"
        "            subprocess.run(['git', 'add', 'tracked.txt'], check=True)\n"
        "        if effect == 'masked-index': Path('tracked.txt').write_text('release\\n')\n"
    )
    hook.chmod(0o700)
    env.update(
        PATH=str(bindir) + os.pathsep + env.get("PATH", os.defpath),
        GITHUB_SHA=expected_head,
        FIXTURE_PHASE=phase,
        FIXTURE_EFFECT=effect,
    )
    first_result = subprocess.run(
        ["bash", "--noprofile", "--norc", "-eo", "pipefail", "-c", first["run"]],
        cwd=repo,
        env={**env, **first["env"]},
        capture_output=True,
        text=True,
        timeout=20,
    )
    report = json.loads((repo / "evidence/precommit-all.json").read_text())
    assert report["exit_code"] == first_result.returncode
    assert report["passed"] is (first_result.returncode == 0)
    second_result = None
    if first_result.returncode == 0:
        second_script = second["run"].replace("d1df708e3e08ee58b7cbe74758767ddb2da2d5f9", baseline)
        second_result = subprocess.run(
            ["bash", "--noprofile", "--norc", "-eo", "pipefail", "-c", second_script],
            cwd=repo,
            env={**env, **second["env"]},
            capture_output=True,
            text=True,
            timeout=20,
        )
    calls = [json.loads(line) for line in (repo / "calls.jsonl").read_text().splitlines()]
    assert calls[0] == {
        "phase": "first",
        "args": ["run", "--all-files", "--show-diff-on-failure"],
        "skip": "black,ruff-format,flake8,update-actions",
        "committed_context": "1",
    }
    if phase == "first":
        assert len(calls) == 1
    else:
        assert calls[1] == {
            "phase": "second",
            "args": ["run", "--files", "tracked.txt"],
            "skip": "black,ruff-format,flake8,update-actions,semgrep",
            "committed_context": None,
        }
    if effect == "none":
        assert first_result.returncode == 0
        assert second_result is not None and second_result.returncode == 0
    elif phase == "first" and effect == "failure":
        assert first_result.returncode == 7
        assert second_result is None
    else:
        assert first_result.returncode == 0
        assert second_result is not None and second_result.returncode != 0
    if effect == "masked-index":
        assert subprocess.run(["git", "diff", "--exit-code", "HEAD"], cwd=repo, env=env).returncode == 0
        assert subprocess.run(["git", "diff", "--cached", "--exit-code", "HEAD"], cwd=repo, env=env).returncode == 1
