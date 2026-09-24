#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Package the exact committed source, installed wheel and acceptance evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import zipfile

from alpha_factory_v1.utils.disclaimer import DISCLAIMER  # noqa: F401


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    sha = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    subprocess.run([sys.executable, "scripts/check_agent_preservation.py"], check=True)
    subprocess.run(
        [
            "git",
            "archive",
            "--format=zip",
            "--prefix=AGI-Alpha-Agent-v1.2.0/",
            "-o",
            str(output / "alpha-agent-v1.2.0-source.zip"),
            sha,
        ],
        check=True,
    )
    with tempfile.TemporaryDirectory(prefix="alpha-release-build-") as temporary:
        clean = Path(temporary)
        with zipfile.ZipFile(output / "alpha-agent-v1.2.0-source.zip") as archive:
            archive.extractall(clean)
        source = clean / "AGI-Alpha-Agent-v1.2.0"
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
        "docs/agent/RELEASE_NOTES_1.2.0.md",
    ):
        shutil.copy2(name, output / Path(name).name)
    with zipfile.ZipFile(output / "alpha-agent-v1.2.0-validation.zip", "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(args.evidence.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(args.evidence))
        for path in sorted(Path("docs/agent/release-evidence").glob("*.json")):
            archive.write(path, "local/" + path.name)
    manifest = {
        "version": "1.2.0",
        "commit": sha,
        "baseline": "ac9b112a44670f67d53fc3d188ef73fa16e90894",
        "repository": "MontrealAI/AGI-Alpha-Agent-v0",
        "workflow_run": (
            f"https://github.com/{os.getenv('GITHUB_REPOSITORY', 'MontrealAI/AGI-Alpha-Agent-v0')}"
            f"/actions/runs/{os.getenv('GITHUB_RUN_ID', 'local')}"
        ),
        "python": sys.version,
        "original_files_preserved": 2125,
        "original_readme_verbatim": True,
        "release_gates": [
            "runtime Python 3.11/3.12/3.13",
            "full offline Python regression",
            "strict runtime types",
            "real Docker isolation",
            "Chromium operator workflow",
            "legacy browser tests",
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
