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
