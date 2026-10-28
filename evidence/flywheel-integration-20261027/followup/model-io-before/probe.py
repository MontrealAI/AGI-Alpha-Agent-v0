from pathlib import Path
import hashlib, json, resource, subprocess, sys, time

root = Path("/workspace/scratch/9c7b9ec78746/repo")
out = Path("/workspace/scratch/9c7b9ec78746/model-evidence-audit")
resource.setrlimit(resource.RLIMIT_CPU, (30, 30))
sys.path[:0] = [str(root), str(root / "tests/runtime")]
import test_flywheel_comparisons as c
from alpha_factory_v1.core.runtime.store import digest as runtime_digest
from alpha_factory_v1.core.runtime.successor.flywheel_execution import (
    ExecutionPermit,
    ExecutionProfile,
    MissionExecutor,
    operation_key,
)
from alpha_factory_v1.core.runtime.successor.flywheel_discovery import ComparisonPlan
from alpha_factory_v1.core.runtime.successor.protocol import digest
from alpha_factory_v1.core.runtime.successor.trust import sign_record

state = c.setup.__wrapped__(out / "fixture-two")
from alpha_factory_v1.core.runtime.models import RuntimeConfig
from alpha_factory_v1.core.runtime.chain import Economics

config = RuntimeConfig(llm_url="http://127.0.0.1:9", llm_model="OFFLINE-NO-IO-FIXTURE")
journal = c.f.Journal.initialize(out / "configured-fixture", config)
costs = c.f.CostLedger(journal, state["trust"])
economics = Economics(journal)
challenge = economics.challenge()
economics.bind(
    c.f.Account.sign_message(c.f.encode_defunct(text=challenge["message"]), state["origin_wallet"].key).signature.hex()
)
authority, rpc = c.f.readers(state["wallet"].address)
for reader in rpc:
    reader.owners[c.f.namehash("one.agent.agi.eth").hex()] = state["origin_wallet"].address.lower()
access = c.f.ResourceAccess(journal, c.f.ServiceIdentity(origin="https://fixture-service.example"), authority)
library = c.f.TransformationLibrary(journal, state["trust"], producer="producer")
checkpoint = c.f.DurableCheckpoint.initialize(out / "configured-custody.sqlite3", journal)
service = c.f.ProtectedLibrary(library, costs, access, {"fixture-key": c.f.secrets_bytes()}, "fixture-key", checkpoint)
state.update(journal=journal, costs=costs, service=service, access=access, library=library, rpc=rpc)
p = c.profile().model_copy(
    update={"model_id": state["journal"].config.llm_model, "model_request_cap_micro_usd": 1, "max_context_bytes": 1024}
)
p = ExecutionProfile.model_validate(p.model_dump())
spec = c.plan(state, 1)
spec = spec.model_copy(
    update={
        "arms": [
            arm.model_copy(update={"model_profile_digest": digest("flywheel-execution-profile", p)})
            for arm in spec.arms
        ]
    }
)
for trial in spec.cases[0].trials:
    trial.mission.components["model"] = "live"
spec = c.freeze(state, ComparisonPlan.model_validate(spec.model_dump()))


class NoIOTransport:
    component = "live"
    calls = 0

    def respond(self, *args):
        self.calls += 1
        raise AssertionError("The audit forbids model I/O; this local double is not a provider")


transport = NoIOTransport()
environment = c.SystemsTool()
trial = spec.cases[0].trials[0]
terms = ExecutionPermit(
    operation_id=trial.operation_id,
    request_digest=digest("flywheel-execution-request", trial.mission),
    profile_digest=digest("flywheel-execution-profile", p),
    environment_digest=digest("flywheel-execution-environment-contract", environment.identity),
    config_digest=runtime_digest(state["journal"].config.model_dump()),
    quota_evidence_digest=c.f.ZERO,
    pricing_evidence_digest=c.f.ZERO,
    max_authorized_micro_usd=1000,
    expires_at=int(time.time()) + 3600,
    bucket="A",
)
signed = sign_record(
    state["keys"]["controller"],
    "controller",
    "flywheel-execution-permit",
    {"journal_identity": state["journal"].identity, "permit": terms.model_dump()},
)
state["trust"].verify(signed, "flywheel-execution-permit", "controller")
record = MissionExecutor(state["journal"], state["trust"], state["costs"], transport, environment).run(
    trial.mission, p, signed
)
report = c.report(state, spec)
assert transport.calls == 0 and record["status"] == "failed-or-uncertain" and record["turn"] == 1
assert record["usage_events"] == [] and record["actions"] == 0 and record["reserved_request_caps_micro_usd"] == 0
assert report["cells"][0]["execution_digest"] is not None and report["cells"][0]["status"] == "failed-or-uncertain"
assert report["cells"][0]["execution_authority_current"] is True
assert report["model_evidence"] == "actual-model-records-with-unqualified-attribution"
receipt = {
    "scope": "Local software conformance counterexample; no live model, identity, bill, quota or customer trial",
    "transport": "Offline no-I/O test double declaring the live protocol component; not a provider transport",
    "source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip(),
    "source_files": {
        name: hashlib.sha256((root / name).read_bytes()).hexdigest()
        for name in [
            "alpha_factory_v1/core/runtime/successor/flywheel_comparisons.py",
            "alpha_factory_v1/core/runtime/successor/flywheel_execution.py",
        ]
    },
    "model_respond_invocations": transport.calls,
    "actual_provider_calls": 0,
    "status": record["status"],
    "error_type": record["error_type"],
    "turn_counter": record["turn"],
    "usage_events": record["usage_events"],
    "actions": record["actions"],
    "reserved_request_caps_micro_usd": record["reserved_request_caps_micro_usd"],
    "model_evidence": report["model_evidence"],
    "cells": report["cells"],
    "contrasts": report["contrasts"],
    "current_evidence_valid": report["current_evidence_valid"],
    "unmodified_execution_record": dict(state["journal"].latest(operation_key(trial.operation_id))),
    "plan": spec.model_dump(),
    "report": report,
}
(out / "RESULT.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(
    json.dumps(
        {
            k: v
            for k, v in receipt.items()
            if k not in {"unmodified_execution_record", "plan", "report", "cells", "contrasts"}
        },
        indent=2,
    )
)
print(json.dumps({"scratch_bytes": sum(p.stat().st_size for p in out.rglob("*") if p.is_file())}))
