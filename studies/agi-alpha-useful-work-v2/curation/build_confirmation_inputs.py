# SPDX-License-Identifier: Apache-2.0
"""Derive fixed historical jobs and environment plans after an explicit freeze.

This creates metadata only. It never fetches a package or runs a mission, and
never overwrites the existing development registry.
"""
from __future__ import annotations

import argparse
import copy
import datetime
import hashlib
import json
from pathlib import Path
import time

ROOT = Path(__file__).resolve().parents[1]
SELECTION_SHA256 = "db83024274acf14b05b21e39cd35af4d52c3d71869e21d15bde4c0610956b55a"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--freeze", type=Path, required=True)
    parser.add_argument("--expected-freeze-sha256", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    start, cpu = time.perf_counter(), time.process_time()
    if sha(args.freeze) != args.expected_freeze_sha256:
        raise ValueError("FREEZE_IDENTITY")
    selection_path = ROOT / "discovery/confirmation-metadata-v1.json"
    if sha(selection_path) != SELECTION_SHA256:
        raise ValueError("PRESPECIFIED_SELECTION_IDENTITY")
    selected = json.loads(selection_path.read_text())
    if selected["primary_mission_count"] != 6 or selected["wheel_or_source_body_downloads"] != 0:
        raise ValueError("SELECTION_SCOPE")
    out = args.out.resolve()
    if not out.is_relative_to(ROOT) or out.exists():
        raise ValueError("FRESH_STUDY_LOCAL_OUTPUT_REQUIRED")
    out.mkdir(parents=True)
    original_plan = ROOT / "data/development-baseline-bridge-plan.json"
    baseline = json.loads(original_plan.read_text())
    development = json.loads((ROOT / "protocol/jobs/native-refresh-development.json").read_text())
    registry_path = ROOT / "protocol/mission-registry.json"
    registry = json.loads(registry_path.read_text())
    if registry.get("schema") != "alpha-component-registry/v1":
        raise ValueError("REGISTRY_SCHEMA")
    registry = copy.deepcopy(registry)
    environments, jobs = {}, []
    for mission in selected["missions"]:
        package = mission["cluster"]
        job = {"schema": "alpha-component-job/v1", "mission_id": mission["id"], "phase": "confirmation",
               "trigger": mission["trigger"], "sampling_role": mission["role"],
               "adjacency": mission["adjacency"], "selection_sha256": SELECTION_SHA256,
               "contract": copy.deepcopy(development["contract"]),
               "consumer": copy.deepcopy(development["consumer"])}
        for side in ("before", "after"):
            version = mission[side + "_version"]
            record = selected["version_records"][package + "==" + version]
            environment_id = package + "-" + version.replace(".", "-")
            plan_path = out / "plans" / (environment_id + ".json")
            if environment_id not in environments:
                plan = copy.deepcopy(baseline)
                plan["environment_id"] = "historical-confirmation-" + environment_id
                plan["phase"] = "confirmation"
                plan["pins"][package] = version
                changed = {package}
                if package == "pydantic":
                    plan["pins"]["pydantic-core"] = record["pydantic_core"]
                    changed.add("pydantic-core")
                plan["unchanged_native_packages"] = [name for name in plan["pins"] if name not in changed]
                plan["native_lock"] = str(ROOT / "discovery/requirements/requirements-agent.lock")
                plan["incoming_constraint_metadata"] = [
                    str(ROOT / "discovery/release-metadata/fastapi-0.141.1.json"),
                    str(ROOT / "discovery/release-metadata/pydantic-settings-2.15.0.json"),
                ]
                plan["consumer_contract"] = str(ROOT / development["contract"]["path"])
                plan["confirmation_freeze_sha256"] = args.expected_freeze_sha256
                plan["primary_confirmation_acquisition"] = True
                plan["scope"] = "Fixed representative historical component environment; no customer order or app activation"
                plan["selection_sha256"] = SELECTION_SHA256
                plan["selected_primary_package"] = package
                plan["selected_primary_wheel"] = {"filename": record["wheel"]["filename"],
                                                   "sha256": record["wheel"]["digests"]["sha256"]}
                write_json(plan_path, plan)
                environments[environment_id] = {
                    "id": environment_id, "plan": str(plan_path.relative_to(ROOT)), "plan_sha256": sha(plan_path),
                    "environment": "data/confirmation-environments/" + environment_id,
                    "expected_versions": plan["pins"], "selected_primary_wheel": plan["selected_primary_wheel"],
                    "metadata_reuse_required": "discovery/release-metadata",
                    "body_acquired": False,
                }
            item = environments[environment_id]
            job[side] = {"environment": item["environment"], "expected_versions": item["expected_versions"]}
        path = out / "jobs" / (mission["id"] + ".json")
        if mission["id"] in registry["missions"]:
            raise ValueError("EXISTING_MISSION_ID_MUST_NOT_BE_REPLACED")
        write_json(path, job)
        registry["missions"][mission["id"]] = {"path": str(path.relative_to(ROOT)), "sha256": sha(path)}
        jobs.append({"id": mission["id"], **registry["missions"][mission["id"]]})
    write_json(out / "mission-registry.json", registry)
    result = {"schema": "fixed-confirmation-input-plan/v1", "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "freeze_sha256": args.expected_freeze_sha256, "selection_sha256": SELECTION_SHA256,
              "builder_sha256": sha(Path(__file__)), "baseline_plan_sha256": sha(original_plan),
              "existing_registry_sha256": sha(registry_path), "existing_registry_unchanged": True,
              "proposed_registry": str((out / "mission-registry.json").relative_to(ROOT)),
              "proposed_registry_sha256": sha(out / "mission-registry.json"),
              "environment_count": len(environments), "environments": list(environments.values()), "jobs": jobs,
              "source_or_wheel_body_downloads": 0, "outcomes_observed": 0,
              "acquisition_rule": "Use preserved primary metadata and check acquired primary wheel against selected_primary_wheel; retain failed setup without replacing the selected job.",
              "wall_seconds": time.perf_counter() - start, "process_cpu_seconds": time.process_time() - cpu,
              "inference_tokens": None, "inference_usd": None}
    write_json(out / "construction.json", result)
    with (ROOT / "metering/source_audit.jsonl").open("a") as output:
        output.write(json.dumps({"event": "confirmation_metadata_inputs_constructed", **result}) + "\n")
    print(json.dumps({"environments": len(environments), "missions": len(jobs),
                      "proposed_registry_sha256": result["proposed_registry_sha256"], "body_downloads": 0}))


if __name__ == "__main__":
    main()
