#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Package the exact committed source, installed wheel and acceptance evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import tomllib
import zipfile

from alpha_factory_v1.utils.disclaimer import DISCLAIMER  # noqa: F401


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    version = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]
    if not isinstance(version, str) or not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise ValueError("release version must be major.minor.patch")
    sha = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    subprocess.run([sys.executable, "-m", "scripts.check_agent_preservation"], check=True)
    subprocess.run(
        [
            "git",
            "archive",
            "--format=zip",
            f"--prefix=AGI-Alpha-Agent-v{version}/",
            "-o",
            str(output / f"alpha-agent-v{version}-source.zip"),
            sha,
        ],
        check=True,
    )
    with tempfile.TemporaryDirectory(prefix="alpha-release-build-") as temporary:
        clean = Path(temporary)
        with zipfile.ZipFile(output / f"alpha-agent-v{version}-source.zip") as archive:
            archive.extractall(clean)
        source = clean / f"AGI-Alpha-Agent-v{version}"
        subprocess.run(
            [sys.executable, "-m", "build", "--no-isolation", "--outdir", str(output)], cwd=source, check=True
        )
    wheel = next(output.glob("*.whl"))
    with zipfile.ZipFile(wheel) as archive:
        names = archive.namelist()
        assert "alpha_factory_v1/core/runtime/web/index.html" in names
        assert "alpha_factory_v1/core/runtime/cli.py" in names
        assert not any("/node_modules/" in name or "/.venv/" in name for name in names)
    subprocess.run(
        [sys.executable, "-m", "twine", "check", *map(str, output.glob("*.whl")), *map(str, output.glob("*.tar.gz"))],
        check=True,
    )
    for name in (
        "requirements-agent.lock",
        "scripts/install_agent.py",
        "docs/agent/OPERATIONS.md",
        "docs/agent/CAPABILITIES.md",
        "docs/agent/VALIDATION.md",
        f"docs/agent/RELEASE_NOTES_{version}.md",
    ):
        shutil.copy2(name, output / Path(name).name)
    browser_source = args.evidence / "browser-distribution" / "insight_browser.zip"
    browser_target = output / f"alpha-agent-v{version}-browser.zip"
    model_manifest = json.loads(Path("scripts/browser_model_manifest.json").read_text(encoding="utf-8"))
    with zipfile.ZipFile(browser_source) as browser_archive:
        required = {
            "index.html",
            "service-worker.js",
            "insight.bundle.js",
            "assets/local-llm/transformers.min.js",
            "assets/local-llm/THIRD_PARTY_MODEL_NOTICES.md",
        }
        if not required.issubset(browser_archive.namelist()):
            raise ValueError("Full browser distribution is incomplete")
        for name, expected in model_manifest["files"].items():
            with browser_archive.open("assets/local-llm/models/gpt2/" + name) as model_file:
                if hashlib.file_digest(model_file, "sha256").hexdigest() != expected:
                    raise ValueError(f"Packaged browser model checksum mismatch: {name}")
    shutil.copy2(browser_source, browser_target)
    with zipfile.ZipFile(output / f"alpha-agent-v{version}-validation.zip", "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(args.evidence.rglob("*")):
            if path.is_file() and "browser-distribution" not in path.relative_to(args.evidence).parts:
                archive.write(path, path.relative_to(args.evidence))
        for path in sorted(Path("docs/agent/release-evidence").glob("*.json")):
            archive.write(path, "local/" + path.name)
    manifest = {
        "version": version,
        "commit": sha,
        "baseline": "ac9b112a44670f67d53fc3d188ef73fa16e90894",
        "repository": "MontrealAI/AGI-Alpha-Agent-v0",
        "workflow_run": (
            f"https://github.com/{os.getenv('GITHUB_REPOSITORY', 'MontrealAI/AGI-Alpha-Agent-v0')}"
            f"/actions/runs/{os.getenv('GITHUB_RUN_ID', 'local')}"
        ),
        "python": sys.version,
        "original_files_preserved": 2125,
        "original_readme_text_and_flywheels_preserved": True,
        "permitted_readme_changes": "CI badge URL queries only",
        "release_gates": [
            "runtime Python 3.11/3.12/3.13",
            "full offline Python regression",
            "strict runtime types",
            "full-repository and changed-file pre-commit hooks",
            "real Docker isolation",
            "real PostgreSQL ledger and locked TypeScript integration",
            "pinned local model inference and generated-code evaluation",
            "Chromium operator workflow",
            "legacy browser tests",
            "complete gallery rebuild and offline simulation",
            "real browser ONNX generation online and offline",
            "Linux/macOS/Windows smoke on Python 3.11/3.12/3.13",
            "Solidity tests with shipped identity logic",
            "real local EVM payments",
            "clean wheel installation",
            "source preservation",
        ],
        "limits": [
            "No mainnet transactions",
            "No general intelligence claim",
            "No automatic treasury spending",
            "Optional legacy skips do not establish those integrations",
        ],
    }
    (output / "release-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    lines = []
    for path in sorted(output.iterdir()):
        if path.is_file():
            with path.open("rb") as stream:
                checksum = hashlib.file_digest(stream, "sha256").hexdigest()
            lines.append(f"{checksum}  {path.name}")
    (output / "SHA256SUMS").write_text("\n".join(lines) + "\n")
    print(json.dumps({"commit": sha, "assets": len(lines) + 1, "output": str(output)}))


if __name__ == "__main__":
    main()
