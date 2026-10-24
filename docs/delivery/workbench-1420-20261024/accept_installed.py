# SPDX-License-Identifier: Apache-2.0
import argparse, copy, hashlib, json, os, pathlib, subprocess, sys, uuid
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from datetime import datetime, timezone
import platform
import threading

p = argparse.ArgumentParser()
p.add_argument("--commit", required=True)
p.add_argument("--module-sha256", required=True)
p.add_argument("--output", type=pathlib.Path, required=True)
a = p.parse_args()
from alpha_factory_v1.core.runtime.store import Conflict, Journal
from alpha_factory_v1.core.runtime import store
from alpha_factory_v1.core.runtime.successor import workbench

root = a.output.resolve()
root.mkdir(mode=0o700)
exe = pathlib.Path(sys.executable).with_name("alpha-agent")
module = pathlib.Path(workbench.__file__).resolve()
assert module.is_relative_to(pathlib.Path(sys.prefix).resolve()), str(module)
assert not module.is_relative_to(root)
assert hashlib.sha256(module.read_bytes()).hexdigest() == a.module_sha256
env = {k: os.environ[k] for k in ("PATH", "SYSTEMROOT", "WINDIR") if k in os.environ}
env.update(NO_DISCLAIMER="1", PYTHONNOUSERSITE="1", PYTHONDONTWRITEBYTECODE="1")
commands = []


def cli(*args, parse=True):
    r = subprocess.run([str(exe), *map(str, args)], cwd=root, env=env, capture_output=True, text=True, timeout=120)
    commands.append(
        {
            "args": list(map(str, args)),
            "exit": r.returncode,
            "stdout_sha256": hashlib.sha256(r.stdout.encode()).hexdigest(),
            "stderr_sha256": hashlib.sha256(r.stderr.encode()).hexdigest(),
        }
    )
    assert r.returncode == 0, (args, r.stderr[-2000:])
    return json.loads(r.stdout) if parse else r.stdout


assert cli("--version", parse=False).strip() == "1.42.0"
home = root / "cli-home"
cli("--home", home, "init")
cli("--home", home, "doctor")
trusted_key = Journal(home).public
mission = root / "mission.json"
cli("successor-work", "example", "documentation", "--output", mission)
cli("successor-work", "plan", mission)
run = cli("--home", home, "successor-work", "run", mission, "--output", root / "run")
shown = cli("--home", home, "successor-work", "show", run["run_id"])
assert shown["state"] == "review"
review = cli(
    "--home",
    home,
    "successor-work",
    "review",
    run["run_id"],
    "--result-digest",
    run["result_digest"],
    "--decision",
    "accepted",
    "--note",
    "Local synthetic documentation artifact checked; no independent admission.",
)
assert review["state"] == "accepted" and review["authority"] == []
cli("--home", home, "successor-work", "export", run["run_id"], "--output", root / "export")
verified = cli("successor-work", "verify-receipt", root / "export/signed-receipt.json", "--source-key", trusted_key)
assert verified["independentProof"] is False and verified["authority"] == []
cli("successor-work", "restore", root / "export/evidence.json", "--output", root / "restored-mission.json")
restored = cli(
    "--home",
    root / "restored-home",
    "successor-work",
    "run",
    root / "restored-mission.json",
    "--output",
    root / "restored-result",
)
assert restored["state"] == "review"
assert json.loads(mission.read_text()) == json.loads((root / "restored-mission.json").read_text())

successor_home = root / "successor-home"
successor_key = Journal.initialize(successor_home).public
successor_evidence = root / "successor-evidence"
successor = cli("--home", successor_home, "successor-demo", "--output", successor_evidence)
assert successor["qualification"] == "HOLD" and successor["production_authority"] is False
assert successor["public_key"] == successor_key
successor_verification = cli(
    "successor-verify",
    successor_evidence / "result.json",
    "--request",
    successor_evidence / "request.json",
    "--public-key",
    successor_key,
)
assert successor_verification["authentication"] == "trusted-local-signer"
assert successor_verification["production_authority"] is False
cli("--home", successor_home, "successor-checkpoint", "--output", successor_evidence / "current-checkpoint.json")
successor_restore = cli(
    "--home",
    root / "successor-restored-home",
    "successor-restore",
    successor_evidence / "portable.json",
    "--source-public-key",
    successor_key,
    "--checkpoint",
    successor_evidence / "checkpoint.json",
)
assert successor_restore["status"] == "restored-stopped"
assert successor_restore["active_proofs"] == successor_restore["active_grants"] == []
assert successor_restore["serving_release"] is None

cold_home = root / "forced-cold-home"
cold_journal = Journal.initialize(cold_home)
cold_spec = workbench.invoke({"operation": "example", "family": "numerical"})
first_id, second_id = str(uuid.uuid4()), str(uuid.uuid4())
first_writing, release_writer, second_freezing = threading.Event(), threading.Event(), threading.Event()
original_write, original_freeze = store.private_write, workbench.freeze


def pause_first_key(path, data):
    if path == cold_home / "workbench-principals/local-controller.key":
        first_writing.set()
        assert release_writer.wait(10)
    return original_write(path, data)


def observe_freeze(journal, submitted, run_id):
    if run_id == second_id:
        second_freezing.set()
    return original_freeze(journal, submitted, run_id)


store.private_write, workbench.freeze = pause_first_key, observe_freeze
try:
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(workbench.execute, cold_home, cold_spec, first_id)
        try:
            assert first_writing.wait(5)
            second = pool.submit(workbench.execute, cold_home, cold_spec, second_id)
            assert second_freezing.wait(5)
            try:
                second.result(timeout=0.5)
            except FutureTimeoutError:
                pass
            else:
                raise AssertionError("Second worker escaped incomplete first-use setup")
        finally:
            release_writer.set()
        cold_results = [first.result(timeout=10), second.result(timeout=10)]
finally:
    store.private_write, workbench.freeze = original_write, original_freeze
assert all(record["state"] == "review" and record["authority"] == [] for record in cold_results)
assert {record["run_id"] for record in cold_results} == {first_id, second_id}
assert cold_journal.verify()["valid"]

duplicate_home = root / "concurrent-duplicate-home"
duplicate_journal = Journal.initialize(duplicate_home)
duplicate_id = str(uuid.uuid4())
worker_entered, release_worker = threading.Event(), threading.Event()
duplicate_worker_calls = []
original_invoke = workbench.invoke


def hold_duplicate_worker(request, *other):
    if request["operation"] == "run":
        duplicate_worker_calls.append(duplicate_id)
        worker_entered.set()
        assert release_worker.wait(10)
    return original_invoke(request, *other)


workbench.invoke = hold_duplicate_worker
try:
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(workbench.execute, duplicate_home, cold_spec, duplicate_id)
        try:
            assert worker_entered.wait(5)
            second = pool.submit(workbench.execute, duplicate_home, cold_spec, duplicate_id)
            try:
                second.result(timeout=5)
            except Conflict:
                pass
            else:
                raise AssertionError("Duplicate request escaped the existing active attempt")
        finally:
            release_worker.set()
        duplicate_result = first.result(timeout=10)
    duplicate_checkpoint = duplicate_journal.verify()
    assert workbench.execute(duplicate_home, cold_spec, duplicate_id) == duplicate_result
    assert duplicate_journal.verify() == duplicate_checkpoint
    assert duplicate_worker_calls == [duplicate_id]
finally:
    workbench.invoke = original_invoke

partial_refusals = []
for missing in ("principals.json", "local-verifier.key"):
    partial_home = root / ("partial-" + missing)
    prior = workbench.execute(partial_home, cold_spec, str(uuid.uuid4()))
    partial_journal = Journal(partial_home)
    checkpoint = partial_journal.verify()
    roles = partial_home / "workbench-principals"
    (roles / missing).unlink()
    remaining = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in roles.iterdir()}
    try:
        workbench.execute(partial_home, cold_spec, str(uuid.uuid4()))
    except ValueError as error:
        assert "incomplete" in str(error)
    else:
        raise AssertionError("Damaged role inventory was silently repaired")
    assert not (roles / missing).exists()
    assert {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in roles.iterdir()} == remaining
    assert partial_journal.verify() == checkpoint
    assert partial_journal.latest("@successor-work:" + prior["run_id"])["state"] == "review"
    partial_refusals.append({"missing": missing, "refused": True, "history_unchanged": True, "keys_regenerated": False})

mutation_results = []
for phase in ("plan", "run"):
    spec = workbench.invoke({"operation": "example", "family": "documentation"})
    submitted = copy.deepcopy(spec)
    original = workbench.invoke

    def mutate(request, *args):
        if request["operation"] == phase:
            spec["inputs"]["markdown"] += "\nCaller changed the submitted document."
        return original(request, *args)

    workbench.invoke = mutate
    api_home, run_id = root / ("mutation-" + phase), str(uuid.uuid4())
    try:
        record = workbench.execute(api_home, spec, run_id)
    finally:
        workbench.invoke = original
    assert spec != submitted
    assert record["request"] == record["result"]["spec"] == submitted
    assert record["request_digest"] == workbench.digest("workbench-request", submitted)
    assert Journal(api_home).latest("@successor-work:" + run_id)["request"] == submitted
    assert workbench.execute(api_home, submitted, run_id)["result_digest"] == record["result_digest"]
    try:
        workbench.execute(api_home, spec, run_id)
    except Conflict:
        pass
    else:
        raise AssertionError("Changed-input duplicate was accepted")
    mutation_results.append(
        {
            "phase": phase,
            "request_digest": record["request_digest"],
            "result_digest": record["result_digest"],
            "passed": True,
        }
    )

recovery_home, recovery_id = root / "recovery-home", str(uuid.uuid4())
spec = workbench.invoke({"operation": "example", "family": "numerical"})
original = workbench.invoke


def interrupt(request, *args):
    if request["operation"] == "run":
        raise KeyboardInterrupt()
    return original(request, *args)


workbench.invoke = interrupt
try:
    try:
        workbench.execute(recovery_home, spec, recovery_id)
    except KeyboardInterrupt:
        pass
finally:
    workbench.invoke = original
assert Journal(recovery_home).latest("@successor-work:" + recovery_id)["state"] == "interrupted"
try:
    workbench.execute(recovery_home, spec, recovery_id)
except Conflict:
    pass
else:
    raise AssertionError("Implicit interrupted replay was accepted")
recovered = workbench.execute(recovery_home, spec, recovery_id, resume=True)
assert recovered["state"] == "review" and recovered["attempts"] == 2
receipt = {
    "schema": "agialpha.workbench-patch-installed.v1",
    "passed": True,
    "version": "1.42.0",
    "observed_at_utc": datetime.now(timezone.utc).isoformat(),
    "commit": a.commit,
    "python": sys.version,
    "platform": platform.platform(),
    "module": str(module),
    "module_sha256": a.module_sha256,
    "node": subprocess.check_output(["node", "--version"], text=True).strip(),
    "commands": commands,
    "mutation_regressions": mutation_results,
    "recovery_attempts": recovered["attempts"],
    "forced_cold_start": {"requests": 2, "completed": 2, "journal": cold_journal.verify(), "authority": []},
    "concurrent_duplicate": {
        "simultaneous_requests": 2,
        "worker_executions": len(duplicate_worker_calls),
        "active_duplicate_refused": True,
        "later_duplicate_acknowledged": True,
        "no_history_added_by_later_acknowledgement": True,
        "journal": duplicate_checkpoint,
    },
    "genuine_partial_inventory_refusals": partial_refusals,
    "successor_rehearsal": {
        "scope": "Existing bounded streaming-metrics-v1 native two-generation rehearsal; synthetic public workloads",
        "local_verdict": successor["local_verdict"],
        "qualification": successor["qualification"],
        "production_authority": successor["production_authority"],
        "trusted_source_key_before_run": successor_key,
        "verification": successor_verification,
        "restoration": successor_restore,
    },
    "trusted_source_key_before_export": trusted_key,
    "journal_checkpoint": Journal(home).verify(),
    "scope": "standalone installed local workbench patch; synthetic public inputs; no Fleet or settlement",
    "authority": [],
    "full_harness_qualification": False,
    "four_installed_tuple_qualification": False,
}
(root / "acceptance.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps({"passed": True, "commands": len(commands), "receipt": str(root / "acceptance.json")}))
