# Productive Capital Engine: architecture, currency and authority audit

Audit date: 25 October 2026. This is a source inspection by a separate agent in the same commission, not an external security audit. Repository responses were fetched through the connected GitHub reader. Copied source was checked against Git blob identities. No financial transaction, new credential, external executor operation or deployed-contract change was performed. A public deployment record is evidence of what that record reports; it is not a fresh RPC or explorer verification.

## Frozen source identities

| Repository | Main observed in this audit | Role relevant to the study |
|---|---|---|
| MontrealAI/AGI-Alpha-Agent-v0 | `f836f06e8351e64db1da770e16e304b5feb01f28` | Mission/workbench packs, bounded planning and repair worker, immutable source/candidate identities, Alpha contracts |
| MontrealAI/AGIJobsv0 | `bc4abbd5c28f3672275b13300e40ea26c820b8ee` | Separate AGIALPHA18 job, escrow, stake, fee and validation implementation |
| MontrealAI/AGIJobManager | `5d5670df9dbbc79da115e0a44b71989f34df58c1` | Separate USDC6 job settlement and computer-work specification adapter |
| MontrealAI/AGI-Fleet-Linux | `45759fb096faf8988f58ae5ea71248d0f35a97c7` | Source-bound project handoff, execution/review separation, returned-artifact checks; no new executor provisioned |

Mutable main URLs are not the research source identity. Use the commit-bound URLs in `evidence/source_contracts.json`.

## Reusable execution surface

The existing Alpha `contrib/strategy_succession/worker/fixed_worker.py` implements `FixedWorker.execute(method, payload, limits, checkpoint)`. Its methods are `run-mission`, `construct` and `run-journey`. The 18 immutable bodies listed in its `SOURCE_FILES.json` were downloaded and all 18 SHA-256 values match. The source manifest is not an external authority signature. The implementation restricts commands, executables, task grammar, budgets and acknowledgement flow; the research should preserve those boundaries.

`run-journey` produces an initial resource-constrained plan, a changed plan, and a repair of the actual preceding checked plan. It derives the repair baseline and locked prefix from that preceding receipt. It does not accept a browser-supplied substitute baseline. Construction uses separate service and improvement counters and recorded attempts. The worker keeps the conventional JavaScript portfolio and the SciPy/HiGHS specialist available. `native_repair.py` minimizes total displacement before makespan within a declared deadline. A separate Python checker in `scientific/review/check.py` checks delivered schedules. Solver optimality/status output is not an independent optimality certificate.

The scientific adapter `scientific/companion/adapter.mjs` exports `runMission` and `inspectMissionPack`; it wraps `createWorkbench`, produces a `release-plan.json` deliverable and records refusal, feasible-but-target-not-met or qualified-local-result status. Its explicit limits include no production authority and no settlement. Direct use is native research. The authenticated transport in `contrib/strategy_succession/transport/strategy_executor.py` has separate approved-source and signed-journal requirements. Research execution is not permission to create a transport home, sign a journal, launch a daemon or relabel a native receipt as approved external execution.

Fleet's `fleet/packages/AGI_Agent/successor/project.mjs` compiles a computer-work request through the pinned Manager adapter, preserves immutable public input, checks the exact delivered bundle, and binds execution/review receipt roles. Its checked-result record explicitly includes `independentController: UNVERIFIED`, `qualification: NOT_RUN`, `authority: none` and `payment: unfunded`. Calling a local serialization or admission checker does not establish Fleet installation or reviewer independence.

The full seven-stage operating vocabulary should produce concrete mission artifacts: Identify (scope/acceptance), Out-Learn (source acquisition and provenance), Out-Think (alternatives and dependency analysis), Out-Design (candidate implementation/specification), Out-Strategise (bounded allocation and route), Out-Execute (delivered files and checks), Out-Evolve (retention decision and subsequent-use evidence). The study should show actual artifacts at each stage, not infer execution from a stage label.

## The five Alpha contracts

`AscensionToken` is an abstract shared base, not a sixth deployed application contract. The five are:

| Contract | Implemented operational role | Capital/rights boundary |
|---|---|---|
| `AscensionAccess` | Live ENS ownership and governor-set expiring admission; role namespaces are under alpha.agi.eth, alpha.agent.agi.eth and alpha.club.agi.eth | Admission is not equity or a cash claim; ownership/admission can expire. Governor retains the source-defined admission authority. |
| `NovaSeed` | ERC-721 commitments to capsule hash, immutable plan root, evidence hash and optional parent; parent sealing requires ownership | Records lineage and plan commitment. Token ownership alone proves neither deliverable quality nor productive capability. |
| `AscensionRiskOracle` | Validator AGIALPHA stake, evidence-bearing quorum, expiring risk approval, business/creator conflict checks and opted-in review capacity locks | Locks working capital; stake can be withdrawn after lock expiry. It does not generate revenue or automatically finance a capability. |
| `AscensionJobMarket` | Bounty escrow, bounded reputation/price/time auction, agent collateral, artifact-bound 2-of-3 approval, payouts, refunds and failure recovery | Customer escrow is encumbered money; only actual beneficiary receipts count as revenue. Missing reviewer quorum is not automatically proof of worker failure. |
| `AscensionMark` | Reversible linear funding-lot curve before bloom; plan-restricted treasury after bloom; collection/refund and closure | Business can route only committed plan leaves within funding/time/risk gates. Lot holders may reclaim proportional unused reserve after closure. They do not receive a source-defined claim on business profits. |

The shared token address is `0xA61a3B3a130a9c20768EEBF97E21515A6046a1fA`, 18 decimals. The shared base rejects non-exact deposits and payouts, and checks both total-supply and paying-contract-balance destruction on burn. This audit does not independently audit the external token or proxy authority.

### Alpha settlement arithmetic

Let `B` be the fully deposited bounty and `P <= B` the winning price in integer AGIALPHA base units. `each = floor(floor(P*500/10000)/2)`, worker gross `G = P-2*each`. On acceptance, worker receives `G-floor(G/100)`; each of two approving validators receives `each-floor(each/100)`. Each payout burns separately, so aggregate rounding must be preserved. `B-P` is a customer refund. At large amounts the worker receives approximately 94.05% of P, validators together approximately 4.95%, and approximately 1% burns. The agent's collateral is `max(floor(B/10), minimumStake)` and is separate from P. Rejection or missed delivery can slash that bond; a submitted result without quorum refunds bounty and unlocks the worker without that slash. Locked principal is a balance-sheet requirement; only losses, financing cost and applicable opportunity cost are expenses.

No automatic 50% reinvestment, general AGIALPHA-holder profit share, buyback or guaranteed appreciation was found in these five contracts. The 0/25/50/75% policies are off-chain study scenarios. A business can economically earmark its own surplus, but these contracts do not automatically implement that earmark. Any proposed future profit-allocation mechanism must be labeled a proposal and must not modify deployed source under this assignment.

## Manager USDC is a separate route

Manager's `contracts/utils/JobSettlement.sol::complete` computes wallet30 and wallet10 as 30% and 10% of the ORIGINAL escrow, then a snapshotted validator pool (default 8%) and an agent remainder (default 52%). For 100 USDC with participating validators the base allocation is 8/30/10/52, with rounding and unused validator pool credited as implemented. The 40% is included in the customer price, not an extra surcharge. Buyer acceptance or authorized success without validators can pay 30/10/60. Bonds are separate. Deferred failed transfers remain claims; their accounting entry is not collected cash. The main contract has five reserve classes: unsettled job escrow, agent bonds, validator bonds, dispute bonds and pending claims. Withdrawable surplus excludes them.

The study must state the economic entity. An agent enterprise cannot count wallet30 or wallet10 receipts as its own proceeds without evidence it owns those beneficiaries. A combined operator entity must consolidate intercompany transfers only once. No token burn, token-holder distribution or AGIALPHA exposure is inferred from this USDC route. Actual USDC issuer restrictions and gas remain relevant but were not tested here.

## Jobs v0 AGIALPHA is another distinct route

Current JobRegistry is a controller over immutable delegates. Inspected actual logic is in `contracts/v2/implementation/JobRegistryBase.sol` and `StakeManagerBase.sol`; the public facade alone is not sufficient evidence. JobRegistry defaults are 5% fee and 8% validator reward, configurable in source. Creation locks reward plus fee (`R + floor(R*feePct/100)`), unlike the Manager split. On success validators can receive a share of R, agent payout may include a frozen NFT multiplier funded from the operator reward pool, and StakeManager burns the configured fraction of modified agent payout. These parameters are not claimed as a fresh live deployment readback.

`FeePool` separately burns a configured percentage of collected FEES (constructor default 1% when its argument is zero), accrues the remainder and distributes it by boosted stake for `rewardRole` (default Platform). This is a scoped participation reward, not an automatic dividend for every token holder. Direct contribution and governance-controlled treasury paths also exist; transfers among treasury, fee pool and staking accounts do not establish external demand. The no-stake path burns pending fees. Owner/governance can change relevant configuration within implemented bounds. Current external deployments and privilege inventory are not freshly verified by this audit.

For comparable economics, calculate gas, conversion spread/slippage, liquidity capacity, volatility between payment and conversion, collateral lock time, failed delivery losses and reviewer capital separately. A useful scenario marks receipts in USD at a stated realized/conservative conversion price. Burn does not create USD income. Token appreciation should be zero in the base operating thesis. A volatility stress can use lower conversion proceeds while costs remain USD; no market price is sourced in this audit.

## Tests versus deployment evidence

Inspected Alpha test source includes lifecycle, marketplace and settlement conservation fixtures. They cover exact payout/burn balance changes, artifact-bound review, validator revocation, timeout distinctions, funding-lot redemption, plan/Merkle constraints, lineage ownership and risk eligibility. These test files were inspected, not executed in this audit. Do not call that a fresh contract test pass.

The current repository deployment record reports five fresh contracts, Etherscan EXACT_MATCH verification and two finalized bindings at block 26220072 for deployed source `c0fc5217e364a39a4cd123d17a8317c06b80f820`. It is a sanitized projection of operator evidence. It explicitly reports activation not allowed, public funding not approved, no global pause, and outstanding external authority, real-dependency, independent security and commissioning gates. This is recorded point-in-time evidence, not a fresh on-chain check. The newer repository revision must not silently substitute for the deployed source.

Manager's `config/mainnet/agi-jobs-usdc.json` is explicitly an operator-evidence projection and not live/default state; `docs/deployments/mainnet.json` separately remains a deployment-required configuration placeholder. Neither establishes current activation or paid use. The historical record and current source must retain their different identities.

## Coordination and negative evidence to preserve

Issue 4850 remains the coordination hub. Existing Economics #4901 and its paper #4902, the 42-job native study #4903 and paper #4904, and the separate operational-economics amendment at `4d1d2af3e77a5346e3dc1a574f509d5c67c0aef7` have their own owners and freezes. The new productive-capital study should neither retune their endpoints nor wait for them to change. Latest retrieved checkpoint says the passive papers had completed their 21 hosted checks and awaited review; it does not claim merge or deployment.

Source-release owner #4899 had an unresolved official scan finding and was restoring its current checkout. Accepted releases and held Harness/Fleet paths retain their original boundaries. The exact-source publication/release policy requires applicable security, integrity, test, artifact and hosted gates. Static preservation of a held path is not authority to execute it. Additive study/paper publication should use the existing owner and process.

Historical Strategy Succession docket reports primary flywheel 517/864, equally enabled learner 517 and fixed portfolio 591; no primary retained asset; zero fresh repairs both invoking their parent and qualifying; diagnostic inherited 36/48 versus parent-free 37/48; and no full-investment admission. Its newer engineering worker retains the actual-plan repair loss to native (movement 9 versus 7). These are historical reported results, not fresh replication by this audit. The source files and manifest downloaded here enable a new separately frozen research run; they do not erase those conclusions.

## Evidence limitations

The audit shares commission, model family, source selection and available tools with the study authors. File hashes establish copied-byte identity, not correctness or independence. Full repository suites, Solidity execution, authenticated browser-to-executor operation, live deployment state and actual paid demand were not run by this source reviewer. Monetary results that combine observed native measurements with unobserved collection, human review or demand assumptions must be labeled modeled.
