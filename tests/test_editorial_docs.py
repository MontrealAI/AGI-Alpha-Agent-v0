# SPDX-License-Identifier: Apache-2.0
"""The editorial fast lane keeps the actual MkDocs page/link acceptance boundary."""

from pathlib import Path

import pytest
import yaml

from scripts import check_editorial_docs as checker

ROOT = Path(__file__).resolve().parents[1]


def fixture_site(tmp_path: Path, text: str) -> Path:
    pytest.importorskip("mkdocs", reason="Renderer tests require the docs dependency profile")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs/CHANGELOG.md").write_text(text, encoding="utf-8")
    (tmp_path / "docs/target.md").write_text("# Target\n\n## Valid anchor\n", encoding="utf-8")
    (tmp_path / "mkdocs.yml").write_text(
        "site_name: Fixture\nsite_url: https://example.org/\n"
        "docs_dir: docs\ntheme: mkdocs\nplugins: []\n"
        "markdown_extensions: [attr_list]\nnav:\n"
        "  - Changelog: CHANGELOG.md\n  - Target: target.md\n",
        encoding="utf-8",
    )
    return tmp_path


@pytest.mark.parametrize(
    "text",
    [
        "# Corrected heading\nOrdinary correction.",
        "# Changelog\n[Target](target.md)",
        "# Changelog\n[Reference][target]\n\n[target]: target.md",
        "# Changelog\n[External](https://example.org/new) and [mail](mailto:hello@example.org)",
        "# Changelog\n[Anchor](target.md#valid-anchor)",
        "# Changelog\n[Self](#changelog)",
        "# Changelog\nA [valid label](target.md){ .custom }",
    ],
)
def test_valid_ordinary_markdown_is_allowed(tmp_path: Path, text: str) -> None:
    checker.validate_docs(fixture_site(tmp_path, text))


@pytest.mark.parametrize(
    "text",
    [
        "# Changelog\n[Missing](does-not-exist.md)",
        "# Changelog\n[Missing][target]\n\n[target]: does-not-exist.md",
        "# Changelog\n![Missing image](missing.png)",
    ],
)
def test_missing_local_targets_fail_like_strict_build(tmp_path: Path, text: str) -> None:
    root = fixture_site(tmp_path, text)
    from mkdocs.exceptions import Abort

    with pytest.raises(Abort):
        checker.validate_docs(root)
    from mkdocs.commands.build import build
    from mkdocs.config import load_config

    with pytest.raises(Abort):
        build(load_config(config_file=str(root / "mkdocs.yml"), strict=True))


def test_actual_configured_anchor_severity_is_used(tmp_path: Path) -> None:
    root = fixture_site(tmp_path, "# Changelog\n[Anchor](target.md#missing)")
    # MkDocs 1.6.1 defaults missing anchors to INFO, not a strict error.
    checker.validate_docs(root)
    with (root / "mkdocs.yml").open("a") as f:
        f.write("validation:\n  links:\n    anchors: warn\n")
    from mkdocs.exceptions import Abort

    with pytest.raises(Abort):
        checker.validate_docs(root)


def test_prebuild_generated_targets_and_page_hooks_are_preserved(tmp_path: Path) -> None:
    root = fixture_site(tmp_path, "# Changelog\n[Generated](generated.json)\nREWRITE_ME")
    (root / "hook.py").write_text(
        "from pathlib import Path\n"
        "def on_pre_build(config):\n"
        "    (Path(config.docs_dir) / 'generated.json').write_text('{}')\n"
        "def on_page_markdown(markdown, **kwargs):\n"
        "    return markdown.replace('REWRITE_ME', '[Target](target.md)')\n",
        encoding="utf-8",
    )
    with (root / "mkdocs.yml").open("a") as f:
        f.write("hooks: [hook.py]\n")
    checker.validate_docs(root)
    assert not (root / "site").exists()


def test_plugin_excluded_targets_follow_mkdocs_semantics(tmp_path: Path) -> None:
    root = fixture_site(tmp_path, "# Changelog\n[Target](target.md)")
    config = root / "mkdocs.yml"
    config.write_text(config.read_text().replace("plugins: []", "plugins:\n  - exclude:\n      glob: ['target.md']"))
    from mkdocs.exceptions import Abort

    with pytest.raises(Abort):
        checker.validate_docs(root)


@pytest.mark.parametrize("mutation", ["altered-plan", "wrong-head", "dirty"])
def test_bad_proof_or_checkout_never_loads_hooks(tmp_path: Path, monkeypatch, mutation: str) -> None:
    scope = {
        "software_commit": "a" * 40,
        "paper_commit": "b" * 40,
        "mode": "paper",
        "transitions": [{"paths": ["docs/CHANGELOG.md"]}],
    }
    proof = dict(scope)
    if mutation == "altered-plan":
        proof["extra"] = "not the supplied proof"
    monkeypatch.setattr(checker, "prove_paper_descendants", lambda *args: proof)
    monkeypatch.setattr(
        checker,
        "git",
        lambda root, *args: (
            b"dirty"
            if args[0] == "status" and mutation == "dirty"
            else b"" if args[0] == "status" else ("c" * 40 if mutation == "wrong-head" else "b" * 40).encode()
        ),
    )
    monkeypatch.setattr(checker, "validate_docs", lambda root: pytest.fail("Unproved checkout executed hooks"))
    with pytest.raises(ValueError):
        checker.check(tmp_path, scope)


@pytest.mark.parametrize(
    "paths,expected",
    [
        (["docs/CHANGELOG.md"], True),
        (["docs/CHANGELOG.md", "docs/research-papers.json"], True),
        (["docs/research-papers.json"], False),
    ],
)
def test_pure_and_mixed_editorial_require_check_but_paper_only_does_not(
    tmp_path: Path, monkeypatch, paths, expected
) -> None:
    scope = {"software_commit": "a" * 40, "paper_commit": "b" * 40, "mode": "paper", "transitions": [{"paths": paths}]}
    monkeypatch.setattr(checker, "prove_paper_descendants", lambda *args: scope)
    monkeypatch.setattr(checker, "git", lambda root, *args: b"" if args[0] == "status" else ("b" * 40).encode())
    calls = []
    monkeypatch.setattr(checker, "validate_docs", calls.append)
    assert checker.check(tmp_path, scope) is expected
    assert calls == ([tmp_path] if expected else [])


def test_workflow_extracts_and_runs_required_check_only_after_proof() -> None:
    workflow = yaml.safe_load((ROOT / ".github/workflows/paper-scope.yml").read_text())
    step = next(s for s in workflow["jobs"]["classify"]["steps"] if s.get("id") == "scope")
    script = step["run"]
    extraction = script.split("for file in", 1)[1].split("; do", 1)[0]
    assert "scripts/check_editorial_docs.py" in extraction
    assert "requirements-editorial-docs.lock" in extraction
    assert script.index("python scripts/paper_changes.py") < script.index("python -m scripts.check_editorial_docs")
    assert "docs/CHANGELOG.md" in script
    assert "--require-hashes --only-binary=:all: -r requirements-editorial-docs.lock" in script
    assert 'python -m scripts.check_editorial_docs --root "$GITHUB_WORKSPACE" --scope scope.json' in script
    assert "continue-on-error" not in step
    assert "|| true" not in script


def test_doc_lock_is_a_subset_of_original_hashed_pins() -> None:
    import re

    original = ROOT / "requirements-docs.lock"
    if not original.exists():
        pytest.fail("Exact source documentation lock must be materialized for this contract")

    def blocks(path):
        return {
            b.split("==", 1)[0]: b.split("\n    #", 1)[0].strip()
            for b in re.split(r"(?=^[a-zA-Z0-9][a-zA-Z0-9_.-]*==)", path.read_text(), flags=re.M)
            if re.match(r"^[a-zA-Z0-9][a-zA-Z0-9_.-]*==", b)
        }

    full = blocks(original)
    selected = blocks(ROOT / "requirements-editorial-docs.lock")
    assert {"mkdocs", "mkdocs-material", "mkdocs-exclude"} <= selected.keys()
    assert len(selected) < len(full)
    assert all(full[name] == value and "--hash=sha256:" in value for name, value in selected.items())


def test_actual_workflow_propagates_editorial_failure(tmp_path: Path) -> None:
    import os
    import subprocess

    workflow = yaml.safe_load((ROOT / ".github/workflows/paper-scope.yml").read_text())
    script = next(s["run"] for s in workflow["jobs"]["classify"]["steps"] if s.get("id") == "scope")
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-b", "main", str(repo)], check=True, capture_output=True)
    paths = script.split("for file in", 1)[1].split("; do", 1)[0].split()
    for name in paths:
        path = repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# trusted fixture\n")
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(repo),
            "-c",
            "user.name=Fixture",
            "-c",
            "user.email=fixture@example.invalid",
            "-c",
            "core.hooksPath=/dev/null",
            "-c",
            "commit.gpgsign=false",
            "commit",
            "-m",
            "fixture",
        ],
        check=True,
        capture_output=True,
    )
    sha = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
    binary = tmp_path / "bin"
    binary.mkdir()
    python = binary / "python"
    python.write_text('#!/bin/bash\nif [[ "$*" == *"scripts.check_editorial_docs"* ]]; then exit 19; fi\nexit 0\n')
    python.chmod(0o755)
    summary = tmp_path / "summary"
    result = subprocess.run(
        ["bash", "-eu", "-o", "pipefail", "-c", script],
        cwd=repo,
        capture_output=True,
        env={
            **os.environ,
            "PATH": f"{binary}:{os.environ['PATH']}",
            "EVENT": "push",
            "BASE": sha,
            "HEAD": sha,
            "RUNNER_TEMP": str(tmp_path),
            "GITHUB_WORKSPACE": str(repo),
            "GITHUB_OUTPUT": str(tmp_path / "output"),
            "GITHUB_STEP_SUMMARY": str(summary),
        },
    )
    assert result.returncode == 19, result.stderr
    assert not summary.exists()


def test_missing_page_template_fails_the_complete_build(tmp_path: Path) -> None:
    root = fixture_site(tmp_path, "---\ntemplate: missing.html\n---\n# Changelog\n")
    from jinja2 import TemplateNotFound

    with pytest.raises(TemplateNotFound):
        checker.validate_docs(root)
    assert not (root / "site").exists()


@pytest.mark.parametrize(
    "template,exception",
    [
        ("{% broken template %}", "syntax"),
        ("{{ 1 / 0 }}", "runtime"),
    ],
)
def test_existing_but_invalid_template_cannot_pass(tmp_path: Path, template: str, exception: str) -> None:
    root = fixture_site(tmp_path, "---\ntemplate: custom.html\n---\n# Changelog\n")
    from jinja2 import TemplateSyntaxError

    templates = root / "templates"
    templates.mkdir()
    (templates / "custom.html").write_text(template)
    config = root / "mkdocs.yml"
    config.write_text(config.read_text().replace("theme: mkdocs", "theme:\n  name: mkdocs\n  custom_dir: templates"))
    with pytest.raises(TemplateSyntaxError if exception == "syntax" else ZeroDivisionError):
        checker.validate_docs(root)


def test_valid_front_matter_and_final_output_hooks_work_from_policy_directory(tmp_path: Path, monkeypatch) -> None:
    root = fixture_site(
        tmp_path, "---\ntemplate: main.html\ntitle: Corrected title\n---\n# Changelog\n[Target](target.md)\n"
    )
    (root / "hook.py").write_text(
        "from pathlib import Path\n"
        "def on_post_build(config):\n"
        "    output = Path(config.site_dir)\n"
        '    assert "<html" in (output / "CHANGELOG/index.html").read_text()\n'
        '    (Path(config.docs_dir).parent / "observed-output").write_text(str(output))\n'
    )
    with (root / "mkdocs.yml").open("a") as f:
        f.write("hooks: [hook.py]\n")
    policy = root / "extracted-policy"
    policy.mkdir()
    monkeypatch.chdir(policy)
    checker.validate_docs(root)
    output = Path((root / "observed-output").read_text())
    assert not output.exists()
    assert not (root / "site").exists()


def test_material_search_and_exclude_render_valid_front_matter(tmp_path: Path) -> None:
    root = fixture_site(tmp_path, "---\ntemplate: main.html\n---\n# Changelog\n[Target](target.md)\n")
    pytest.importorskip("material", reason="Production theme requires the docs dependency profile")
    config = root / "mkdocs.yml"
    config.write_text(
        config.read_text()
        .replace("theme: mkdocs", "theme: material")
        .replace("plugins: []", "plugins:\n  - search\n  - exclude:\n      glob: ['ignored/**']")
    )
    (root / "docs/ignored").mkdir()
    (root / "docs/ignored/draft.md").write_text("[Excluded draft](missing.md)")
    checker.validate_docs(root)
    assert not (root / "site").exists()
