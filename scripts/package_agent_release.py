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
from urllib.parse import urlsplit

from alpha_factory_v1.utils.disclaimer import DISCLAIMER  # noqa: F401
from scripts.check_agent_preservation import BADGE_MAINTENANCE
from scripts.check_manuscript import verify as verify_manuscript
from scripts.check_factory_readiness import check as verify_factory


def release_documents(version: str) -> tuple[str, ...]:
    """Retain the existing release documents and include the complete operating path."""
    return (
        "requirements-agent.lock",
        "scripts/install_agent.py",
        "docs/agent/START_HERE.md",
        "docs/agent/FACTORY_GUIDE.md",
        "docs/agent/DEMOS.md",
        "docs/agent/ASCENSION_PROTOCOL.md",
        "docs/agent/OPERATIONS.md",
        "docs/agent/CAPABILITIES.md",
        "docs/agent/VALIDATION.md",
        "docs/agent/DEMO_VALIDATION.md",
        "docs/agent/PAGES_GUIDE.md",
        "docs/agent/WHITEPAPER_IMPLEMENTATION.md",
        "docs/agent/INSIGHT_ATLAS.md",
        "docs/agent/PROOF_BLOOM.md",
        "docs/agent/COMPOUNDING_LAB.md",
        "docs/agent/DECISION_STUDIO.md",
        "docs/agent/BUSINESS3.md",
        "docs/agent/GOVERNANCE.md",
        "docs/agent/DISCOVERY.md",
        "docs/agent/EXPERIENCE.md",
        "docs/agent/MATS.md",
        "docs/agent/CURRICULUM_LAB.md",
        "docs/agent/MUZERO.md",
        "docs/agent/MANUSCRIPT_ALIGNMENT.md",
        "docs/manuscript/AGI_ALPHA_Unified_Publication_Final.pdf",
        "docs/manuscript/AGI_ALPHA_Unified_Publication_Final.md",
        "docs/manuscript/source-manifest.json",
        "docs/agent/RELEASE_READINESS.md",
        f"docs/agent/RELEASE_NOTES_{version}.md",
    )


def copy_release_documents(root: Path, output: Path, version: str, commit: str) -> None:
    """Make flattened guide links usable while retaining manuscript bytes exactly."""
    root = root.resolve()
    names = release_documents(version)
    packaged = {name: Path(name).name for name in names}
    for name in names:
        source = root / name
        target = output / source.name
        if not name.startswith("docs/agent/") or source.suffix != ".md":
            shutil.copy2(source, target)
            continue

        def rewrite(match: re.Match[str]) -> str:
            link = match.group(1)
            parsed = urlsplit(link)
            if parsed.scheme or parsed.netloc or not parsed.path:
                return match.group(0)
            destination = (source.parent / parsed.path).resolve()
            if destination == root / "docs/assets/whitepaper_v0.1.0-alphav15.pdf":
                destination = root / "whitepaper_v0.1.0-alphav15.pdf"
            if not destination.is_relative_to(root) or not destination.exists():
                raise ValueError(f"Broken release guide link: {name}: {link}")
            relative = destination.relative_to(root).as_posix()
            if relative in packaged and not source.name.startswith("RELEASE_NOTES_"):
                url = packaged[relative]
            elif relative.startswith("docs/") and relative.endswith(".html"):
                url = "https://montrealai.github.io/AGI-Alpha-Agent-v0/" + relative.removeprefix("docs/").removesuffix(
                    "index.html"
                )
            else:
                kind = "tree" if destination.is_dir() else "blob"
                url = f"https://github.com/MontrealAI/AGI-Alpha-Agent-v0/{kind}/{commit}/{relative}"
            return (
                "]("
                + url
                + ("?" + parsed.query if parsed.query else "")
                + ("#" + parsed.fragment if parsed.fragment else "")
                + ")"
            )

        sections = re.split(r"(```.*?```)", source.read_text(encoding="utf-8"), flags=re.S)
        for index in range(0, len(sections), 2):
            sections[index] = re.sub(r"\]\(([^\s)]+)\)", rewrite, sections[index])
        target.write_text("".join(sections), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    args = parser.parse_args()
    subprocess.run(["git", "diff", "--exit-code", "--quiet", "HEAD"], check=True)
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    version = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]
    if not isinstance(version, str) or not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise ValueError("release version must be major.minor.patch")
    sha = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    subprocess.run([sys.executable, "-m", "scripts.check_agent_preservation"], check=True)
    manuscript_hashes = verify_manuscript()
    factory_preservation = verify_factory()
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
    copy_release_documents(Path.cwd(), output, version, sha)
    with zipfile.ZipFile(output / f"alpha-agent-v{version}-operator-guide.zip", "w", zipfile.ZIP_DEFLATED) as archive:
        for name in release_documents(version):
            if name.startswith("docs/agent/"):
                path = output / Path(name).name
                archive.write(path, path.name)
    with zipfile.ZipFile(output / f"alpha-agent-v{version}-manuscript.zip", "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(Path("docs/manuscript").rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to("docs/manuscript"))
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
    site_archive = args.evidence / "pages-distribution" / "site.tar.gz"
    shutil.copy2(site_archive, output / f"alpha-agent-v{version}-site.tar.gz")
    with zipfile.ZipFile(output / f"alpha-agent-v{version}-validation.zip", "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(args.evidence.rglob("*")):
            if path.is_file() and not {"browser-distribution", "pages-distribution", "github-pages"}.intersection(
                path.relative_to(args.evidence).parts
            ):
                archive.write(path, path.relative_to(args.evidence))
        for path in sorted(Path("docs/agent/release-evidence").glob("*.json")):
            archive.write(path, "local/" + path.name)
    manifest = {
        "version": version,
        "manuscript": {"pages": 198, "files": manuscript_hashes},
        "factory": factory_preservation,
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
        "permitted_readme_changes": BADGE_MAINTENANCE,
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
            "complete browser workspace, native handoff and Ed25519 verification",
            "Insight Atlas exact allocation, architecture search, evidence replay and Chronicle recovery",
            "Proof Bloom jobs, native signed returns, reviewed gates, capability reuse and transitive revocation",
            "Compounding Lab future-task transfer, costs, human review, native/browser replay "
            "and complete Evidence Docket",
            "byte-identical latest 198-page manuscript and pinned source manifest",
            "native CPU demos and Streamlit lineage UIs",
            "Sovereign Python 3.11/3.12/3.13 dependency-gated workflow, signed packets, recovery and Chromium reviews",
            "complete demo catalog and every browser replay",
            "Business 3 exact Python/browser portfolios and exports, notebook, installed wheel and isolated container",
            "Decision Studio calculation oracles, versioned replay, staffing coverage, "
            "deadlines and public offline journeys",
            "Linux/macOS/Windows smoke on Python 3.11/3.12/3.13",
            "Solidity tests with shipped identity logic",
            "real local EVM payments",
            "native Ascension commitments, signed reviewed deliveries and strict evidence types",
            "Ascension protocol exact assets, canonical and mirrored routes, keyboard access and offline recovery",
            "clean wheel installation",
            "complete operator Python advisory audit with exact lock digest",
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
