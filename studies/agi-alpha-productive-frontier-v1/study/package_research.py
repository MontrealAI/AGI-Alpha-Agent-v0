# SPDX-License-Identifier: Apache-2.0
"""Create a reproducible research archive with the exact native source closure."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import zipfile
from pathlib import Path

STUDY = Path(__file__).resolve().parents[1]
REPOSITORY = STUDY.parents[1]
PREFIX = "AGI_ALPHA_Productive_Frontier_Research"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    study_relative = STUDY.relative_to(REPOSITORY).as_posix()
    listing = subprocess.check_output(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z", "--", study_relative],
        cwd=REPOSITORY,
    )
    paths = {p.decode() for p in listing.split(b"\0") if p}
    paths = {p for p in paths if not p.endswith(".zip")}
    native = json.loads((STUDY / "evidence/native_source_manifest.json").read_text())
    for entry in native["files"]:
        data = (REPOSITORY / entry["path"]).read_bytes()
        if sha256(data) != entry["sha256"]:
            raise ValueError(f"Pinned native source changed: {entry['path']}")
        paths.add(entry["path"])
    paths.update({"LICENSE", "docs/DISCLAIMER_SNIPPET.md"})
    payloads = {path: (REPOSITORY / path).read_bytes() for path in sorted(paths)}
    payloads["README.md"] = (
        "# AGI ALPHA FLYWHEEL: Making the Next Opportunity Possible\n\n"
        "Vincent Boucher — President of MONTREAL.AI\n\n"
        f"Open `{study_relative}/README.md` for the paper, English/French demonstration, "
        "evidence and reproduction commands. The browser edition works locally.\n\n"
        "This archive contains the full additive research study and the 13 unchanged native "
        "modules required by its accounting adapter, not the complete production repository. "
        "Keep `alpha_factory_v1/` beside `studies/`; do not flatten the directory structure.\n\n"
        "The observed effect is faster numerical delivery of an already feasible offering. "
        "Commercial behavior is simulated; actual customer collections are zero. Live "
        "frontier-model performance, ENS admission and repeated profitable frontier expansion "
        "are not established. Existing publication qualification remains required.\n\n"
        "`MANIFEST.json` identifies every original file. Enterprise histories are lossless "
        "gzip files with additional original-byte hashes in the study's evidence directory. "
        "Both earlier complete economic cohorts, the submitted edition1.0.0 paper, and the "
        "declared policy/capacity correction history remain included. This is edition1.0.1.\n"
    ).encode()
    manifest = {
        "schema": "agi-alpha-productive-frontier-package/v1",
        "edition": "1.0.1",
        "native_source_commit": native["repository_commit"],
        "native_files": len(native["files"]),
        "study": study_relative,
        "files": [{"path": p, "bytes": len(data), "sha256": sha256(data)} for p, data in sorted(payloads.items())],
    }
    payloads["MANIFEST.json"] = (json.dumps(manifest, indent=2) + "\n").encode()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(args.output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path, data in sorted(payloads.items()):
            info = zipfile.ZipInfo(f"{PREFIX}/{path}", date_time=(2026, 10, 27, 0, 0, 0))
            info.external_attr = 0o100644 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, data, compresslevel=9)
    with zipfile.ZipFile(args.output) as archive:
        if archive.testzip() is not None:
            raise ValueError("Archive CRC validation failed")
        for path, data in payloads.items():
            if archive.read(f"{PREFIX}/{path}") != data:
                raise ValueError(f"Archive byte verification failed: {path}")
    print(
        json.dumps(
            {
                "path": str(args.output.resolve()),
                "bytes": args.output.stat().st_size,
                "sha256": sha256(args.output.read_bytes()),
                "members": len(payloads),
                "native_files": len(native["files"]),
                "crc_and_bytes_verified": True,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
