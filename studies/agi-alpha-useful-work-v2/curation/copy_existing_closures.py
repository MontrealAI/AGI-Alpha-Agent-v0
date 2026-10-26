# SPDX-License-Identifier: Apache-2.0
"""Carry unchanged, identity-checked local dependency closures into this study."""
from __future__ import annotations

import datetime
import hashlib
import json
from pathlib import Path
import time

ROOT = Path(__file__).resolve().parents[1]
PRIOR = ROOT.parent / "value-compounds"


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def blob(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def save(path: Path, raw: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_bytes() != raw:
        raise ValueError("DIFFERENT_EXISTING_OUTPUT: " + str(path))
    path.write_bytes(raw)


def main() -> None:
    start, cpu = time.perf_counter(), time.process_time()
    source_manifest = PRIOR / "native/SOURCE.json"
    source = json.loads(source_manifest.read_text())
    native_records = []
    for row in source["files"]:
        if not row["path"].endswith(".mjs"):
            continue
        raw = (PRIOR / "native" / row["path"]).read_bytes()
        if sha(raw) != row["sha256"] or blob(raw) != row["git_blob"] or len(raw) != row["bytes"]:
            raise ValueError("NATIVE_IDENTITY: " + row["path"])
        save(ROOT / "native" / row["path"], raw)
        native_records.append({**row, "copied_unchanged": True,
                               "upstream_url": f"https://github.com/{source['repository']}/blob/{source['commit']}/{row['path']}"})
    vendor = json.loads((ROOT / "discovery/native-vendor-retrieval.json").read_text())
    for row in vendor["files"]:
        if row["encoding"] != "utf-8":
            raise ValueError("EXPECTED_UTF8_SOURCE")
        raw = row["content"].encode()
        if blob(raw) != row["sha"]:
            raise ValueError("VENDOR_GIT_BLOB")
        name = "LICENSE" if row["kind"] == "vendor_license" else "provenance.json"
        relative = "examples/build-successor/vendor/agijobs/" + name
        save(ROOT / "native" / relative, raw)
        native_records.append({"path": relative, "bytes": len(raw), "sha256": sha(raw),
                               "git_blob": row["sha"], "commit": source["commit"], "copied_unchanged": True,
                               "upstream_url": row["display_url"]})
    license_raw = (PRIOR / "native/LICENSE.Alpha").read_bytes()
    save(ROOT / "native/LICENSE.Alpha", license_raw)
    native_manifest = {"schema": "unchanged-native-workbench-closure/v1", "repository": source["repository"],
                       "commit": source["commit"], "origin_manifest_sha256": sha(source_manifest.read_bytes()),
                       "files": native_records,
                       "license": {"path": "LICENSE.Alpha", "sha256": sha(license_raw), "bytes": len(license_raw)},
                       "scope": "Seven unchanged JavaScript modules only; vendored Jobs MIT notice and provenance retained.",
                       "authority": "Local Workbench extension seam; no installed operator, production or settlement authority."}
    save(ROOT / "native/SOURCE.json", (json.dumps(native_manifest, indent=2) + "\n").encode())
    canonical_records = []
    identities = json.loads((PRIOR / "discovery/source-file-identities.json").read_text())
    for row in identities:
        if not row["path"].startswith("discovery/canonical/"):
            continue
        raw = (PRIOR / row["path"]).read_bytes()
        if sha(raw) != row["sha256"] or blob(raw) != row["git_blob"]:
            raise ValueError("CANONICAL_SOURCE_IDENTITY")
        relative = "value-compounds/" + row["path"]
        save(ROOT / "canonical" / relative, raw)
        canonical_records.append({**row, "local_path": relative, "copied_unchanged": True})
    adapter = PRIOR / "src/economics.mjs"
    adapter_raw = adapter.read_bytes()
    relative = "value-compounds/src/economics.mjs"
    save(ROOT / "canonical" / relative, adapter_raw)
    canonical_records.append({"local_path": relative, "prior_path": "src/economics.mjs",
                              "sha256": sha(adapter_raw), "bytes": len(adapter_raw), "copied_unchanged": True,
                              "url": "https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/f019a1d2d1c1c678c7363bf9cde61dab6ec0de12/studies/agi-alpha-value-compounds-v1/src/economics.mjs",
                              "scope": "Prior research economics adapter; preserves original relative canonical imports."})
    save(ROOT / "canonical/LICENSE.Alpha", license_raw)
    canonical_manifest = {"schema": "unchanged-canonical-accounting-closure/v1", "files": canonical_records,
                          "canonical_source_commit": "496fa3c00dc7498173a896404ec756dfdeb94033",
                          "source_boundary": "Canonical modules inspected in held PR4899; not claimed released or adopted.",
                          "adapter_origin": "Preserved prior research study and public draft PR4931",
                          "license": {"path": "LICENSE.Alpha", "sha256": sha(license_raw)},
                          "authority": "Inert accounting only; no transfer, token issuance or financial authority."}
    save(ROOT / "canonical/SOURCE.json", (json.dumps(canonical_manifest, indent=2) + "\n").encode())
    prior_records = []
    for name in ("source-audit.json", "source-audit.md", "source-file-identities.json", "final-status.json"):
        raw = (PRIOR / "discovery" / name).read_bytes()
        save(ROOT / "discovery/prior-ecosystem-audit" / name, raw)
        prior_records.append({"path": "discovery/prior-ecosystem-audit/" + name, "sha256": sha(raw), "bytes": len(raw)})
    result = {"event": "unchanged_closures_copied", "utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "native_modules": 7, "native_source_manifest_sha256": sha((ROOT / "native/SOURCE.json").read_bytes()),
              "canonical_source_manifest_sha256": sha((ROOT / "canonical/SOURCE.json").read_bytes()),
              "prior_audit_copies": prior_records, "wall_seconds": time.perf_counter() - start,
              "process_cpu_seconds": time.process_time() - cpu, "remote_reads": 2,
              "remote_read_scope": "Exact existing vendor LICENSE/provenance absent from prior native folder",
              "primary_bodies_acquired": False, "inference_tokens": None, "inference_usd": None}
    with (ROOT / "metering/source_audit.jsonl").open("a") as output:
        output.write(json.dumps(result) + "\n")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
