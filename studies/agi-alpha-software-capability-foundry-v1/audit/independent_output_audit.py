# SPDX-License-Identifier: Apache-2.0
"""Read-only independent audit of the recorded single confirmation campaign."""

from __future__ import annotations

import ast
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import random
import statistics
import time
import zipfile
import zlib


ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def object_bytes(repo, identity):
    raw = zlib.decompress((repo / ".git/objects" / identity[:2] / identity[2:]).read_bytes())
    if hashlib.sha1(raw).hexdigest() != identity:
        raise ValueError("Corrupt independent Git object: " + identity)
    header, body = raw.split(b"\0", 1)
    kind, size = header.split(b" ", 1)
    if int(size) != len(body):
        raise ValueError("Independent object length mismatch")
    return kind, body


def committed_files(repo, identity):
    kind, body = object_bytes(repo, identity)
    if kind != b"commit" or not body.startswith(b"tree "):
        raise ValueError("Independent commit identity mismatch")
    tree = body.split(b"\n", 1)[0][5:].decode()
    result = {}

    def visit(identity, prefix=""):
        kind, body = object_bytes(repo, identity)
        if kind != b"tree":
            raise ValueError("Independent tree identity mismatch")
        offset = 0
        while offset < len(body):
            space, null = body.index(b" ", offset), body.index(b"\0", offset)
            mode, name = body[offset:space], body[space + 1 : null].decode("utf8")
            oid = body[null + 1 : null + 21].hex()
            offset = null + 21
            path = prefix + name
            if mode in {b"40000", b"040000"}:
                visit(oid, path + "/")
            elif mode in {b"100644", b"100755"}:
                kind, content = object_bytes(repo, oid)
                if kind != b"blob":
                    raise ValueError("Independent blob type mismatch")
                result[path] = (oid, content)
            else:
                raise ValueError("Unexpected nonregular confirmation input")

    visit(tree)
    return result


def audit():
    started, cpu = time.perf_counter(), time.process_time()
    failures, checks = [], 0

    def require(condition, label):
        nonlocal checks
        checks += 1
        if not condition:
            failures.append(label)

    freeze = json.loads((ROOT / "protocol/FREEZE.json").read_text())
    for name, expected in freeze["files"].items():
        require(digest(ROOT / name) == expected, "frozen source: " + name)
    frozen_id = digest(ROOT / "protocol/FREEZE.json")
    campaign_path = ROOT / "results/confirmation/campaign.json"
    campaign = json.loads(campaign_path.read_text())
    require(campaign["freeze_before"] == campaign["freeze_after"], "unchanged campaign freeze")
    require(campaign["freeze_before"]["freeze_sha256"] == frozen_id, "active campaign boundary")
    cases_root = ROOT / "confirmation"
    cases = json.loads((cases_root / "cases.json").read_text())
    seed = json.loads((ROOT / "protocol/confirmation-seed.json").read_text())
    require(seed["seed"] == cases["seed"], "recorded seed used")
    require(seed["freeze"]["freeze_sha256"] == frozen_id, "seed bound to active freeze")
    require(seed["confirmation_attempt"] == 1 and seed["prior_confirmation_generated"] is False, "recorded one confirmation attempt")
    require(datetime.fromisoformat(seed["generated_at_utc"]) > datetime.fromisoformat(freeze["storage_amendment"]["recorded_utc"]), "seed follows prospective amendment")
    lock = json.loads((ROOT / "results/confirmation/TASKS_LOCK.json").read_text())
    for name, expected in lock.items():
        require(digest(cases_root / name) == expected, "protected input: " + name)
    require(len(lock) == 49, "complete 49-file input lock")
    require(digest(cases_root / "cases.json") == campaign["source_manifest_sha256"], "campaign task manifest identity")
    require(digest(ROOT / "protocol/protocol.json") == campaign["protocol_sha256"], "campaign protocol identity")
    protocol = json.loads((ROOT / "protocol/protocol.json").read_text())
    selection = json.loads((ROOT / "protocol/selection.json").read_text())
    require(cases["source_commit"] == protocol["source_commit"] == freeze["source_commit"], "pinned public source identity")
    require(len(cases["cases"]) == 24, "24 task instances")
    indexed = {case["id"]: case for case in cases["cases"]}
    expected_pairs = {(case, arm) for case in indexed for arm in protocol["arms"]}
    outcomes = campaign["outcomes"]
    require(len(outcomes) == len(expected_pairs) == 168, "168 total outcomes")
    require({(row["case"], row["arm"]) for row in outcomes} == expected_pairs, "all declared case-arm pairs")
    stream = [json.loads(line) for line in (ROOT / "results/confirmation/outcomes.jsonl").read_text().splitlines()]
    require(stream == outcomes, "incremental outcome stream matches final campaign")
    expected_order = [(case["id"], arm) for case in cases["cases"] for arm in protocol["arms"]]
    random.Random(campaign["order_seed"]).shuffle(expected_order)
    require([(row["case"], row["arm"]) for row in outcomes] == expected_order, "frozen randomized/interleaved run order")
    oracles, independent_inputs, changed_worktrees = {}, 0, 0
    for case_id, case in indexed.items():
        oracle = json.loads((cases_root / case["oracle"]).read_text())
        oracles[case_id] = oracle
        actual = committed_files(cases_root / case["repository"], case["commit"])
        independently_observed = {name: {"bytes": len(body), "sha256": hashlib.sha256(body).hexdigest()} for name, (_, body) in actual.items()}
        require(independently_observed == oracle["files"], "independent Git graph and bytes: " + case_id)
        require(set(actual) == set(case["paths"]), "requested inventory: " + case_id)
        for name, (oid, body) in actual.items():
            require(oracle["source_provenance"][name]["oid"] == oid, "public blob provenance: " + case_id + "/" + name)
            independent_inputs += 1
        first = sorted(actual)[0]
        changed_worktrees += (cases_root / case["repository"] / first).read_bytes() != actual[first][1]
        with zipfile.ZipFile(cases_root / case["archive"]) as archive:
            members = {entry.filename: archive.read(entry) for entry in archive.infolist()}
        expected = {
            "changed": sorted(name for name in actual.keys() & members.keys() if actual[name][1] != members[name]),
            "missing": sorted(actual.keys() - members.keys()),
            "extra": sorted(members.keys() - actual.keys()),
        }
        require(expected == oracle["drift"], "independent archive-drift oracle: " + case_id)
    require(changed_worktrees == 24, "all working-tree decoys remain distinct from committed source")
    template = None
    for node in ast.parse((ROOT / "src/constructor.py").read_text()).body:
        if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == "CHILD" for target in node.targets):
            template = ast.literal_eval(node.value)
    require(isinstance(template, str), "frozen child template available")
    asset_arms = {"flywheel", "conventional", "equivalent", "reconstruction"}
    accepted_outputs, retained_children, trace_count = 0, 0, 0
    by_arm = {arm: {"read_outputs": 0, "diagnostic_outputs": 0, "bound_parent_invocations": 0} for arm in protocol["arms"]}
    for ordinal, row in enumerate(outcomes):
        case_id, arm = row["case"], row["arm"]
        case, oracle = indexed[case_id], oracles[case_id]
        directory = ROOT / "results/confirmation" / case_id / arm
        read = json.loads((directory / "read.json").read_text())
        child = json.loads((directory / "child.json").read_text())
        acceptance = json.loads((directory / "acceptance.json").read_text())
        label = case_id + "/" + arm
        require(row["ordinal"] == ordinal, "ordinal: " + label)
        require(read["status"] == child["status"] == "completed", "completed phases: " + label)
        require([record["repeat"] for record in read["records"]] == list(range(4)), "four read repetitions: " + label)
        require([record["repeat"] for record in child["records"]] == list(range(4)), "four child repetitions: " + label)
        for record in read["records"]:
            require(record["files"] == oracle["files"], "read bytes: " + label)
            by_arm[arm]["read_outputs"] += 1
            accepted_outputs += 1
        expected_source = digest(ROOT / ("review/specialist.py" if arm in {"specialist", "no_asset"} else selection["equivalent_source"] if arm == "equivalent" else selection["template_source"] if arm == "reconstruction" else selection["selected_source"]))
        expected_acceptance = {
            "passed": True,
            "parent_sha256": expected_source,
            "case": case_id,
            "commit": case["commit"],
            "checked_read_sha256": hashlib.sha256(canonical(read["records"])).hexdigest(),
            "oracle_sha256": digest(cases_root / case["oracle"]),
        }
        require(read["source_sha256"] == expected_source, "served reader source identity: " + label)
        require(acceptance == expected_acceptance, "actual accepted prior read: " + label)
        binding = hashlib.sha256(canonical(acceptance)).hexdigest()
        if arm in asset_arms:
            asset = directory / "asset"
            metadata = json.loads((asset / "drift.json").read_text())
            reader_metadata = json.loads((asset / "reader.json").read_text())
            require(digest(asset / "reader.py") == expected_source == reader_metadata["sha256"], "retained parent bytes: " + label)
            require(reader_metadata["qualification"]["development_record"] == selection["qualification_sha256"], "A qualification provenance: " + label)
            require(json.loads((asset / "accepted_parent.json").read_text()) == acceptance, "child retains actual acceptance: " + label)
            require(metadata["parent_sha256"] == expected_source and metadata["parent_acceptance_sha256"] == binding, "child acceptance binding: " + label)
            require((asset / "drift.py").read_text() == template.format(parent=expected_source, acceptance=binding), "executed child bytes from frozen template: " + label)
            require(digest(asset / "drift.py") == metadata["sha256"], "child executable identity: " + label)
            require(metadata["source_dependencies"] == {name: digest(ROOT / "src" / name) for name in ("constructor.py", "drift_core.py")}, "child dependency identities: " + label)
            retained_children += 1
        observed_traces = []
        for record in child["records"]:
            result = record["result"]
            require({key: result[key] for key in ("changed", "missing", "extra")} == oracle["drift"], "complete child diagnosis: " + label)
            by_arm[arm]["diagnostic_outputs"] += 1
            accepted_outputs += 1
            trace = result.get("parent_trace")
            observed_traces.append(trace)
            if arm in asset_arms:
                expected_trace = {
                    "selected_execution": True,
                    "invocations": 1,
                    "parent_sha256": expected_source,
                    "acceptance_sha256": binding,
                    "input_commit": case["commit"],
                    "input_paths_sha256": hashlib.sha256(json.dumps(sorted(case["paths"])).encode()).hexdigest(),
                    "output_inventory_sha256": hashlib.sha256(json.dumps({name: data["sha256"] for name, data in oracle["files"].items()}, sort_keys=True).encode()).hexdigest(),
                }
                require(trace == expected_trace, "selected child parent-use trace: " + label)
                trace_count += 1
                by_arm[arm]["bound_parent_invocations"] += 1
        require(observed_traces == row["parent_traces"], "campaign trace preservation: " + label)
        costs = read["costs"] + child["costs"]
        service = sum(cost["wall_seconds"] for cost in costs if cost["account"] == "service")
        improvement = sum(cost["wall_seconds"] for cost in costs if cost["account"] == "improvement")
        require(abs(service - row["service_wall_seconds"]) < 1e-12 and abs(improvement - row["improvement_wall_seconds"]) < 1e-12, "separate budget ledgers: " + label)
        require(service <= protocol["budgets"]["service_seconds_per_arm_instance"] and improvement <= protocol["budgets"]["improvement_seconds_per_arm_instance"], "admission budgets: " + label)
        instance = row["instance_cost"]
        require(abs(instance["parent_cpu_seconds"] + instance["child_cpu_seconds"] - row["total_cpu_seconds"]) < 1e-12, "total CPU components: " + label)
        require(row["wall_seconds"] == instance["wall_seconds"], "elapsed cost consistency: " + label)
        require(all(row[key] for key in ("read_passed", "child_passed", "trace_passed", "budget_passed")), "all reported gates: " + label)
    baseline = {row["case"]: row for row in outcomes if row["arm"] == "specialist"}
    proposed = {row["case"]: row for row in outcomes if row["arm"] == "flywheel"}
    logs = [math.log(proposed[name]["total_cpu_seconds"] / baseline[name]["total_cpu_seconds"]) for name in sorted(indexed)]
    estimate = math.exp(statistics.mean(logs))
    rng = random.Random(395022)
    samples = sorted(math.exp(sum(rng.choices(logs, k=24)) / 24) for _ in range(10_000))

    def quantile(q):
        position = (len(samples) - 1) * q
        lower = int(position)
        return samples[lower] + (samples[min(lower + 1, len(samples) - 1)] - samples[lower]) * (position - lower)

    interval = [quantile(0.025), quantile(0.975)]
    reported = json.loads((ROOT / "results/analysis.json").read_text())
    require(abs(estimate - reported["primary"]["geometric_cpu_ratio"]) < 1e-12, "independent primary point estimate")
    require(all(abs(a - b) < 1e-12 for a, b in zip(interval, reported["primary"]["ci95"])), "independent primary interval")
    require(reported["decision"] == "HOLD_FLYWHEEL_SUPERIORITY" and interval[1] >= 0.95, "primary admission decision")
    require(accepted_outputs == 1344 and retained_children == 96 and trace_count == 384, "complete output and lineage counts")
    record = {
        "schema": "foundry-independent-output-audit/v1",
        "reviewed_utc": datetime.now(timezone.utc).isoformat(),
        "passed": not failures,
        "checks": checks,
        "failures": failures,
        "audit_script_sha256": digest(Path(__file__)),
        "freeze_sha256": frozen_id,
        "frozen_files_checked": len(freeze["files"]),
        "protected_files_checked": len(lock),
        "repository_instances": len(indexed),
        "independently_read_committed_files": independent_inputs,
        "working_tree_decoys_verified": changed_worktrees,
        "case_arm_pairs": len(outcomes),
        "outputs_checked": accepted_outputs,
        "bound_child_instances": retained_children,
        "bound_parent_invocations": trace_count,
        "by_arm": by_arm,
        "independently_recomputed_primary": {"geometric_cpu_ratio": estimate, "ci95": interval},
        "campaign_sha256": digest(campaign_path),
        "analysis_sha256": digest(ROOT / "results/analysis.json"),
        "benchmark_rerun": False,
        "input_audit_method": "Direct decompression and hash verification of commit, tree and blob objects; independent ZIP reads and output comparisons; no candidate or comparator method rerun.",
        "limitations": [
            "Internal role-separated audit in a shared workspace, not OS-isolated or external replication.",
            "Parent traces are source-bound in-process records, not hardware attestation or independently captured system calls.",
            "One child design instantiated 96 times; these are not 96 independently discovered algorithms.",
            "No-asset specialist and ordinary tooling may reuse independent reader functions; zero bound-parent traces means no proposed lineage record, not zero software reuse.",
            "24 generated instances share one source ecosystem and one host; timings remain conditional on that environment.",
            "Full research, model, human, integration and maintenance costs remain incomplete.",
        ],
        "audit_wall_seconds": time.perf_counter() - started,
        "audit_process_cpu_seconds": time.process_time() - cpu,
    }
    (ROOT / "audit/independent-output-audit.json").write_text(json.dumps(record, sort_keys=True, indent=2) + "\n")
    print(json.dumps({key: record[key] for key in ("passed", "checks", "failures", "outputs_checked", "bound_parent_invocations", "independently_recomputed_primary")}))
    return record


if __name__ == "__main__":
    result = audit()
    raise SystemExit(0 if result["passed"] else 1)
