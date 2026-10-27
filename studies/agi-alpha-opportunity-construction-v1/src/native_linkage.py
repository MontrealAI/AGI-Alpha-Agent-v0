# SPDX-License-Identifier: Apache-2.0
"""Link supplied opportunity research to unchanged native Insight and FusionPlan APIs.

This adapter performs local artifact construction and inspection only. It never
executes milestone commands, fetches source URLs, configures a wallet, calls RPC,
submits a job, qualifies a deployment, or converts a CAD budget into tokens.

Usage:
    python native_linkage.py --input selected_opportunity.json --output linkage
    python native_linkage.py --verify linkage
    python native_linkage.py --example example.json

The full research annex is deliberately separate from supported native schemas.
Its exact digest is committed in each milestone goal. The canonical Insight draft
remains a one-review-job draft; it is not rewritten to impersonate a sealed seed.
"""

from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import importlib.metadata
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any


REPO = Path(__file__).resolve().parents[3]
STUDY = Path(__file__).resolve().parents[1]
COMPONENT_MAP = STUDY / "sources" / "COMPONENT_MAP.json"
INSIGHT_BOUNTY_TOKENS_FIXTURE = 1
MILESTONE_BOUNTY_BASE_UNITS_FIXTURE = "100"
ALLOWED_PERMISSIONS = {"local-read", "local-write", "local-execute", "public-read"}
BOUNDARY = {
    "research_only": True,
    "plaintext": True,
    "minted": False,
    "funded": False,
    "listed": False,
    "submitted_jobs": False,
    "milestone_commands_executed": False,
    "wallet_connected": False,
    "rpc_used": False,
    "new_registry_or_authority": False,
    "source_urls_fetched_by_adapter": False,
    "token_fields": "Unsubmitted native-format fixtures only; no value, price, funding, or CAD conversion.",
}

# Import the repository's actual implementations, not copied approximations.
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
from alpha_factory_v1.demos.alpha_agi_insight_v0 import discovery as insight  # noqa: E402
from alpha_factory_v1.core.runtime import ascension  # noqa: E402


def sha256(data: bytes) -> str:
    """Return an exact-byte SHA-256 digest without asserting authenticity."""
    return hashlib.sha256(data).hexdigest()


def encoded(value: Any) -> bytes:
    """Use native Insight canonical JSON for this adapter's local records."""
    return insight.canonical(value) + b"\n"


def with_digest(value: dict[str, Any]) -> dict[str, Any]:
    """Attach a content digest; this is not a signature or external attestation."""
    return {**value, "sha256": insight.digest(value)}


def read_json(path: Path) -> Any:
    """Read bounded, duplicate-key-rejecting JSON through the native parser."""
    return insight.read_json(path)


def repository_file(value: str) -> Path:
    """Resolve an explicit local evidence path and refuse repository escape."""
    path = Path(value)
    path = (path if path.is_absolute() else REPO / path).resolve()
    if not path.is_relative_to(REPO):
        raise ValueError("Evidence and component paths must remain inside this repository")
    if any(part in {".git", ".aws", ".ssh"} for part in path.relative_to(REPO).parts):
        raise ValueError("Private operational directories are not research evidence inputs")
    if path.name == ".env" or path.name.startswith(".env."):
        raise ValueError("Environment files are not research evidence inputs")
    return path


def component_provenance() -> dict[str, Any]:
    """Check the frozen component map against the actual reused source bytes."""
    mapping = read_json(COMPONENT_MAP)
    components = []
    for item in mapping["components"]:
        path = repository_file(item["path"])
        actual = sha256(path.read_bytes())
        record = {
            "name": item["name"],
            "path": item["path"],
            "expected_sha256": item["sha256"],
            "actual_sha256": actual,
            "matches_frozen_map": actual == item["sha256"],
            "scope": item["scope"],
        }
        components.append(record)
        if not record["matches_frozen_map"]:
            raise ValueError(f"Canonical component changed from COMPONENT_MAP.json: {item['path']}")
    extra_paths = [
        "docs/assets/ascension-wallet/client.mjs",
        "docs/assets/ascension-wallet/qualified-profiles.mjs",
        str(Path(__file__).resolve().relative_to(REPO)),
    ]
    return {
        "repository_baseline": mapping["repository_baseline"],
        "component_map_sha256": sha256(COMPONENT_MAP.read_bytes()),
        "components": components,
        "additional_actual_sources": [
            {"path": name, "sha256": sha256(repository_file(name).read_bytes())} for name in extra_paths
        ],
        "direct_native_calls": [
            "discovery.evaluate",
            "discovery.verify",
            "discovery.artifacts",
            "core.runtime.ascension.compile_plan",
            "core.runtime.ascension.verify_plan",
        ],
        "contract_scope": "Solidity source inspection only; no deployed-bytecode or live-authority verification.",
    }


def validate_input(data: Any) -> dict[str, Any]:
    """Check research fields without adding them to any native schema."""
    required = {
        "opportunity",
        "sources",
        "assessments",
        "witness",
        "rights",
        "uncertainties",
        "next_experiment",
        "evidence",
        "milestones",
    }
    if not isinstance(data, dict) or not required.issubset(data):
        raise ValueError("Input requires: " + ", ".join(sorted(required)))
    if not isinstance(data["opportunity"], dict):
        raise ValueError("opportunity must be an object")
    if not isinstance(data["assessments"], dict) or set(data["assessments"]) != set(insight.METRICS):
        raise ValueError("assessments must explicitly provide demand, feasibility, readiness, and advantage")
    if not isinstance(data["evidence"], list):
        raise ValueError("evidence must be an array of explicit repository paths or path records")
    milestones = data["milestones"]
    if not isinstance(milestones, list) or not 3 <= len(milestones) <= 5:
        raise ValueError("Supply 3–5 ordered executable milestone specifications")
    seen: set[str] = set()
    for index, milestone in enumerate(milestones):
        if not isinstance(milestone, dict):
            raise ValueError("Each milestone must be an object")
        milestone.setdefault("id", f"m{index + 1}")
        insight.identifier(milestone["id"])
        if milestone["id"] in seen:
            raise ValueError("Duplicate milestone id")
        for field in ("goal", "successMetric", "acceptance", "falsifier"):
            insight.text(milestone.get(field), f"Milestone {field}", 400 if field == "goal" else 4000)
        command = milestone.get("command")
        if not isinstance(command, list) or not command or len(command) > 64:
            raise ValueError("Milestone command must be a nonempty argv array; shell strings are not executed")
        for arg in command:
            if not isinstance(arg, str) or not arg or "\x00" in arg or len(arg.encode()) > 16000:
                raise ValueError("Milestone argv contains invalid or oversized text")
        dependencies = milestone.get("dependencies")
        if not isinstance(dependencies, list) or any(dep not in seen for dep in dependencies):
            raise ValueError("Dependencies must identify earlier milestones in the ordered plan")
        permissions = milestone.get("permissions")
        if not isinstance(permissions, list) or any(p not in ALLOWED_PERMISSIONS for p in permissions):
            raise ValueError("Milestone permissions exceed the local/public-reading research boundary")
        budget = milestone.get("budget_cad")
        if type(budget) not in (int, float) or not math.isfinite(budget) or budget < 0:
            raise ValueError("budget_cad must be a finite nonnegative planning number")
        if any(key in milestone for key in ("bounty", "tokens", "jobBountyTokens", "funded")):
            raise ValueError("Token/funding inputs are forbidden; native bounty fields are fixed format fixtures")
        seen.add(milestone["id"])
    return data


def native_scenario(data: dict[str, Any]) -> dict[str, Any]:
    """Map explicit researcher signals to exactly the supported native fields."""
    supplied = data["opportunity"]
    opportunity = {key: supplied[key] for key in ("id", "sector", "title", "thesis", "goal", "successMetric")}
    opportunity["reviewMinutes"] = supplied.get("reviewMinutes", 60)
    opportunity["signals"] = {
        metric: {key: data["assessments"][metric][key] for key in ("low", "base", "high", "source")}
        for metric in insight.METRICS
    }
    scenario = {
        "schema": insight.SCHEMA,
        "id": supplied["id"],
        "title": supplied["title"],
        "note": (
            "Researcher-selected opportunity; four supplied source-linked assessment intervals are not probabilities, "
            "authenticated evidence, or customer acceptance. Single-candidate native screening is not cross-arm ranking. "
            "All token values are unsubmitted format fixtures, independent of CAD budgets; no funded capital is asserted."
        ),
        "weights": data.get("insight_weights", {metric: 2500 for metric in insight.METRICS}),
        "policy": {
            "reviewMinutes": opportunity["reviewMinutes"],
            "minScoreBps": data.get("insight_min_score_bps", 0),
            "minCoverageBps": 10000,
            "jobBountyTokens": INSIGHT_BOUNTY_TOKENS_FIXTURE,
        },
        "sources": [
            {key: source[key] for key in ("id", "title", "url", "excerpt", "kind")} for source in data["sources"]
        ],
        "opportunities": [opportunity],
    }
    return insight.validate(scenario)


def evidence_records(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Hash available evidence bytes and explicitly retain missing evidence."""
    records = []
    for value in data["evidence"]:
        item = {"path": value} if isinstance(value, str) else dict(value)
        path = repository_file(item["path"])
        record = {**item, "path": str(path.relative_to(REPO)), "present": path.is_file()}
        if record["present"]:
            record.update(sha256=sha256(path.read_bytes()), bytes=path.stat().st_size)
        else:
            record.update(sha256=None, bytes=None, limitation="Referenced evidence is missing; no content verified")
            if item.get("required") is True:
                raise ValueError(f"Required evidence file is missing: {item['path']}")
        records.append(record)
    return records


def research_annex(data: dict[str, Any], dossier: dict[str, Any]) -> dict[str, Any]:
    """Keep uncertainty, rights, witness, evidence and executable details separate."""
    body = {
        "schema": "agi-alpha.opportunity-research-annex.v1",
        "boundary": BOUNDARY,
        "input_canonical_sha256": insight.digest(data),
        "insight_dossier_sha256": dossier["sha256"],
        "opportunity": data["opportunity"],
        "researcher_assessments": data["assessments"],
        "assessment_mapping": {
            metric: f"Input assessments.{metric} -> native signals.{metric}; no automatic score conversion"
            for metric in insight.METRICS
        },
        "assessment_scope": "Basis-point assessment intervals; not statistical confidence intervals or profit forecasts.",
        "source_records": [
            {
                **source,
                "record_sha256": insight.digest(source),
                "excerpt_sha256": sha256(source["excerpt"].encode("utf-8")),
                "hash_scope": "Supplied record and excerpt bytes only; URL content not fetched or authenticated",
            }
            for source in data["sources"]
        ],
        "transformation_witness": data["witness"],
        "rights": data["rights"],
        "uncertainties": data["uncertainties"],
        "next_experiment": data["next_experiment"],
        "evidence": evidence_records(data),
        "milestones": data["milestones"],
        "execution_scope": (
            "Commands are committed argv specifications and are not executed by this adapter. Dependencies and "
            "permissions are research declarations, not a scheduler, grant of authority, or native schema extension."
        ),
        "token_fixture_policy": {
            "insight_job_bounty_whole_tokens": INSIGHT_BOUNTY_TOKENS_FIXTURE,
            "milestone_bounty_base_units": MILESTONE_BOUNTY_BASE_UNITS_FIXTURE,
            "reason": "Positive numeric fixtures required by unchanged native validators; no value or funding assumed",
            "cad_conversion": None,
            "cad_budget_scope": "Supplied planning hypotheses retained only in milestone annex records",
        },
        "native_draft_relationship": (
            "Insight's original Nova-Seed draft commits its own one-review-job list. The separate milestone FusionPlan "
            "is linked here and in the local manifest; the draft was not rewritten or asserted to be an on-chain seed."
        ),
    }
    return with_digest(body)


def milestone_specs(annex: dict[str, Any]) -> list[dict[str, Any]]:
    """Bind the complete research annex into exact five-field native JobSpecs."""
    return [
        {
            "goal": f"Research {item['id']}; annex SHA-256 {annex['sha256']}. {item['goal']}",
            "successMetric": item["successMetric"],
            "bounty": MILESTONE_BOUNTY_BASE_UNITS_FIXTURE,
            "duration": item.get("duration_seconds", 604800),
            "priceWeight": 5000,
        }
        for item in annex["milestones"]
    ]


MARK_INSPECTION = r"""
import {pathToFileURL} from 'node:url';
import {readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
const payload=JSON.parse(readFileSync(0,'utf8'));
let attemptedNetworkCalls=0;
globalThis.fetch=async()=>{attemptedNetworkCalls++;throw Error('Network disabled in local research inspection');};
const base=pathToFileURL(process.argv[1]+'/docs/assets/ascension-wallet/');
const protocol=await import(new URL('protocol.mjs',base));
const qualification=await import(new URL('qualification.mjs',base));
const client=await import(new URL('client.mjs',base));
const sha=text=>createHash('sha256').update(text).digest('hex');
const refusal=(label,fn)=>{try{fn();return {label,rejected:false};}catch(e){return {label,rejected:true,reason:e.message};}};
const routeArgs=(job,spec=job.spec)=>['0',String(job.index),JSON.stringify(spec),JSON.stringify(job.proof),'1',
  JSON.stringify(Array(3).fill('0x'+'00'.repeat(20)))];
const specs=payload.plan.jobs.map(job=>{
  const values=protocol.parseFields('route',routeArgs(job))[2];
  const bytes=protocol.tuple(protocol.METHODS.route.inputs[2],values);
  return {index:job.index,exactNativeFields:true,abiEncodedSpecSHA256:sha(bytes),
    encodingScope:'Pure five-field Spec ABI encoding only; no route transaction constructed'};
});
const claimedPublic={...payload.annex,schema:'agialpha.qualified-wallet-profile.v1',
  profile:'unreviewed-research-artifact',chainId:1,environment:'qualified-mainnet',mainnetQualification:true,
  newExposureEnabled:true};
const refusals=[
  refusal('Research annex cannot be a public qualification',()=>qualification.validateQualification(payload.annex,'public')),
  refusal('Relabelled public claim lacks source-pinned approval',()=>qualification.validateQualification(claimedPublic,'public')),
  refusal('Unregistered research profile cannot enter native MARK client',()=>client.validateProfile(claimedPublic)),
  refusal('An annex field cannot be added to the native Spec',()=>protocol.parseFields('route',
    routeArgs(payload.plan.jobs[0],{...payload.plan.jobs[0].spec,budget_cad:0}))),
];
const result={valid:refusals.every(item=>item.rejected),mode:'offline-local-artifact-inspection',
  specs,refusals,qualificationIdentitySHA256:sha(qualification.qualificationIdentity()),
  unsentReadCall:{method:'plan(uint256)',fixtureArgument:'0',calldata:protocol.callData('plan',['0']),sent:false},
  attemptedNetworkCalls,providerConfigured:false,walletConnected:false,rpcIssued:false,
  transactionConstructed:false,registryModified:false,
  scope:'Pure canonical codec/qualification/profile calls only; no live admission or authority established'};
console.log(JSON.stringify(result));
if(!result.valid||attemptedNetworkCalls!==0)process.exitCode=1;
"""


def mark_inspection(plan: dict[str, Any], annex: dict[str, Any]) -> dict[str, Any]:
    """Use actual MARK pure modules, never a provider or RPC-backed inspection."""
    node = shutil.which("node")
    if node is None:
        raise ValueError("Node is required for actual native MARK codec and refusal checks")
    result = subprocess.run(
        [node, "--input-type=module", "-e", MARK_INSPECTION, str(REPO)],
        input=encoded({"plan": plan, "annex": annex}),
        capture_output=True,
        check=False,
        timeout=30,
    )
    if result.returncode != 0:
        raise ValueError(
            "Native MARK local inspection failed: " + result.stderr.decode("utf-8", errors="replace")[:2000]
        )
    return json.loads(result.stdout)


def expect_refusal(name: str, function: Any, value: Any) -> dict[str, Any]:
    """Record an actual native verifier rejection without treating hashes as truth."""
    try:
        function(value)
    except (ValueError, TypeError, KeyError) as exc:
        return {"check": name, "rejected": True, "reason": str(exc)}
    raise ValueError(f"Expected refusal did not occur: {name}")


def native_checks(dossier: dict[str, Any], plan: dict[str, Any]) -> dict[str, Any]:
    """Recompute valid artifacts and exercise rehashed dossier/plan tampering."""
    verified_dossier = insight.verify(dossier)
    verified_plan = ascension.verify_plan(plan)
    forged_dossier = deepcopy(dossier)
    forged_dossier["result"]["ranking"][0]["scores"]["base"] += 1
    forged_dossier["sha256"] = insight.digest({k: v for k, v in forged_dossier.items() if k != "sha256"})
    forged_plan = deepcopy(plan)
    forged_plan["jobs"][0]["spec"]["goal"] += " tampered"
    forged_metadata = deepcopy(plan)
    forged_metadata["funded"] = True
    return {
        "insight_recomputed": verified_dossier == dossier,
        "fusion_plan": verified_plan,
        "tamper_refusals": [
            expect_refusal("Rehashed changed score rejected by recomputation", insight.verify, forged_dossier),
            expect_refusal("Changed job rejected by native plan verification", ascension.verify_plan, forged_plan),
            expect_refusal(
                "Extra funding claim rejected by native exact schema", ascension.verify_plan, forged_metadata
            ),
        ],
        "scope": "Deterministic native integrity checks; not independent scientific, commercial, or safety acceptance",
    }


def write_new_or_identical(path: Path, value: bytes) -> None:
    """Write a local result, refusing altered artifacts or symlink destinations."""
    if path.is_symlink():
        raise ValueError(f"Refusing symlink output: {path}")
    if path.exists():
        if not path.is_file() or path.read_bytes() != value:
            raise ValueError(f"Existing artifact differs; choose a new output directory: {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(value)


def build(input_path: Path, output: Path) -> dict[str, Any]:
    """Build unchanged native artifacts plus a separately committed research annex."""
    if output.is_symlink() or (output / "insight").is_symlink():
        raise ValueError("Refusing a symlinked artifact directory")
    raw = input_path.read_bytes()
    data = validate_input(insight.parse(raw))
    provenance = component_provenance()
    dossier = insight.evaluate(native_scenario(data))
    annex = research_annex(data, dossier)
    plan = ascension.compile_plan(milestone_specs(annex))
    native = native_checks(dossier, plan)
    mark = mark_inspection(plan, annex)
    artifact_values = {"insight/" + name: value for name, value in insight.artifacts(dossier).items()}
    artifact_values.update(
        {
            "selected-opportunity.json": encoded(data),
            "research-annex.json": encoded(annex),
            "fusion-plan.json": encoded(plan),
            "milestone-specs.json": encoded(milestone_specs(annex)),
            "source-provenance.json": encoded(provenance),
            "mark-inspection.json": encoded(mark),
        }
    )
    report = {
        "schema": "agi-alpha.native-linkage-verification.v1",
        "boundary": BOUNDARY,
        "input_file_sha256": sha256(raw),
        "normalized_input_sha256": insight.digest(data),
        "insight_status": dossier["result"]["status"],
        "nova_seed_drafts": len(dossier["result"]["novaSeedDrafts"]),
        "draft_selection_note": "No selection or source threshold is bypassed; a rejected native candidate yields no draft.",
        "insight_dossier_sha256": dossier["sha256"],
        "research_annex_sha256": annex["sha256"],
        "milestone_plan_root": plan["planRoot"],
        "milestone_count": len(plan["jobs"]),
        "native_checks": native,
        "mark_checks_passed": mark["valid"],
        "source_pins_match": all(item["matches_frozen_map"] for item in provenance["components"]),
        "runtime": {
            "python": sys.version.split()[0],
            "pydantic": importlib.metadata.version("pydantic"),
            "eth-hash": importlib.metadata.version("eth-hash"),
        },
        "files": {name: sha256(value) for name, value in sorted(artifact_values.items())},
        "limitations": [
            "Native scores rank supplied assumptions; sources, novelty and beneficiary acceptance are not authenticated.",
            "The source-linked assessments are researcher judgments, not output of an autonomous discovery engine.",
            "Exact bytes and native recomputation establish consistency, not external truth or chain qualification.",
            "The native draft is plaintext and unminted. No encrypted capsule, ownership, seed ID or funded campaign exists.",
            "Milestone commands are specified but not executed. Missing evidence remains explicitly unresolved.",
        ],
    }
    artifact_values["verification.json"] = encoded(with_digest(report))
    artifact_values["SHA256SUMS"] = "".join(
        f"{sha256(value)}  {name}\n" for name, value in sorted(artifact_values.items())
    ).encode("utf-8")
    for name, value in artifact_values.items():
        write_new_or_identical(output / name, value)
    return verify_bundle(output)


def verify_bundle(output: Path) -> dict[str, Any]:
    """Reinspect saved bytes, native recomputation and the annex-to-plan linkage."""
    if output.is_symlink() or (output / "insight").is_symlink():
        raise ValueError("Refusing a symlinked artifact directory")
    report = read_json(output / "verification.json")
    body = {key: value for key, value in report.items() if key != "sha256"}
    if report["sha256"] != insight.digest(body):
        raise ValueError("Verification record digest mismatch")
    expected_names = {
        "insight/scenario.json",
        "insight/dossier.json",
        "insight/jobs.json",
        "insight/nova-seeds.json",
        "insight/review-brief.md",
        "insight/SHA256SUMS",
        "selected-opportunity.json",
        "research-annex.json",
        "fusion-plan.json",
        "milestone-specs.json",
        "source-provenance.json",
        "mark-inspection.json",
    }
    if set(report["files"]) != expected_names or report["boundary"] != BOUNDARY:
        raise ValueError("Verification manifest file set or research boundary was altered")
    for name, expected in report["files"].items():
        path = output / name
        if path.is_symlink() or sha256(path.read_bytes()) != expected:
            raise ValueError(f"Artifact exact-byte mismatch: {name}")
    checksum_records = {**report["files"], "verification.json": sha256((output / "verification.json").read_bytes())}
    expected_checksums = "".join(f"{digest}  {name}\n" for name, digest in sorted(checksum_records.items()))
    if (output / "SHA256SUMS").read_text(encoding="utf-8") != expected_checksums:
        raise ValueError("Top-level exact-byte checksum list was altered")
    data = validate_input(read_json(output / "selected-opportunity.json"))
    dossier = read_json(output / "insight" / "dossier.json")
    annex = read_json(output / "research-annex.json")
    plan = read_json(output / "fusion-plan.json")
    if insight.canonical(dossier) != insight.canonical(insight.evaluate(native_scenario(data))):
        raise ValueError("Dossier does not recompute from the selected research input")
    if insight.canonical(annex) != insight.canonical(research_annex(data, dossier)):
        raise ValueError("Research annex or current evidence differs from recomputation")
    expected_plan = ascension.compile_plan(milestone_specs(annex))
    if insight.canonical(expected_plan) != insight.canonical(plan):
        raise ValueError("FusionPlan no longer binds the complete executable milestone annex")
    for name, value in insight.artifacts(dossier).items():
        if (output / "insight" / name).read_bytes() != value:
            raise ValueError("Native Insight artifact differs from discovery.artifacts output: " + name)
    provenance = component_provenance()
    if insight.canonical(provenance) != insight.canonical(read_json(output / "source-provenance.json")):
        raise ValueError("Source provenance changed; regenerate rather than asserting the old verification")
    checked = native_checks(dossier, plan)
    mark = mark_inspection(plan, annex)
    if insight.canonical(mark) != insight.canonical(read_json(output / "mark-inspection.json")):
        raise ValueError("Saved MARK inspection differs from current pure native checks")
    expected_summary = {
        "normalized_input_sha256": insight.digest(data),
        "insight_dossier_sha256": dossier["sha256"],
        "research_annex_sha256": annex["sha256"],
        "milestone_plan_root": plan["planRoot"],
        "milestone_count": len(plan["jobs"]),
        "nova_seed_drafts": len(dossier["result"]["novaSeedDrafts"]),
        "native_checks": checked,
        "mark_checks_passed": mark["valid"],
    }
    if any(report[key] != value for key, value in expected_summary.items()):
        raise ValueError("Saved verification summary differs from native recomputation")
    return {
        "valid": True,
        "output": str(output.resolve()),
        "boundary": BOUNDARY,
        "insight_dossier_sha256": dossier["sha256"],
        "nova_seed_drafts": len(dossier["result"]["novaSeedDrafts"]),
        "annex_sha256": annex["sha256"],
        "plan_root": plan["planRoot"],
        "milestones": len(plan["jobs"]),
        "native_integrity_checks": checked,
        "mark_local_checks": mark["valid"],
    }


def example() -> dict[str, Any]:
    """Return an explicitly synthetic format fixture, never a selected opportunity."""
    return {
        "opportunity": {
            "id": "format-fixture",
            "title": "Synthetic adapter format fixture",
            "sector": "Local research",
            "thesis": "Exercise native linkage without asserting a real opportunity or economic value.",
            "goal": "Verify a bounded native linkage fixture.",
            "successMetric": "Native recomputation succeeds and altered artifacts are rejected.",
        },
        "sources": [
            {
                "id": "s1",
                "title": "Synthetic fixture declaration",
                "url": "https://example.com/research-fixture",
                "excerpt": "Synthetic assessment fixture only; no empirical demand, deployment or commercial evidence.",
                "kind": "synthetic",
            }
        ],
        "assessments": {
            metric: {"low": 1000, "base": 2000, "high": 3000, "source": "s1"} for metric in insight.METRICS
        },
        "witness": {"status": "Synthetic fixture; no scientific result asserted"},
        "rights": {"input": "Synthetic local material", "external_actions": "None"},
        "uncertainties": ["No real opportunity, customer or field validation is represented."],
        "next_experiment": {"action": "Replace fixture with an explicitly selected source-linked research object."},
        "evidence": [],
        "milestones": [
            {
                "id": f"m{index}",
                "goal": f"Run local fixture stage {index}.",
                "successMetric": "The explicitly synthetic local command exits successfully.",
                "command": ["python", "-c", f"print('Synthetic fixture stage {index}')"],
                "acceptance": "Exit code zero is a format check only, not opportunity acceptance.",
                "budget_cad": 0,
                "dependencies": [f"m{index - 1}"] if index > 1 else [],
                "permissions": ["local-read", "local-execute"],
                "falsifier": "Local command cannot run.",
            }
            for index in range(1, 4)
        ],
    }


def main() -> int:
    """Run one local build, verification or example-writing action."""
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--input", type=Path)
    mode.add_argument("--verify", type=Path)
    mode.add_argument("--example", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        if args.example is not None:
            write_new_or_identical(args.example, encoded(example()))
            result = {"example": str(args.example.resolve()), "synthetic_fixture_only": True}
        elif args.verify is not None:
            result = verify_bundle(args.verify)
        else:
            if args.output is None:
                parser.error("--input requires --output")
            result = build(args.input, args.output)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0
    except (ValueError, KeyError, TypeError, OSError, subprocess.SubprocessError) as exc:
        print(json.dumps({"valid": False, "error": str(exc), "boundary": BOUNDARY}, indent=2), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
