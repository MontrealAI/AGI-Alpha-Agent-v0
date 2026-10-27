# SPDX-License-Identifier: Apache-2.0
"""Execute existing research lifecycle and native ledger without production admission."""

from __future__ import annotations

import base64
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parent
REPOSITORY = ROOT.parents[1]
UPSTREAM = ROOT / "upstream" / "beyond_beta"
sys.path.insert(0, str(REPOSITORY))

NODE_PROGRAM = r"""
import {readFileSync} from 'node:fs';
import {pathToFileURL} from 'node:url';
const q=JSON.parse(readFileSync(0,'utf8'));
const load=p=>import(pathToFileURL(`${q.module_root}/${p}`).href);
const {createSkillNetwork,combineComparisonDigest}=await load('graph/lifecycle.mjs');
const {createModeledAuthority}=await load('graph/simulation_adapter.mjs');
const {createFixtureResolver,createFixtureAttestation,createFixtureRoot}=await load('upstream/graph/authority.mjs');
const {contentDigest}=await load('graph/encoding.mjs');
const {assessAlpha}=await load('model/alpha_gate.mjs');
const members=['atlas.agent.agi.eth','lyra.agent.agi.eth','orion.agent.agi.eth','validator.agent.agi.eth'];
const fixture=createModeledAuthority(members), resolver=createFixtureResolver(fixture);
const scope=contentDigest('scientific-computing-local-research/v1');
const environment=contentDigest('local-computation-synthetic-network-monetary-assumptions/v1');
const networkId='invention-relay-research/v1';
const network=createSkillNetwork({networkId,betaVersion:q.beta_version,
  scopeDigest:scope,environmentDigest:environment,authorityFixture:fixture,
  currentSnapshotId:fixture.snapshots[0].id,
  executionAuthorizer:()=>({allowed:true,mode:'SIMULATED_MISSION_AUTHORITY',actualExecution:false})});
network.protectEvaluationMaterial(q.protected_material);
let nonce=0;
const rows=[], checks=[], owners=new Map();
const signTransition=(key,action,options,week)=>{
  const p=network.prepareTransition(key,action,options,week), agent=p.command.actor;
  const root=createFixtureRoot(p.packet,{agent,signer:`fixture:${agent}`,
    snapshotId:network.context().currentSnapshotId,issuedAt:week,expiresAt:week+1000,
    nonce:`root:${nonce++}`,graphId:p.packet.graphId},resolver);
  return network.commitTransition(p,root,week);
};
const memberProof=(agent,week)=>{
  const binding=network.membershipBinding(agent);
  return createFixtureAttestation(binding,{agent,signer:`fixture:${agent}`,
    snapshotId:network.context().currentSnapshotId,issuedAt:week,expiresAt:week+1000,
    nonce:`member:${nonce++}`,graphId:`${networkId}:membership`},resolver);
};
const mission=()=>({scopeDigest:scope,environmentDigest:environment,betaVersion:network.context().betaVersion});
for(const c of q.candidates){
  let key=null;
  try{
    const week=c.week??0, expiry=c.expiry??100, owner=c.owner??members[0];
    const rights=c.rights??(c.shared?{shareable:true,retrieve:'network',execute:'network',compose:'network',export:false}:
      {shareable:false,retrieve:[owner],execute:[owner],compose:[owner],export:false});
    const payload={schema:'local-scientific-artifact/v1',artifactSha256:c.artifact_sha256,
      contentEncoding:c.content_encoding,content:c.artifact_content,
      provenance:'researcher-constructed learning code; local numerical learning; simulated network authority'};
    const manifest={id:c.id,version:String(c.version),ownerAgent:owner,
      implementationDigest:c.artifact_sha256,equivalenceKey:c.equivalence_key??`${c.id}-v${c.version}`,
      scopeDigest:scope,environmentDigest:environment,expiresAt:expiry,
      prerequisitePins:c.prerequisite_pins??[],components:c.components??[],rights,
      payloadDigest:contentDigest(payload,'beyond-beta-private-payload')};
    const submitted=network.submitCandidate(manifest,{privatePayload:payload,now:week});
    key=submitted.key;owners.set(key,owner);
    const context=network.context(), comparator=contentDigest(c.comparison_id??q.beta_version);
    const bindings={candidateId:c.id,candidateVersion:String(c.version),candidateDigest:submitted.candidateDigest,
      betaVersion:context.betaVersion,policyVersion:context.policyVersion,scopeDigest:scope,
      environmentDigest:environment,comparisonUniverseDigest:combineComparisonDigest(network.inventoryDigest(key),comparator),
      evaluatedAt:week,expiresAt:expiry,prerequisitePins:manifest.prerequisitePins};
    const assessment=assessAlpha({bindings,pairedTrials:c.paired_trials??[],
      lifecycleCostCents:c.lifecycle_cost_cents??0,evaluationCostCents:c.evaluation_cost_cents??0,
      forecastEligibleUses:c.forecast_uses??0,correctnessChecksPassed:c.correctness_passed===true,
      alreadyAvailable:c.already_available===true});
    network.attachEvidence(key,{mode:'OBSERVED_LOCAL_TESTS',replayAvailable:c.replay_available===true,boundaryPass:c.boundary_passed===true,
      blockedClaimsPresent:false,artifactDigest:c.artifact_sha256,replayDigest:assessment.observedPairsDigest,
      provenanceDigest:contentDigest({artifact:c.artifact_sha256,assay:c.provenance_digest??'local-test-observations',
        money:'ASSUMED_RESOURCE_VALUE',frontierComparison:false})},week);
    const assessed=network.recordAssessment(key,assessment,week,{declaredComparatorDigest:comparator});
    let admission=null;
    if(assessed.ok){
      const b=network.validationBinding(key),validator='validator.agent.agi.eth';
      const attestation=createFixtureAttestation(b,{agent:validator,signer:`fixture:${validator}`,
        snapshotId:context.currentSnapshotId,issuedAt:week,expiresAt:b.expiresAt,
        nonce:`validation:${nonce++}`,graphId:`${networkId}:${owner}`},resolver);
      const validated=network.validate(key,[attestation],week);
      if(validated.ok)admission=signTransition(key,'admit',{},week);
    }
    rows.push({id:c.id,key,assessment,assessed,admission,state:network.inspect(key,week),
      researchAuthority:'FIXTURE_ONLY',productionAdmission:'NOT_QUALIFIED',frontierAlpha:'UNMEASURED'});
  }catch(error){rows.push({id:c.id,key,error:error.message,productionAdmission:'NOT_QUALIFIED'});}
}
for(const op of q.operations){
  try{
    let result;
    const week=op.week??1, member=op.member??members[1];
    if(op.action==='discover')result=network.discover(memberProof(member,week),mission(),week);
    else if(op.action==='retrieve'||op.action==='execute'||op.action==='compose'||op.action==='export'){
      result=network.requestReuse(op.key,memberProof(member,week),{...mission(),...(op.mission??{})},
        {right:op.action,dryRun:op.dry_run??false},week);
      if(result.payload){
        const p=result.payload;
        result.transferredArtifact={sha256:p.artifactSha256,contentEncoding:p.contentEncoding,content:p.content};
        delete result.payload;
      }
    }else if(op.action==='revoke'||op.action==='retire')
      result=signTransition(op.key,op.action,{reason:op.reason??'declared research lifecycle control'},week);
    else if(op.action==='beta-update'){
      network.advanceBeta(op.beta_version,week,op.baseline_keys??[]);result={ok:true};
    }else if(op.action==='inspect')result=network.inspect(op.key,week);
    else throw Error('UNKNOWN_RESEARCH_OPERATION');
    checks.push({operation:op,result});
  }catch(error){checks.push({operation:op,result:{ok:false,reasons:[error.message]}});}
}
process.stdout.write(JSON.stringify({schema:'invention-network-lifecycle-replay/v1',candidates:rows,
  operations:checks,snapshot:network.snapshot({includeCiphertext:false}),
  liveCapsuleAdmission:'NOT_QUALIFIED_UNSUPPORTED_SCIENTIFIC_SCOPE',
  actualFrontierCalls:0,actualReceiptsMicroUSD:0,
  distinction:'Research fixture access replays local artifact bytes; it neither deploys a protected service nor runs the artifact.'}));
"""


def verify_upstream() -> dict[str, Any]:
    """Check every reused source against the unchanged recorded byte identity."""
    manifest: dict[str, Any] = json.loads((ROOT / "upstream" / "SOURCE_MANIFEST.json").read_text())
    for row in manifest["files"]:
        actual = (UPSTREAM / row["path"]).read_bytes()
        if len(actual) != row["bytes"] or hashlib.sha256(actual).hexdigest() != row["sha256"]:
            raise ValueError(f"upstream source drift: {row['path']}")
    return manifest


def run_lifecycle(
    candidates: Iterable[dict[str, Any]],
    *,
    operations: Iterable[dict[str, Any]] = (),
    protected_material: Iterable[Any] = (),
    beta_version: str = "technical-beta-v1",
) -> dict[str, Any]:
    """Replay generic research admission using actual artifact bytes and declared monetary assumptions."""
    manifest = verify_upstream()
    node = shutil.which("node")
    if node is None:
        raise RuntimeError("Node.js is required for the pinned upstream research lifecycle")
    rows = []
    for value in candidates:
        row = dict(value)
        path = Path(row.pop("artifact_path"))
        content = path.read_bytes()
        if len(content) > 2_000_000:
            raise ValueError("research artifact exceeds the declared two megabyte bridge bound")
        actual_sha = hashlib.sha256(content).hexdigest()
        expected_sha = row.pop("expected_artifact_sha256", None)
        if expected_sha is not None and expected_sha != actual_sha:
            raise ValueError("frozen scientific artifact bytes changed")
        row["artifact_sha256"] = actual_sha
        try:
            row["artifact_content"] = content.decode("utf-8")
            row["content_encoding"] = "utf-8"
        except UnicodeDecodeError:
            row["artifact_content"] = base64.b64encode(content).decode("ascii")
            row["content_encoding"] = "base64"
        rows.append(row)
    request = {
        "module_root": str(UPSTREAM),
        "candidates": rows,
        "operations": list(operations),
        "protected_material": list(protected_material),
        "beta_version": beta_version,
    }
    completed = subprocess.run(
        [node, "--input-type=module", "-e", NODE_PROGRAM],
        input=json.dumps(request, allow_nan=False),
        text=True,
        capture_output=True,
        timeout=60,
        check=True,
    )
    result: dict[str, Any] = json.loads(completed.stdout)
    result["upstream_commit"] = manifest["commit"]
    result["node_version"] = subprocess.check_output([node, "--version"], text=True).strip()
    return result


def replay_native_costs(
    charges: Iterable[dict[str, Any]],
    *,
    collections: Iterable[dict[str, Any]] = (),
    capital_micro_usd: int = 0,
    reserve_micro_usd: int = 0,
    seal: bool = True,
) -> dict[str, Any]:
    """Use the existing signed native ledger; input amounts remain simulation attestations."""
    native_manifest = json.loads((ROOT / "evidence" / "native_import_closure.json").read_text())
    for source in native_manifest["files"]:
        actual = (REPOSITORY / source["path"]).read_bytes()
        if hashlib.sha256(actual).hexdigest() != source["sha256"]:
            raise ValueError(f"frozen native source drift: {source['path']}")
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
    from alpha_factory_v1.core.runtime.store import Journal
    from alpha_factory_v1.core.runtime.successor.flywheel_costs import CATEGORIES, CostLedger
    from alpha_factory_v1.core.runtime.successor.protocol import digest
    from alpha_factory_v1.core.runtime.successor.trust import TrustAnchor, TrustRegistry, sign_record

    with tempfile.TemporaryDirectory(prefix="invention-ledger-") as temporary:
        journal = Journal.initialize(Path(temporary) / "native")
        key = Ed25519PrivateKey.generate()
        public = key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw).hex()
        trust = TrustRegistry({"research-accounting": TrustAnchor(public, frozenset({"accounting"}))})
        ledger = CostLedger(journal, trust)
        commands: list[dict[str, Any]] = []

        def apply(action: str, record: Any) -> None:
            payload = {
                "journal_identity": journal.identity,
                "operation_id": f"research-operation-{len(commands)}",
                "action": action,
                "record": record,
            }
            ledger.apply(sign_record(key, "research-accounting", "flywheel-cost-command", payload))
            commands.append({"action": action, "record": record})

        if capital_micro_usd:
            apply(
                "capital",
                {
                    "record_id": "seed-capital",
                    "mission_id": "enterprise",
                    "amount_micro_usd": capital_micro_usd,
                    "evidence_digest": digest("research-seed", {"amount": capital_micro_usd}),
                },
            )
        groups: dict[tuple[str, str], list[dict[str, Any]]] = {}
        for value in charges:
            row = dict(value)
            row.setdefault("paid_micro_usd", row.get("accrued_micro_usd") or 0)
            row.setdefault("basis", "unknown" if row.get("accrued_micro_usd") is None else "attested")
            row.setdefault("note", "SIMULATED amount; executed accounting; not a provider invoice")
            row.setdefault("evidence_digest", digest("research-charge", row))
            apply("charge", row)
            groups.setdefault((row["mission_id"], row["bucket"]), []).append(row)
        for value in collections:
            row = dict(value)
            row.setdefault("evidence_digest", digest("research-collection", row))
            apply("collection", row)
        if seal:
            for (mission, bucket), rows in groups.items():
                if {r["category"] for r in rows} != CATEGORIES or any(r["accrued_micro_usd"] is None for r in rows):
                    continue
                action = {"A": "seal", "B": "seal-retention", "C": "seal-investment"}[bucket]
                apply(
                    action,
                    {
                        "mission_id": mission,
                        "categories": sorted(CATEGORIES),
                        "evidence_digest": digest("research-completeness", rows),
                    },
                )
        apply("reserve", reserve_micro_usd)
        report = ledger.report()
        verification = journal.verify()
        return {
            "schema": "native-cost-ledger-replay/v1",
            "report": report,
            "verified_journal": {"valid": verification["valid"], "events": verification["events"]},
            "commands": commands,
            "input_basis": "SIMULATED_ACCOUNTING_ATTESTATIONS",
            "actual_collections_micro_usd": 0,
            "credentials": "ephemeral local test keys; no exported keys or live account",
        }


def native_source_manifest() -> dict[str, Any]:
    """Record the imported native Python closure after a ledger replay."""
    rows = []
    for name, module in sorted(sys.modules.items()):
        path_value = getattr(module, "__file__", None)
        if not name.startswith("alpha_factory_v1") or not path_value:
            continue
        path = Path(path_value).resolve()
        if not path.is_relative_to(REPOSITORY) or path.suffix != ".py":
            continue
        data = path.read_bytes()
        rows.append(
            {
                "path": path.relative_to(REPOSITORY).as_posix(),
                "bytes": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
            }
        )
    return {"repository_commit": "80b345828f34fd8a6e592977dd17ef37141305f4", "files": rows}
