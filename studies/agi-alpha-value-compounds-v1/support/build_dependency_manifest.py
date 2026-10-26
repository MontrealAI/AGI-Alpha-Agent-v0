# SPDX-License-Identifier: Apache-2.0
"""Index existing wheels and retain their supplied license files; no network."""
from __future__ import annotations

import email
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def main() -> None:
    wheels, licenses, requirements = [], [], []
    for path in sorted((ROOT / "deps/wheels").glob("*.whl")):
        if path.is_symlink():
            raise ValueError("WHEEL_SYMLINK")
        raw = path.read_bytes()
        with zipfile.ZipFile(path) as archive:
            metadata_names = [n for n in archive.namelist() if n.endswith(".dist-info/METADATA")]
            if len(metadata_names) != 1:
                raise ValueError("WHEEL_METADATA_COUNT")
            metadata = email.message_from_bytes(archive.read(metadata_names[0]))
            name, version = metadata["Name"], metadata["Version"]
            if not re.fullmatch(r"[A-Za-z0-9_.-]+", name + version):
                raise ValueError("WHEEL_IDENTITY")
            record = {"name": name, "version": version, "path": path.relative_to(ROOT).as_posix(),
                      "bytes": len(raw), "sha256": digest(raw), "requires_python": metadata["Requires-Python"],
                      "requires_dist": metadata.get_all("Requires-Dist", []),
                      "license_expression": metadata["License-Expression"],
                      "license_field": metadata["License"], "license_files": []}
            for member in sorted(archive.namelist()):
                parts = PurePosixPath(member).parts
                if member.endswith("/") or ".dist-info/" not in member:
                    continue
                if not any(x in PurePosixPath(member).name.lower() for x in ("license", "notice", "copying")):
                    continue
                if ".." in parts or member.startswith("/"):
                    raise ValueError("LICENSE_PATH")
                content = archive.read(member)
                target = ROOT / "licenses/distributions" / f"{name}-{version}" / PurePosixPath(member).name
                target.parent.mkdir(parents=True, exist_ok=True)
                if target.exists() and target.read_bytes() != content:
                    raise ValueError("LICENSE_COLLISION")
                target.write_bytes(content)
                license_row = {"distribution": name, "version": version, "wheel_path": record["path"],
                               "wheel_member": member, "path": target.relative_to(ROOT).as_posix(),
                               "bytes": len(content), "sha256": digest(content)}
                licenses.append(license_row)
                record["license_files"].append(license_row["path"])
            if not record["license_files"]:
                raise ValueError("MISSING_DISTRIBUTION_LICENSE: " + name)
            wheels.append(record)
            requirements.append(f"{name}=={version} --hash=sha256:{digest(raw)}")
    if not wheels:
        raise ValueError("NO_WHEELS")
    manifest = {
        "schema": "value-compounds-offline-runtime/v1", "network_requests": 0,
        "origin": "Existing local wheel artifacts acquired before this support packaging task; exact byte identities retained.",
        "platform": {"implementation": "CPython", "python": "3.12", "os": "Linux", "machine": "x86_64",
                     "minimum_glibc": "2.34", "node_observed": "24.22.1", "node_bundled": False},
        "wheels": wheels, "total_wheel_bytes": sum(x["bytes"] for x in wheels),
        "excluded_optional_extras": ["griffe faster/pypi", "pydantic email/timezone", "cryptography ssh"],
        "external_prerequisites": ["CPython 3.12 with venv and bundled ensurepip", "Linux x86_64 glibc >=2.34", "Node.js 24.22.1 for the observed Workbench replay"],
        "license_scope": "Exact distribution-supplied license/notice files, not an independent legal certification of all transitive native components."
    }
    (ROOT / "support/dependency-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    (ROOT / "support/requirements-replay.lock").write_text(
        "# Exact existing wheel identities. Install only from deps/wheels with --no-index --require-hashes.\n"
        + "\n".join(requirements) + "\n")
    (ROOT / "licenses/distribution-index.json").write_text(json.dumps({"schema": "value-compounds-license-index/v1", "files": licenses}, indent=2) + "\n")
    print(json.dumps({"wheels": len(wheels), "wheel_bytes": manifest["total_wheel_bytes"], "license_files": len(licenses)}))


if __name__ == "__main__":
    main()
