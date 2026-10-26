# SPDX-License-Identifier: Apache-2.0
"""Complete bounded source assessment; production and financial authority absent."""
from __future__ import annotations

import argparse
from collections import Counter
import difflib
import hashlib
import json
from pathlib import Path
import sys
import time
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "native"))
sys.path.insert(0, str(ROOT / "deps" / "site"))
from alpha_factory_v1.core.runtime.successor.transformation_source_audit import Meter, SourcePackage, reference_report
import conventional
import dossier
from validate_dossier import validate_dossier


def encoded(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def module_name(path: str) -> str:
    return path.removeprefix("src/").removesuffix(".py").replace("/", ".").removesuffix(".__init__")


def source_tree(directory: Path, prefix: str = "") -> dict[str, str]:
    if directory.is_symlink() or not directory.is_dir():
        raise ValueError("Source snapshot must be a regular directory")
    result = {}
    for file in sorted(directory.rglob("*.py")):
        if file.is_symlink() or not file.is_file():
            raise ValueError("Source symlink or nonregular input")
        name = prefix + file.relative_to(directory).as_posix()
        if "__pycache__" in file.parts:
            continue
        if file.stat().st_size > dossier.MAX_BYTES:
            raise ValueError("SOURCE_FILE_TOO_LARGE")
        result[name] = file.read_bytes().decode("utf-8")
    if len(result) > 250 or sum(len(x.encode()) for x in result.values()) > 15_000_000:
        raise ValueError("SOURCE_PACKAGE_TOO_LARGE")
    return result


def native_inventory(source: str, path: str, repository: str, commit: str) -> dict[str, Any]:
    if not source:
        return {"status": "absent", "path": path, "report": None, "logical_units": 0}
    raw = source.encode()
    try:
        file = {"path": path, "source": source, "git_blob": hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest(), "sha256": sha(raw)}
        package = SourcePackage.model_validate({"repository": repository, "commit": commit, "root": path.split("/")[0], "files": [file]})
        meter = Meter(100_000_000)
        report = reference_report(package, meter)
        return {"status": "accepted-scoped-inventory", "path": path, "report": report, "logical_units": meter.used, "trace": dict(meter.trace)}
    except (ValueError, SyntaxError, RecursionError) as exc:
        return {"status": "native-policy-refusal", "path": path, "report": None, "logical_units": None,
                "error": type(exc).__name__ + ": " + str(exc)[:1800]}


def assess(before: dict[str, str], after: dict[str, str], *, repository: str, before_ref: str, after_ref: str,
           consumer_files: list[dict[str, str]], arm: str, cache_dir: Path | None = None,
           run_native: bool = True) -> dict[str, Any]:
    started, cpu = time.perf_counter_ns(), time.process_time_ns()
    if arm not in {"incumbent", "retained", "conventional"}:
        raise ValueError("UNKNOWN_ARM")
    paths = sorted(before.keys() | after.keys())
    changed = [p for p in paths if before.get(p, "") != after.get(p, "")]
    manifest = [{"path": p, "before_sha256": sha(before[p].encode()) if p in before else None,
                 "after_sha256": sha(after[p].encode()) if p in after else None,
                 "changed": p in changed} for p in paths]
    identity = sha(encoded({"repository": repository, "before": before_ref, "after": after_ref, "files": manifest,
                            "consumers": [{"path": x["path"], "sha256": sha(x["source"].encode())} for x in consumer_files]}))
    if not changed:
        return {"schema": "upgrade-assessment/v1", "mission_digest": identity, "status": "NO_OP", "arm": arm,
                "changed_modules": 0, "manifest": manifest, "new_customer_jobs": 0,
                "meter": {"cpu_ns": time.process_time_ns() - cpu, "wall_ns": time.perf_counter_ns() - started}}
    native, reports, validation, diffs = [], [], [], []
    store = dossier.SnapshotStore(cache_dir) if arm == "retained" and cache_dir is not None else None
    for path in changed:
        old, new = before.get(path, ""), after.get(path, "")
        diffs.append({"path": path, "patch": "".join(difflib.unified_diff(old.splitlines(True), new.splitlines(True), fromfile="before/" + path, tofile="after/" + path))})
        if run_native:
            native.append({"path": path, "before": native_inventory(old, path, repository, before_ref),
                           "after": native_inventory(new, path, repository, after_ref)})
        if arm == "incumbent":
            continue
        if arm == "retained":
            report = dossier.compare_facts(store.get(old), store.get(new), module_name(path)) if store else dossier.compare_sources(old, new, module_name(path))
        else:
            report = conventional.compare_sources(old, new, module_name(path), use_cache=cache_dir is not None)
        reports.append({"path": path, **report})
        validation.append({"path": path, **validate_dossier(old, new, module_name(path), report)})
    if arm == "incumbent":
        consumers = {"status": "not-computed-by-existing-native-inventory", "potential_breaks": [],
                     "reason": "Existing static source inventory and ordinary diffs retained; no fictitious call-compatibility assertion is substituted."}
    else:
        from consumer import assess_consumers
        consumers = assess_consumers(consumer_files, before, after, reports)
    count = Counter(row["status"] for report in reports for row in report["functions"])
    valid = all(v["accepted"] for v in validation) if validation else None
    common = {"schema": "upgrade-assessment/v1", "mission_digest": identity, "arm": arm,
              "status": "INVENTORY_ONLY" if arm == "incumbent" else "ASSESSMENT_READY" if valid else "ASSESSMENT_REQUIRES_CORRECTION",
              "repository": repository, "before_ref": before_ref, "after_ref": after_ref,
              "changed_modules": len(changed), "unchanged_modules": len(paths) - len(changed),
              "manifest": manifest, "native_inventory": native, "diffs": diffs, "reports": reports,
              "independent_validation": validation, "consumer_assessment": consumers,
              "summary": {"functions": dict(sorted(count.items())), "independent_report_valid": valid,
                          "native_source_refusals": sum(item[side]["status"] == "native-policy-refusal" for item in native for side in ["before", "after"]),
                          "runtime_model_calls": 0, "production_approved": False, "actual_paid_customer_jobs": 0},
              "limits": ["Local source assessment, not a release authorization or performed upgrade.",
                         "Captured declarations and consumer scope only; unresolved imports, dynamic calls, methods and behavior need follow-up.",
                         "Native inventory refusals are preserved; local compatibility output does not override native admission."]}
    common["meter"] = {"cpu_ns": time.process_time_ns() - cpu, "wall_ns": time.perf_counter_ns() - started,
                       "input_bytes": sum(len(v.encode()) for v in before.values()) + sum(len(v.encode()) for v in after.values()),
                       "consumer_bytes": sum(len(x["source"].encode()) for x in consumer_files),
                       "runtime_model_calls": 0, "network_requests": 0,
                       "candidate_cache": {k: getattr(store, k) for k in ["hits", "misses", "bytes_read", "bytes_written"]} if store else None,
                       "conventional_cache": conventional.cache_info() if arm == "conventional" else None}
    return common


def load_mission(mission_id: str) -> tuple[dict[str, Any], dict[str, str], dict[str, str], list[dict[str, str]]]:
    registry = json.loads((ROOT / "data" / "missions.json").read_text())
    if mission_id not in registry["missions"]:
        raise ValueError("UNREGISTERED_MISSION")
    item = registry["missions"][mission_id]
    def load_snapshot(name: str) -> dict[str, str]:
        path = (ROOT / item[name]).resolve()
        if not path.is_relative_to(ROOT / "data"):
            raise ValueError("SOURCE_PATH_ESCAPE")
        result = source_tree(path)
        expected = item.get(name + "_inventory_sha256")
        inventory = {k: sha(v.encode()) for k, v in sorted(result.items())}
        if expected and expected != sha(encoded(inventory)):
            raise ValueError("SOURCE_INVENTORY_IDENTITY")
        return result
    consumers = []
    for relative in item["consumers"]:
        directory = (ROOT / relative).resolve()
        if not directory.is_relative_to(ROOT / "data"):
            raise ValueError("CONSUMER_PATH_ESCAPE")
        consumers.extend({"path": relative + "/" + name, "source": value} for name, value in source_tree(directory).items())
    expected = item.get("consumer_inventory_sha256")
    if expected and expected != sha(encoded({x["path"]: sha(x["source"].encode()) for x in consumers})):
        raise ValueError("CONSUMER_INVENTORY_IDENTITY")
    return item, load_snapshot("before_dir"), load_snapshot("after_dir"), consumers


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mission", required=True)
    parser.add_argument("--arm", choices=["incumbent", "retained", "conventional"], default="retained")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--cache", type=Path)
    args = parser.parse_args()
    item, before, after, consumers = load_mission(args.mission)
    report = assess(before, after, repository=item["repository"], before_ref=item["before_ref"], after_ref=item["after_ref"],
                    consumer_files=consumers, arm=args.arm, cache_dir=args.cache)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(encoded(report) + b"\n")
    print(json.dumps({"mission": args.mission, "status": report["status"], "output": str(args.out), "sha256": sha(args.out.read_bytes()),
                      "meter": report["meter"], "summary": report.get("summary")}))


if __name__ == "__main__":
    main()
