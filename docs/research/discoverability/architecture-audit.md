# SUCCESSOR enabling-capability audit — 22 October 2026

Read-only research lane. No transaction, GitHub mutation, review approval, release or deployment was performed. This is a source and historical-record audit, not current chain readiness or installed acceptance.

## Exact sources

| Repository | Observed main |
|---|---|
| MontrealAI/AGI-Alpha-Agent-v0 | 61532fb82621a065e668fd11e57289dcfb65c67b |
| MontrealAI/AGIJobsv0 | ba67d5d19ef7d9ac643f99f2b8f49c160714fdf6 |
| MontrealAI/AGIJobManager | 3153ac394d37eeecb03e825ecce37559427bc6c3 |
| MontrealAI/AGI-Fleet-Linux | 45759fb096faf8988f58ae5ea71248d0f35a97c7 |

These are independently fetched branch identities. They are not a tested compatible release set. Coordination is [issue 4850](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/issues/4850), notably current ownership record [6352557424](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/issues/4850#issuecomment-6352557424).

## Existing owners and restrictions

- Native thin enterprise harness: [PR 4863](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/pull/4863), head c455ad4ce109c86df2fef09d19674810290b5185, branch codex/successor-omega-harness-20261022. Existing owner MONTREAL.AI; role described as harness/runtime owner in coordination. An explicit unresolved review restriction remains. Do not copy held code into a new PR.
- Ascension enterprise bridge: [PR 4865](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/pull/4865), head 6bb361d522d80dc900cc2a480014531c6a44b66e, stacked on 4863. Adds enterprise_ascension.py, tests and guide. Owner reports 39 local tests including explicitly synthetic RPC. It does not establish actual new-source EVM execution.
- Thermal witness: [PR 4871](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/pull/4871), head 175d8a50473ea94f8c63d20959c22c95dfc6b886, based on current main. Owner has already built volume-witness calorimetry, heat capacity, and storage-adjusted recovery. A new flagship must not reproduce these three as its novelty.
- Alpha 4855 software source lease, subsequent 4869/4870 research/catalog/site integration, Jobs 4021, Manager 1623 publication, Fleet 64/65/66 all remain with their current owners. Fleet 61 also remains held. The latest thread explicitly preserves publication ordering and does not authorize an alternate route around a hold.

## A–H map: existing code, interface, tests, actual evidence boundary

Paths in this table are relative to Alpha main unless another repository is named.

| Component | Existing implementation/interface | Evidence/tests and limitation |
|---|---|---|
| A — Insight | alpha_factory_v1/demos/alpha_agi_insight_v0/discovery.py: validate, evaluate, verify, artifacts. Supplied excerpt-backed signals, interval scores, review-budget knapsack, ordinary job specs and unreviewed Nova drafts. Native core/runtime/ascension.py compiles actual indexed FusionPlan commitments. | Inspection confirms exact bounded integer scoring and review-capacity selection. Sources are supplied, never fetched/authenticated; supplied intervals are not confidence intervals, priority is not foresight or realizable value. A new mechanistic flagship must contribute its own explanatory test and actual work. |
| B — Nova-Seeds | contracts/ascension/NovaSeed.sol seal; core/runtime/ascension.py and existing Nova Studio. Immutable capsuleHash, planRoot, evidenceHash, parent, job count and creator stored in ERC-721 Genome. | tests/contracts/test/ascension/native-handoff.test.js compares Python/JS/Solidity indexed proofs including odd/max trees and uint96. seal requires eligible business, nonzero commitments, 1–128 jobs, URI 1–512 bytes, current ownership of parent. ERC-721 transfer does not transfer passphrase, legal/IP rights or old campaign authority. |
| C — MARK/risk | AscensionRiskOracle.sol openReview/attest/green, stake and review-capacity reservation; AscensionMark.sol open/buy/sell/transferLots/bloom/route/collect/close/reclaim. Existing docs/assets/ascension-wallet client and Studio connect the actual protocol. | Existing lifecycle/marketplace/settlement tests and tests/contracts/scripts/ascension-cycle.js. Actual local test implementation exists; this audit did not execute it. Funding lots are internal units on the exact linear curve, not generic exchange or company equity. |
| D — Enterprise | Released successor/workbench.py uses existing Journal, Institution, MissionConstitution, ResourceBudget, CandidateReleaseManifest and SuccessorStore; fixed worker invocation, durable attempts, leases, stop/recovery, local review/export. Held enterprise.py in 4863 extends this into enterprise configurations and successors. | tests/runtime/test_successor_workbench.py plus held harness suite. Main workbench result explicitly has settlement NOT_CONNECTED and empty authority. Existing fixed families work locally; the new flagship must register through the legitimate owner route. |
| E — Marketplace | Alpha AscensionJobMarket has bounded auction, staked bids, reputation-weighted selection and three chosen reviewers. Native successor/ascension.py seals terms, binds observed assignment/delivery, imports real receipts. Jobs v0 has separate JobRegistry-v2 backend; Manager has separate USDC compiler/settlement. | Alpha successor-adapter.test.js executes real Hardhat with Python adapter. Correct negative report can be accepted/paid while candidate fails. Jobs applying atomically assigns first eligible caller; it is not this Alpha auction. No fastest/cheapest global guarantee. |
| F — Workers/Jobs | Released successor/workbench.py invokes shipped Node code only, input/output <=2MB, Node>=22, 3 attempts, per-attempt budget, explicit checkpoint. Computer/Fleet routes exist separately under successor/computer*.py and Jobs integrations/alpha-agent. | Alpha fixed work source is not general model autonomy. Fleet local-runtime/supervisor/successor.mjs requires distinct Agent/Node actor records and same returned bytes; it labels review internal, independentReview=false, authority=none. Real independent Fleet provisioning is not established. |
| G — Architect | successor/state.py, mission/evaluation, transformation/campaign modules maintain candidate/proof/admission/authority distinctions; workbench nominates a method without activating it. Held harness permits accepted-parent template derivation without inherited authority or results. | Existing tests cover state/revocation/concurrency and negative outcomes. General autonomous RSI and beneficial capability compounding are not proved by a local candidate selection. New mechanism needs unchanged acceptance, held-out tests, reject+accept, invalidation and rollback measurements. |
| H — Council/CLUB | AscensionAccess strict role+live ENS+admission; oracle isValidator requires minimum stake; job committees exactly3 distinct eligible validators, reserves actual opt-in capacity, excludes business/client/worker, terminal decision2 votes. | Existing marketplace tests check conflicts/expiry/stake/timeout. Address separation and locally generated Ed25519 principals are not independently controlled beneficial owners. Imported keys/approvals never establish trust. |

## Exact Alpha semantics

All five contracts plus AscensionToken were fetched at current main and at deployed source c0fc5217e364a39a4cd123d17a8317c06b80f820. Every compared source body and Git blob is identical. This proves those file identities, not current chain configuration or whole-tree/build equality.

### Admission and ownership

AscensionAccess constructor fixes Business root alpha.agi.eth, Agent root alpha.agent.agi.eth and Validator root alpha.club.agi.eth. register accepts a canonical single lowercase ASCII label (1–63 characters, interior hyphens permitted). eligible requires BOTH registered-name ownership and governor admission until>now. ENS registry owner can directly match; wrapped ownership must match account with expiry>now. Resolver-address bypass does not exist in this Alpha contract. Admission evidence must be nonzero for nonzero future expiration, maximum365 days; until0 revokes. Token holdings alone confer no role.

The source Mainnet observation has oracle quorum2, maximumRiskBps2000 and minimumStake10 AGIALPHA; marketplace minimumStake10 AGIALPHA. Those are historical getter values, not fresh observations.

Oracle reviews last7 days, bind current seed owner, reject owner/creator as reviewer, allow one vote per round and stop at either quorum. green rechecks current owner eligibility and every supporting validator. Stakes are locked through the maximum deadline; withdraw requires strictly later timestamp. Job availability is an opt-in per business, expiry<=120 days, global capacity<=128. Early job completion releases active-job count, not the historical lockedUntil time.

### MARK curve and treasury

quote(supply,count,base,slope)=count*base+slope*count*(2*supply+count-1)/2, with count0 handled explicitly and total lots<=1,000,000. Integer expression is exact for this arithmetic sequence. open requires current seed owner and green, reachable positive target, funding window<=30 days, and execution duration>3 days and<=90 days. buy requires admission, green, unchanged owner, live funding phase and max-cost bound. transferLots also requires both participants admitted. sell in Funding deliberately does not require current admission/green or an unexpired funding deadline, protecting permitted unused-funding exit.

bloom is business-only, before funding end, at reserve>=target, current seed owner, green and unchanged business ENS ownership. It ends curve redemption. route requires same authority, valid indexed Merkle proof, unposted index, enough reserve, fresh green and full auction+execution+3-day review fitting inside campaign executionEnd. MARK sets allowance only for the bounty then resets it to0. MARK, not business wallet, is escrow client. collect is idempotently one-per-job and returns terminal refund to reserve. close after funding expiry or once all active jobs ended and either all plan indices posted or executionEnd passed. reclaim floors pro-rata reserve*lots/supply, reduces both reserve and supply, so the last claimant receives remaining integer dust. Spent funding is not guaranteed refundable principal.

### Jobs, exact selection, conservation

Job bounty>=100 base units, duration>0 and<=90 days, priceWeight<=10000; auction>0 and<=7days. Bond=max(floor(bounty/10),minimumStake). Up to32 bids; one per agent; all offered bonds locked until award. Bid price>=100<=bounty and duration<=job duration. Auction winner minimizes ((price*weight*10^6/bounty)+(duration*(10000-weight)*10^6/maxDuration))*10000/(10000+min(rep,10000)), with Solidity floor at each division. Ties break lower price, shorter duration, lower numeric address. Delayed award skips ineligible/expired-duration bids; zero eligible bids refunds bounty and unlocks bidders.

Delivery is only assigned worker, eligible and timestamp<=due, nonzero result hash and URI1–512 bytes. Review is selected current eligible reviewer, exact delivered hash, nonzero evidence, one vote, timestamp<=reviewEnd. Two approvals pay; before payment current approval eligibility is rechecked. Two rejections fail/slash, and rejection eligibility is rechecked. Missing delivery timeout strictly after due slashes. Missing review quorum timeout strictly after reviewEnd refunds full bounty and unlocks worker without slash or reputation decrement.

At successful price p, reviewer gross each e=floor(floor(p*500/10000)/2)=floor(p/40), worker gross w=p-2e. Each recipient separately burns floor(gross/100), receives gross-burn. Total burn=floor(w/100)+2*floor(e/100), not necessarily floor(p/100). Client refund=bounty-p. Gross payouts+refund=bounty; net payouts+actual burns+refund=bounty. On rejection/missed delivery, bond burn=floor(bond/100), client refund=bounty+bond-burn, worker stake decreases by bond. A separate claimRefund is single-use and actual payout occurs there. Refund/stake/funding transfers have no extra protocol burn. AscensionToken verifies exact ERC20 deposits, receipts and actual supply destruction, rejecting fee-on-transfer or no-op burn behavior.

Useful integer edge tests: p100 =>e2,w96,total burn0; p103 =>e2,w99,burn0; p104=>e2,w100,burn1; p1000=>e25,w950,burn9 (not10); p80000000000000000000=>burn800000000000000000. Cover bounty/10 versus minimumStake, partial lots reclaim in different orders, one-unit residuals, max uint96, reputation10000 ceiling, timestamp equality for delivery/review and strict timeout, revoked supporter, ownership transfer during Funding, duplicate refund/collect/import and missing quorum. These calculations are analytic expectations, not newly run Solidity results.

## Distinct backends

| Backend | Asset/selection | Relevant boundaries |
|---|---|---|
| Alpha agialpha.ascension.v1 | canonical18-decimal AGIALPHA; bounded weighted auction above | Strict alpha ENS roots, expiring admission, 2of3 job committee, no global pause. Oct18 manifest explicitly activationAllowed=false/readyForPublicFunding=false. |
| Jobs agijobsv0-jobregistry-v2 | canonical18-decimal AGIALPHA; apply is atomic first-eligible assignment | Separate25-contract stack, deployed-source818b3a246871e4cd4dde86558dbb91ef82b15eef, runtime/wiring/pause/identity/tax rules; Oct18 recorded eight managed modules paused. Do not import Alpha auction/review economics. |
| Manager | native Circle USDC6 decimals; separate management, escrow, dispute and settlement rules | Constructor checks chain-specific USDC. Configurable primary+alpha ENS roots, allowlists and Merkle eligibility; ENSOwnership handles live wrapper/controller and some approval/resolver cases. Separate intake and settlement pause. Explicit new USDC price, never implicit conversion or dual charging. |
| Fleet | execution/review provider, not settlement contract | Existing authenticated Studio/Companion/ComputeWorker, bounded grants/tickets, idempotency, stop and preserved artifacts. Internal separate actors are explicitly not external independence. |

## Local EVM path and next integration requirement

Use existing tests/contracts/package-lock.json and pinned package.json (Hardhat2.29.1, ethers6.17.0, solc0.8.37, OpenZeppelin5.6.1). Existing hardhat.config.js refuses URL-backed or forked providers. tests/contracts/test/ascension/successor-adapter.test.js drives actual Solidity local fixtures while Python successor/ascension.py uses allowlisted read-only RPC. It verifies nonzero plan index, exact rich terms, assigned worker, artifact, real2-review payout, negative candidate report, no-quorum refund, tampering, duplicate import and disposable-network refusal. tests/contracts/scripts/ascension-cycle.js connects local UI/native journey and recovery; browser test service is explicitly fixture-only.

Documented command: install reviewed Python runtime and Node environment, npm ci under tests/contracts, then ALPHA_PYTHON=/absolute/python SUCCESSOR_EVM_EVIDENCE_DIR=/new/empty/path npx hardhat test test/ascension/successor-adapter.test.js. Full existing npm test adds lifecycle/settlement cases. This audit did not run these: required Node EVM packages are absent, and package/source transport is blocked in current shell. Adding a novel mission requires the existing harness/Ascension owner to bind its actual result/review evidence through these same facilities after legitimate parent review, then run fresh actual-source EVM tests. Existing synthetic RPC bridge tests cannot substitute.

## Deployment observation

contract-manifest.json preserves exact five addresses, historical runtime Keccak and published ABI hashes, configuration, source commit/tree and observedAt2026-10-18T14:51:02.815Z at block26220072. ABI bytes were not retrieved; included hashes identify historical published ABI evidence. Current raw source equality was independently checked. A fresh eth_blockNumber read to ethereum-rpc.publicnode.com failed Operation not permitted; Etherscan was inaccessible to the available web tool. Therefore no fresh same-block bytecode/getter/state acceptance is claimed. Existing wallet profile remains separately qualified; publishing the Oct18 record does not silently install it or authorize funding.
