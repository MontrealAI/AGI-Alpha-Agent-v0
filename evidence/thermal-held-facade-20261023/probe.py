# SPDX-License-Identifier: Apache-2.0
"""Bounded thermal-specific probe against unchanged, locally composed public commits."""
from __future__ import annotations

import argparse
from copy import deepcopy
import datetime as dt
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import sqlite3
import subprocess
import sys
import traceback

ROOT = Path(__file__).resolve().parent
CHECKOUT = ROOT / "checkout"
sys.path.insert(0, str(CHECKOUT))

from alpha_factory_v1.core.runtime import ascension as legacy
from alpha_factory_v1.core.runtime.store import Conflict, Journal
from alpha_factory_v1.core.runtime.successor import enterprise, enterprise_ascension, workbench

THERMAL = "f1ac7df95d802b12bf194b3fa7be6f4c30a62ef4"
HELD = "6bb361d522d80dc900cc2a480014531c6a44b66e"
TREE = "abc12184debbdd7f2c8ecf9928cc5482dc7b09f8"
RESULTS = ROOT / "artifacts"


def write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x") as stream:
        json.dump(value, stream, sort_keys=True, indent=2)
        stream.write("\n")


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=CHECKOUT, text=True).strip()


def record(home: Path, ident: str) -> dict:
    return workbench.handle(argparse.Namespace(home=home, work_command="show", run_id=ident))


def handler(home: Path, ident: str, command: str, **kwargs: object) -> dict:
    return enterprise.handle(argparse.Namespace(home=home, enterprise_id=ident, enterprise_command=command, **kwargs))


def thermal_config(family: str) -> dict:
    config = enterprise.new("thermal-witness", "Thermal held-facade probe: " + family)
    inputs = config["work"]["inputs"]
    inputs["family"] = family
    if family == "heat-capacity":
        inputs["extension"] = {
            "sourceId": "sample-acceptance-fixture",
            "kind": "INDEPENDENT_SIMULATED",
            "temperatureRiseUK": {"low": 20_000_000, "estimate": 20_000_000, "high": 20_000_000},
            "lossEnergyMicroJ": {"low": "600000000", "estimate": "600000000", "high": "600000000"},
            "containerEnergyMicroJ": {"low": "80000000", "estimate": "80000000", "high": "80000000"},
        }
    elif family == "heat-recovery":
        inputs["extension"] = {
            "sourceId": "energy-acceptance-fixture",
            "kind": "INDEPENDENT_SIMULATED",
            "inputEnergyMicroJ": {"low": "5000000000", "estimate": "5000000000", "high": "5000000000"},
            "storageReleaseMicroJ": {"low": "180000000", "estimate": "180000000", "high": "180000000"},
            "minimumRecoveryPpm": 700_000,
        }
    return config


def assert_result(value: dict, family: str) -> dict:
    assert value["state"] == "review" and value["attempts"] == 1
    pack = value["result"]
    result, evidence = pack["result"], pack["result"]["evidence"]
    assert pack["spec"]["family"] == "thermal-witness"
    assert result["decision"] == "CONDITIONAL_BOUNDS_MET"
    assert evidence["family"] == family and evidence["completion"] == "COMPLETE"
    assert all(evidence["quantity"][key] == "3680000000" for key in ("low", "estimate", "high"))
    if family == "delivered-heat":
        assert evidence["downstream"] is None
    else:
        expected = "150/1" if family == "heat-capacity" else "7/10"
        assert all(evidence["downstream"][key] == expected for key in ("low", "estimate", "high"))
    assert evidence["simulation"] is True and evidence["physicalValidity"] == "NOT_ESTABLISHED"
    assert evidence["independentReview"] is False and result["summary"]["acceptedCapability"] is False
    assert value["authority"] == [] and value["settlement"] == "NOT_CONNECTED"
    assert pack["evaluation"]["independentProof"] is False and pack["evaluation"]["admission"] == "HOLD"
    return {"decision": result["decision"], "quantity": evidence["quantity"], "downstream": evidence["downstream"]}


def reload_case(path: Path) -> None:
    request = json.loads((path / "reload-request.json").read_text())
    home, ident = Path(request["home"]), request["enterpriseId"]
    journal = Journal(home)
    before = journal.verify()
    visible = enterprise.show(home, ident)
    reused = enterprise.operate(home, ident)
    after = Journal(home).verify()
    assert before == request["checkpoint"] == after
    assert visible == reused == request["expected"]
    assert reused["attempts"] == 1 and reused["state"] == "accepted"
    assert reused["authority"] == [] and reused["independent_qualification"] is False
    print(json.dumps({"state": reused["state"], "attempts": reused["attempts"], "checkpoint": after,
                      "resultDigest": reused["result_digest"], "freshProcess": True}, sort_keys=True))


def one_family(family: str) -> tuple[dict, dict, Path]:
    case = RESULTS / family
    case.mkdir(parents=True)
    home = ROOT / "private-homes" / family
    config = thermal_config(family)
    ident = config["enterprise_id"]
    write(case / "configuration.json", config)
    active = enterprise.activate(home, config)
    assert active["state"] == "planned" and active["attempts"] == 0 and active["authority"] == []
    write(case / "activated.json", active)
    operated = enterprise.operate(home, ident)
    observed = record(home, ident)
    result_summary = assert_result(observed, family)
    assert operated["state"] == "review" and operated["result_digest"] == observed["result_digest"]
    write(case / "executed-record.json", observed)
    checkpoint = Journal(home).verify()
    try:
        handler(home, ident, "review", result_digest="0" * 64, decision="accepted", note="Wrong-digest boundary probe")
    except Conflict as error:
        write(case / "wrong-digest-rejection.json", {"type": type(error).__name__, "message": str(error)})
    else:
        raise AssertionError("Wrong digest was accepted")
    assert Journal(home).verify() == checkpoint
    reviewed = handler(home, ident, "review", result_digest=observed["result_digest"], decision="accepted",
                       note="Local operator inspection of the declared simulated fixture; no independent qualification")
    assert reviewed["state"] == "accepted" and reviewed["review"]["independent"] is False
    assert reviewed["authority"] == [] and reviewed["attempts"] == 1
    write(case / "locally-reviewed-record.json", reviewed)
    checkpoint = Journal(home).verify()
    visible = enterprise.show(home, ident)
    write(case / "reload-request.json", {"home": str(home), "enterpriseId": ident, "checkpoint": checkpoint,
                                        "expected": visible})
    argv = [sys.executable, "-I", "-B", str(Path(__file__).resolve()), "reload", str(case)]
    child = subprocess.run(argv, cwd=CHECKOUT, capture_output=True, check=False)
    (case / "reload.stdout").write_bytes(child.stdout)
    (case / "reload.stderr").write_bytes(child.stderr)
    write(case / "reload-command.json", {"argv": argv, "cwd": str(CHECKOUT), "exit": child.returncode})
    assert child.returncode == 0, child.stderr.decode(errors="replace")
    reload_observed = json.loads(child.stdout)
    write(case / "reopened-result.json", reload_observed)
    exported = handler(home, ident, "export", output=case / "export")
    write(case / "export-result.json", exported)
    assert Journal(home).verify() == checkpoint
    return config, {"family": family, "enterpriseId": ident, "state": "accepted", "attempts": 1,
                    "resultDigest": observed["result_digest"], "checkpoint": checkpoint, **result_summary}, home


def successor(parent: dict, home: Path, child_work: dict) -> dict:
    case = RESULTS / "successor"
    parent_id = parent["enterprise_id"]
    parent_before = enterprise.show(home, parent_id)
    child = enterprise.derive(home, parent_id, name="Distinct heat-capacity successor", work=deepcopy(child_work))
    assert child["enterprise_id"] != parent_id and child["work"]["inputs"]["family"] == "heat-capacity"
    assert child["parent"] == {"enterprise_id": parent_id,
                               "configuration_digest": parent_before["configuration_digest"],
                               "result_digest": parent_before["result_digest"]}
    write(case / "configuration.json", child)
    active = enterprise.activate(home, child)
    assert active["state"] == "planned" and active["attempts"] == 0 and active["review"] is None
    assert active["authority"] == [] and active["independent_qualification"] is False
    write(case / "activated.json", active)
    visible = enterprise.operate(home, child["enterprise_id"])
    observed = record(home, child["enterprise_id"])
    result_summary = assert_result(observed, "heat-capacity")
    assert visible["state"] == "review" and visible["review"] is None
    assert enterprise.show(home, parent_id) == parent_before
    write(case / "executed-record.json", observed)
    write(case / "parent-retained.json", parent_before)
    write(case / "journal-checkpoint.json", Journal(home).verify())
    write(case / "export-result.json", handler(home, child["enterprise_id"], "export", output=case / "export"))
    return {"parent": parent_id, "child": child["enterprise_id"], "parentState": "accepted",
            "childState": "review", "inheritedAcceptance": False, "inheritedAuthority": False, **result_summary}


def rejection_boundary(parent: dict, home: Path) -> dict:
    case = RESULTS / "studio-boundary"
    plan = legacy.compile_plan([{"goal": "Evaluate exact thermal bounds",
                                 "successMetric": "Retain conditional numerical bounds and model limits",
                                 "bounty": "10103", "duration": 86400, "priceWeight": 6000}])
    legacy.verify_plan(plan)
    write(case / "compiled-plan.json", plan)
    ident = parent["enterprise_id"]
    before = Journal(home).verify()
    files_before = sorted(str(path.relative_to(home)) for path in home.rglob("*") if path.is_file())
    outcomes = []
    for name, action in (("enterprise.handoff", enterprise.handoff),
                         ("enterprise_ascension.prepare", enterprise_ascension.prepare)):
        try:
            action(home, ident, plan, 0)
        except ValueError as error:
            assert str(error) == "This executor supports only the installed fixed workbench families"
            outcomes.append({"operation": name, "errorType": type(error).__name__, "message": str(error)})
        else:
            raise AssertionError(name + " unexpectedly admitted thermal")
        assert Journal(home).verify() == before
    files_after = sorted(str(path.relative_to(home)) for path in home.rglob("*") if path.is_file())
    assert files_before == files_after
    with sqlite3.connect(f"file:{Journal(home).path}?mode=ro", uri=True) as connection:
        keys = [row[0] for row in connection.execute("SELECT DISTINCT mission FROM events ORDER BY mission")]
        events = [dict(zip(("seq", "mission", "body", "hash", "signature"), row))
                  for row in connection.execute("SELECT * FROM events ORDER BY seq")]
    assert not any("studio" in key.lower() for key in keys)
    write(case / "rejections.json", {"outcomes": outcomes, "before": before, "after": Journal(home).verify(),
                                    "filesUnchanged": True, "journalKeys": keys, "transactionsSent": False})
    write(RESULTS / "delivered-heat" / "public-journal-events.json", events)
    return {"outcomes": outcomes, "journalUnchanged": True, "filesUnchanged": True,
            "studioRecordsCreated": 0, "transactionsSent": False}


def main() -> None:
    if len(sys.argv) == 3 and sys.argv[1] == "reload":
        reload_case(Path(sys.argv[2]))
        return
    assert len(sys.argv) == 1
    assert git("rev-parse", "HEAD") == THERMAL and git("rev-parse", "MERGE_HEAD") == HELD
    assert git("write-tree") == TREE and git("ls-files", "--unmerged") == ""
    assert git("diff", "--name-only") == "", "Tracked worktree edits found before probe"
    assert git("hash-object", "alpha_factory_v1/core/runtime/successor/enterprise.py") == "50e4eded26da75ca039b6f972d0a0b334d951660"
    assert git("hash-object", "alpha_factory_v1/core/runtime/successor/enterprise_ascension.py") == "623a261e7bc95f0f9f2ec7ac35d47e9080967780"
    report = {"schema": "thermal-held-facade-local-composition/v1", "startedAt": dt.datetime.now(dt.timezone.utc).isoformat(),
              "candidate": THERMAL, "heldHead": HELD, "prospectiveTree": TREE,
              "criteriaSha256": hashlib.sha256((ROOT / "criteria.json").read_bytes()).hexdigest(),
              "runnerSha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "python": platform.python_version(), "executable": sys.executable,
              "node": subprocess.check_output(["node", "--version"], text=True).strip(),
              "dependencies": {name: importlib.metadata.version(name)
                               for name in ("pydantic", "cryptography", "eth-hash", "fastapi")},
              "families": [], "status": "RUNNING"}
    try:
        configs, homes = {}, {}
        for family in ("delivered-heat", "heat-capacity", "heat-recovery"):
            config, outcome, home = one_family(family)
            configs[family], homes[family] = config, home
            report["families"].append(outcome)
        report["successor"] = successor(configs["delivered-heat"], homes["delivered-heat"], configs["heat-capacity"]["work"])
        report["studioBoundary"] = rejection_boundary(configs["delivered-heat"], homes["delivered-heat"])
        assert git("write-tree") == TREE and git("diff", "--name-only") == ""
        report["status"] = "PASS_WITH_EXPECTED_STUDIO_REJECTION"
        report["actualWorkExecutions"] = 4
        report["freshProcessReopens"] = 3
        report["qualification"] = {"thermalEnterpriseFacade": "LOCAL_COMPOSITION_EXERCISED",
                                   "thermalAscensionFacade": "BLOCKED_BY_EXISTING_FAMILY_ALLOWLIST",
                                   "independentInstitutionalAcceptance": False, "physicalValidation": False,
                                   "mainnetOrEvmUsed": False, "releaseQualification": False,
                                   "reviewRestrictionCleared": False, "forthcomingRecoveryFixQualified": False}
    except BaseException as error:
        report["status"] = "FAIL"
        report["failure"] = {"type": type(error).__name__, "message": str(error), "traceback": traceback.format_exc()}
        raise
    finally:
        report["finishedAt"] = dt.datetime.now(dt.timezone.utc).isoformat()
        write(ROOT / "result.json", report)
    print(json.dumps({"status": report["status"], "actualWorkExecutions": report["actualWorkExecutions"],
                      "freshProcessReopens": report["freshProcessReopens"], "prospectiveTree": TREE,
                      "result": str(ROOT / "result.json")}, sort_keys=True))


if __name__ == "__main__":
    main()
