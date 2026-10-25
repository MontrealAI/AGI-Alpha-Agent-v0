# SPDX-License-Identifier: Apache-2.0
import json, time, os
from pathlib import Path
import sys

if os.environ.get("STRATEGY_INSTALLED_ACCEPTANCE") == "1":
    from strategy_succession_engineering.serve import create, ROOT
else:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from serve import create, ROOT
from fastapi.testclient import TestClient
from alpha_factory_v1.core.runtime.store import Journal


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
        "repair": {"observed_at": 9, "capacity": [1 if 14 <= i < 19 else 2 for i in range(32)], "deadline": 28},
        "construction": {"enabled": True},
    }


def test_real_public_runtime_fixed_worker_journey(tmp_path):
    journal = Journal.initialize(tmp_path / "operator")
    token = (journal.root / "api.token").read_text().strip()
    client = TestClient(create(journal.root, ROOT / "ENGINEERING_MANIFEST.json", native=True))
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
                "runtime": "actual public Alpha1.42.0 wheel; inherited dependency environment",
                "source_hash": plan["source_hash"],
                "outcome_hash": completed["outcome_hash"],
                "wall_seconds": time.perf_counter() - started,
                "native_calls": costs["native_calls"],
                "charged_native_solve_allowance_seconds": costs["native_solve_seconds"],
                "phase_makespans": [p["result"]["makespan"] for p in phases],
                "costs": costs,
                "human_minutes": None,
                "monetary_cost": None,
                "public_engineering_release": False,
            },
            indent=2,
        )
        + "\n"
    )
