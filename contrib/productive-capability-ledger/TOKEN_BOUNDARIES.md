# Currency and authority boundaries

Source inspection: 25 October 2026. This is an implementation map for the inert product ledger,
not current chain verification, a deployment approval, transaction preparation or a complete protocol audit.
No chain RPC, signing, spending, configuration update or contract test was performed for this map.
“Tests present” below means inspected test sources exist; it does not mean those tests ran here.

## Inspected identities

| Repository | Exact inspected main |
| --- | --- |
| Alpha | `aaad4763c0df96943a3e8a66987c4c013a6e3589` |
| AGIJobManager | `5d5670df9dbbc79da115e0a44b71989f34df58c1` |
| AGI Jobs v0 | `bc4abbd5c28f3672275b13300e40ea26c820b8ee` |
| Fleet Linux | `45759fb096faf8988f58ae5ea71248d0f35a97c7` |

## Implemented paths and their scope

| Path | Funding, collateral, incentives and payout | Authority and qualification |
| --- | --- | --- |
| Manager / USDC6 | `createJob` pulls exact USDC escrow. Agent, validator and dispute bonds have separate liability accounting. `finalizeJob`/`acceptJob` reach `JobSettlement.complete`: 30% and 10% recipients, snapshotted validator budget and remaining agent payout, subject to rounding, reviewer accounting and bond return. Failed transfers become beneficiary claims (`claimUSDC`). | Owner controls configuration and pauses; job/participant roles control lifecycle actions. `withdrawableUSDC` excludes escrow, all locked bonds and deferred claims; owner withdrawal requires paused intake and unpaused settlement. No automatic conversion, $AGIALPHA purchase or $AGIALPHA burn follows a USDC settlement. Current package config says `deployment-required`, with no default manager target. |
| Alpha Ascension / AGIALPHA18 | `AscensionMark.open`/`buy` fund a bounded campaign; `sell` reverses funding lots. `bloom` locks the campaign phase; `route` spends reserve only on a Merkle-proved plan job. `collect` returns job refunds; `close`/`reclaim` return remaining principal proportionally to lots. These returns are not enterprise earnings. | Seed owner/business, current eligibility/risk checks, exact plan and reserve constrain routing. This is a plan-restricted contract reserve, not an autonomous enterprise treasury. Governor has specified one-time graph binding powers; these are separate from off-chain execution approval. |
| Alpha Ascension job market / AGIALPHA18 | `post`/`postFromSeed` escrow bounty. Agent `deposit`/`withdraw` maintain unlocked stake; bids lock a bond of max(minimumStake, bounty/10). Artifact-bound committee voting leads to `_pay`, `_fail`, timeout or refund. `_payout` burns `gross/100` and sends the remainder; failed-worker bond slashing also burns 1% of the bond. Accepted job rewards include the selected approving validators. | Business, agent and selected validator eligibility apply. `_pay` requires two approvals and rechecks eligibility. This actual burn mechanism must not be generalized to unrelated Manager settlements, off-chain work, or every token transfer. |
| Jobs v0 canonical registry / AGIALPHA18 | `JobRegistry.createJob` and lifecycle reach delegated `StakeManager` escrow. `lockReward`, `releaseReward`, `refundReward`, `finalizeJobFunds` maintain job-linked custody. Participant staking, configurable fees, payout burns and slashing are distinct. `FeePool.depositFee` receives accounted fees; `distributeFees`/`claimRewards` allocate eligible boosted-stake rewards. `contribute` and authorized `reward` are explicit additional funding/reward actions. | Actual delegated entry bodies enforce registry/governance/participant permissions and pause/acknowledgement conditions. FeePool setters/rewarder allowlisting are owner controlled. Rewards are conditional protocol distributions to eligible stakers, not a universal entitlement of passive token holders or a distribution of enterprise accounting profit. Source/configuration/test existence does not establish a deployed instance's current settings or readiness. |
| Fleet project route | `manager-usdc` explicitly maps to USDC; `agijobsv0-jobregistry-v2` maps to AGIALPHA. Bounded execution/check results carry `authority:none`, `independentReview:false` and `settlement:not-connected`. | Source adapters preserve units and upstream identity. They do not settle funds or qualify an installed four-product executor combination. |
| Alpha runtime receipts | `Economics` verifies an invoice-linked AGIALPHA `Transfer`, confirmed block/configuration and duplicate-consumption identity; records `reinvestment_earmark_units = amount * reinvest_bps / 10000`. | The association is operator-linked because ERC20 transfers lack mission memos. `reinvestment_executed:false` is explicit. An earmark on a gross transfer is not full-cost surplus or an executed investment. |
| Nova read-only history | Receipt revalidation attributes payouts and returned principal separately; returned principal has `income:false`. Provider/storage/all-cycle gas costs, `profit` and `spendableIncrease` remain unknown. `createReinvestmentProposal` produces a balance-bounded suggestion/read-only quote. | The proposal has `allocation:none` and `actualSpend:none`. Existing wallet preparation and explicit confirmation remain separate; the shadow ledger never invokes them. |

## Deployment and test evidence

Alpha's preserved October 18 manifest records exact-match explorer results, creation/binding transactions
and a point-in-time five-contract authority observation. It simultaneously sets `activationAllowed:false`,
`readyForPublicFunding:false` and `fullyProductionReady:false`, with external authority inventory,
real-dependency fork, independent security and commissioning work still outstanding. This map does not
refresh those observations. Manager's current USDC configuration records an owner-reported older paused
instance separately from the current software package. Jobs' mainnet configuration and verification
recipes are configuration inputs, not evidence that the current source graph was deployed or accepted.

Tests present include Alpha Ascension lifecycle/marketplace/settlement fixtures and runtime economics;
Manager settlement fuzz/lifecycle invariant tests; Jobs FeePool, StakeManagerBurn and escrow/accounting
invariants; Fleet project-journey/budget tests. Their prior outcomes retain their own exact source scope.
No current test pass or deployed compatibility is inferred from this inventory.

## What the product ledger may model

The new shadow ledger accepts one explicit fiat planning currency; token quantities never become fiat
revenue without a separately supplied valuation. Collected revenue, assumed prices, complete costs,
unpaid obligations, reserves and proposed investment remain separate. Choosing 50% reinvestment is an
editable scenario, including a zero-investment scenario, and conveys no execution authority.

No automatic **50% enterprise-surplus reinvestment**, enterprise-profit sharing to all token holders,
market buyback or guaranteed appreciation mechanism was established in the inspected paths. Existing
protocol fee rewards and burns above are real source mechanisms and remain distinguished. Adding a
surplus-funded allocator would require a separately scoped proposal: accepted-work/proceeds provenance,
complete-cost and liability reconciliation, finite budget, explicit operator approval, destination and
unit identities, idempotent accounting, failure/rollback rules and independent deployment review.
This assignment proposes no contract mutation and enables no transfer interface.

## Immutable source references

- [Alpha contracts](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/tree/aaad4763c0df96943a3e8a66987c4c013a6e3589/contracts/ascension),
  [deployment snapshot](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/aaad4763c0df96943a3e8a66987c4c013a6e3589/deployments/ethereum-mainnet/2026-10-18/manifest.json),
  [runtime receipts](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/aaad4763c0df96943a3e8a66987c4c013a6e3589/alpha_factory_v1/core/runtime/chain.py),
  [Nova ledger](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/aaad4763c0df96943a3e8a66987c4c013a6e3589/docs/assets/nova-studio/ledger.mjs).
- [Manager contract](https://github.com/MontrealAI/AGIJobManager/blob/5d5670df9dbbc79da115e0a44b71989f34df58c1/contracts/AGIJobManager.sol),
  [settlement](https://github.com/MontrealAI/AGIJobManager/blob/5d5670df9dbbc79da115e0a44b71989f34df58c1/contracts/utils/JobSettlement.sol),
  [USDC package configuration](https://github.com/MontrealAI/AGIJobManager/blob/5d5670df9dbbc79da115e0a44b71989f34df58c1/config/usdc-deployment.json).
- [Jobs registry](https://github.com/MontrealAI/AGIJobsv0/blob/bc4abbd5c28f3672275b13300e40ea26c820b8ee/contracts/v2/JobRegistry.sol),
  [actual escrow entry bodies](https://github.com/MontrealAI/AGIJobsv0/blob/bc4abbd5c28f3672275b13300e40ea26c820b8ee/contracts/v2/implementation/StakeManagerBase.sol),
  [FeePool](https://github.com/MontrealAI/AGIJobsv0/blob/bc4abbd5c28f3672275b13300e40ea26c820b8ee/contracts/v2/FeePool.sol),
  [mainnet inputs](https://github.com/MontrealAI/AGIJobsv0/blob/bc4abbd5c28f3672275b13300e40ea26c820b8ee/deployment-config/mainnet.json).
- [Fleet project transfer](https://github.com/MontrealAI/AGI-Fleet-Linux/blob/45759fb096faf8988f58ae5ea71248d0f35a97c7/local-runtime/project/transfer.mjs),
  [route guide](https://github.com/MontrealAI/AGI-Fleet-Linux/blob/45759fb096faf8988f58ae5ea71248d0f35a97c7/docs/local-skills/PROJECT_JOURNEY.md).
