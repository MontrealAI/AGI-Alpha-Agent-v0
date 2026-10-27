# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import random
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .audit import Packet, State, audit, verify_assessment
from .reference import assignment_bit, relational_audit

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
PARENT_FILES = {
    "src/mpc_worker.py": "914a4bd3d9e6a35805f75615ca61327b6d28a42cc13e1a253b1e49ec7a3ffd28",
    "src/study.py": "0f9d081121c25af00b3a166592f935e3c2e7bfe3ef63b7aad104e3b238a461a7",
    "integration/query_authority.py": "47165b989895fd1b1cc8b098a98872c70c50dbff3704776cf8bb529d7c30c378",
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


def load(path: Path) -> Any:
    return json.loads(path.read_text())


def verify_parent(root: Path) -> dict[str, str]:
    frozen = load(root / "evidence/technical_freeze.json")["files"]
    frozen = {**frozen, **PARENT_FILES}
    for name, expected in frozen.items():
        if sha(root / name) != expected:
            raise ValueError("research source changed: " + name)
    return dict(frozen)


def source_bindings(root: Path) -> dict[str, str]:
    paths = sorted(HERE.glob("*.py")) + [HERE / "protocol.json"]
    names = {str(path.relative_to(REPO)): sha(path) for path in paths}
    names.update({"research/" + name: value for name, value in verify_parent(root).items()})
    for name in ("protocol.py", "trust.py", "flywheel_costs.py"):
        path = REPO / "alpha_factory_v1/core/runtime/successor" / name
        names[str(path.relative_to(REPO))] = sha(path)
    names["alpha_factory_v1/core/runtime/store.py"] = sha(REPO / "alpha_factory_v1/core/runtime/store.py")
    names["research/src/economics.py"] = sha(root / "src/economics.py")
    names["research/config/commercial_protocol.json"] = sha(root / "config/commercial_protocol.json")
    names["research/results/economics_freeze.json"] = sha(root / "results/economics_freeze.json")
    return names


def cases(seed: int, count: int) -> list[dict[str, Any]]:
    rng = random.Random(seed)
    names = load(HERE / "protocol.json")["families"]
    result = []
    for index in range(count):
        family = names[index % len(names)]
        permutation = rng.sample(range(6), 6)
        if family == "one-property":
            masks = [[rng.randrange(3)]]
        elif family == "two-properties":
            masks = [sorted(rng.sample(range(3), 2))]
        elif family == "side-information":
            masks = [[0, 1]]
        elif family == "composed-properties":
            masks = [[bit] for bit in rng.sample(range(3), 3)]
        else:
            masks = [[0, 1, 2]]
        result.append(
            {
                "case_id": f"{seed}-{index:03d}",
                "family": family,
                "permutation": permutation,
                "masks": masks,
                "actual_secret": rng.randrange(8),
                "outage_scenario": rng.randrange(21),
                "max_claims": 2,
            }
        )
    return result


def append_world(
    owners: list[dict[str, Any]], case: dict[str, Any], secret: int, mask: list[int], scenario_count: int
) -> None:
    selected = {case["permutation"][bit] for bit in mask}
    private_eligibility = [0] * 6
    for bit in range(3):
        private_eligibility[case["permutation"][bit]] = (secret >> bit) & 1
    public_eligibility = [int(demand not in selected) for demand in range(6)]
    for party in range(3):
        world = {
            "eligibility": [list(private_eligibility if party == 0 else public_eligibility) for _ in range(2)],
            "availability": [[1] * scenario_count for _ in range(2)],
            "retention": [[0] * scenario_count for _ in range(2)],
        }
        if case["family"] == "correlated-outage" and party == 0:
            for row in range(2):
                world["availability"][row][case["outage_scenario"]] = 0
        owners[party]["worlds"].append(world)


def build_inputs(
    selected: list[dict[str, Any]], destination: Path, *, all_secrets: bool, scope: str
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    owners: list[dict[str, Any]] = [
        {
            "schema": "reserve-mpc-v1",
            "party_id": party,
            "nonce": hashlib.sha256(f"PUBLIC:{scope}:{party}".encode()).hexdigest(),
            "worlds": [],
        }
        for party in range(3)
    ]
    groups = [group for size in (1, 2) for group in itertools.combinations(range(6), size)]
    scenarios = [{"id": "demand-" + "-".join(map(str, group)), "demand_clients": list(group)} for group in groups]
    mapping = []
    for case in selected:
        for secret in range(8) if all_secrets else [case["actual_secret"]]:
            for column, mask in enumerate(case["masks"]):
                append_world(owners, case, secret, mask, len(groups))
                mapping.append({"case_id": case["case_id"], "secret": secret, "column": column})
    commitments = []
    for party, owner in enumerate(owners):
        path = destination / "private" / f"party_{party}.json"
        save(path, owner)
        commitments.append(sha(path))
    manifest = {
        "schema": "reserve-mpc-v1",
        "parties": 3,
        "assets_per_party": 2,
        "demands": 6,
        "max_claims": 2,
        "scope_id": scope,
        "scenario_epoch": scope,
        "world_count": len(mapping),
        "scenarios": scenarios,
        "input_commitments": commitments,
    }
    if not 0 < len(mapping) <= 512:
        raise ValueError("experiment world budget exceeded or empty execution requested")
    save(destination / "manifest.json", manifest)
    save(destination / "mapping.json", mapping)
    return manifest, owners, mapping


def packets(
    selected: list[dict[str, Any]], mapping: list[dict[str, Any]], bits: list[int], worker: str
) -> list[Packet]:
    lookup: dict[tuple[str, int], list[tuple[int, int]]] = {}
    for row, bit in zip(mapping, bits, strict=True):
        lookup.setdefault((row["case_id"], row["secret"]), []).append((row["column"], bit))
    result = []
    for case in selected:
        rows: list[dict[str, Any]] = []
        for secret in range(8):
            outputs = [value for _, value in sorted(lookup[(case["case_id"], secret)])]
            view = f"known-bit-2:{secret >> 2}" if case["family"] == "side-information" else "public-fixed-assets"
            rows.append(
                {"state_id": f"secret-{secret}", "secret_value": secret, "observer_view": view, "outputs": outputs}
            )
        result.append(
            Packet(
                opportunity_id="research-reserve-feasibility",
                mission_id=case["case_id"],
                worker_sha256=worker,
                minimum_alternatives=2,
                required_state_ids=[row["state_id"] for row in rows],
                states=[State.model_validate(row) for row in rows],
            )
        )
    return result


def execute(root: Path, inputs: Path, output: Path, journal: Path, port: int) -> dict[str, Any]:
    verify_parent(root)
    command = [
        sys.executable,
        "-B",
        str(HERE / "mpc_bridge.py"),
        "--research-root",
        str(root),
        "--inputs",
        str(inputs),
        "--output",
        str(output),
        "--journal",
        str(journal),
        "--port",
        str(port),
    ]
    started = time.perf_counter()
    process = subprocess.run(command, capture_output=True, text=True, timeout=330)
    save(
        output / "bridge-attempt.json",
        {
            "command": command,
            "exit_code": process.returncode,
            "stdout": process.stdout,
            "stderr": process.stderr,
            "wall_seconds": time.perf_counter() - started,
        },
    )
    if process.returncode:
        raise RuntimeError("MPC bridge failed; attempt preserved: " + str(output))
    verify_parent(root)
    return dict(load(output / "answer.json"))


def experiment(root: Path, output: Path, stage: str, port: int) -> dict[str, Any]:
    policy = load(HERE / "protocol.json")
    if stage == "confirmation" and source_bindings(root) != load(HERE / "FREEZE.json")["bindings"]:
        raise ValueError("source changed after confirmation freeze")
    selected = cases(policy[stage + "_seed"], policy[stage + "_cases"])
    save(output / "declared-cases.json", selected)
    manifest, owners, mapping = build_inputs(
        selected, output / "characterization-inputs", all_secrets=True, scope=stage + "-characterization"
    )
    reference = [assignment_bit(owners, manifest["scenarios"], index) for index in range(len(mapping))]
    planned = packets(selected, mapping, reference, sha(root / "src/mpc_worker.py"))
    assessments = [audit(packet) for packet in planned]
    for packet, assessment in zip(planned, assessments, strict=True):
        expected, minimum = relational_audit(packet.model_dump()["states"], 2)
        assert expected == (assessment["decision"] == "eligible-for-separate-authorization")
        assert minimum == assessment["minimum_alternatives"]
    save(output / "preflight-packets.json", [packet.model_dump(mode="json") for packet in planned])
    save(output / "preflight-assessments.json", assessments)
    execution = execute(
        root,
        output / "characterization-inputs",
        output / "characterization-execution",
        output.parent / (stage + "-private-characterization-journal"),
        port,
    )
    observed = execution["answer"]["all_scenarios_sufficient"]
    assert observed == reference, "unchanged MPC and separate assignment reference disagree"
    eligible = []
    outcomes = []
    for case, packet, assessment in zip(selected, planned, assessments, strict=True):
        verify_assessment(packet, assessment)
        admitted = assessment["decision"] == "eligible-for-separate-authorization"
        if admitted:
            eligible.append(case)
        outcomes.append(
            {
                "case_id": case["case_id"],
                "family": case["family"],
                "preflight": assessment["decision"],
                "state": "pending-execution" if admitted else "unexecuted-preflight-refusal",
                "accepted_delivery": False,
                "minimum_alternatives": assessment["minimum_alternatives"],
                "nonconstant": assessment["nonconstant"],
            }
        )
    delivery = None
    if eligible:
        delivery_manifest, delivery_owners, delivery_mapping = build_inputs(
            eligible, output / "delivery-inputs", all_secrets=False, scope=stage + "-guarded-delivery"
        )
        delivery = execute(
            root,
            output / "delivery-inputs",
            output / "delivery-execution",
            output.parent / (stage + "-private-delivery-journal"),
            port + 10,
        )
        delivery_reference = [
            assignment_bit(delivery_owners, delivery_manifest["scenarios"], index)
            for index in range(len(delivery_mapping))
        ]
        assert delivery["answer"]["all_scenarios_sufficient"] == delivery_reference
        for outcome in outcomes:
            if outcome["state"] == "pending-execution":
                outcome.update(state="synthetic-executed-reference-checked", accepted_delivery=True)
    save(output / "mission-outcomes.json", outcomes)
    result = {
        "evidence": "Actual three-process local execution over public synthetic fixtures; no private customer data.",
        "stage": stage,
        "cases": len(selected),
        "unchanged_mpc_reference_agreements": len(reference),
        "positive_bits": sum(reference),
        "negative_bits": len(reference) - sum(reference),
        "eligible_cases": len(eligible),
        "refused_unexecuted_cases": len(selected) - len(eligible),
        "informative_eligible_cases": sum(
            item["nonconstant"] for item in assessments if item["decision"] == "eligible-for-separate-authorization"
        ),
        "unrestricted_exact_answer_obligation_satisfied_for_all_cases": len(eligible) == len(selected),
        "denial_is_actual_secret_independent": True,
        "ordinary_same_information_reference": "tie",
        "worker_sha256": sha(root / "src/mpc_worker.py"),
        "sources": source_bindings(root),
        "characterization_wall_seconds": execution["wall_seconds"],
        "guarded_delivery_wall_seconds": delivery["wall_seconds"] if delivery else 0,
        "characterization_stream_bytes": execution["total_stream_bytes_sent"],
        "guarded_delivery_stream_bytes": delivery["total_stream_bytes_sent"] if delivery else 0,
        "actual_model_api_calls": 0,
        "actual_customer_collections_usd": 0,
        "actual_complete_cost_usd": None,
    }
    save(output / "SUMMARY.json", result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=["development", "freeze", "confirmation"])
    parser.add_argument("--research-root", type=Path, default=REPO / "studies/agi-alpha-opportunity-construction-v1")
    parser.add_argument("--output", type=Path, default=HERE / "evidence")
    parser.add_argument("--port", type=int, default=24110)
    args = parser.parse_args()
    if args.stage == "freeze":
        if (HERE / "FREEZE.json").exists():
            raise ValueError("preserve the previous freeze; use a new explicitly versioned protocol for a correction")
        save(
            HERE / "FREEZE.json",
            {
                "frozen_at_utc": datetime.now(timezone.utc).isoformat(),
                "bindings": source_bindings(args.research_root),
                "policy": load(HERE / "protocol.json"),
                "freshness": "Authored synthetic held-out protocol, not a protected external evaluation.",
            },
        )
        print("frozen")
    else:
        if args.output.exists():
            raise ValueError("preserve every previous attempt; choose a fresh output directory")
        result = experiment(args.research_root, args.output, args.stage, args.port)
        print(json.dumps({key: value for key, value in result.items() if key != "sources"}, sort_keys=True))


if __name__ == "__main__":
    main()
