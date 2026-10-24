# BLOOM∞ — current-source integration audit

## Scope and verdict

This is a read-only audit of four public `main` snapshots, assembled on 24 October 2026 UTC (23 October in Montreal). It is an implementation map, not a new release qualification, installed-fleet test, chain-state verification, or independent scientific reproduction. No repository was changed and no contract, wallet, provider, or fleet execution was invoked. Thirty-four locally materialized files have been byte-verified against their Git tree blob hashes; their exact SHA-256 values and immutable source URLs are in `integration_source_receipts.json`.

The usable integration boundary is **bounded local evidence and inactive work drafts**. Alpha supplies a strict data language, source-bound finite experiments, history, and separately authorized native runtime. Manager and Jobs expose explicit local-inspection receivers. Fleet has a separate installed execution and review path that requires current runtime, policy, session, and action authorization. A new scientific result can be exported and inspected immediately, but it must not be relabeled as a natively accepted Discovery campaign or as a qualified four-repository commercial workflow.

| Repository | Inspected commit | Tree |
|---|---|---|
| [AGI-Alpha-Agent-v0](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/commit/dfc79c4ae81ac612cbff9865a0af8389b6ff3de9) | `dfc79c4ae81ac612cbff9865a0af8389b6ff3de9` | `aea4336b84607b92a8fa699ef5583fc2bf5d56e3` |
| [AGIJobsv0](https://github.com/MontrealAI/AGIJobsv0/commit/9983478d42c32fe399f28dd9b0e0173f904b8a11) | `9983478d42c32fe399f28dd9b0e0173f904b8a11` | `1eb4743264c82ea16426d2038ba1270ca41827ae` |
| [AGIJobManager](https://github.com/MontrealAI/AGIJobManager/commit/c5958eae872458c2f3cac48fea0b4bbfadc6ac6c) | `c5958eae872458c2f3cac48fea0b4bbfadc6ac6c` | `0c7022fd0d70ab12803869493917c130497aa6d4` |
| [AGI-Fleet-Linux](https://github.com/MontrealAI/AGI-Fleet-Linux/commit/45759fb096faf8988f58ae5ea71248d0f35a97c7) | `45759fb096faf8988f58ae5ea71248d0f35a97c7` | `71a0ab1f0d2784ba552d0126903bd31d60262313` |

No conclusion below assumes that changing `main` after these snapshots inherits these observations. Publication owners and held operations remain controlled by their original records; this audit does not resolve any hold.

## 1. Four repositories: actual responsibilities

### Alpha: construction, checking, history, and separate native permission

The current [Discovery Lab guide](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/dfc79c4ae81ac612cbff9865a0af8389b6ff3de9/docs/discovery-lab/README.md) describes a supplied finite virtual workcell with three or four binary controls, six closed constructor stages, independent finite checkers, frozen future queries, and a workspace event history. This scope does not establish arbitrary invention, real material performance, customer revenue, or general intelligence.

The [existing native architecture](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/dfc79c4ae81ac612cbff9865a0af8389b6ff3de9/docs/agent/SUCCESSOR_ARCHITECTURE.md) separates protocol, state, mission, Jobs/Ascension, Chronicle, interfaces, and release. Its default candidate is a configuration of fixed maintained aggregation engines; arbitrary code requires the distinct explicit Docker path. A browser rehearsal is not a protected final verifier. Existing signed formats and Solidity commitments differ from the JavaScript data protocol and must not be silently interchanged.

The exact native types in [successor/protocol.py](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/dfc79c4ae81ac612cbff9865a0af8389b6ff3de9/alpha_factory_v1/core/runtime/successor/protocol.py) are useful for a paper architecture map. Mere creation of compatible JSON does not issue an authenticated receipt or grant:

| Boundary | Existing type | Relevant exact fields and implication |
|---|---|---|
| World | `WorldProgram` | `world_id`, `artifact_digest`, `inputs`, `state`, `transitions`, `predictions`, `invariants`, `outputs`, `uncertainty`, `assumptions`, `evidence`, `falsifiers`, `revision_history`. A model and its falsifiers are separate from execution permission. |
| Policy | `PolicyProgram` | `policy_id`, `artifact_digest`, `objective`, `decision_rules`, `admissible_actions`, `constraints`, `abstention`, `escalation`, `dependencies`, `configuration`. Proposed decisions do not authorize actions. |
| Proof | `ProofProtocol`, `ProofReceipt` | Protocol binds `candidate_release_digest`, `comparator_manifest_digest`, `environment_digest`, `evidence_commitment`, thresholds, randomization, exclusions, uncertainty, multiplicity, cost rule, validity, and `frozen_at`. Receipt binds those identities to an attributed outcome, `claim`, `evidence_scope`, `evaluation_units`, measurements, costs, failures, interventions, and exclusions. Trust and scientific qualification are separate checks. |
| Authority | `AuthorityEnvelope` | `grant_id`, `institution_id`, `mission_id`, `release_digest`, `subject`, `issuer`, `actions`, `tools`, `targets`, `resources`, `proof_ids`, `valid_until`, `context_digest`, `scope`, approval/monitoring/revocation conditions. One complete current grant must cover an action; independent grants cannot be combined. |

`ResourceBudget` distinguishes `limits`, `units`, `enforceable`, `unknown_costs`, and `stop_loss`. `MissionConstitution.accounting_rule` defaults to “each measured cost deducted once; unknown costs remain unknown”; `authority_ceiling` defaults to `none`. These existing distinctions fit the requested complete-cost ledger without inventing a new native meaning for monetary or measurement units.

### Manager and Jobs: distinct currency routes, inactive local review

The [Manager receiver](https://github.com/MontrealAI/AGIJobManager/blob/c5958eae872458c2f3cac48fea0b4bbfadc6ac6c/scripts/integrations/discovery-lab-work-request.mjs) and [Jobs receiver](https://github.com/MontrealAI/AGIJobsv0/blob/9983478d42c32fe399f28dd9b0e0173f904b8a11/integrations/alpha-agent/discovery-lab-work-request.mjs) expose `discoveryLabReceiverCapabilities()`, `inspectDiscoveryLabWorkRequest(raw, options)`, and `receiveDiscoveryLabWorkRequest(raw, options)`.

| Property | Manager | Jobs |
|---|---|---|
| Admission receipt schema | `agijobmanager/discovery-lab-admission/v1` | `agijobsv0/discovery-lab-admission/v1` |
| Route | `manager-usdc` | `jobs-agialpha` |
| Currency | `USDC6` | `AGIALPHA18` |
| Execution mode | `synthetic-local` | `synthetic-local` |
| Admission | `local-inspection-only` | `local-inspection-only` |
| External execution | `unprovisioned` | `unprovisioned` |
| Submission | `unsupported` | `unsupported` |
| Authority | `none` | `none` |

These receivers validate a current, caller-supplied `expectedBindings` snapshot and `expectedCommission`, then invoke the installed `inspectCampaign` function on the inert payload. They retain actual failure charges and unresolved native reservation exposure when a checker throws without a report. Admission states are `local-checked`, `local-rejected`, or `inconclusive`; unsupported schemas and execution modes report `unsupported` or `unprovisioned`. The successful local receipt still contains:

```json
{"commission":"DRAFT_NOT_SUBMITTED","reservedBaseUnits":"0","execution":"unprovisioned","review":"separate-review-required","settlement":"not-connected"}
```

`capabilityAcceptance` remains `not-granted-by-import`. The receipt's resource-accounting label distinguishes declared checking units and encoded bytes from measured `elapsedMs`; those counts are not measured CPU instructions or commercial currency.

Manager's [USDC implementation](https://github.com/MontrealAI/AGIJobManager/blob/c5958eae872458c2f3cac48fea0b4bbfadc6ac6c/scripts/lib/usdc.js) declares `USDC_DECIMALS = 6`, parses six-decimal nonnegative amounts into integer base units, and restricts canonical addresses by chain. This is a distinct accounting domain from Ascension's 18-decimal `$AGIALPHA` token. No exchange rate, valuation, or cross-token budget equivalence is implied.

The [Jobs installed runtime](https://github.com/MontrealAI/AGIJobsv0/blob/9983478d42c32fe399f28dd9b0e0173f904b8a11/integrations/alpha-agent/discovery-installed-runtime.mjs) checks an `INSTALLED_SOURCE.json` profile, `authority: none`, zero currency cap, pinned Alpha sources, and the deployment compatibility record; its extraction state is `EXTRACTED_INACTIVE_LOCAL_REVIEW_ONLY`. The [Manager installed runtime](https://github.com/MontrealAI/AGIJobManager/blob/c5958eae872458c2f3cac48fea0b4bbfadc6ac6c/scripts/integrations/discovery-installed-runtime.mjs) similarly checks a pinned source closure and an inactive `manager/discovery-alpha-capsule/v1`. Neither source file by itself proves a new downloaded installation passed.

### Fleet: installed execution path, live gates, honest local records

[SuccessorController](https://github.com/MontrealAI/AGI-Fleet-Linux/blob/45759fb096faf8988f58ae5ea71248d0f35a97c7/fleet/packages/AGI_Agent/successor/controller.mjs) uses the installed `Controller -> Studio -> Companion -> ComputeWorker` path. It owns no alternate worker, provider credential, local service, or wallet. `health()` requires an unlocked vault, enabled workstation companion, ready and unstopped gateway, matching current policy hash, and `isolated-public` runtime. `prepare()` requires a principal and stopped controller, verifies exact task scope, and returns a short-lived ticket. `execute()` requires `confirm === true`, the same principal/key/scope, an unexpired ticket and fresh unchanged runtime/policy. Statuses include `reserved`, `dispatched`, `blocked-or-uncertain`, and `stopped`.

[project.mjs](https://github.com/MontrealAI/AGI-Fleet-Linux/blob/45759fb096faf8988f58ae5ea71248d0f35a97c7/fleet/packages/AGI_Agent/successor/project.mjs) exposes `agi-fleet/successor-request/v1` with exact fields `schema`, `capsule`, `plan`. It checks mission and candidate hashes before compiling a `computer-work/v2` specification. Custom project preparation binds the entire public specification into the immutable mission and yields `authority: none`. The custom path is historical evidence, not automatic candidate or execution authority.

[receipt.mjs](https://github.com/MontrealAI/AGI-Fleet-Linux/blob/45759fb096faf8988f58ae5ea71248d0f35a97c7/fleet/packages/AGI_Agent/successor/receipt.mjs) requires `agi-studio-handoff/v1` and `agi-studio-run/v1`, exact spec/delivery hashes, `evidenceType: local-controller-record`, and `independent: false`. Its own comment states that a bound receipt is an editable historical controller record, not an attestation. `checkReturnedWork()` retains `independentController: UNVERIFIED`, `qualification: NOT_RUN`, `authority: none`, and `payment: unfunded`, even after local output checks.

[outcomes.mjs](https://github.com/MontrealAI/AGI-Fleet-Linux/blob/45759fb096faf8988f58ae5ea71248d0f35a97c7/fleet/packages/AGI_Agent/successor/outcomes.mjs) keeps `estimated`, `metered`, `invoiced`, `subscription-allocated`, and `unknown` cost bases distinct, and human time as observed or operator-reported active/waiting seconds. The controller explicitly records unknown provider billing. [Admission](https://github.com/MontrealAI/AGI-Fleet-Linux/blob/45759fb096faf8988f58ae5ea71248d0f35a97c7/fleet/packages/AGI_Agent/src/admission.mjs) returns `LOCAL_SIMULATION_ONLY` for chain ID 31337; live admission involves separate canonical USDC, policy, snapshot, budget, freshness, and signing checks. None were exercised here.

## 2. Exact shared work-request language

The [Alpha shared contract](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/dfc79c4ae81ac612cbff9865a0af8389b6ff3de9/examples/successor-capability/discovery-lab-contract.mjs) is byte-identical to the inspected Manager and Jobs copies. Important exact fields:

- Schema: `successor-discovery-work-request/v1`.
- Binding keys: `missionId`, `revision`, `purposeDigest`, `charterDigest`, `modelDigest`, `sourceDigest`, `evaluatorDigest`.
- Stage: one of `learn`, `think`, `design`, `strategise`, `execute`, `evolve`.
- Resource limits: `acquisitions`, `search`, `checking`, `memoryBytes`, `storageBytes`, `workerCapacity`, `installations`, `elapsedMs`; exact nonnegative safe integers.
- Inputs: `inputArtifacts`, at most six distinct SHA-256 digests; `payloadDigest` must equal the canonical payload commitment.
- Commission: exact `id`, `branch`, `route`, `currency`, `capBaseUnits`, `status`; only the two routes above, `capBaseUnits: "0"`, `status: "DRAFT_NOT_SUBMITTED"`.
- Bounded JSON: maximum 2 MB, safe integers, scalar Unicode, duplicate-key rejection, depth at most 32, bounded nodes, plain inert objects, no accessor values. Arbitrary floating-point values must not be silently coerced into integer commitments.

A new BLOOM harness can reuse this existing bounded import/canonicalization primitive with its preserved license and source hash. It should identify its own scientific payload schema and limitations explicitly. A syntactically valid request is not semantic qualification of an arbitrary calibration or synthesis experiment. The installed `inspectCampaign` expects the existing finite campaign and ancestry; forging that meaning would misstate integration.

## 3. Ascension contracts: implemented behavior

All source links in this section refer to the inspected Alpha commit and the production-source files under `contracts/ascension/`. The matching `tests/contracts/contracts/ascension/` copies are separate test inputs; current deployment snapshots can differ and were not treated as identical to main.

| Contract | Implemented responsibility | Boundary |
|---|---|---|
| [AscensionAccess](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/dfc79c4ae81ac612cbff9865a0af8389b6ff3de9/contracts/ascension/AscensionAccess.sol) | `Role { Business, Agent, Validator }`; live ENS or unexpired wrapper ownership plus owner-issued expiring admission evidence. Business root is `alpha.agi.eth`; Agent root is `alpha.agent.agi.eth`; Validator root is `alpha.club.agi.eth`. `eligible` requires admission and ownership of the registered node. | No resolver-address bypass. Registration alone is insufficient. Admission is a governor action, not self-certified by a research report. |
| [NovaSeed](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/dfc79c4ae81ac612cbff9865a0af8389b6ff3de9/contracts/ascension/NovaSeed.sol) | Transferable ERC-721; `Genome { capsuleHash, planRoot, evidenceHash, parent, jobs, creator }`. `seal()` requires eligible Business, nonzero commitments, 1–128 jobs, bounded URI, and ownership of any nonzero parent. | No genome/plan setter. `parent` records lineage, not inherited proof, authority, scientific usefulness, funding, or automatic execution. A changed plan requires a fresh seal under explicit authority. |
| [AscensionRiskOracle](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/dfc79c4ae81ac612cbff9865a0af8389b6ff3de9/contracts/ascension/AscensionRiskOracle.sol) | Stake-backed, eligible validators attest to a particular seed's current owner in a seven-day review; quorum 2–15; risk threshold; nonzero evidence. Supporters are rechecked by `green()`. Reviewer availability/capacity is reserved through one-time-bound marketplace. | `green()` is implemented approval state, not truth of a scientific claim or profitability. Transfer, expiry, or lost eligibility can invalidate the gate. |
| [AscensionJobMarket](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/dfc79c4ae81ac612cbff9865a0af8389b6ff3de9/contracts/ascension/AscensionJobMarket.sol) | `State { None, Auction, Assigned, Submitted, Paid, Failed, Refunded }`; `Spec { goal, successMetric, bounty, duration, priceWeight }`; at most 32 bids; collateral; bounded reputation-weighted price/time award; three distinct eligible validators with reserved capacity; result-hash-bound review; two approvals or rejections; exact payouts/refunds. | Two approvals settle the contracted result, not a generalized proof. Delivered work lacking review quorum becomes `Refunded` without treating missing review as proof of failure. |
| [AscensionMark](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/dfc79c4ae81ac612cbff9865a0af8389b6ff3de9/contracts/ascension/AscensionMark.sol) | `Phase { None, Funding, Bloomed, Closed }`; reversible bounded linear-curve funding lots; `bloom()` requires funded, unexpired Funding, current green seed owner/business, and unchanged live business ENS. It sets `phase = Bloomed`, sets `executionEnd`, and emits `Bloomed`. `route()` requires Merkle membership of an unposted plan leaf, budget, current authority/green state and execution horizon. | **Bloom does not spawn a successor or create wealth.** A plan cannot silently mutate. `collect`, `close`, and `reclaim` reconcile terminal jobs and unused capital; no profit guarantee is implemented. |

`AscensionJobMarket.hashSpec(index, spec)` is a double-keccak commitment over ABI-encoded index, goal hash, success metric hash, bounty, duration, and price weight. Mark validates the plan leaf with its actual index. The marketplace's job-level `specHash` uses index zero; those hashes must not be confused at a nonzero Merkle index.

[AscensionToken](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/dfc79c4ae81ac612cbff9865a0af8389b6ff3de9/contracts/ascension/AscensionToken.sol) binds the canonical `Constants.AGIALPHA`, checks 18 decimals, enforces exact deposits/payouts, and verifies supply destruction on burns. Job payouts burn 1% of each gross payout; the total 5% validator allocation is divided between two approving validators. These are actual token functions; they establish no token price or proven economic growth. Manager USDC must remain separately denominated.

## 4. Disposable local EVM fixtures

The source provides an appropriate disposable test boundary:

- [tests/contracts/hardhat.config.js](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/dfc79c4ae81ac612cbff9865a0af8389b6ff3de9/tests/contracts/hardhat.config.js) rejects any network other than in-process `hardhat`, any URL, and any fork configuration.
- [scripts/fixture.js](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/dfc79c4ae81ac612cbff9865a0af8389b6ff3de9/tests/contracts/scripts/fixture.js) calls `requireDisposableLocalNetwork`, resets local state, uses Hardhat signers, mock ENS/wrapper, synthetic token minting, and local versions of the five contracts. It supplies `createSeed`, `green`, `campaign`, `post`, `assign`, `deliver`, and `approve` helpers.
- [scripts/plan.js](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/dfc79c4ae81ac612cbff9865a0af8389b6ff3de9/tests/contracts/scripts/plan.js) constructs the bounded Merkle plan used by those fixtures.
- [test/ascension/lifecycle.test.js](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/dfc79c4ae81ac612cbff9865a0af8389b6ff3de9/tests/contracts/test/ascension/lifecycle.test.js) includes exact payouts/refunds, altered goals/metrics/budgets, nontrivial Merkle proofs, replay, and module-cross-wiring cases. Test names alone are not evidence they passed in this study.
- The checked [package.json](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/dfc79c4ae81ac612cbff9865a0af8389b6ff3de9/tests/contracts/package.json) pins Hardhat 2.29.1, ethers 6.17.0, OpenZeppelin 5.6.1 and solc 0.8.37. The checked [compiler policy](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/dfc79c4ae81ac612cbff9865a0af8389b6ff3de9/tests/contracts/scripts/compiler-policy.js) specifies `viaIR: true`, optimizer 200 runs with a declared pass-removal workaround, and `evmVersion: cancun`.

From a complete verified checkout with its locked dependencies installed, the existing focused local command is `cd tests/contracts && npm test -- test/ascension/lifecycle.test.js`. This audit did not install those dependencies or run that command. Any experiment using it must retain the full lockfile/source closure and actual exit/output; a fresh same-name Python state machine would not be execution of these Solidity contracts.

## 5. Stage-to-artifact mapping for the new local study

The six exact shared stage identifiers above permit an intelligible trace. “Identify” is the prior mission/charter framing step, not an extra literal stage accepted by `STAGES`. The new study should supply its own actual artifact paths and measured outputs when implemented:

| Requested stage | Existing binding or stage | Appropriate new-study input → output and check |
|---|---|---|
| Identify | Mission constitution, mission/revision/purpose/charter bindings | User need and constraints → frozen bounded task and acceptance rule; reject missing authority or unsuitable scope. |
| Out-Learn | `learn` | Development-only observations → empirical assumptions/calibration with sample provenance; preserve failed learning. |
| Out-Think | `think` | Current constraint and eligible operators → reasoned method comparison; preserve conventional fallback and full cost estimate. |
| Out-Design | `design` | Justified unresolved constraint → explicit construction/repair/composition artifact; skip when reuse already qualifies. |
| Out-Strategise | `strategise` | Frozen options and budgets → execution and stop decision; no post-hoc switch based on held-out answers. |
| Out-Execute | `execute` | Selected operator plus case → measured result, costs, qualification and failure record. |
| Out-Evolve | `evolve` | Accepted artifact and distinct future need → newly bound successor or normal stop; deletion/substitution interventions test actual dependency. |

This table maps concepts to the current vocabulary; it does not assert that the new study has executed the existing six-stage native Discovery payload. Do not invent ceremonial stages when no learning, construction, or successor is useful.

## 6. Export, restoration, and successor boundaries

The existing [native state implementation](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/dfc79c4ae81ac612cbff9865a0af8389b6ff3de9/alpha_factory_v1/core/runtime/successor/state.py) exports `kind: successor-portable`, signed source checkpoint/history, artifact bundle and historical proofs/evidence/memory, with **empty `active_proofs` and `active_grants`**. Restore rejects nonempty active proof/grant fields, requires a clean institution destination, treats imported records as historical, and sets `stopped=True`. `SuccessorRecord` distinguishes inherited memory from `new_proof_ids`, `new_admission_id`, and `new_grant_ids`.

The [Fleet sidecar](https://github.com/MontrealAI/AGI-Fleet-Linux/blob/45759fb096faf8988f58ae5ea71248d0f35a97c7/fleet/packages/AGI_Agent/successor/sidecar.mjs) has schema `agi-fleet/successor-sidecar/v1`, exact file inventory/bytes/hash, `walletBackup: excluded`, and `authority: none`. Restoring preserves the original pack, writes `RESTORED-CAPSULE.json`, and returns `qualification: NOT_RUN` and no authority.

For the new local experiment, export should preserve original source, protocol, input, output and ledger hashes; restoration should first reconstruct inactive history, then revalidate the current environment, artifact, policy and permitted execution scope. A matching parent hash alone is insufficient to revive proof or permission.

## Recommended minimal implementation boundary

1. Keep the new scientific runner and its results independently named and frozen. Reuse the verified strict canonical/import primitive with attribution if useful.
2. Export a source-bound scientific bundle and readable report. Map World/Policy/Proof/Authority to exact existing type names without issuing native signatures, grants or eligibility claims.
3. Exercise the actual existing receiver only on an authentic supported finite fixture, clearly separate from the new scientific outcomes. An unsupported new-study schema should remain a readable explicit refusal.
4. If the disposable Solidity dependencies are available, run a focused local contract fixture demonstrating unchanged-plan enforcement and explicit fresh-seed lineage. Keep its synthetic accounting separate from scientific cost/revenue evidence.
5. Keep Fleet installed dispatch, runtime acceptance, proof trust and live settlement outside any claimed integration until their existing owners and ordinary process supply the required evidence. This is a scope fact, not a new review gate introduced by this audit.

## Audit limitations

All claims here are grounded in inspected source and exact source-identity checks. No tests, browser journeys, deployed contract reads, actual installation, review authorization, external customer acceptance, or financial transactions were performed. Direct `git ls-remote` failed because the workspace network proxy was unavailable; the supported read-only GitHub connector supplied the exact public source. This transport failure was not retried through a bypass.
