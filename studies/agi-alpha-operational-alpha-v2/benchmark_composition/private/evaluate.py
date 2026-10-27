# SPDX-License-Identifier: Apache-2.0
import argparse
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import random
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
SEED = 6102751


def equal(left, right):
    if left != right:
        raise AssertionError(f"{left!r} != {right!r}")


def digest(packet):
    return hashlib.sha256(json.dumps(packet, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def campaign(seed, count=6):
    rng = random.Random(seed)
    packet = dict(version=1, initial_credits={"alpha": 1000, "beta": 1000}, capacity=9,
                  jobs=[], journal_events=[], schedule_commands=[], artifacts=[], settlements=[])
    revisions = {"alpha": 0, "beta": 0, "__usage__": 0}
    spent = {"alpha": 0, "beta": 0}
    previous = {}
    size = 0
    for i in range(count):
        owner = rng.choice(["alpha", "beta"])
        job = f"job-{i}"
        cap = rng.randrange(15, 60)
        actual = rng.randrange(0, cap + 1)
        data = bytes(rng.randrange(256) for _ in range(rng.randrange(0, 50)))
        upload = f"result-{i}"
        packet["jobs"].append(dict(owner=owner, job=job, cap=cap, cost=rng.randrange(1, 10),
                                   deps=[previous[owner]] if owner in previous else [], artifact=upload))
        previous[owner] = job
        reserve = dict(id=f"r-{i}", owner=owner, job=job, kind="reserve", amount=cap)
        settle = dict(id=f"s-{i}", owner=owner, job=job, kind="settle", amount=actual)
        packet["journal_events"].extend([reserve, settle])
        if i % 2:
            packet["journal_events"].append(deepcopy(settle))
        packet["schedule_commands"].extend([
            dict(action="claim", owner=owner, job=job, lease=f"lease-{i}"),
            dict(action="finish", owner=owner, job=job, lease=f"lease-{i}", success=True)])
        packet["artifacts"].append(dict(owner=owner, upload=upload, size=len(data),
                                        digest=hashlib.sha256(data).hexdigest(), state="committed", cells=list(data)))
        size += len(data)
        if actual:
            batch = dict(request=f"settlement:{job}", operations=[dict({"from": owner, "to": "__usage__", "amount": actual})],
                         expected={owner: revisions[owner], "__usage__": revisions["__usage__"]})
            packet["settlements"].append(batch)
            if i % 2:
                packet["settlements"].append(deepcopy(batch))
            revisions[owner] += 1
            revisions["__usage__"] += 1
        spent[owner] += actual
    packet["artifacts"].sort(key=lambda a: (a["owner"], a["upload"]))
    summary = dict(jobs=count, succeeded=count, running_units=0, artifact_bytes=size,
                   wallets={o: dict(available=1000 - spent[o], reserved=0, spent=spent[o]) for o in spent},
                   settled_credits=spent, usage_sink=sum(spent.values()))
    return packet, summary


def assess(module, check):
    def release(packet, expected):
        result = module.audit(packet)
        equal(set(result), {"schema", "decision", "packet_sha256", "reasons", "summary"})
        equal(result, dict(schema="campaign-audit/1", decision="release", packet_sha256=digest(packet),
                           reasons=[], summary=expected))

    def hold(packet):
        result = module.audit(packet)
        equal(set(result), {"schema", "decision", "packet_sha256", "reasons", "summary"})
        equal(result["schema"], "campaign-audit/1")
        equal(result["decision"], "hold")
        equal(result["summary"], {})
        equal(result["packet_sha256"], digest(packet))
        if not isinstance(result["reasons"], list) or not result["reasons"] or not all(
                isinstance(x, str) and x for x in result["reasons"]):
            raise AssertionError("hold needs descriptive reasons")

    for i in range(4):
        def valid(i=i):
            packet, expected = campaign(SEED + i, count=4 + i)
            release(packet, expected)
        check(f"fresh-complete-campaign-{i}", valid)

    def binding():
        packet, expected = campaign(SEED, count=3)
        first = module.audit(packet)
        changed = deepcopy(packet)
        changed["journal_events"].append(deepcopy(changed["journal_events"][-1]))
        second = module.audit(changed)
        equal(first["summary"], second["summary"])
        equal(first["packet_sha256"], digest(packet))
        equal(second["packet_sha256"], digest(changed))
        if first["packet_sha256"] == second["packet_sha256"]:
            raise AssertionError("different evidence bytes not bound")
        reordered = {k: packet[k] for k in reversed(list(packet))}
        release(reordered, expected)
    check("complete-evidence-digest", binding)

    def incomplete():
        packet, _ = campaign(SEED, count=1)
        packet["schedule_commands"] = []
        hold(packet)
        packet["schedule_commands"] = [dict(action="cancel", owner=packet["jobs"][0]["owner"], job="job-0")]
        hold(packet)
    check("completed-execution-required", incomplete)

    def namespace():
        packet, _ = campaign(SEED, count=1)
        owner = packet["artifacts"][0]["owner"]
        packet["artifacts"][0]["owner"] = "beta" if owner == "alpha" else "alpha"
        hold(packet)
    check("artifact-tenant-binding", namespace)

    def committed():
        packet, _ = campaign(SEED, count=1)
        packet["artifacts"][0]["state"] = "active"
        hold(packet)
    check("committed-artifact-evidence-required", committed)

    def swapped():
        packet, _ = campaign(SEED, count=5)
        # Reassign settlement job IDs within a tenant; totals and all component replays still agree.
        by_owner = {}
        for batch in packet["settlements"]:
            by_owner.setdefault(batch["operations"][0]["from"], {})[batch["request"]] = batch
        candidates = next(list(rows.values()) for rows in by_owner.values() if len(rows) >= 2)
        left, right = candidates[:2]
        if left["operations"][0]["amount"] == right["operations"][0]["amount"]:
            raise AssertionError("test fixture lacks differing amounts")
        mapping = {left["request"]: right["request"], right["request"]: left["request"]}
        for batch in packet["settlements"]:
            batch["request"] = mapping.get(batch["request"], batch["request"])
        hold(packet)
    check("per-job-settlement-binding", swapped)

    def component_failures():
        packet, _ = campaign(SEED, count=2)
        bad = deepcopy(packet)
        bad["journal_events"][0]["amount"] = 9999
        hold(bad)
        bad = deepcopy(packet)
        bad["artifacts"][0]["digest"] = "0" * 64
        hold(bad)
        bad = deepcopy(packet)
        bad["settlements"][0]["expected"]["__usage__"] = 99
        hold(bad)
        bad = deepcopy(packet)
        bad["schedule_commands"][0]["owner"] = "unauthorized"
        hold(bad)
    check("all-component-failures-held", component_failures)

    def zero():
        packet, _ = campaign(SEED, count=1)
        owner = packet["jobs"][0]["owner"]
        packet["journal_events"][1]["amount"] = 0
        packet["settlements"] = []
        summary = dict(jobs=1, succeeded=1, running_units=0, artifact_bytes=packet["artifacts"][0]["size"],
                       wallets={o: dict(available=1000, reserved=0, spent=0) for o in ["alpha", "beta"]},
                       settled_credits={"alpha": 0, "beta": 0}, usage_sink=0)
        release(packet, summary)
        packet["settlements"] = [dict(request="settlement:job-0", operations=[{"from": owner, "to": "__usage__", "amount": 1}],
                                      expected={owner: 0, "__usage__": 0})]
        hold(packet)
    check("zero-consumption-boundary", zero)

    def purity():
        packet, expected = campaign(SEED, count=3)
        saved = deepcopy(packet)
        result = module.audit(packet)
        equal(packet, saved)
        result["summary"]["wallets"]["alpha"]["available"] = -1
        release(packet, expected)
        malformed = [None, [], {}, dict(packet, version=True), dict(packet, extra=1), dict(packet, jobs=[])]
        for value in malformed:
            hold(value)
        bad = deepcopy(packet)
        bad["jobs"].append(deepcopy(bad["jobs"][0]))
        hold(bad)
    check("read-only-schema-and-duplicate-scope", purity)


def evaluate(submission):
    submission = Path(submission).resolve()
    rows = []
    started = time.perf_counter()

    def check(name, function):
        try:
            function()
            rows.append(dict(category=name, passed=True))
        except Exception as error:
            rows.append(dict(category=name, passed=False, error=type(error).__name__, detail=str(error)))

    def components_unchanged():
        for source in (ROOT / "cases/c5/components").glob("*.py"):
            equal((submission / "components" / source.name).read_bytes(), source.read_bytes())
    check("identical-common-components", components_unchanged)
    for key in list(sys.modules):
        if key == "components" or key.startswith("components."):
            del sys.modules[key]
    sys.path.insert(0, str(submission))
    try:
        spec = importlib.util.spec_from_file_location("submission", submission / "engine.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        assess(module, check)
    except Exception as error:
        rows.append(dict(category="import-or-suite", passed=False, error=type(error).__name__, detail=str(error)))
    finally:
        sys.path.pop(0)
    public = subprocess.run([sys.executable, "-c", (ROOT / "cases/c5/test_public.py").read_text()], cwd=submission,
                            capture_output=True, text=True, timeout=20)
    rows.append(dict(category="canonical-public-smoke", passed=public.returncode == 0,
                     output=public.stdout + public.stderr))
    return dict(case="c5", submission=str(submission), seed=SEED, accepted=all(r["passed"] for r in rows),
                passed=sum(r["passed"] for r in rows), total=len(rows), checks=rows,
                elapsed_seconds=time.perf_counter() - started,
                source_sha256=hashlib.sha256((submission / "engine.py").read_bytes()).hexdigest())


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("submission")
    parser.add_argument("--out")
    args = parser.parse_args()
    result = evaluate(args.submission)
    encoded = json.dumps(result, indent=2) + "\n"
    if args.out:
        Path(args.out).write_text(encoded)
    print(encoded)
    raise SystemExit(0 if result["accepted"] else 1)
