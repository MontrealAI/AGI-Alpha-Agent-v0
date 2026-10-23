#!/usr/bin/env python3
"""Build a deterministic, manifest-bound software/evidence companion."""
from pathlib import Path
import hashlib
import json
import zipfile

root = Path(__file__).resolve().parent
output = root / "deliverables"
output.mkdir(exist_ok=True)
excluded_parts = {"node_modules", "__pycache__", ".git", ".npm-cache"}
files = [root / name for name in ["README.md", "LICENSE", "NOTICE.md", ".node-version", "PUBLICATION_HANDOFF.md", "VERIFY.py", "package-companion.py"]]
for directory in ["study", "evidence", "publication"]:
    for p in sorted((root / directory).rglob("*")):
        if not p.is_file() or p.is_symlink():
            continue
        rel = p.relative_to(root)
        if excluded_parts.intersection(rel.parts):
            continue
        if directory == "publication" and "build" in rel.parts:
            continue
        if str(rel).startswith("publication/qa/") and len(rel.parts) > 3 and rel.parts[2] != "single-file-final":
            continue
        if str(rel).startswith("evidence/foundations/") and rel.name.endswith("-selected.txt"):
            continue
        if str(rel).startswith("evidence/contracts/") and rel.suffix == ".html":
            continue
        files.append(p)
files = sorted(set(files), key=lambda p: str(p.relative_to(root)))
manifest = "".join(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(root).as_posix()}\n" for p in files)
(root / "MANIFEST.sha256").write_text(manifest, encoding="utf-8")
files.append(root / "MANIFEST.sha256")
target = output / "Successor_Omega_Harness_Companion.zip"
with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
    for p in files:
        name = "Successor_Omega_Harness/" + p.relative_to(root).as_posix()
        info = zipfile.ZipInfo(name, date_time=(2026, 10, 23, 17, 0, 0))
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = 0o100644 << 16
        z.writestr(info, p.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
with zipfile.ZipFile(target) as z:
    assert z.testzip() is None
    for p in files:
        assert z.read("Successor_Omega_Harness/" + p.relative_to(root).as_posix()) == p.read_bytes()
receipt = {"schema": "tae.companion-release.v1", "file": target.name, "bytes": target.stat().st_size, "sha256": hashlib.sha256(target.read_bytes()).hexdigest(), "files": len(files), "manifestSha256": hashlib.sha256(manifest.encode()).hexdigest(), "crcAndByteVerification": "passed", "sourceRepositories": "Fetched by exact public pins; not redistributed", "scope": "Complete local research companion, not a deployed production runtime"}
(output / "companion-receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps(receipt, indent=2))
