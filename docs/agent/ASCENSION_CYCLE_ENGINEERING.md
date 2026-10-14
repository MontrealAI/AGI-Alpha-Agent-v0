[Project notice](../DISCLAIMER_SNIPPET.md)

# Ascension complete cycle: implementation and evidence

## Inspected source and initial gap matrix

Integration owner: the implementation coordinator. Source inspected: PR #4779 at
`89b6f78b83a6643416649173d7d16b6d1c7a65c1`, on merged MARK main
`c38f430d5a07064ad7c19ae761e91eaad3e48efe`. At inspection #4779 was an open draft,
with no submitted reviews or inline review threads. The latest MARK acceptance
run passed; other current-head checks were still running. These are observations,
not approval or commissioning evidence.

| Requirements | Existing implementation | Gap / minimal addition | Acceptance / review |
|---|---|---|---|
| 01–35, 56 | Existing Studio, shared MARK client/session, exact compiler, capsule, storage and local EVM journey | Preserve and extend; do not create a second wallet or journal | Existing Nova/MARK suites; independent integration review |
| 36–37, 53 | Canonical 12-node graph; one seed package per Studio session | Add compatible outer project/cycle manifest and observable graph/history | Graph topology and recovery tests; frontend review |
| 38–40, 57–61, 65 | SUCCESSOR seal, assignment, controller trust and settlement importer | Connect portable Studio requests to those production APIs and actual bounded executor | Preposting, grant, exact output, negative report and attribution tests; native trust review |
| 41–47, 71–72 | Live campaign/job reads and exit transactions | Add owner-specific reconciled projections; never sum backing custody with claims | Integer accounting, stale/reorg and shared-custody tests; accounting review |
| 48–51, 68–70 | SUCCESSOR evaluation and fixed workbench adapters | Freeze comparable evaluation and carry permitted artifacts into a distinct mission | Positive/negative evaluation and new-input/run/settlement tests; evaluation review |
| 29–30, 52, 62–64, 76 | Readable recovery v1 and signed native historical records | Add encrypted full-project outer export; preserve originals and require fresh trust | Tamper, wrong key, no authority replay and interruption tests; recovery review |
| 54, 77–80 | Exact-source Hardhat and Chromium harness, existing release acceptance | Extend evidence index and production-path two-mission qualification | Current-source generated UI/native/EVM evidence; release review |
| 12, 31–32, 34, 55, 67, 74 | Storage adapter, bounded optional Computer Use and deployment registry | External account/device/human/provider/canary trials remain separate prerequisites | Not performed without actors/access/authorization; no corresponding claim |

No contract, archived source, compiler lock or original diagram change is planned.
Necessary shared-source edits are confined to Studio integration, native command
integration, generated-asset inventory and existing acceptance wiring. Production
qualified profiles remain empty and archived Mainnet exposure remains blocked.

Implementation, executable tests, field verification and commissioning are separate
states. The evidence index must name any remaining software blocker as well as
unperformed external trials; a checksummed import is neither authority nor a chain
observation.

## Scope, source identity and acceptance meaning

The implementation extends the existing `/ascension/mainnet/` Studio and the native SUCCESSOR Ascension adapter.
The original [BACKGROUND graph](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/89b6f78b83a6643416649173d7d16b6d1c7a65c1/BACKGROUND.md) is unchanged. Its twelve nodes and eighteen directed
connections are the traceability baseline below; a bidirectional connection counts as two directions.
These vision labels do not certify performance, control, economic returns or a live deployment.

The [operator guide](ASCENSION_CYCLE.md) describes the supported journey. The machine-readable
[80-case acceptance index](ascension-cycle-acceptance.json) retains the supplied requirement identities.
An implementation reference means code exists; a test reference means an executable check exists. Neither
means that check passed on this integration candidate. Only a retained result with exact source, environment
and evidence identity can advance a validation state. Earlier Studio acceptance is baseline evidence only.

The release gate remains the actual production-browser journey through a genuine supported executor,
reviewed settlement, owner-specific reconciliation, evaluated change, explicit continuation, and a **distinct
second mission with new reviewed output and settlement**. A native unit test, an exported request, two minted
seeds, or a scripted browser status cannot substitute for this gate. Missing external participants does not
waive missing software integration.

## Project, evidence and authority boundaries

The compatible project manifest is an outer record around the existing sealed package, wallet journal and
native signed records. It must not reserialize signed native bodies, replace the original wallet recovery
key, or modify old capsule semantics. A project has a stable identity before minting; each cycle records its
own exact package, profile, seed, plan indices, jobs, runs, artifacts, evaluation and continuation decision.
The current cycle is a view of that history, not a replacement for the earlier cycle.

| Dimension | Establishing source | Must not be inferred from |
|---|---|---|
| Artifact identity and availability | Verified bytes, exact format/domain and successful retrieval | A filename, URI, checksum in an untrusted import or a remembered upload |
| Wallet context | Explicit selected provider/account/network and current provider epoch | Page load, restored project, NFT possession or another tab's prior permission |
| Business/Agent/Validator eligibility | Current exact-profile ENS, registration, admission and stake reads | A role label, token balance, old badge or local controller key |
| Seed ownership and lineage | Canonical selected-contract state and matching receipt | Predicted next ID, creator identity or another deployment's same-number token |
| Seed review | Current round, evidence, eligibility, quorum and expiry | Job acceptance, a paid report, prior-cycle approval or fixture independence |
| Campaign and job state | Current exact-profile MARK/market state and validated receipts | An exported request, reserve estimate or a simulated successful call |
| Runtime authority | Separately trusted controller grant bound to assignment, terms, release and environment | Observer signature, wallet connection, market payment or import |
| Execution and delivery | Actual bounded run, exact result bytes and valid worker submission | Heartbeat, local status field or executor's completion message |
| Acceptance and settlement | Actual committee decisions, canonical closing state and exact accounting | Candidate PASS, artifact admission or a transaction hash alone |
| Spendable assets | Fresh native-unit observations, rightful ownership and protected obligations | Backing custody plus claims, returned principal as profit or modeled savings |
| Candidate adoption | Frozen comparable evaluation and explicit authorized decision | Payment for evaluation, local PASS or descendant creation |
| Recovery trust | Original signed bytes plus independently retained trust/checkpoints and fresh state | Embedded keys, an outer checksum, restored grants or local timestamps |

No single `complete` flag represents these dimensions. Unknown, stale, disputed, revoked, unavailable,
failed and not performed are independent states. A reorganization invalidates affected observations while
preserving their historical record; missing RPC data is never a zero balance or proof of no obligations.

### Compatible project APIs and bounds

`docs/assets/nova-studio/cycle.mjs` adds `agialpha.nova-studio.project.v1`, with UUID project/cycle
identities and an append-preserving cycle list. `agialpha.nova-studio.private-recovery.v1` is an outer
encrypted envelope; it does not change `package.v1`, `recovery.v1`, capsules or their hashes.
Encryption uses standard Web Crypto AES-256-GCM and PBKDF2-HMAC-SHA256 with 600,000 iterations,
random salt/IV and authenticated versioned header. The passphrase is never included in the export.

| API | Contract |
|---|---|
| `createProject`, `validateProject`, `updateCycle`, `addCycle` | Stable pre-NFT identity, exact packages, ordered retained cycles and explicit lineage |
| `preserveSignedRecord` | Retain the exact original text and its byte hash as historical-unverified evidence; duplicate cross-cycle attribution rejects |
| `observeCycle`, `projectCycleState` | In-process current observations bound to profile/package/seed/provider epoch; imported serialized observations cannot authorize a view |
| `exportProjectKit`, `importProjectKit` | Authenticated private outer export/import; reject credentials, active grants and unsupported schemas/fields |
| `registerAsset`, `verifyReuseRights` | Retain rights/provenance and require current verification for approved reuse |
| `freezeEvaluation`, `recordEvaluation`, `verifyEvaluation`, `decideEvaluation` | Freeze criteria, preserve original reports and limitations, require fresh verification before adoption |
| `registerMission`, `completeMission` | Bind exact input/objective/request; reject reused run/result/settlement identities and unjustified replay as a second mission |
| `prepareSuccessor` | Require current verified reuse/adoption where applicable and create a separate cycle without inherited authority |
| `projectReservoir` | Separate wallet custody, nonspendable stake/campaign/claim, local reservations and unknown costs; stale observations expose no available amount |
| `reconcileCapital` | Native-unit arithmetic over identified flows; receipt authentication/current custody remain separate prerequisites |
| `proposeReinvestment` | An owner-specific proposal only; exact calls require fresh existing wallet preparation, simulation and confirmation |
| `ledger.readProjectLedger` | Reverify original signed settlements against a separately pinned observer, exact current deployment, terminal job, canonical finalized receipt and actual payout/refund events |
| `ledger.createReinvestmentProposal` | Bound a nonbinding destination/lot proposal to the connected owner's current wallet observation and quote; no reservation, approval or transaction |

Project bounds are 32 cycles, 128 job references per cycle, and 256 records/assets/evaluations/missions per
cycle. Private plaintext is capped at 8,000,000 bytes; an original signed record is capped at 1,500,000
bytes. Encrypted export size is larger because it includes base64 and authenticated metadata. State
observations default to a two-minute freshness window and cannot be configured above five minutes;
the next consequential action still requires its own fresh preflight. These bounds are rejection limits,
not measured mobile performance guarantees. Preserve old evidence outside the active working set when
its supported size is exceeded; never discard it silently.

`reuse.mjs` provides a concrete initial reuse path. `authorizeArtifactReuse` selects the exact
`calculation-input.json` bytes inside a verified accepted numerical result, matches their workbench
digest and original executed input, refreshes the exact result/settlement through the workflow, and
records the operator's explicit source/license declaration. It does not assert an independent license
audit. `assertNumericalReuse` makes the next numerical request actually consume that recipe's bounds,
step count and absolute tolerance while requiring different polynomial coefficients. A filename,
relabelled artifact, rejected report, imported selection or same cached work cannot satisfy that path.
The retained selection is current in-process state, not transferable authority in a recovery file.

`ledger.mjs` adds `agialpha.nova-studio.receipt-ledger.v1`. Its recipient-specific historical view
checks original settlement signatures, package/seed commitments, one chain/market/job attribution,
canonical finalized receipts, deployed terminal-state economics, exact payouts/burns and refund custody.
It rechecks old settlements after campaign closure instead of requiring the old campaign to remain active.
Rejected-job slash/refund accrual is not worker income; collected refunds overlap campaign reserve.
Closure gas is a partial observed ETH cost, not total project expense. Returned-principal beneficiaries
need their own `CapitalReturned` evidence and are not inferred from zero remaining lot supply. Foreign
deployment cycles remain explicitly unverified on the selected deployment. The view covers retained
signed settlements, not a complete wallet transaction history, and never adds historical income to current
wallet balances or invents profit.

The guided reinvestment proposal records the rightful connected owner, current source amount, exact
destination campaign, bounded lot quote, rationale and risks. Proceeding copies inputs into the existing
funding controls, which still require fresh preparation and separate approval/purchase confirmation.
The proposal reserves no funds. There is no persisted shared allocation lock across projects or devices;
caller-supplied planning reservations cannot prove that all other commitments were supplied.

## Node implementation map

| Original node | Existing integration surface / minimum observable record | Actor and remaining trust boundary |
|---|---|---|
| Insight | Project opportunity, public-safe inputs, objective, assumptions and frozen baseline | Operator supplies evidence and rights; forecasts remain forecasts |
| Seeds | `package.mjs`, `plan.mjs`, `storage.mjs`, `StudioChain.verifyMint`; exact package/plan/profile/NFT | Owner controls disclosure and wallet confirmation; possession is not IP permission |
| Mark | `NovaWorkflow.prepare/confirm/reconcile`, shared `MarkClient` and `WalletSession` | Each participant signs its own permitted transaction; archived new exposure stays blocked |
| Sovereign | Project/cycle history, selected scope, dependencies, pending actions and native records | Coordination displays authority; it does not manufacture authority |
| Biz | `StudioChain.identity`, campaign business and current owner observations | Actual ENS owner/registered business/admission; governance decisions remain separate |
| Market | MARK's immutable bound Jobs contract; indexed proof, actual route and auction | Business routes original committed work; protocol awards actual auction winner |
| Jobs | `StudioChain.verifyRoute`, exact market job state, richer term seal and settlement import | Worker, committee and entitled client perform their distinct protocol actions |
| Agents | Native assignment binding, controller authorization, actual bounded execution and delivery | Worker wallet identity and runtime identity are distinct, explicitly bound identities |
| Nodes | Native runtime release/environment, installed capabilities, limits, health and journal | Host does not inherit worker, reviewer or governance permissions |
| Reservoir | Separate capital/obligation projection, reusable artifacts and measured outcomes | Ownership and claims govern allocation; artifacts and forecasts are not balances |
| Architect | Frozen baseline/candidate comparison, evidence, verdict, decision and successor draft | Evaluation does not itself adopt, deploy, spend or revise a minted plan |
| Council | Seed review, result acceptance, adoption and spending records displayed separately | Distinct real actors require actual authorization; different keys do not prove independence |

## Every directed graph edge

`S` denotes the existing Studio modules under `docs/assets/nova-studio/`; `N` denotes the existing native
`alpha_factory_v1/core/runtime/successor/` modules. The project outer manifest and native cycle integration
must retain the identities in every row. Acceptance numbers refer to the unchanged 80-case index.
“Required evidence” is a gate, not an assertion that this branch has already produced it.

| ID / original direction | Record and API binding | Actor / permission | Preconditions | State and required evidence | Recovery / failure rule | Acceptance |
|---|---|---|---|---|---|---|
| E01 Insight → Seeds | Opportunity, rights and baseline → `S.createPackage`, `S.compilePlan`; exact package/plan | Operator; no wallet permission needed for local preparation | Supported input bounds, explicit public/private fields, objective criteria and rights | Frozen exact plan, encrypted capsule, local decrypt/verify and recovery export | Preserve original package; edits create a new version; missing rights block authorized reuse | 03, 08–11, 37, 63, 68 |
| E02 Seeds → Mark | Verified package/profile/seed → `StudioChain.verifyMint`, `NovaWorkflow.prepare('open')` | Eligible original business/current seed owner for opening | Exact finalized mint/readback, approved profile, current eligibility and review | Campaign identity and original intent, separate receipt/phase observation | Unknown mint/open remains unresolved; refresh original receipt and campaign, never duplicate | 13–19, 25–29, 51 |
| E03 Mark → Sovereign | Campaign observation and shared journal → project/cycle projection | Read-only coordination; writes retain the actual wallet actor | Exact profile, canonical block and matching seed | Funding/execution phase, original business, reserve, deadlines and unresolved intents | Stale/reorg invalidates current projection; keep previous evidence and pending barrier | 02, 22, 37, 53, 72 |
| E04 Sovereign → Biz | Project request → `StudioChain.identity`, operator handoff and campaign authority checks | Actual business owner; namespace/admission authorities decide their own requests | Canonical single-label role, current name ownership/admission; no inferred authority | Attributable prerequisite request, observed eligibility, responsible next actor | Revocation/expiry blocks new exposure; restore requests without granting admission | 06–07, 28, 40, 78 |
| E05 Biz → Market | Exact plan job and immutable MARK market binding → `NovaWorkflow.prepare('route')` | Original business with current seed ownership and valid role/review | Active campaign, unposted index, reserve, horizon, three eligible opted-in reviewers | Human-reviewed intent, canonical route receipt, MARK/Jobs relationship | Changed capacity/quote/ownership fails fresh preflight; reconcile uncertain route before retry | 20–21, 40, 45, 57–58 |
| E06 Market → Jobs | `MissionRouted` + stored market job → `StudioChain.verifyRoute`, `N.bind_assignment` | Protocol observation; winning worker comes from actual award | Exact proof/index, posting after richer-term seal, assignment receipts and code identity | Actual job ID/committee/escrow; indexed leaf and stored index-zero hash both retained | Never attach late terms or infer winner; changed/reorged receipts revoke current binding | 20–23, 57–59, 72 |
| E07 Jobs → Agents | Richer `JobContract`, assignment binding → controller `ExecutionAuthorization`, dispatch | Actual selected worker plus separately trusted runtime controller | Exact inputs/release/environment, bounded expiry/resources and market-binding digest | Signed binding/grant and actual run ID; posted/authorized/running stay distinct | Unknown effect blocks replay; revoked/expired/changed authority blocks new actions | 22, 38–40, 59, 64–65 |
| E08 Agents → Reservoir | Exact run/delivery → `N.bind_delivery`, artifact/reuse record | Executor supplies evidence; reviewer/rights holder separately admits reuse | Bound result bytes, input/output rights, actual review scope | Reusable artifact hash/provenance/license, execution and acceptance state | Failed work remains evidence; no automatic reuse admission, valuation or authority | 38, 41, 48–50, 60, 68 |
| E09 Jobs → Reservoir (`ΔΣUSD`) | `N.import_settlement`, original signed record → `S.readProjectLedger` and current custody projection | Market observer verifies; each beneficiary retains its own entitlement | Exact bytes, pinned observer, canonical receipt/state, finality and one chain/market/job attribution | Gross/net recipient payouts, per-payout burn and refund custody; current claims/stake and measured outcomes separately | Duplicate import is idempotent; conflicting attribution rejects; reorg invalidates current attribution; original history remains; no payout-plus-balance addition | 23–24, 41–44, 60–61, 71–72 |
| E10 Reservoir → Seeds (reinvest) | Owner-specific continuation proposal → new exact package and successor draft | Rightful fund owner and current parent owner; separate spending/review actors | Unencumbered owned funds or verified reclaim; reusable artifact rights; valid parent | New plan/evidence/cycle, explicit version/reinvestment decision; fresh permissions | Partial claims stay partial; never sweep other holders' reserve or inherit old grants/review | 43, 46–47, 50–52, 68, 70–71 |
| E11 Reservoir → Market (fund) | Existing campaign reserve/refund → `collect`, permitted original `route`; new campaign via own `buy` | Business routes original plan; entitled holder reclaims/funds a different campaign | Valid refund/phase/proof/horizon; exact owner/source/destination and refreshed quote | Distinct refund collection, closure/reclaim, approval and purchase receipts | Unknown send retains pending intent; no automatic batch, reserve sweep or double allocation | 24–27, 42–47, 71–72 |
| E12 Agents → Nodes | Exact work request and grant → installed native runtime/worker | Worker request; actual host/controller authorizes bounded local capabilities | Installed matching runtime, independently pinned trust, scoped grant and limits | Request/run identity, accepted capabilities and resource reservations | Absent host, rejected grant and queued run differ; file import does not start execution | 38–40, 59, 64–66 |
| E13 Nodes → Agents | Authenticated run progress/return and cleanup → native signed record verification | Host signs its observed record; caller separately pins its key | Exact request/result/source/environment binding; no embedded-key trust shortcut | Actual output/usage where observed, failure/unknown/cleanup state | Preserve uncertain effects and quarantine failed cleanup; no effectful auto-resume | 39, 52, 62, 65–67, 76 |
| E14 Architect → Sovereign | Frozen candidate comparison → explicit adoption/hold/reject and successor preparation | Authorized operator/reviewer decides adoption separately from evaluation payment | Comparable criteria/budgets, retained failures, rights and rollback path | Versioned decision and bounded next-cycle proposal; baseline preserved | FAIL/inconclusive cannot auto-promote; successor requires fresh review/funding/grant | 48–51, 60, 68–70 |
| E15 Sovereign → Architect | Exact baseline, completed observations, costs and failures → frozen evaluation request | Operator supplies authorized artifacts; evaluator has declared custody | Immutable baseline/candidate/protocol, held-out or justified fresh inputs | Frozen identities, complete measured outcomes, missing costs and scope | Changed criteria/inputs become a new evaluation; no retrospective success filtering | 48–49, 60, 69 |
| E16 Architect → Insight | Versioned findings, tradeoffs and unresolved questions → next opportunity/baseline | Operator accepts scoped findings; source/reviewer attribution retained | Actual retained measurements and provenance; uncertainty remains visible | New assumptions or revised objective linked to exact evidence | Negative result remains useful; estimated value is never spendable cash | 41, 44, 48–50, 68–69 |
| E17 Insight → Architect | Objective, alternatives and preregistered acceptance conditions → candidate proposal/freeze | Opportunity owner proposes; reviewer controls actual evaluation decision | Stated scope, rights, resource budgets and fresh comparison protocol | Versioned proposal/diff, criteria and rejection path before evaluation | Missing evidence stays not run; future work cannot change old commitments | 37, 48–50, 68–69 |
| E18 Council → Sovereign | Separate seed attestations, job acceptance, adoption and spending records → coordination | Relevant eligible validator, assigned committee, operator or fund owner only | Each action's current role, evidence, scope, deadlines and explicit consent | Attributable decision records; no synthetic universal Council approval | Expired/revoked decision is not carried forward; missing quorum is not worker failure | 07, 16, 23, 40, 49, 51, 60 |

The graph inspector must offer a keyboard-accessible equivalent list/table. Clicking an edge must reveal
its actual record, evidence scope and next valid action. A missing observation means not observed, not a
successful animation. E09's historical label does not denominate settlement in USD: Ascension uses the
selected profile's `$AGIALPHA` accounting; ETH gas and any known external costs remain separate.
The current implementation preserves and tests the exact topology, but individual edge links still lack
their own observed state and permitted-action presentation. Case 53 remains an explicit software blocker;
the matrix above defines the required contract and does not claim that presentation is complete.

## Exact artifact and hash conventions

The existing [Studio format contract](NOVA_SEED_STUDIO_ENGINEERING.md#hash-and-schema-contracts) and
[Ascension adapter](SUCCESSOR_ASCENSION.md#preserved-protocol-identity) remain authoritative.

| Identity | Convention / compatibility rule |
|---|---|
| Existing capsule inner commitment | Established SHA-256 of canonical `{blind,payload}`; not the mint hash |
| Mint `capsuleHash` | `0x` + established `hashObject(finalSealedCapsule)` |
| Capsule file bytes | Canonical capsule JSON plus one LF; exact SHA-256 retained separately |
| FusionPlan indexed leaf | Double Keccak of ABI-encoded actual index and legacy specification |
| Market's stored specification | Same legacy rule at index zero; does not bind richer runtime terms |
| Merkle proof | Sorted pairs, odd unpaired node promoted unchanged; identical specs retain distinct indices |
| Native rich-term/runtime records | Existing versioned domain-separated SHA-256 and original signed bytes |
| Native-bound result artifact | `artifact_sha256` identifies exact portable bytes; `artifact_keccak256` binds those same bytes to native Ascension delivery/review/settlement |
| Earlier Studio result records | Retain their original declared hash convention; never reinterpret an old SHA-256 commitment as Keccak |
| Storage CID | Content locator; neither protocol commitment nor perpetual availability proof |
| Outer project/export identity | Versioned envelope integrity; does not replace inner identities or current trust |

Encryption of a new private recovery envelope protects its contents; it does not retroactively privatize
the existing readable-plan `agialpha.nova-studio.recovery.v1` kit. Keep the prior readers and warnings.
Exports must omit passphrases, private signing keys, service credentials, active grants and inherited
signing permission. Restored signed records establish only their declared historical scope.

## Native cycle and local operator interfaces

`alpha_factory_v1/core/runtime/successor/studio.py` implements the compatible portable bridge. The request
schema is `agialpha.ascension.studio-work.v1`; the signed result schema is
`agialpha.ascension.studio-result.v1`. A request contains the stable `project_id` and `cycle_id`, exact
FusionPlan and `plan_index`, and inert bounded `work_spec`. It cannot select executable paths, install
trust, supply an RPC endpoint or obtain authority. Supported fixed workbench families are `reliability`,
`performance`, `documentation`, `public-data` and `numerical`. They run installed reviewed code without
arbitrary host-code or network execution.

| Native interface | Responsibility and boundary |
|---|---|
| `validate_request`, `prepare_work` | Validate the exact plan/input and fingerprint the installed worker/runtime/environment; preparation grants nothing |
| `seal_work` | Register the exact prepared release and graph through the existing store, then call preposting `seal_terms` |
| `bind_work` | Observe actual posting/assignment and produce the exact market binding; controller signature stays separate |
| `execute_work` | Recheck current configured grant and binding through the existing dispatcher, execute bounded fixed work and sign actual bytes/evidence |
| `verify_work_result` | Check independently supplied observer identity, original signature, exact request/binding and both result hash domains |
| `acceptance_request`, `accept_work` | Prepare the exact acceptance object, then verify the separately configured acceptance owner's decision through the existing dispatcher |
| `settle_work` | Use the existing Ascension importer for canonical settlement and one chain/market/job attribution |
| `retained_work` | Return already retained signed output; this is recovery, not new execution or renewed permission |

The initial production comparison is deliberately narrow: `freeze_evaluation` binds a retained numerical
baseline artifact and a distinct fresh polynomial/domain request before that request starts. The installed
trapezoid and Simpson methods use common inputs and the same step budget. `evaluate_work` checks exact
rational analytic/error/tolerance evidence, execution ordering, measured time and the frozen environment;
it preserves PASS, FAIL, TIE and insufficient-evidence outcomes. Signed domains are
`ascension-evaluation-freeze` and `ascension-evaluation-report`. Inputs are operator-visible, not an
independently protected holdout. Compute/review money costs remain unknown, `independent_proof` is false,
and admission/authority are not granted. This comparison cannot establish general algorithm superiority,
live model capability, an independent audit or economic gain.

`studio_operator.py` retains requests in the existing journal and consumes
`<home>/studio-operator.json` and `<home>/successor-trust.json`. The former uses
`agialpha.ascension.studio-operator.v1`; the latter supplies independently pinned current principal trust.
Explicit profiles bind project/cycle/plan index, institution, mission, producer, acceptance owner, expiry,
exact `MarketContext` including seed, read-only RPC and six approved companion-job families. Existing
institution and graph invariants remain enforced.

The typed first-install form can create the operator configuration once from reviewed deployment/role
fields and preinstalled trust; it refuses to replace an existing configuration. It never imports or
generates a private key, role approval token or trust registry. A reviewed template permits an explicit
`pair` action for the exact project/cycle/plan index and actual seed: it derives a bounded institution and
the exact companion-job proposals in the signed journal. Those obligations remain pending. Pairing does
not grant execution, admission, acceptance or completion, and incoming work cannot change the template.

Optional installed local signer slots use already-held controller/acceptance keys plus distinct role
approval tokens. Tokens reside at `studio-approval/<sha256(principal UTF8)>.token`; they must be separate
from the API token and other role tokens. `sign-grant` requires the controller's token and explicit consent;
`run-signed` is a later separate execution action. `sign-review` requires the acceptance owner's token
and explicit accept/reject decision. The operator checks each key against its independently configured
role identity. External signed-envelope handoffs remain supported. These local roles do not establish
real-world control independence merely because their keys or tokens differ.

The local browser workspace is `/ascension-studio` on the existing `alpha-agent serve` application, with
its existing bearer token, Origin/Host checks and body limits. GET `/api/ascension-studio/status` reports
prerequisites without contacting a node; `/work` and `/work/{request_digest}` inspect retained history.
`/work/{request_digest}/export` and `/work/{request_digest}/settlement` return retained signed records.
Explicit POST actions include first `install`, exact-work `pair`, `import`, `prepare`, `seal`, `bind`,
`sign-grant`, `run-signed`, external-envelope `run`, `sign-review`, external-envelope `accept`, `settle`,
`recover`, `freeze-evaluation` and `evaluate`. Typed installation is limited to the first configuration;
there is no generic configuration replacement, proxy, arbitrary shell or imported-key trust shortcut.
The hosted Studio exchanges portable files with this local same-origin workspace; it does not bypass
browser cross-origin protections by connecting an unauthenticated public page to localhost.

The compatible command group is `alpha-agent --home <private-home> successor-cycle`: `status`,
`prepare`, `seal`, `bind`, `run`, `accept`, `settle`, `verify`, `show`, `export` and `recover-result`.
Each mutating phase requires explicit validated input; read/export/recovery commands do not replay a grant.
These commands support operator integration; the normal installed browser workflow uses forms and file
selection rather than hand-written JSON or calculated hashes.

The existing private backup format must not be assumed to include new configurable operator signer/token
files. Retain `studio-operator.json`, current trust configuration and the administrator-selected private
signer/approval-token slots through an explicitly reviewed private backup process, or reprovision them
through current trusted channels. Public project recovery never includes these secrets. Historical
completed output can be recovered without restoring the old profile or current grant; starting new work
still requires valid present configuration and authority.

## Deployment and execution qualification

| Environment/profile | Permitted scope | What remains unproved |
|---|---|---|
| Offline local preparation | Describe, compile, encrypt, inspect and recover without wallet or paid service | Chain ownership, publication, execution, acceptance or settlement |
| October 11 Mainnet archive | Exact-identity read-only inspection and actual permitted recovery/obligations | Current-source safeguards; new mint/funding/routing stays blocked |
| Disposable exact-source test | Genuine current-source EVM actions with declared test actors/assets; actual local executor where run | Real ENS/token dependencies, beneficial reviewer independence, physical wallets and Mainnet |
| Authorized canary registry entry | Only separately reviewed exact actors/actions/amounts/time/dependencies | Public activation outside that scope |
| Public qualified registry entry | Only exact reviewed implementation/profile operation policy | Arbitrary provider/wallet support, independent audit or guaranteed economic benefit |

Production `qualified-profiles.mjs` remains empty. Test-only registries live in isolated temporary copies;
the existing disposable-network guard must reject URL-backed, forked and non-disposable fixture targets
before any reset/code/balance mutation. A chain ID is insufficient isolation evidence.

The baseline executor is local native bounded work and requires no paid model. Its real output is distinct
from independent customer acceptance. Optional Computer Use retains its disposable Linux-container
Chromium, permitted network/actions, finite budgets, reservation and cleanup boundary. It does not grant
desktop, personal-browser, login, wallet, payment or message authority. Actuator tests do not qualify a
live model. See [Computer Use](SUCCESSOR_COMPUTER_USE.md) for the separately authorized provider trial.

## Evidence package and completion gates

### Retained component evidence

The [project-model unit report](release-evidence/ascension-cycle-model.json) records **14/14 passing
tests** with command, TAP output and nine exact source/dependency hashes. It covers private recovery,
stable identity, original records, current-observation refusal, native-unit projections, rights, frozen
evaluation and replay guards. The final regression rejects evaluation IDs cloned or reused across cycles.
Its chain observations are synthetic; generated-browser/native/EVM behavior has separate evidence.

The [accepted-artifact reuse report](release-evidence/ascension-cycle-reuse.json) records **4/4 passing
tests** using the actual shipped numerical workbench and locally signed fixture envelopes. It checks
selection of original accepted bytes, paid-negative findings, concrete consumption in fresh numerical
work and rejection of contradictory/foreign/relabelled source records. Its chain verification callback
is synthetic. The [receipt-ledger report](release-evidence/ascension-cycle-ledger.json) adds **4/4 passing
tests** for original signed settlements, canonical event attribution, refund custody and bounded nonbinding
proposals. These three reports use the repository-pinned Node 22.17.1, retain complete runtime versions
and verify that their declared source hashes stayed unchanged during execution. Principal-return receipts,
all-cycle costs and shared project/device allocations are outside the current ledger's implemented scope.

The [native component report](release-evidence/ascension-cycle-native.json), with its retained
[pytest output](release-evidence/ascension-cycle-native.txt) and
[JUnit results](release-evidence/ascension-cycle-native.xml), records **59 passing tests**, zero
failures/errors/skips, Python 3.12.14 and Node 22.17.1. It performs genuine installed fixed work and
frozen numerical evaluation; its RPC observations are synthetic. Controller/refusal, exact hashes,
preposting terms, retained-output recovery and attribution checks are component evidence. This report
does not qualify the local operator server, production browser, actual EVM two-cycle path or external
actors/providers/wallets. Its seventeen retained source/dependency hashes identify the final native snapshot.

The [local operator report](release-evidence/ascension-cycle-operator.json),
[pytest output](release-evidence/ascension-cycle-operator.txt) and
[JUnit results](release-evidence/ascension-cycle-operator.xml) record **28 passing tests**, zero
failures/errors/skips and one dependency warning. The actual FastAPI/uvicorn application runs in
Chromium 139.0.7258.5 with Playwright 1.54.0, Python 3.12.14 and Node 22.17.1. The test uses the
normal typed first-install, per-work pairing, separate controller signing/execution and acceptance-owner
forms, with previously installed trust, role keys and approval tokens. Genuine numerical work runs;
the RPC receipt fixtures are synthetic. French and 390-pixel layout checks do not replace human
screen-reader or physical-device trials. Eleven retained source hashes match that stable run. This
operator test and the actual Studio/EVM qualification establish different parts of the supported handoff.
The final browser boundary check accepts a 280 KB Unicode request and an exact 524,288-byte serialized
POST, while either a raw file or encoded POST of 524,289 bytes is rejected before sending.

The [browser/native verifier report](release-evidence/ascension-cycle-runtime.json) records **12/12
passing tests**, including edited FAIL/PASS claims, modified frozen protocols and moved cross-cycle
evaluation records. Valid signatures cannot substitute a different request, criterion or cycle context.

### Complete-cycle and regression evidence

The [retained example](examples/ascension-cycle/README.md) contains the final production
[workflow report](examples/ascension-cycle/cycle-report.json),
[browser report](examples/ascension-cycle/cycle-browser-report.json), exact packages, prior seals,
original signed results/settlements, frozen comparison and encrypted recovery. Its 46 declared source
hashes matched the final executable checkout. Three genuine numerical jobs completed across two cycles
on an actual disposable EVM: a paid accurate negative report, a fresh preregistered comparison and a
distinct successor using the accepted calculation recipe on new inputs. The browser also checks rightful
reclaim/funding, historical settlement flows, no-send recovery and all 12 node labels/18 directions.
All 33 axe audits reported zero violations; no overflow or page errors were reported.

The actual screenshots remain in the separately retained public archive and CI artifacts; the repository
example contains their original digests. Fixture actors, an injected wallet and local storage do not
establish independent human review, physical-wallet compatibility, real service-account storage, a live
model, protected holdout, commercial value or Mainnet qualification. Initial native trust/key/token
provisioning remains an explicit administrator prerequisite.

| Retained regression | Outcome and scope |
|---|---|
| [MARK tests](release-evidence/ascension-cycle-mark.json) | 117 Node and 4 Python tests passed; original ABI/client/session/recovery/build behavior |
| [Contract tests](release-evidence/ascension-cycle-contracts.json) | 108 passed on disposable EVM; unchanged contract semantics |
| [Built MARK browser](release-evidence/ascension-cycle-mark-browser.json) | Exact assets, consent, recovery, locks, finality and accessibility checks passed with a fixture provider |
| [Coordinator checks](release-evidence/ascension-cycle-coordinator-checks.json) | 48 Studio tests, all 18 pre-commit hooks and strict MkDocs passed on frozen executable sources; source map captured after execution |
| [GitHub MARK acceptance](release-evidence/ascension-cycle-ci.json) | Run 38513745974 passed at hosted source `9f3b6b84ce7ff242b33a7dbd8d2cac34f32289b7`, including complete-cycle browser/native/EVM and three uploaded artifacts |

These results do not establish full-repository pytest, coverage or mypy success. The
[developer handoff](ASCENSION_CYCLE_HANDOFF.md) and acceptance index retain the outstanding broad gates,
software gaps and external trials. Original reports keep their actual execution identity; subsequent
source commits are reconciled by exact file hashes rather than rewriting historical reports.
The [full-suite summary](release-evidence/ascension-cycle-fullsuite.json) records a failed,
disk-contaminated run despite reaching 80.57% coverage. All 151 disk-affected outcomes passed bounded
reruns; two persistent notebook startup failures reproduced at the exact base. The 158 total follow-up
passes do not replace a clean whole-suite result. The [full typecheck comparison](release-evidence/ascension-cycle-mypy.json) records
222 diagnostics against 208 at the base, including 14 additional API/operator decorator diagnostics.
Neither gate is waived by focused tests or scoped CI.

Every retained qualification run must include:

1. Exact reviewed source commit, dirty-tree state/source hashes, runtime/environment and dependency identities.
2. Selected chain/profile/addresses/code identities, explicit test-actor scope and disposable-network evidence.
3. Exact two packages/plans, richer-term seals before posting, actual assignments and separate controller grants.
4. First and distinct second run identities, input/artifact digests, raw retained signed records and new results.
5. Actual review/settlement observations, native-unit reconciliation, failed/inconclusive candidate evidence
   and the explicit continuation/version decision.
6. Fresh-session recovery and interruption results, actual generated-browser screenshots, commands and outcomes.
7. All unperformed external trials, named responsible actor, next action and objective clearance evidence.

The acceptance JSON distinguishes `implemented`, `implemented_unverified`, `in_progress` and `external_prerequisite`
implementation states; validation distinguishes `not_run`, `passed`, `failed`, `partial` and `blocked`.
A combined requirement stays partial when local checks passed but required human/service/device trials
did not. Test-suite totals do not silently mark every mapped requirement passed.

Software completion requires cases 38, 50 and 54 at their full production-browser/native scope together
with all applicable remaining software cases. Operational Mainnet completion additionally requires exact
deployment qualification, independently authorized participants/providers, bounded canary/continuation
evidence, reconciled obligations and a separate public-launch decision. A release may accurately describe
its implementation scope; it may not relabel blocked software or unperformed trials as completion.

## Necessary edits, preservation and rollback

| Area | Necessary integration | Compatibility / rollback condition |
|---|---|---|
| Existing Studio workflow/UI | Carry one project through real work, evidence, accounting and continuation | Preserve `/ascension/mainnet/`, old package/kit readers and normal first-cycle controls |
| Shared transaction boundary | Only the smallest extension needed for existing exact actions | Preserve `MarkClient`, journal key, `WalletSession`, atomic lock and uncertain-send barrier |
| Native command integration | Route portable requests through existing SUCCESSOR trust/Ascension APIs | Preserve legacy commands and original signed bytes; restore never grants new authority |
| Build/evidence integration | Include new executable assets and source-matched acceptance artifacts | Retain existing CI gates, cache exclusions, offline installation and generated-asset checks |
| Protected source/history | No planned change to original graph, Solidity, archive or compiler lock | A later exception needs specific defect evidence, review and regression coverage |

Reverting frontend code does not pause contracts, revoke native grants, refund funds or erase history.
Before a frontend rollback, retain recovery exports and exact pending intents. Suspend unsafe new exposure
through reviewed profile policy while preserving legitimate exits and processing existing obligations.
The final PR report must enumerate actual changed files and verification, not treat this intended scope as
proof that the resulting diff remained within it.
