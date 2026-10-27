# Research lifecycle for retained Alpha

This additive module implements and tests a **modeled** retained-capability lifecycle for **Paid Work. Retained Alpha. Expanding Possibility.** It reuses the exact authority and typed-commitment primitives pinned in `upstream/PROVENANCE.json`. It does not deploy a second Jobs protocol or alter existing `*.club.agi.eth` roles, contracts, settlement, or governance.

The local controls establish software behavior. They do not establish real ENS ownership, cryptographic validator identity, live production enforcement, frontier-model invention, or real customer value. A positive modeled assessment is explicitly distinct from empirical operational validation.

## Lifecycle and authority

The state transition is `CANDIDATE → EVIDENCED → ASSESSED → VALIDATED → ADMITTED`. A failure can reject the candidate; an admitted record can be revalidated, superseded by a separately admitted replacement, revoked, or retired. The required checks bind the exact candidate/version, current competent Beta, scope, environment, admission policy, comparison universe, prerequisite versions, evidence, costs, and expiry. Candidate or evidence storage alone grants no future influence.

The Alpha assessment comes from `model/alpha_gate.mjs`. It requires fresh paired observations, a positive conditional lower bound after the supplied remaining lifecycle and evaluation costs, complete cost accounting, and correctness checks. This graph verifies the bindings and admission sequence; it cannot establish that supplied economic assumptions or evaluator outputs describe the world. In the current paid-work study, the caller must assign already-paid job development to ledger A and pass only additional retention/reuse or optional research costs from B/C. The graph does not deduct A a second time.

Identity, validation, root publication, access, and action permission are separate checks:

| Boundary | Implemented behavior | Qualification |
|---|---|---|
| Eligible validator | Only one direct label before `.agent.agi.eth`; creator self-validation is rejected under the default policy | Authenticated with an explicit synthetic authority fixture |
| Creator/root writer | Current creator controller must authorize a typed root transition with current policy, epoch, previous root, and nonce | No actual ENS lookup or transaction |
| Admission | Positive current assessment, eligible validator evidence, current prerequisites, and creator root publication | Modeled admission, not real-world capability certification |
| Discovery | Every authenticated network member can discover an eligible shareable capability | Discovery does not record adoption or value |
| Access | Retrieve, execute, export, and compose are separately checked; scope, freshness, dependency state, and revocation are checked each time | In-process research access control |
| Execution | A separately supplied mission-authority callback is required even when the capability is admitted | Adapter supplies a declared simulated authorization; no external action is executed |

The graph never gives nested names authority by suffix matching. Existing Jobs club validators are not accepted in this **additional agent-only layer**; their existing Jobs authority remains unchanged. A new Beta or policy version invalidates affected prior bindings until fresh revalidation. Revoked, retired, superseded, or rejected records cannot be restored by revalidation or importing an old snapshot. The API intentionally has no history-import operation. Canonical promotion requires an already current admission and is checked again when resolved.

## Network availability and optional use

A manifest declared `shareable: true` must allow network-wide retrieve, execute, and compose access. Selective recipient distribution cannot be represented as shareable admission. Each member still chooses whether to use the capability. `available()` performs a dry-run eligibility/access check and creates no adoption event; `reuse()` records a separately authorized **modeled** access event. It returns `actualExecution: false`.

Composition pins exact prerequisite IDs, versions, and candidate digests and recursively checks that each prerequisite remains current. Complementary bundle components are not independently admitted by admitting their bundle. A caller requesting only part of a validated bundle is rejected. Existing equivalent implementations or declared equivalence keys, and capabilities already in the declared Beta baseline, are rejected as redundant. Equivalence keys are a declared semantic input; this module does not solve general program equivalence or prove novelty.

## Private capsules, commitments, and evaluation separation

`crypto_capsule.mjs` performs real local AES-256-GCM encryption with a random 256-bit ephemeral key and random 96-bit nonce. Candidate/context commitments are authenticated as additional data. Public snapshots include ciphertext and hashes; they exclude keys and plaintext capsule contents. Keys remain only in the local closure and are not persisted. Losing that process loses the demonstration keys. This is not an operational key-management system, on-chain encrypted store, or zero-knowledge proof implementation.

The economic adapter defaults to `snapshot({includeCiphertext: false})`. This reproducible projection retains algorithm, context commitment, and byte lengths while omitting random ciphertext, nonce, tag, and ciphertext digest. The typed public graph roots commit to the fixed payload/candidate/evidence bindings, not those random bytes. The low-level graph defaults to including ciphertext for local cryptographic inspection. A dedicated control verifies identical economic snapshots across two independently encrypted instances and different ciphertext when explicitly requested.

Authorized plaintext retrieval, execution integration, composition, or export can reveal content to the authorized recipient. Once plaintext is available it can be copied; an `export: false` API policy cannot provide digital-rights enforcement against a recipient that already received plaintext. Revocation blocks subsequent graph-mediated access and does not erase previously disclosed content. Encryption and Merkle inclusion establish neither truth nor economic Alpha.

Protected evaluation values can be registered with `protectEvaluationMaterial()`. The module rejects registered values and reserved scorer/held-out-case fields in public manifests, evidence, assessments, private shared capsules, and failure memory. This is a tested defense against known or explicitly labeled leakage. It cannot recognize arbitrary undeclared semantic encodings of a secret. The evaluator must retain separate custody of protected cases and scorer internals; process isolation and production security are outside this research implementation.

Failure memory is a separate record set labeled `FAILURE_MEMORY_NOT_ALPHA`, with `positiveCapability`, `admissionAuthority`, and `executionAuthority` all false. A failed candidate may inform an external research policy, but the failure record cannot be admitted as a positive capability or bypass the ordinary gate. Hash commitments to failure evidence do not themselves prove a failure explanation.

## Integration API

Import `createModeledNetwork` from `graph/simulation_adapter.mjs`:

```js
const network = createModeledNetwork({
  members: ['atlas.agent.agi.eth', 'lyra.agent.agi.eth'],
  betaVersion: 'beta-1',
  policyVersion: 'beyond-beta-alpha-policy-v1',
  scopeDigest, environmentDigest
});

const bindings = network.assessmentBindings({
  id, keys, owner, betaVersion, comparisonUniverse,
  week: completionWeek,
  expiryWeek: evidenceExpiryWeek,
  assetExpiryWeek: fullUsefulLifetimeExpiryWeek
});
// Caller uses fresh held-out paired observations and charges the incremental
// evaluation/resource costs once when constructing the assessment.
const admitted = network.admit({
  id, keys, owner, assessment, readyWeek: completionWeek,
  expiryWeek: fullUsefulLifetimeExpiryWeek,
  comparisonUniverse: currentRecipientComparisonUniverse
});
const eligible = network.available({id, member, week});
```

`assessmentBindings()` prepares an immutable descriptor without advancing graph time. It can therefore be called at investment start with a future completion week. Its future timestamp is only a prepared binding; the graph cannot admit it early. Pass the **current** recipient comparison universe again at completion. If that context or the network comparison inventory changed, the old assessment fails closed. Do not give it future latent outcomes.

All digest strings are 64 lowercase hexadecimal characters without a `0x` prefix. All times are integer simulation weeks. `expiryWeek` is the evidence deadline; `assetExpiryWeek` is the immutable asset useful-lifetime ceiling. Fresh revalidation may extend evidence beyond a previous evidence deadline, but cannot extend the asset lifetime or resurrect a terminal record. `advanceBeta(version, week)` prevents rollback to any previous version. `retire(id, reason, week)` fails closed for unknown or terminal records.

The low-level lifecycle additionally exposes policy/authority-state changes, canonical promotion, supersession, revocation, and independently supplied membership proofs for targeted research controls. Its manifests and transition proposals are owned copies; mutation of a returned snapshot cannot change live state. Publication uses the unchanged upstream `SHA256_RESEARCH_V1` typed forest and per-creator epoch chain. This research profile is not byte-compatible with the foundational production Keccak profile.

## Reproduce the controls

From the repository root:

```sh
node studies/beyond-beta-network-v1/graph/lifecycle.test.mjs
```

`results/graph_qualification.json` records **41/41 passing targeted controls**, including unauthorized/wrong-purpose/tampered validation, creator control, direct-label boundary, stale proposals, typed inclusion, canonical bypass prevention, terminal-state history, Beta/policy drift, evidence expiry, dependency revocation/version pinning, bundle scope, ciphertext/context/key authentication, protected evaluation material, failure-memory separation, completion-time comparator change, evidence/asset lifetime separation, and reproducible economic projections with genuinely randomized local encryption.

The first attempt passed 39/40; its sole failure was a test trying to mutate an intentionally frozen fixture binding before reaching the gate. The test now clones the deliberately adversarial input. The second attempt passed 40/40. The third adds the requested ciphertext-redaction projection and passes 41/41. All attempts and logs remain in `evidence/implementation_history/`. These controls are bounded software tests, not an exhaustive security audit. Native monorepo CI, deployment checks, live ENS, production model calls, and release qualification were not run for this isolated study.

## Sources and prototype boundaries

Exact immutable source URLs, Git objects, byte hashes, read coverage, and the source-to-implementation witness map appear in `evidence/graph_sources.json`. GoalOS V97.4, v114 Merkle Roots, and PROOF LOOPS were read as architecture/research foundations. The combined Gym/Specialist ASI/SUCCESSOR Ω v2.1.0 manuscript supplies further separation of formation, protected proof, admission, authority, and allocation; its Ω definition is stronger than this simulation.

The requested V93 HTML was located in the subsequently identified `MontrealAI/MontrealAI.github.io` repository and its visible text and complete embedded JavaScript were read. It is a declared browser-local teaching prototype: sliders and synthetic bundle records set proof/utility scores, and later missions are generated from text templates. Static inspection found that its canonical-promotion function does not require prior admission and its next-mission function does not recheck whether a historical Chronicle skill was retired. These limitations are preserved in `evidence/v93_source_readout.md`; they are evidence about that prototype, not evidence against frontier capability. The new lifecycle's already-passing controls require prior current admission and prevent old-history resurrection. No existing V93 source was modified.
