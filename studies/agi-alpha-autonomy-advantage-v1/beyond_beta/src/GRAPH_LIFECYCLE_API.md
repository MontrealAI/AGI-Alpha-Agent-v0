# BeyondBeta lifecycle and access adapter

This module is an offline, executable research implementation of candidate registration, complete-cost net-alpha assessment, independent validation, canonical admission, network discovery and guarded reuse. It is an additive layer for an existing execution system. It does not run a new agent runtime or contact identity, model, customer, payment or settlement services.

The implementation uses actual **AES-256-GCM authenticated encryption** for capsules and actual **Ed25519 signatures and verification** for ephemeral fixture identities, validation records, admission receipts and reuse permits. Keys exist only in process memory. Eligibility and role assignments are explicitly modeled fixtures; there is no live ENS authentication, EIP-712 verification, ZK policy proof or mainnet enforcement. Existing AGI Jobs club roles are unchanged. The only reused authority primitive is the unchanged direct-agent fixture predicate from `venture_creation/src/authority_fixture.py`, already checked against the native JavaScript foundation.

## Integration surface

```python
from graph_lifecycle import BeyondBetaGraph, OfflinePrincipal, authority_fixture
from fixture_factory import (
    make_fixture_environment, fixture_artifact,
    matched_evidence, bind_cost_ownership, qualify, mission_for,
)

# Fictional example only. Production simulation supplies its fresh frozen policy.
graph, people = make_fixture_environment()
key = graph.create(
    people["creator"], people["writer"], fixture_artifact("solver"),
    skill_id="example-solver", version=1, shareable=True, epoch=0,
)
evidence = matched_evidence(
    graph, key, candidate_costs=[80, 80], comparator_costs=[100, 100],
    construction_micros=10, allocation_uses=1, case_prefix="independent-a",
)
assessment = qualify(graph, people, key, evidence, epoch=0)
if assessment["qualified"]:
    graph.admit(people["admitter"], key, epoch=0)
    available = graph.discover(people["reader"], epoch=0)
    permit = graph.authorize_reuse(
        people["executor"], key, mission_for(graph, "solver"), epoch=0,
    )
    invocation = graph.resolve_reuse(people["executor"], permit, epoch=0)
```

The example's numbers are handwritten control values, not prices, measured resource costs, quality priors or study defaults. Construct `BeyondBetaGraph(custom_policy, beta, inventory, authority_fixtures)` for the actual experiment. Do not edit `graph.policy` or `graph.beta` in place: hashes deliberately detect uncommitted mutation.

| Method | Purpose and main gate |
|---|---|
| `create(creator, writer, artifact, ..., epoch)`; alias `register` | Bind immutable skill/version, creator/writer, typed artifact, dependencies, policy and initial Beta; encrypt capsule. |
| `comparison_context(key)` | Return current policy/Beta/inventory hashes and every required matched comparator arm. |
| `register_evidence(writer, key, evidence, epoch)` | Bind fresh matched evidence and explicit complete-cost records. |
| `assess(assessor, key, epoch)` | Compute paired net alpha against competent Beta and every relevant current inventory alternative. |
| `validate(validator, key, epoch, verdict)` | Sign the exact assessment/evidence/capsule/policy using a distinct eligible validator. |
| `admit(admitter, key, epoch)` | Recheck all current bindings and positive net-alpha/quality gates, then promote canonically. |
| `discover(agent, epoch, function=None)` | List currently usable shared admissions for every eligible direct agent; no forced usage. |
| `authorize_reuse(executor, key, mission, epoch)` | Issue a scoped, expiring execution permit after current admission and dependency checks. |
| `resolve_reuse(executor, permit, epoch)` | Recheck current state at dispatch; release plaintext IR only to an actor with both execution and retrieval rights. |
| `retrieve(agent, key, epoch)` | Explicit plaintext retrieval right, without authorizing execution. |
| `export_capsule(agent, key, epoch)` | Explicit export right; returns ciphertext and commitments, never the decryption key. |
| `advance_beta`, `advance_inventory`, `advance_policy` | Version baseline/policy/inventory and require fresh relevant proof before reuse. |
| `revalidate(writer, key, fresh_evidence, epoch)` | Register new evidence, then repeat assessment, validation and admission. |
| `retire`, `revoke` | Irreversibly remove future authority while preserving audit provenance. |
| `record(key)`, `audit_log()` | Read copied records and typed commitments; these are never a fallback execution source. |
| `failure_memory(agent, epoch, function=None)` | Read separate non-executable failure hints and their proof bindings; never return positive admission or execution authority. |

All epochs are nonnegative integers supplied by the trusted simulation/event loop. The graph rejects time reversal. Refused unauthorized requests do not advance that clock; the implementation is not a distributed trusted-time service.

## Identity and role separation

An `OfflinePrincipal` generates an ephemeral Ed25519 key. `authority_fixture(principal, roles)` binds its public key to a direct `label.agent.agi.eth` fixture and declares eligibility, expiry and revocation. A deeper name such as `child.label.agent.agi.eth` does not inherit authority. Signature possession authenticates only the enrolled offline key, not a real ENS controller.

Roles are separately granted: `creator`, `writer`, `assessor`, `validator`, `admission`, `execution`, `retrieve`, `export`, `compose`. Assessors cannot assess their own created/written candidate; validators must differ from creator, writer and assessor. Admission cannot be performed by the candidate's creator, writer or any validator signer for that admission. The newly supplied Navigator Ω + SEIZE v5.0.0 §5.2 (physical PDF page 20, printed page 10, Equations 26–30) explicitly requires Producer ≠ Verifier and Verifier ≠ Admitter; the example assigns these to distinct automated fixture principals. These are automated role separations, with no permanent human staffing assumption.

Every eligible agent can discover every current shareable admission, regardless of its execution role. Retrieval, export, composition and execution permissions remain separate. An executor that receives plaintext has explicit retrieval permission. This does **not** provide execute-only code secrecy, prevent copying by an authorized plaintext recipient or erase previously disclosed plaintext after revocation. All new guarded dispatches still recheck current authority and admission.

Private retention is permitted only when `policy.privateAblation` is explicitly true and `create(..., shareable=False)` is used. The creator remains its private owner. A foreign private dependency cannot be inserted into another creator's private bundle, and a private dependency cannot be exported through a shared wrapper. Compose ownership/permissions are checked recursively.

## Shareable artifact boundary

Capsules contain only `beyond-beta-shareable-ir/v1`: a declared function, a bounded acyclic list of policy-approved operators, references to prior nodes/inputs, approved public parameter keys and approved public provenance identifiers. They contain no free-text prompts, client records, arbitrary constants, URLs, file paths, annotations, code blobs or binaries.

This is a **narrow typed allowlist**, not a general confidential-code detector, semantic redactor or guarantee against all information encoded in program structure. The operator/public-parameter/provenance policy must itself be approved. Client inputs remain outside the retained artifact. A real arbitrary-code packaging integration would need additional controls and evidence; it is not implemented here.

## Complete-cost net alpha

Each evidence object binds the candidate, current policy, competent Beta, relevant inventory snapshot, capture epoch, distinct cases, evidence basis and exactly the required arm names. An internally retained comparator must currently pass the same usable-admission predicate as discovery at the graph's trusted clock; expired, revoked, Beta-stale and comparison-stale receipts do not represent available alternatives. A foreign private artifact is also excluded because the candidate's owner cannot access it. External software inventory uses its explicitly declared availability flag. Every arm uses the same ordered case identifiers and the same externally supplied per-case value. Each outcome records acceptance, critical failure and explicit known costs in all twelve categories:

`production`, `verification`, `correction`, `tooling_compute`, `integration`, `support`, `maintenance`, `adaptation`, `revalidation`, `construction`, `failed_research`, `search`.

Unknown, missing or negative costs fail. A known zero is allowed; the graph cannot independently prove that a caller's zero is truthful. Evidence provenance and independent checking remain necessary. The `costs(...)` helper fills known-zero categories for fixtures; an economic adapter must not use it to disguise unknown costs.

For arm \(a\), case \(i\), case value \(v_i\), execution cost \(c_{ai}\), complete fixed cost \(F_a\), and declared finite allocation uses \(u_a\), the assessed net value is

\[
z_{ai}=\mathbf{1}_{\mathrm{accepted}}v_i-c_{ai}-F_a/u_a.
\]

The adapter computes paired mean differences against **each** required alternative and subtracts a predeclared multiple of their paired standard error. It accepts only if every resulting lower value exceeds the policy's minimum net alpha, the candidate meets the declared acceptance fraction, and there are no recorded critical failures. Candidates cannot choose or inject an uncertainty allowance. This is a finite-evidence decision rule, not a distribution-free confidence guarantee or proof of market demand. Cost per accepted outcome is reported separately and is undefined when acceptance is zero; failed attempts retain their costs.

Allocation uses are bounded by policy and remain an externally justified reuse assumption. A large allocation denominator is not observed demand. The graph binds and checks the declared evidence; the owning financial experiment must independently reconcile actual/simulated paid resources, complete program losses, accepted outcomes, demand and cash.

### Paid-job learning and ownership of costs

The primary accounting boundary separates **A: original delivery**, **B: incremental retention/admission/distribution**, and **C: optional separate research**. Work already charged to a completed job in A is historical origin provenance. It is not charged again to the prospective Alpha calculation. All incremental B and C costs remain in the candidate's complete fixed retention cost; they cannot be erased by labeling them as delivery experience.

Every evidence object contains the following explicit binding:

```python
"costOwnership": {
    "schema": "beyond-beta-cost-ownership/v1",
    "originJobCosts": [{
        "jobId": "completed-job-id",
        "ledgerCommitment": "64-character-lowercase-sha256",
        "costMicros": 123,
        "ownership": "DELIVERY_A_ALREADY_CHARGED",
    }],
    "retentionEntries": [{
        "chargeId": "paid-incremental-retention-charge",
        "ledgerCommitment": "different-64-character-sha256",
        "costs": costs(construction=45, verification=12),
        "ownership": "INCREMENTAL_RETENTION_B",
    }],
    "researchEntries": [{
        "chargeId": "optional-separate-research-charge",
        "ledgerCommitment": "another-distinct-64-character-sha256",
        "costs": costs(failed_research=7),
        "ownership": "OPTIONAL_RESEARCH_C",
    }],
}
```

The values above are schematic fictional micros, not calibrated costs. The real adapter must bind ledger commitments to its actual simulated paid bills. The graph itself neither makes payments nor independently proves ledger truth.

`bind_cost_ownership(evidence, origin_job_costs=..., retention_entries=..., research_entries=...)` copies the evidence and derives candidate `lifecycleCosts` from B+C. `matched_evidence(..., cost_ownership=...)` accepts an exact ownership object; its lifecycle totals must already agree. The default helper uses explicitly fictional B commitments for control fixtures. It must not be presented as measured or paid evidence.

Category totals of B+C must equal candidate `lifecycleCosts` exactly. A is excluded. No ledger commitment can occur in both A and B/C. Identical A provenance may be referenced in later revalidation without a new charge, but its ownership, amount and job binding cannot change. B/C charge IDs and ledger commitments likewise cannot be rebound or moved into free origin provenance. Assessment outputs expose origin cost, incremental B, optional C and the resulting Alpha lifecycle denominator separately.

All paid fixed initial qualification categories are carried forward when an unadmitted candidate is repaired. Failed initial qualification also records all matched arms' execution cost as failed research for the next initial assessment. Reassessing identical evidence cannot duplicate that charge. A never-admitted candidate cannot relabel the next attempt as prospective revalidation or erase its build/research costs.

Only a previously admitted skill can use prospective revalidation. Its fresh comparison excludes already-paid construction from the prospective hurdle, retains the original construction amount in recovery history, and must use new case IDs. The owning ledger still reports complete historical program value; a positive retention decision does not erase an earlier loss or prove complete investment repayment.

### Separate failure memory

Negative assessments and validator repair/rejection decisions append bounded records to a separate failure-memory collection. These records contain function, evidence/assessment/policy/Beta hashes, reasons and epochs. They contain no executable artifact and confer no positive graph admission, discovery ranking or production authority. Repeating the same failure does not duplicate it. Eligible agents may query `failure_memory` as a research hint; any subsequent search, repair or qualification remains a separately charged process with fresh evidence and all normal gates. Failure memory does not make a failed capability productive by definition.

## Compositions and support-only components

Every composition binds exact dependency keys and artifact hashes and supplies separate independent cases that do not reuse component validation cases. New component versions, revocation or retirement cannot be substituted through old history. New relevant inventory stales older standalone alpha receipts; irrelevant function updates do not. A successful fresh revalidation also advances the relevant comparison epoch when it restores an available alternative. An attempted duplicate admission cannot advance it because the mandatory validation stage has already been consumed.

Complementarity does not require every component to have profitable standalone Alpha. `create(..., support_only=True, support_construction_micros=...)` creates a confined support artifact. Its declared support construction cost covers incremental B/C retention or separate research, not original paid delivery A. A component obtained during paid delivery can have zero additional support construction; subsequent extraction, sanitization, testing and packaging still cost B/C. It cannot be canonically promoted, discovered or independently dispatched. A bundle may use it only after its own complete matched alpha/quality assessment and independent composition validation. The bundle evidence binds the **deduplicated transitive** incremental support construction costs, so a cheap wrapper cannot hide an expensive descendant. Unadmitted support components require their owner's compose consent; the current narrow implementation permits their owner to compose them and supplies no foreign-owner delegation API.

A same-function parent may be used internally by a newly qualified bundle without restoring the parent's standalone Alpha after the bundle changes the comparison frontier. Its current version, authority, Beta/policy, evidence age and revocation checks still apply. The bundle's distinct evidence authorizes that confined use. This exception never authorizes a direct historical lookup or standalone dispatch.

## Commitments and evidence boundary

The append-only event history uses typed, domain-separated SHA-256 hashes. The Merkle implementation declares UTF-8 sorted-key integer JSON, separate leaf/node domains and duplicate-last odd-leaf handling. Validation and admission receipts bind the relevant artifact/capsule/evidence/policy/Beta/dependency commitments and historical log roots. Those commitments establish integrity. Current state and proof checks establish guarded eligibility. Neither proves commercial value, truthful measurements or live identity.

Adversarial controls:

```bash
python3 beyond_beta/tests/test_graph_lifecycle.py
```

Independent review reproductions and corrected runs are retained separately under `beyond_beta/foundations/` and `beyond_beta/validation/`. All numerical examples in those controls are fictional; no calibrated economic worlds or customer transactions execute.

## Existing native planning integration

`beyond_beta/src/native_bridge.mjs` reuses the unchanged `venture_creation/src/native_integration.mjs` projection adapter, which invokes the unchanged `native_snapshot/canonical/shadow-ledger.mjs` `planMission` function and the existing direct-agent fixture `authorityStatus` predicate. It does not invoke the historical study's qualification rules. BeyondBeta admission and guarded reuse execute in this module before their audit root is bound into the native projection input.

The batch DTO has schema `beyond-beta-native-input/v1` and `worlds` entries containing `id`, `projection` (the unchanged CashBook `nativeProjectionInput`), `graphAuditRoot`, optional `graphSourceHash`, and `authorityChecks` containing `{fixture, week}` records. The CLI preserves zero observed revenue and unknown actual complete cost while reconciling simulated accrual and cash after obligations/reserves, with the native cents boundary declared in its output.

```bash
node beyond_beta/src/native_bridge.mjs INPUT.json NEW_OUTPUT.json
python3 beyond_beta/tests/test_native_smoke.py
```

The smoke runs an actual local graph admission/reuse, pays fictional A and B costs in the existing finite CashBook, then executes two native planning calls and three authority predicates. Its source hashes, input, graph audit and native outputs are retained in `beyond_beta/validation/native-smoke.json`. The initial fixture's integer-canonicalization refusal is preserved in `native-smoke-development.json`. This demonstrates integration with existing inert planning infrastructure; it is not model execution, live authenticated permission enforcement or a professionally accepted customer delivery.
