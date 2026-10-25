# SPDX-License-Identifier: Apache-2.0
import json, time, os
import base64
import hashlib
from pathlib import Path
import sys

if os.environ.get("STRATEGY_INSTALLED_ACCEPTANCE") == "1":
    from strategy_succession_engineering.serve import create, ROOT
else:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from serve import create, ROOT
from fastapi.testclient import TestClient
from alpha_factory_v1.core.runtime.store import Journal
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey


def sample():
    return {
        "initial": {
            "schema": "release-plan/v1",
            "id": "public-release-plan",
            "kind": "plan",
            "public_or_synthetic": "synthetic",
            "planning_only": True,
            "jobs": [
                {"id": "J1", "duration": 2, "crew": 1, "deps": []},
                {"id": "J2", "duration": 4, "crew": 2, "deps": ["J1"]},
                {"id": "J3", "duration": 3, "crew": 1, "deps": ["J1"]},
                {"id": "J4", "duration": 3, "crew": 2, "deps": ["J2"]},
                {"id": "J5", "duration": 2, "crew": 1, "deps": ["J3"]},
                {"id": "J6", "duration": 1, "crew": 1, "deps": ["J4", "J5"]},
            ],
            "capacity": [2] * 32,
            "deadline": 24,
        },
        "changes": {"durations": {"J2": 6}, "deadline": 28},
        "repair": {"observed_at": 9, "capacity": [1 if 12 <= i < 15 else 2 for i in range(32)], "deadline": 28},
        "construction": {"enabled": True},
    }


def test_real_public_runtime_fixed_worker_journey(tmp_path):
    journal = Journal.initialize(tmp_path / "operator")
    token = (journal.root / "api.token").read_text().strip()
    app = create(journal.root, ROOT / "ENGINEERING_MANIFEST.json", native=True)
    child_environment = app.state.public_runtime["child_environment"]
    assert child_environment["observation"]["invocation_context_matches"] is True
    assert child_environment["observation"]["prefix_context_matches"] is True
    client = TestClient(app)
    headers = {"Authorization": "Bearer " + token}
    assert client.get("/api/strategy-executor/status").status_code == 401
    assert (
        client.post(
            "/api/strategy-executor/prepare", json={}, headers={**headers, "Origin": "https://untrusted.example"}
        ).status_code
        == 403
    )
    plan_response = client.post(
        "/api/strategy-executor/prepare",
        json={"method": "run-journey", "input": sample(), "request_id": "real-integration"},
        headers=headers,
    )
    assert plan_response.status_code == 200, plan_response.text
    plan = plan_response.json()
    assert plan["caps"]["improvement_work"] == 3_000_000 and plan["caps"]["service_work"] == 500_000
    binding = {"plan_id": plan["plan_id"], "plan_digest": plan["plan_digest"]}
    assert (
        client.post(
            "/api/strategy-executor/approve", json={**binding, "plan_digest": "0" * 64}, headers=headers
        ).status_code
        == 409
    )
    assert client.post("/api/strategy-executor/approve", json=binding, headers=headers).status_code == 200
    started = time.perf_counter()
    response = client.post("/api/strategy-executor/run", json=binding, headers=headers)
    assert response.status_code == 200, response.text
    completed = response.json()
    assert completed["state"] == "completed", completed
    assert completed["outcome"]["verified"] is True
    phases = completed["outcome"]["result"]["phases"]
    assert len(phases) == 3 and all(p["verified"] and p["qualified"] for p in phases)
    assert phases[0]["task"]["jobs"] != phases[1]["task"]["jobs"]
    assert phases[2]["baseline_source"]["receipt_hash"] == phases[1]["receipt_hash"]
    # Independently check that the actual changed plan needs a repair under
    # the new calendar, and that the fixed producer preserved its commitments.
    before = {row["id"]: row for row in phases[1]["result"]["schedule"]}
    repaired_task = phases[2]["task"]
    jobs = {row["id"]: row for row in repaired_task["jobs"]}
    baseline_load = [
        sum(jobs[jid]["crew"] for jid, row in before.items() if row["start"] <= slot < row["end"])
        for slot in range(len(repaired_task["capacity"]))
    ]
    invalid_baseline_slots = [slot for slot, load in enumerate(baseline_load) if load > repaired_task["capacity"][slot]]
    assert invalid_baseline_slots, "The example must require a real calendar repair"
    after = {row["id"]: row for row in phases[2]["result"]["schedule"]}
    assert all(after[jid]["start"] == start for jid, start in repaired_task["locked"].items())
    assert phases[2]["result"]["movement"] > 0
    assert phases[2]["result"]["movement"] == sum(abs(after[jid]["start"] - before[jid]["start"]) for jid in jobs)
    assert all(
        sum(jobs[jid]["crew"] for jid, row in after.items() if row["start"] <= slot < row["end"]) <= capacity
        for slot, capacity in enumerate(repaired_task["capacity"])
    )
    assert len(completed["partial_receipts"]) == 3
    assert [p["receipt_hash"] for p in completed["partial_receipts"]] == [p["receipt_hash"] for p in phases]
    costs = completed["outcome"]["costs"]
    assert 0 < costs["service_work"] <= plan["caps"]["service_work"]
    assert 0 < costs["improvement_work"] <= plan["caps"]["improvement_work"]
    assert costs["native_calls"] == 6 and costs["native_solve_seconds"] == 12
    repeat = client.post("/api/strategy-executor/run", json=binding, headers=headers)
    assert repeat.status_code == 200 and repeat.json()["outcome_hash"] == completed["outcome_hash"]
    status = client.get("/api/strategy-executor/status", headers=headers).json()
    assert status["spent"]["native_calls"] == 6 and not status["active_after_browser_close"]
    exported = client.get("/api/strategy-executor/export/" + plan["plan_id"], headers=headers).json()
    assert token not in json.dumps(exported) and str(journal.root) not in json.dumps(exported)
    assert journal.verify()["valid"] is True
    output = Path(os.environ.get("STRATEGY_EVIDENCE_DIR", Path(__file__).resolve().parents[1] / "acceptance-public"))
    output.mkdir(exist_ok=True)
    (output / "integrated-journey.json").write_text(json.dumps(completed, indent=2) + "\n")
    (output / "integrated-summary.json").write_text(
        json.dumps(
            {
                "schema": "strategy-engineering-acceptance/v1",
                "runtime": "actual public Alpha1.42.0 wheel; exact parent/child dependency profile checked; installation cleanliness is separately attested",
                "child_environment": child_environment,
                "source_hash": plan["source_hash"],
                "outcome_hash": completed["outcome_hash"],
                "wall_seconds": time.perf_counter() - started,
                "native_calls": costs["native_calls"],
                "charged_native_solve_allowance_seconds": costs["native_solve_seconds"],
                "phase_makespans": [p["result"]["makespan"] for p in phases],
                "unchanged_baseline_invalid_calendar_slots": invalid_baseline_slots,
                "committed_prefix_preserved": True,
                "costs": costs,
                "human_minutes": None,
                "monetary_cost": None,
                "public_engineering_release": False,
            },
            indent=2,
        )
        + "\n"
    )

    # Additive API control: same input and approved envelope, construction off.
    # The original construction-enabled acceptance and its evidence remain above.
    control_started = time.perf_counter()
    service_input = sample()
    service_input["construction"]["enabled"] = False
    comparison_input = json.loads(json.dumps(service_input))
    comparison_input["construction"]["enabled"] = True
    assert comparison_input == plan["input"]
    before_service = client.get("/api/strategy-executor/status", headers=headers).json()
    service_request = {"method": "run-journey", "input": service_input, "request_id": "real-service-only-control"}
    prepared = client.post("/api/strategy-executor/prepare", json=service_request, headers=headers)
    assert prepared.status_code == 200, prepared.text
    service_plan = prepared.json()
    assert service_plan["state"] == "prepared" and service_plan["input"] == service_input
    assert service_plan["source_hash"] == plan["source_hash"]
    assert service_plan["caps"] == plan["caps"], "This control changes no allowance or installed policy"
    service_binding = {"plan_id": service_plan["plan_id"], "plan_digest": service_plan["plan_digest"]}
    assert client.post("/api/strategy-executor/run", json=service_binding, headers=headers).status_code == 409
    assert (
        client.post(
            "/api/strategy-executor/approve", json={**service_binding, "plan_digest": "0" * 64}, headers=headers
        ).status_code
        == 409
    )
    approved = client.post("/api/strategy-executor/approve", json=service_binding, headers=headers)
    assert approved.status_code == 200 and approved.json()["input"] == service_input
    api_wall_start, api_cpu_start = time.perf_counter(), time.process_time()
    service_response = client.post("/api/strategy-executor/run", json=service_binding, headers=headers)
    api_wall_seconds, api_process_cpu_seconds = (
        time.perf_counter() - api_wall_start,
        time.process_time() - api_cpu_start,
    )
    assert service_response.status_code == 200, service_response.text
    service_completed = service_response.json()
    # Retain the actual returned record before assertions so failed qualification
    # does not erase a completed-but-inferior or otherwise rejected outcome.
    (output / "service-only-journey.json").write_text(json.dumps(service_completed, indent=2) + "\n")
    verification_started, verification_cpu_started = time.perf_counter(), time.process_time()

    def independent_digest(value):
        encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()
        return hashlib.sha256(encoded).hexdigest()

    assert service_completed["state"] == "completed" and service_completed["input"] == service_input
    service_outcome = service_completed["outcome"]
    assert service_outcome["verified"] is True
    assert service_completed["source_hash"] == service_outcome["source_hash"] == plan["source_hash"]
    assert independent_digest(service_outcome) == service_completed["outcome_hash"]
    service_result, service_costs = service_outcome["result"], service_outcome["costs"]
    assert service_result["capabilities"] == []
    assert service_result["inheritance"]["diagnostics"] == []
    assert service_result["inheritance"]["lineage"] == []
    assert service_result["inheritance"]["parent_benefit"] == "NOT_ESTABLISHED"
    assert service_result["repair_usefulness"]["candidate_trial"] is None
    assert service_result["repair_usefulness"]["candidate_frozen_digest"] is None
    assert service_result["repair_usefulness"]["training_qualification"] is None
    assert service_result["repair_usefulness"]["consequence"] == "DEFER_NO_FROZEN_REPAIR"
    assert service_result["repair_usefulness"]["economic_decision"] == "HOLD_FULL_COST_UNKNOWN"
    assert service_result["repair_usefulness"]["production_promotion"] is False
    assert service_costs["improvement_work"] == service_result["accounting"]["improvement_total"] == 0
    assert service_result["accounting"]["improvement_ledger"] == []
    assert 0 < service_costs["service_work"] <= service_plan["caps"]["service_work"]
    assert service_result["accounting"]["service_total"] == service_costs["service_work"]
    assert service_costs["native_calls"] == 6 and service_costs["native_solve_seconds"] == 12
    assert service_costs["unknown_costs"], "Unknown lifecycle/human/money costs must remain explicit"
    assert all(event["costs"]["improvement_work"] == 0 for event in service_result["events"])
    service_phases = service_result["phases"]
    assert len(service_phases) == len(service_completed["partial_receipts"]) == 3
    assert service_phases[0]["task"] == service_input["initial"]
    changed_expected = json.loads(json.dumps(service_input["initial"]))
    changed_expected["id"] += "-changed"
    changed_expected["jobs"][1]["duration"] = 6
    changed_expected["deadline"] = 28
    assert service_phases[1]["task"] == changed_expected
    for index, phase in enumerate(service_phases):
        task, delivered = phase["task"], phase["result"]
        assert phase["verified"] is True and phase["qualified"] is True
        assert delivered["schema"] == "release-plan-result/v1" and delivered["task_id"] == task["id"]
        assert phase["receipt"]["source_hash"] == service_plan["source_hash"]
        assert phase["receipt"]["proof"] == phase["receipt"]["authority"] == []
        assert independent_digest(phase["receipt"]) == phase["receipt_hash"]
        partial = service_completed["partial_receipts"][index]
        assert partial["phase_index"] == index
        assert partial["receipt_hash"] == phase["receipt_hash"]
        assert partial["task"] == task and partial["result"] == delivered
        assert partial["selectedmethod"] == phase["selected_method"]
        specifications = {job["id"]: job for job in task["jobs"]}
        rows = {row["id"]: row for row in delivered["schedule"]}
        assert len(rows) == len(delivered["schedule"]) == len(specifications) and rows.keys() == specifications.keys()
        for job_id, row in rows.items():
            spec = specifications[job_id]
            assert type(row["start"]) is int and type(row["end"]) is int
            assert row["start"] >= task.get("release", {}).get(job_id, 0)
            assert row["end"] == row["start"] + spec["duration"] <= len(task["capacity"])
            assert all(rows[dependency]["end"] <= row["start"] for dependency in spec["deps"])
        assert delivered["makespan"] == max(row["end"] for row in rows.values()) <= task["deadline"]
        assert all(
            sum(specifications[job_id]["crew"] for job_id, row in rows.items() if row["start"] <= slot < row["end"])
            <= capacity
            for slot, capacity in enumerate(task["capacity"])
        )
        native_methods = {"native-repair", "native-makespan"} if index == 2 else {"native-deadline", "native-makespan"}
        attempts = phase["attempts"]
        assert {attempt["method"] for attempt in attempts} == {"ordinary-portfolio", *native_methods}
        assert all(
            attempt["valid"] and attempt["qualified"] for attempt in attempts if attempt["method"] in native_methods
        )

        def quality(result):
            return (result["movement"], result["makespan"]) if index == 2 else (result["makespan"], result["movement"])

        assert quality(delivered) == min(quality(attempt["result"]) for attempt in attempts if attempt.get("qualified"))
    service_before = {row["id"]: row for row in service_phases[1]["result"]["schedule"]}
    service_repair = service_phases[2]["task"]
    service_after = {row["id"]: row for row in service_phases[2]["result"]["schedule"]}
    observed = service_input["repair"]["observed_at"]
    expected_locks = {job_id: row["start"] for job_id, row in service_before.items() if row["start"] < observed}
    assert service_repair["baseline"] == {job_id: row["start"] for job_id, row in service_before.items()}
    assert service_repair["locked"] == expected_locks
    assert service_repair["release"] == {
        job_id: (
            service_phases[1]["task"].get("release", {}).get(job_id, 0)
            if job_id in expected_locks
            else max(service_phases[1]["task"].get("release", {}).get(job_id, 0), observed)
        )
        for job_id in service_before
    }
    assert service_repair["capacity"] == service_input["repair"]["capacity"]
    assert service_repair["capacity"][:observed] == service_phases[1]["task"]["capacity"][:observed]
    assert service_phases[2]["baseline_source"]["receipt_hash"] == service_phases[1]["receipt_hash"]
    assert service_phases[2]["baseline_source"]["verified"] is True
    assert all(service_after[job_id]["start"] == start for job_id, start in expected_locks.items())
    service_conflicts = [
        slot
        for slot, capacity in enumerate(service_repair["capacity"])
        if sum(
            job["crew"]
            for job in service_repair["jobs"]
            if service_before[job["id"]]["start"] <= slot < service_before[job["id"]]["end"]
        )
        > capacity
    ]
    assert service_conflicts
    assert (
        service_phases[2]["result"]["movement"]
        == sum(abs(service_after[job_id]["start"] - row["start"]) for job_id, row in service_before.items())
        > 0
    )
    after_service = client.get("/api/strategy-executor/status", headers=headers).json()
    assert after_service["request_count"] == before_service["request_count"] + 1
    assert after_service["active_after_browser_close"] is False
    assert all(value == 0 for value in after_service["reserved"].values())
    for counter in ("service_work", "improvement_work", "native_calls", "native_solve_seconds"):
        assert after_service["spent"][counter] == before_service["spent"][counter] + service_costs[counter]
        assert service_completed["observed"][counter] == service_costs[counter]
    assert after_service["spent"]["native_calls"] == 12 and after_service["spent"]["native_solve_seconds"] == 24
    duplicate = client.post("/api/strategy-executor/run", json=service_binding, headers=headers)
    assert duplicate.status_code == 200 and duplicate.json()["outcome_hash"] == service_completed["outcome_hash"]
    reprepare = client.post("/api/strategy-executor/prepare", json=service_request, headers=headers)
    assert reprepare.status_code == 200 and reprepare.json()["outcome_hash"] == service_completed["outcome_hash"]
    assert (
        client.post(
            "/api/strategy-executor/prepare", json={**service_request, "input": comparison_input}, headers=headers
        ).status_code
        == 409
    )
    deduplicated = client.get("/api/strategy-executor/status", headers=headers).json()
    assert deduplicated["spent"] == after_service["spent"] and deduplicated["reserved"] == after_service["reserved"]
    assert deduplicated["request_count"] == after_service["request_count"]
    service_export = client.get("/api/strategy-executor/export/" + service_plan["plan_id"], headers=headers).json()
    assert service_export["body"]["plan"] == service_completed
    assert service_export["body"]["source_hash"] == service_plan["source_hash"]
    assert service_export["body"]["journal_identity"] == journal.identity
    assert service_export["public_key"] == exported["public_key"]
    assert service_export["body"]["production_authority"] is False
    assert independent_digest(service_export["body"]) == service_export["sha256"]
    Ed25519PublicKey.from_public_bytes(bytes.fromhex(service_export["public_key"])).verify(
        base64.b64decode(service_export["signature"], validate=True), bytes.fromhex(service_export["sha256"])
    )
    assert token not in json.dumps(service_export) and str(journal.root) not in json.dumps(service_export)
    journal_observation = journal.verify()
    assert journal_observation["valid"] is True
    (output / "service-only-export.json").write_text(json.dumps(service_export, indent=2) + "\n")
    service_summary = {
        "schema": "strategy-engineering-service-only-acceptance/v1",
        "interface": "authenticated API test; no browser execution in this control",
        "construction_enabled": False,
        "same_input_except_construction": True,
        "comparison_outcome_hash": completed["outcome_hash"],
        "comparison_input_sha256": independent_digest(plan["input"]),
        "input_sha256": independent_digest(service_input),
        "source_hash": service_plan["source_hash"],
        "plan_id": service_plan["plan_id"],
        "outcome_hash": service_completed["outcome_hash"],
        "caps_unchanged": True,
        "costs": service_costs,
        "charged_native_solve_allowance_seconds": service_costs["native_solve_seconds"],
        "api_call_wall_seconds": api_wall_seconds,
        "api_test_process_cpu_seconds": api_process_cpu_seconds,
        "independent_verification_wall_seconds": time.perf_counter() - verification_started,
        "independent_verification_test_process_cpu_seconds": time.process_time() - verification_cpu_started,
        "control_window_wall_seconds": time.perf_counter() - control_started,
        "worker_runtime_telemetry": service_result["runtime_telemetry"],
        "python_call_observations": [
            {
                key: row[key]
                for key in (
                    "role",
                    "status",
                    "signal",
                    "error",
                    "process_wall_seconds",
                    "startup",
                    "call_wall_seconds",
                    "call_cpu_seconds",
                )
                if key in row
            }
            for row in service_result["native_telemetry"]
        ],
        "timing_scope": "Observed API/test-process, Node and Python-call components have different boundaries and may overlap. Test-process CPU excludes child CPU. These are not full host, human or monetary costs; do not sum overlapping timings or confuse charged native allowance with measured time.",
        "phase_makespans": [phase["result"]["makespan"] for phase in service_phases],
        "phase_receipts": [phase["receipt_hash"] for phase in service_phases],
        "unchanged_baseline_invalid_calendar_slots": service_conflicts,
        "committed_prefix_preserved": True,
        "no_constructed_assets": True,
        "deduplicated_without_new_charges": True,
        "journal_verified": journal_observation["valid"],
        "signed_export_sha256": hashlib.sha256((output / "service-only-export.json").read_bytes()).hexdigest(),
        "human_minutes": None,
        "monetary_cost": None,
        "comparison_scope": "Sequential matched-input API engineering control, with only construction.enabled changed. Not protected science, randomized causal speedup, full-cost superiority, profit or evidence of autonomous recurrence.",
    }
    (output / "service-only-summary.json").write_text(json.dumps(service_summary, indent=2) + "\n")
