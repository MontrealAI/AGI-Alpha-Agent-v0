# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from pathlib import Path
from typing import Any

from ..claim_probe.protected_exchange import ProtectedExchange
from ..structural_transfer.contracts import bounded, digest, exact_keys
from . import programs

KEY = b"invention-automation-SIM-v1".ljust(32, b"0")
CONTRACT = "agialpha/invention-component-fault-contract/v1"
MONEY = {"price", "screening", "measurement", "production", "required_value", "buyer_cash", "observed_value"}


def validate_case(case: dict[str, Any]) -> None:
    bounded(case)
    exact_keys(case, MONEY | {"id", "measurement_valid", "settlement", "deadline", "scope"})
    if case["scope"] != "software-fault-fixture" or case["settlement"] not in {"clear", "withhold", "interrupt"}:
        raise ValueError("component scope or settlement tape")
    if not isinstance(case["id"], str) or not case["id"].isalnum() or len(case["id"]) > 32:
        raise ValueError("bounded case identity")
    if any(type(case[k]) is not int or not 0 <= case[k] <= 10**12 for k in MONEY | {"deadline"}):
        raise ValueError("integer simulated-microUSD and tick quantities required")
    if case["price"] == 0 or type(case["measurement_valid"]) is not bool:
        raise ValueError("positive price and exact observation validity")


def task_frame(case: dict[str, Any]) -> dict[str, Any]:
    return {k: case[k] for k in ["id", "scope", "required_value"]}


def execute(
    program: dict[str, Any],
    cases: list[dict[str, Any]],
    path: Path,
    *,
    opening: int,
    working: int = 0,
    max_operations: int = 256,
) -> dict[str, Any]:
    programs.validate(program)
    if not 1 <= len(cases) <= 16 or len({c["id"] for c in cases}) != len(cases):
        raise ValueError("bounded unique immutable cohort")
    for case in cases:
        validate_case(case)
    if type(max_operations) is not int or not 1 <= max_operations <= 1024:
        raise ValueError("operation cap")
    if path.exists():
        raise ValueError("new evidence database required; never overwrite an attempt")
    observations = {c["id"]: c for c in cases}

    def validate_task(task: dict[str, Any]) -> None:
        if task != task_frame(observations[task["id"]]):
            raise ValueError("task frame mismatch")

    def check(task: dict[str, Any], artifact: dict[str, Any]) -> dict[str, Any]:
        case = observations[task["id"]]
        wanted = {
            "case": case["id"],
            "measurement_hash": digest({"value": case["observed_value"], "valid": case["measurement_valid"]}),
            "scope": "software-fault-fixture",
        }
        accepted = artifact == wanted and case["measurement_valid"] and case["observed_value"] >= case["required_value"]
        return {"accepted": accepted, "decisive": True}

    ex = ProtectedExchange(
        path, key=KEY, contract=CONTRACT, validate=validate_task, check=check, opening=opening, working=working
    )
    trace: list[dict[str, Any]] = []
    outcomes = []
    operations = 0
    clock = 0
    try:
        for case in cases:
            ident = case["id"]
            ex.wallet(ident, case["buyer_cash"])
            deadline = clock + case["deadline"]
            ex.offer(ident, ident, case["price"], "nonrecourse-simulated", task_frame(case), deadline)
            outcome = "UNRESOLVED"
            measured, produced, screened = False, False, False
            step = clock
            for node in program["steps"]:
                if operations >= max_operations:
                    outcome = "BUDGET_STOP"
                    break
                clock += 1
                step = clock
                operations += 1
                action = node["op"]
                before = ex.snapshot()
                state = ex.order(ident)["state"]
                frame = {
                    "available": before["available"],
                    "price": case["price"],
                    "production": case["production"],
                    "required_value": case["required_value"],
                }
                if measured:
                    frame.update(measured_value=case["observed_value"], measurement_valid=case["measurement_valid"])
                entry = {
                    "case": ident,
                    "tick": step,
                    "action": action,
                    "before": before,
                    "measured": measured,
                    "produced": produced,
                }
                trace.append(entry)
                try:
                    if action == "guard":
                        if programs.expression(node["test"], frame)[1] is not True:
                            entry["refusal"] = node["constraint"]
                            outcome = "DEFERRED"
                            break
                    elif action == "screen":
                        ex.cost(ident + "-screen", case["screening"])
                        screened = True
                        if case["buyer_cash"] < case["price"]:
                            outcome = "DECLINED"
                            break
                    elif action == "measure":
                        ex.cost(ident + "-measurement", case["measurement"])
                        measured = True
                    elif action == "fund":
                        row = ex.order(ident)
                        terms = {
                            k: row[k] for k in ["id", "buyer", "price", "rail", "task_hash", "contract", "deadline"]
                        }
                        ex.event(
                            ident, ident + "-consent", "consent", {"buyer": ident, "termsHash": digest(terms)}, step
                        )
                        ex.event(ident, ident + "-fund", "fund", ex.provider.issue(ex.order(ident), "funded"), step)
                    elif action == "produce":
                        ex.cost(ident + "-production", case["production"])
                        produced = True
                    elif action == "inspect":
                        if not measured or not produced:
                            raise ValueError("production and observation required")
                        artifact = {
                            "case": ident,
                            "measurement_hash": digest(
                                {"value": case["observed_value"], "valid": case["measurement_valid"]}
                            ),
                            "scope": "software-fault-fixture",
                        }
                        ex.event(ident, ident + "-inspect", "prepare", artifact, step)
                    elif action == "settle":
                        if case["settlement"] == "interrupt":
                            outcome = "INTERRUPTED"
                            break
                        if case["settlement"] == "withhold":
                            outcome = "NONPAYMENT"
                            break
                        ex.event(
                            ident, ident + "-settle", "release", ex.provider.issue(ex.order(ident), "cleared"), step
                        )
                        ex.download(ident, ident)
                        outcome = "ACCEPTED_COMPONENT"
                except (ValueError, PermissionError) as error:
                    entry["refusal"] = str(error)
                    outcome = "REFUSED"
                    break
                finally:
                    entry["after"] = ex.snapshot()
                    entry["state_before"] = state
                    entry["state_after"] = ex.order(ident)["state"]
            state = ex.order(ident)["state"]
            if state in {"funded", "verified"} and outcome != "INTERRUPTED":
                clock += 1
                ex.event(ident, ident + "-remedy", "refund", {}, clock)
                trace.append({"case": ident, "action": "refund", "tick": clock, "after": ex.snapshot()})
            outcomes.append(
                {
                    "case": ident,
                    "outcome": outcome,
                    "state": ex.order(ident)["state"],
                    "screening_incurred": screened,
                    "measured": measured,
                    "produced": produced,
                }
            )
        summary = ex.snapshot()
        return {
            "schema": "agialpha/invention-component-result/v1",
            "scope": "SIM software fault tests only",
            "program_hash": digest(program),
            "cohort_hash": digest(cases),
            "opening": opening,
            "working": working,
            "operations": operations,
            "outcomes": outcomes,
            "trace": trace,
            "summary": summary,
            "native_route": "NATIVE ROUTE BLOCKED",
            "confirmed": False,
        }
    finally:
        ex.close()


def failures(cases: list[dict[str, Any]], result: dict[str, Any]) -> list[dict[str, Any]]:
    by_id = {c["id"]: c for c in cases}
    found = []
    for event in result["trace"]:
        case = by_id[event["case"]]
        if (
            event["action"] == "produce"
            and not event["measured"]
            and (not case["measurement_valid"] or case["observed_value"] < case["required_value"])
        ):
            found.append(
                {
                    "critic": "technical",
                    "family": "measurement-before-production",
                    "case": case["id"],
                    "loss_driver": "production spent before decisive measurement",
                    "waste": case["production"],
                }
            )
        if event["action"] == "produce" and event["after"]["payables"] > event["before"]["payables"]:
            found.append(
                {
                    "critic": "economic",
                    "family": "collateral-and-production",
                    "case": case["id"],
                    "loss_driver": "escrow protection consumed equity headroom",
                    "waste": case["production"],
                }
            )
    return found


def validate_criticism(
    program: dict[str, Any], cases: list[dict[str, Any]], witness: dict[str, Any], path: Path, *, opening: int
) -> dict[str, Any]:
    result = execute(program, cases, path, opening=opening)
    if witness not in failures(cases, result):
        raise ValueError("criticism is not reproduced; no correction promoted")
    return {
        "family": witness["family"],
        "validated": True,
        "candidate_hash": digest(program),
        "witness_hash": digest(witness),
        "reproduction_hash": digest(result),
        "scope": "development-only",
    }
