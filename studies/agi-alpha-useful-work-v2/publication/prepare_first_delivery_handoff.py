# SPDX-License-Identifier: Apache-2.0
"""Prepare an additive corrected edition; preserve original decision evidence."""
from __future__ import annotations

import datetime
import difflib
import hashlib
import json
from pathlib import Path
import shutil
import time

ROOT = Path(__file__).resolve().parents[1]


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n")


def main() -> None:
    wall, cpu = time.perf_counter(), time.process_time()
    metadata_dir = ROOT / "publication/wheel-metadata"
    metadata_dir.mkdir(parents=True, exist_ok=False)
    wheel_rows = {}
    for environment in ("development-baseline-bridge-environment", "development-target-environment"):
        directory = ROOT / "data" / environment
        report = json.loads((directory / "preparation.json").read_text())
        for wheel in report["wheels"]:
            key = wheel["name"] + "-" + wheel["version"]
            path = directory / "metadata" / (key + ".json")
            raw = path.read_bytes()
            metadata = json.loads(raw)
            info = metadata["info"]
            files = [item for item in metadata["urls"] if item["filename"] == wheel["filename"]]
            if len(files) != 1 or files[0]["digests"]["sha256"] != wheel["sha256"]:
                raise ValueError("METADATA_WHEEL_IDENTITY")
            compact = {"schema": "source-handoff-wheel-metadata-projection/v1",
                       "source_url": metadata.get("source_url", f"https://pypi.org/pypi/{wheel['name']}/{wheel['version']}/json"),
                       "preserved_metadata_file_sha256": sha(raw),
                       "official_response_sha256": metadata.get("raw_metadata_sha256", sha(raw)),
                       "projection": "Only descriptive package requirements and the exact already acquired wheel metadata; no wheel bytes.",
                       "info": {field: info.get(field) for field in
                                ("name", "version", "requires_python", "requires_dist", "license", "license_expression")},
                       "urls": files}
            destination = metadata_dir / (key + ".json")
            if not destination.exists():
                write_json(destination, compact)
            wheel_rows[key] = {"path": str(destination.relative_to(ROOT)), "sha256": sha(destination.read_bytes()),
                               "wheel_sha256": wheel["sha256"], "wheel_bytes": wheel["bytes"]}
    source = json.loads((ROOT / "discovery/handoff-source-snapshot.json").read_text())
    tree = {item["path"]: item for item in source["inspected_files"]}
    consumers = []
    for local, upstream in (
        ("data/consumer/api.py", "alpha_factory_v1/core/runtime/api.py"),
        ("data/consumer/models.py", "alpha_factory_v1/core/runtime/models.py"),
        ("discovery/test_api_boundary.py", "tests/runtime/test_api_boundary.py"),
        ("discovery/requirements/requirements-agent.lock", "requirements-agent.lock"),
    ):
        raw = (ROOT / local).read_bytes()
        git_blob = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
        if git_blob != tree[upstream]["sha"]:
            raise ValueError("CURRENT_SOURCE_DIFFERS: " + upstream)
        consumers.append({"local_path": local, "upstream_path": upstream, "sha256": sha(raw), "bytes": len(raw),
                          "git_blob": git_blob, "experiment_commit": "eb07086ac42799ff45f7b1c946a2f7c514bd3bbc",
                          "current_equal_source_commit": source["current_main"],
                          "url": f"https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/{source['current_main']}/{upstream}"})
    write_json(ROOT / "publication/current-consumer-identities.json", {"sources": consumers})
    write_json(ROOT / "publication/wheel-metadata-index.json", {"files": wheel_rows, "wheel_bytes_in_public_handoff": 0})
    original = ROOT / "results/development/first-delivery"
    corrected = ROOT / "results/development/first-delivery-corrected"
    shutil.copytree(original, corrected)
    original_identities = {str(path.relative_to(original)): sha(path.read_bytes())
                           for path in sorted(original.rglob("*")) if path.is_file()}
    readme = (corrected / "READ-ME.md").read_text()
    readme = readme.replace("current production lock", "current native lock")
    readme = readme.replace("verrou de production actuel", "verrou natif actuel")
    (corrected / "READ-ME.md").write_text(readme)
    replay = """Runnable replay from the source handoff or complete companion (Python 3.12 / Linux x86_64):

1. Change directory to the study root containing protocol/, src/, curation/ and publication/.
   In the repository this is studies/agi-alpha-useful-work-v2/.
2. Choose a fresh writable output path; existing evidence is never overwritten.
3. If the complete companion includes both development wheel directories, run:

   python publication/replay_first_delivery.py --out /tmp/agialpha-first-delivery-replay --offline

   For the source-only public draft, omit --offline. This downloads only the declared
   public distribution wheels, validates their exact preserved official SHA256 hashes,
   and installs from those local files with --no-index --require-hashes. There are no
   model, customer, blockchain, paid-service or application-activation requests.

The script creates new plans with absolute input paths at the current location, records
both original and relocated plan hashes, and changes no package version or input hash.
It recreates the ten-package environments, checks the original FastAPI bridge, runs
the unchanged original component definitions and all 61 cases with the actual
15-second timeout in each environment, then runs the separate verifier. Expect at
least 30 seconds of deliberate timeout observation plus setup. Its replay.json and
per-command receipts preserve costs, bindings, status and failures. Replaying this
development mission is not a new customer job or fresh confirmation.

Expected result: PRESERVED_WITHIN_COMPONENT_CONTRACT, PASS=61, INCOMPLETE=0,
BEHAVIOR_MISMATCH=0 on both sides. This is not full application or release approval.
The entire native application lock remains unchanged pending broader qualification.

The original execution argv and hashes remain in evidence/*execution.json. This
corrected edition changes reporting/replay guidance only; its decision and behavioral
evidence are byte-identical to ../first-delivery/. See correction-receipt.json.
"""
    (corrected / "reproduce.txt").write_text(replay)
    changes, diff = [], []
    for name in ("READ-ME.md", "reproduce.txt"):
        before, after = (original / name).read_bytes(), (corrected / name).read_bytes()
        changes.append({"path": name, "before_sha256": sha(before), "after_sha256": sha(after)})
        diff.extend(difflib.unified_diff(before.decode().splitlines(True), after.decode().splitlines(True),
                                        fromfile="first-delivery/" + name, tofile="first-delivery-corrected/" + name))
    patch = ROOT / "publication/first-delivery-correction.diff"
    patch.write_text("".join(diff))
    manifest = {"files": [{"path": str(path.relative_to(corrected)), "sha256": sha(path.read_bytes()),
                            "bytes": path.stat().st_size}
                           for path in sorted(corrected.rglob("*"))
                           if path.is_file() and path.name != "artifact-manifest.json"]}
    write_json(corrected / "artifact-manifest.json", manifest)
    correction = {"schema": "first-delivery-report-correction/v1", "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  "original_directory": "results/development/first-delivery", "original_files": original_identities,
                  "changed_content_files": changes, "behavioral_evidence_changed": False, "decision_changed": False,
                  "method_or_evaluator_changed": False, "mission_count_increment": 0,
                  "reason": "Use observed native-profile wording; replace incomplete replay prose with an exact relocation-aware command.",
                  "original_assembly_receipt_preserved": True,
                  "original_assembly_receipt_scope": "Describes the original manual packet, not this correction",
                  "corrected_artifact_manifest_sha256": sha((corrected / "artifact-manifest.json").read_bytes()),
                  "correction_diff_sha256": sha(patch.read_bytes()), "script_sha256": sha(Path(__file__).read_bytes()),
                  "wall_seconds": time.perf_counter() - wall, "process_cpu_seconds": time.process_time() - cpu,
                  "money_usd": None, "inference_tokens": None,
                  "outer_manifest_required": "Public handoff index binds the inner manifest, original assembly receipt and this correction receipt."}
    write_json(corrected / "correction-receipt.json", correction)
    for path, expected in original_identities.items():
        if sha((original / path).read_bytes()) != expected:
            raise ValueError("ORIGINAL_PACKET_CHANGED")
    with (ROOT / "metering/source_audit.jsonl").open("a") as output:
        output.write(json.dumps({"event": "first_delivery_corrected_edition_created", **correction}) + "\n")
    print(json.dumps({"corrected": str(corrected), "files": len(manifest["files"]) + 2,
                      "decision_sha256": sha((corrected / "decision.json").read_bytes()),
                      "correction_receipt_sha256": sha((corrected / "correction-receipt.json").read_bytes()),
                      "projected_wheel_metadata_files": len(wheel_rows)}))


if __name__ == "__main__":
    main()
