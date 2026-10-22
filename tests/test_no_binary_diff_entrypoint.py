# SPDX-License-Identifier: Apache-2.0
"""Direct CI entrypoints retain catalog validation without inherited import paths."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

from scripts import research_papers as papers
from tests.test_research_papers import paper_row, pdf_bytes, refresh_fixture, write_paper_fixture

ROOT = Path(__file__).resolve().parents[1]


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(root), "-c", f"core.hooksPath={os.devnull}", *args],
        text=True,
        stderr=subprocess.PIPE,
    ).strip()


def save(root: Path) -> str:
    git(root, "add", "--all")
    git(root, "-c", "commit.gpgsign=false", "commit", "--allow-empty", "-m", "Entrypoint fixture")
    return git(root, "rev-parse", "HEAD")


def history(tmp_path: Path) -> tuple[Path, str, Path]:
    root = tmp_path / "repo"
    root.mkdir()
    git(root, "init", "-b", "main")
    git(root, "config", "user.name", "Entrypoint Fixture")
    git(root, "config", "user.email", "fixture@example.invalid")
    (root / ".gitignore").write_text("__pycache__/\n")
    write_paper_fixture(root)
    for name in ("scripts/check_no_binary_diff.py", "scripts/research_papers.py"):
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT / name).read_bytes())
    base = save(root)
    event = tmp_path / "event.json"
    event.write_text(json.dumps({"pull_request": {"base": {"sha": base}}}))
    return root, base, event


def run_gate(root: Path, event: Path, *, module: bool = False) -> subprocess.CompletedProcess[str]:
    env = {key: value for key, value in os.environ.items() if key not in {"PYTHONPATH", "PYTHONHOME"}}
    env["GITHUB_EVENT_PATH"] = str(event)
    command = ["-m", "scripts.check_no_binary_diff"] if module else ["scripts/check_no_binary_diff.py"]
    return subprocess.run([sys.executable, *command], cwd=root, env=env, capture_output=True, text=True, timeout=30)


def check_clean_diff_and_valid_catalog_addition(tmp_path: Path, *, module: bool) -> None:
    root, _, event = history(tmp_path)
    clean = run_gate(root, event, module=module)
    assert clean.returncode == 0, clean.stderr
    assert clean.stdout.strip() == "No binary changes detected."
    data = papers.load_catalog(root)
    raw = pdf_bytes("Additional public paper")
    row = paper_row("additional", featured=False, raw=raw)
    (root / row["pdf"]["path"]).write_bytes(raw)
    data["papers"].append(row)
    refresh_fixture(root, data)
    save(root)
    added = run_gate(root, event, module=module)
    assert added.returncode == 0, added.stderr
    assert added.stdout.strip() == "No binary changes detected."


def test_direct_script_handles_clean_diff_and_valid_catalog_addition(tmp_path: Path) -> None:
    check_clean_diff_and_valid_catalog_addition(tmp_path, module=False)


def test_module_invocation_handles_clean_diff_and_valid_catalog_addition(tmp_path: Path) -> None:
    check_clean_diff_and_valid_catalog_addition(tmp_path, module=True)


def check_binary_rejection(tmp_path: Path, name: str) -> None:
    root, _, event = history(tmp_path)
    (root / name).write_bytes(b"unauthorized\x00binary\n")
    save(root)
    result = run_gate(root, event)
    assert result.returncode == 1
    assert result.stdout.splitlines() == ["ERROR: Binary files changed in diff:", "  - " + name]
    assert "ModuleNotFoundError" not in result.stderr


def test_direct_entrypoint_rejects_unauthorized_bin_with_the_gate_diagnostic(tmp_path: Path) -> None:
    check_binary_rejection(tmp_path, "unauthorized.bin")


def test_direct_entrypoint_rejects_extensionless_binary_with_the_gate_diagnostic(tmp_path: Path) -> None:
    check_binary_rejection(tmp_path, "extensionless")


def test_direct_entrypoint_rejects_original_pdf_tampering_even_with_updated_catalog_hash(
    tmp_path: Path,
) -> None:
    root, _, event = history(tmp_path)
    data = papers.load_catalog(root)
    row = data["papers"][0]
    original = root / row["pdf"]["path"]
    changed = original.read_bytes() + b"\nchanged original\n"
    original.write_bytes(changed)
    row["pdf"]["sha256"] = hashlib.sha256(changed).hexdigest()
    refresh_fixture(root, data)
    save(root)
    result = run_gate(root, event)
    assert result.returncode == 1
    assert "Historical paper paths and bytes are immutable" in result.stderr
    assert "ModuleNotFoundError" not in result.stderr
    assert "No binary changes detected." not in result.stdout
