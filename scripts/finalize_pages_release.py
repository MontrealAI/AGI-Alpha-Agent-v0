# SPDX-License-Identifier: Apache-2.0
"""Include successful public Pages acceptance in an unpublished release package."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import zipfile


def finalize(folder: Path, evidence: Path) -> None:
    """Bind public evidence to the packaged commit and refresh package checksums."""
    manifest_path = folder / "release-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    public = json.loads((evidence / "public-pages" / "release.json").read_text(encoding="utf-8"))
    workspace = json.loads((evidence / "public-pages" / "workspace.json").read_text(encoding="utf-8"))
    url = "https://montrealai.github.io/AGI-Alpha-Agent-v0/"
    if public["commit"] != manifest["commit"] or public["version"] != manifest["version"]:
        raise ValueError("Public Pages evidence differs from the packaged source")
    if workspace["origin"] != url or not workspace["model_required"] or public["url"] != url:
        raise ValueError("Public Pages acceptance must exercise the full canonical site")
    ascension = None
    insight = None
    if tuple(int(part) for part in manifest["version"].split(".")) >= (1, 5, 0):
        ascension = json.loads((evidence / "public-pages" / "ascension" / "ascension.json").read_text(encoding="utf-8"))
        if ascension.get("passed") is not True or ascension.get("origin") != url:
            raise ValueError("Ascension must pass on the canonical public site")
        if ascension.get("paper_sha256") != "fd14d444d51e9f6ebaec13387fc8d2170615d1bbfab13edc7e84ea1f655d20aa":
            raise ValueError("Public white paper differs from the preserved original")
    if tuple(int(part) for part in manifest["version"].split(".")) >= (1, 6, 0):
        insight = json.loads(
            (evidence / "public-pages" / "insight-atlas" / "insight-atlas.json").read_text(encoding="utf-8")
        )
        required = {
            "all-three-scenarios",
            "stale-proof-rejected",
            "tampered-proof-rejected",
            "unsafe-quorum-blocked",
            "native-mission-schema",
            "native-research-execution-and-signed-export",
            "reviewed-design-reuse-requires-fresh-evidence",
            "recovery-replays-promotions",
            "tampered-history-rejected",
            "revocation-survives-recovery",
            "mirrored-page",
            "offline-reload-recovery-and-replay",
            "axe-wcag-a-aa-no-violations",
            "keyboard-selection-retains-focus",
        }
        if (
            insight.get("schema") != "agialpha.insight.acceptance.v1"
            or insight.get("passed") is not True
            or insight.get("origin") != url
            or insight.get("browser_errors") != []
            or not required.issubset(insight.get("checks", []))
            or {item.get("id") for item in insight.get("scenarios", [])} != {"energy", "science", "enterprise"}
        ):
            raise ValueError("Insight Atlas must pass every required journey on the canonical public site")
    for line in (folder / "SHA256SUMS").read_text().splitlines():
        expected, name = line.split("  ", 1)
        path = folder / name
        if path.parent != folder or not path.is_file() or path.is_symlink():
            raise ValueError("Invalid packaged asset")
        with path.open("rb") as stream:
            if hashlib.file_digest(stream, "sha256").hexdigest() != expected:
                raise ValueError(f"Packaged asset changed before public acceptance: {name}")
    archive_path = folder / f"alpha-agent-v{manifest['version']}-validation.zip"
    with zipfile.ZipFile(archive_path, "a", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(evidence.rglob("*")):
            if path.is_symlink():
                raise ValueError("Evidence must contain ordinary files")
            if path.is_file():
                archive.write(path, path.relative_to(evidence))
    manifest["public_pages"] = public
    if insight:
        manifest["public_insight_atlas"] = insight
        manifest["release_gates"].append(
            "public Insight Atlas, native exports, adversarial proof checks and offline recovery"
        )
    if ascension:
        manifest["public_ascension"] = ascension
        manifest["release_gates"].append(
            "public Ascension journey, authenticated recovery, exact settlement and offline use"
        )
    manifest["release_gates"].append("public HTTPS Pages workflows and actual offline model generation")
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    checksums = []
    for path in sorted(folder.iterdir()):
        if path.is_file() and path.name != "SHA256SUMS":
            with path.open("rb") as stream:
                checksums.append(f"{hashlib.file_digest(stream, 'sha256').hexdigest()}  {path.name}")
    (folder / "SHA256SUMS").write_text("\n".join(checksums) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release", type=Path, default=Path("release"))
    parser.add_argument("--evidence", type=Path, required=True)
    args = parser.parse_args()
    finalize(args.release, args.evidence)


if __name__ == "__main__":
    main()
