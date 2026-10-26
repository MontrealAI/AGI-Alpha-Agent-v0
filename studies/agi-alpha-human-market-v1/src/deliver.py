# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import resource
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from cleaner import FIELDS, clean, write_csv

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT.parents[1]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def unique(items: list[tuple[str, Any]]) -> dict[str, Any]:
    obj: dict[str, Any] = {}
    for key, value in items:
        if key in obj:
            raise ValueError("DUPLICATE_JSON_KEY")
        obj[key] = value
    return obj


def source_identity() -> str:
    paths = [*sorted((ROOT / "src").glob("*.py")), *sorted((ROOT / "src").glob("*.mjs"))]
    native_root = WORKSPACE / "upstream/alpha"
    manifest = json.loads((native_root / "alpha_factory_v1/core/runtime/successor/workbench_sources.json").read_text())
    for name, expected in manifest["sources"].items():
        path = native_root / name
        if sha(path) != expected:
            raise ValueError("UPSTREAM_SOURCE_DRIFT:" + name)
        paths.append(path)
    paths.append(native_root / "docs/assets/transformational-intelligence/source-understanding.mjs")
    values = {str(p.relative_to(WORKSPACE)): sha(p) for p in paths}
    return hashlib.sha256(json.dumps(values, sort_keys=True).encode()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--job", type=Path, required=True)
    parser.add_argument("--generation", type=int, choices=[0, 1, 2], required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--revision-of", default=None)
    args = parser.parse_args()
    if args.out.exists():
        raise SystemExit("OUTPUT_EXISTS; use a new path to preserve earlier evidence")
    args.out.mkdir(parents=True)
    start, cpu_start = time.perf_counter(), time.process_time()
    before = resource.getrusage(resource.RUSAGE_CHILDREN)
    outcome: dict[str, Any] = {"generation": args.generation, "status": "FAILED", "actual_collections_usd": 0,
                               "actual_complete_cost": None, "human_attention_minutes": None, "model_calls": 0,
                               "revision_of": args.revision_of}
    try:
        code_hash = source_identity()
        job = json.loads(args.job.read_text(encoding="utf-8"), object_pairs_hook=unique)
        outcome["job_id"] = job.get("id")
        source_name = job.get("source", {}).get("file", "")
        if not source_name or Path(source_name).name != source_name or source_name in {".", ".."}:
            raise ValueError("SOURCE_PATH")
        original = args.job.parent / source_name
        if original.is_symlink() or not original.is_file():
            raise ValueError("SOURCE_NOT_REGULAR")
        if original.stat().st_size > 10 * 1024 * 1024:
            raise ValueError("SOURCE_SIZE_OR_IDENTITY")
        raw = original.read_bytes()
        revision_digest = None
        if args.revision_of:
            parent = Path(args.revision_of)
            previous = json.loads(parent.read_text(encoding="utf-8"), object_pairs_hook=unique)
            if previous.get("schema") != "csv-delivery/v1" or previous.get("status") != "COMPLETED":
                raise ValueError("INVALID_REVISION_PARENT")
            if previous.get("source", {}).get("sha256") != hashlib.sha256(raw).hexdigest():
                raise ValueError("REVISION_SOURCE_MISMATCH")
            revision_digest = sha(parent)
            outcome["revision_of"] = revision_digest
        result = clean(job, raw, args.generation)
        (args.out / "original.csv").write_bytes(raw)
        dump(args.out / "job.json", job)
        dump(args.out / "revision-job.json", {**job, "source": {**job["source"], "file": "original.csv"}})
        dump(args.out / "semantic.json", result)
        write_csv(args.out / "clean.csv", result["clean"], FIELDS + ["source_row"])
        write_csv(args.out / "exceptions.csv", result["quarantine"], ["source_row", "reasons"])
        write_csv(args.out / "duplicates.csv", result["duplicates"], ["source_row", "kept_source_row"])
        write_csv(args.out / "superseded.csv", result["superseded"], ["source_row", "kept_source_row"])
        write_csv(args.out / "disposition.csv", result["disposition"], ["source_row", "status"])
        counts = {key: len(result[key]) for key in ["clean", "quarantine", "duplicates", "superseded"]}
        counts["input"] = len(result["disposition"])
        dump(args.out / "quality.json", {"schema": "csv-quality/v1", "counts": counts,
                                        "source": job["source"], "rules": job["rules"],
                                        "missing_values_invented": 0, "every_source_record_accounted_for": True,
                                        "formula_execution": False, "external_customer_acceptance": "NOT_OBSERVED"})
        (args.out / "READ_ME.txt").write_text(
            "CSV cleanup and reconciliation\n\nImport clean.csv using explicit text types for identifiers.\n"
            "Use exceptions.csv to resolve missing, invalid or conflicting source records.\n"
            "Use disposition.csv to trace every original record. Original bytes are retained.\n"
            "No missing value was guessed. Formula-like cells are inert CSV text; do not execute them.\n"
            "For one scoped revision, change explicit rules in revision-job.json and rerun deliver.py with a new\n"
            "output directory and --revision-of pointing to this delivery-manifest.json. Retain both deliveries.\n"
            "Synthetic study output: factual acceptance and actual commercial activity are separate.\n",
            encoding="utf-8")
        files = [{"name": p.name, "bytes": p.stat().st_size, "sha256": sha(p)}
                 for p in sorted(args.out.iterdir()) if p.is_file()]
        delivery = {"schema": "csv-delivery/v1", "status": "COMPLETED", "job_id": job["id"],
                    "generation": args.generation, "data_class": job["data_class"], "source": job["source"],
                    "counts": counts, "files": files, "source_code_sha256": code_hash,
                    "revision_of": revision_digest}
        dump(args.out / "delivery-manifest.json", delivery)
        node = os.environ.get("CODEX_PRIMARY_RUNTIME_NODE") or shutil.which("node")
        if not node:
            raise RuntimeError("NODE_UNAVAILABLE")
        proc = subprocess.run([node, str(ROOT / "src/package.mjs"), str((args.out / "delivery-manifest.json").resolve())],
                              capture_output=True, text=True, timeout=60, check=False)
        (args.out / "package.stdout").write_text(proc.stdout)
        (args.out / "package.stderr").write_text(proc.stderr)
        if proc.returncode:
            raise RuntimeError("WORKBENCH_FAILED:" + str(proc.returncode))
        pack = json.loads((args.out / "workbench-pack.json").read_text())
        if pack["evaluation"] != {"scope": "PUBLIC_LOCAL_EXECUTION", "independentProof": False,
                                   "admission": "HOLD", "authority": [], "settlement": "NOT_CONNECTED"}:
            raise RuntimeError("AUTHORITY_DRIFT")
        outcome.update(status="COMPLETED", counts=counts, source_sha256=job["source"]["sha256"],
                       source_code_sha256=code_hash, semantic_sha256=sha(args.out / "semantic.json"),
                       pack_sha256=sha(args.out / "workbench-pack.json"),
                       output_bytes=sum(p.stat().st_size for p in args.out.iterdir() if p.is_file()))
    except (ValueError, UnicodeError, csv.Error, KeyError, TypeError, OSError, RuntimeError, subprocess.TimeoutExpired) as exc:
        outcome["reason"] = str(exc)
        outcome["status"] = "REFUSED" if isinstance(exc, (ValueError, UnicodeError, csv.Error)) else "FAILED"
    after = resource.getrusage(resource.RUSAGE_CHILDREN)
    outcome.update(elapsed_seconds=time.perf_counter() - start,
                   cpu_seconds=time.process_time() - cpu_start + after.ru_utime + after.ru_stime - before.ru_utime - before.ru_stime,
                   max_rss_kib=max(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss, after.ru_maxrss))
    dump(args.out / "summary.json", outcome)
    print(json.dumps(outcome, sort_keys=True))


if __name__ == "__main__":
    main()
