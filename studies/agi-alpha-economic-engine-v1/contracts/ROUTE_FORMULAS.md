# Four separate settlement routes

**Evidence cut: 25 October 2026. Prospective mechanism definitions only; no financial scenario has been evaluated in this inspection.** Source pins and byte hashes are in `SOURCE_REGISTER.json`. All divisions below are integer floors in the asset's atomic units unless explicitly described as a continuous approximation. A source formula is not a current deployed-state observation, authorization, revenue receipt, or promise of profitability.

## 1. Ordinary off-chain invoicing — proposed commercial arrangement

Let `P` be customer cash actually collected, `a` an explicitly assumed collection/marketplace percentage, and `f` an explicitly assumed fixed collection fee. A proposed supplier's collected proceeds are `P - a*P - f`, less refunds, taxes, production costs and all other obligations before any surplus is available. There is no repository-enforced ordinary-invoice contract or specified processor fee for this proposed arrangement. The financial protocol must supply the seller identity, currency, collection terms, refunds, tax treatment, processing costs, and appropriation authority. Unknown values must not silently become zero.

No token purchase, burn, collateral requirement, tokenholder payment, or automatic reinvestment follows from this route. An assumed appropriation of operating surplus is an enterprise policy, not an existing protocol rule.

## 2. AGIJobManager — native USDC, six decimals

The employer deposits `P` into the Manager. For a completed job, let `v` be its posting-time validator-budget percentage, `n` the number of validators, and `k` the number on the correct side. The current source default is `v=8`, owner-adjustable for future jobs within 1–60. The fixed wallet percentages are 30 and 10.

```text
V = 0                         if n = 0
V = floor(P*v/100)             otherwise
W30 = floor(P*30/100)
W10 = floor(P*10/100)
A0 = P - V - W30 - W10
S = floor(validator_bond * validator_slash_bps / 10000)
pool = V + S*(n-k)             on a reputation-eligible agent win
each = floor(pool/k)           if k > 0, else 0
residue = pool - each*k
agent_settlement_award = A0 + residue
```

Buyer acceptance disables dissenting-validator slashing. Correct validators also receive their own bond back; incorrect validators receive their unslashed bond. The agent's own performance bond and any awarded dispute bond are separate transfers. **Returning one's own collateral is not revenue.** Where forfeited bonds enter the pool, separate that penalty transfer from ordinary customer-funded earnings. For a divisible payment with all reviewers correct and no residue, the default customer-funded split is 8% validators, 30% wallet30, 10% wallet10 and 52% agent. With no validators, explicit buyer acceptance or authorized agent-win arbitration can pay 30% / 10% / 60%; lack of votes alone does not immediately produce a paid job.

`wallet30` and `wallet10` are configured beneficiary addresses. Their names do not establish corporate ownership, tokenholder entitlement, a buyback, a research treasury, or supplier revenue. Owner rotation requires paused intake and no outstanding job escrow or bond reserves. Existing deferred claims retain their beneficiary. Failed transfers become reserved beneficiary claims rather than free treasury money. The generic release config deliberately leaves manager, final owner and both settlement wallets blank.

**Bond formulas.** In atomic USDC, defaults are agent `bps=500`, minimum `1e6`, maximum `88888888e6`; validator `bps=1500`, minimum `10e6`, maximum `88888888e6`; validator incorrect-side slash `8000` basis points. For the agent, first compute `b0=max(floor(P*bps/10000), minimum)`. If the configured duration limit `L` is nonzero, add `floor(b0*duration/L)`; apply the nonzero configured maximum and then the cap `P`. With all agent-bond parameters zero, the bond is zero. A validator bond is `min(P, maximum, max(floor(P*bps/10000), minimum))`, with an all-zero disable case. Default dispute bond is `min(P, 200e6, max(floor(P*50/10000), 1e6))`. These are configuration-sensitive collateral stocks, not percentages to subtract from every successful payout.

**Failure and exits.** Unassigned cancellation returns buyer escrow. Assigned expiry after the source-defined submission deadline returns escrow and transfers the agent bond to the employer. On an employer-win dispute, full buyer escrow returns; correct-review rewards are funded from forfeited agent collateral, capped by that collateral, and remaining collateral/residue returns to the employer. Unanswered arbitration returns escrow and every bond without deciding work quality. No 30/10 successful-job wallet shares are deducted from those refunds. This route has no commit/reveal non-reveal penalty. Settlement pause can delay exits; USDC issuer restrictions can defer transfers. Neither cash timing nor current liquidity is established by source inspection.

**Primary references:** [posting and policy](https://github.com/MontrealAI/AGIJobManager/blob/5d5670df9dbbc79da115e0a44b71989f34df58c1/contracts/AGIJobManager.sol#L705-L767); [payout, collateral and failure accounting](https://github.com/MontrealAI/AGIJobManager/blob/5d5670df9dbbc79da115e0a44b71989f34df58c1/contracts/utils/JobSettlement.sol#L82-L165); [bond calculation](https://github.com/MontrealAI/AGIJobManager/blob/5d5670df9dbbc79da115e0a44b71989f34df58c1/contracts/utils/BondMath.sol#L6-L41); [expiry](https://github.com/MontrealAI/AGIJobManager/blob/5d5670df9dbbc79da115e0a44b71989f34df58c1/contracts/AGIJobManager.sol#L1179-L1201).

## 3. AscensionJobMarket — $AGIALPHA, eighteen decimals

An admitted business, or the uniquely bound MARK contract on its behalf, escrows bounty `B`. The winning bid price is `P <= B`. A selected three-validator committee approves by two votes. Define:

```text
e = floor(floor(P*500/10000)/2)
w = P - 2*e
agent_net = w - floor(w/100)
each_of_two_approvers_net = e - floor(e/100)
burn_total = floor(w/100) + 2*floor(e/100)
client_refund_after_success = B - P
```

The continuous, no-rounding approximation is 94.05% of `P` to the worker, 2.475% to each approving validator, and 1% aggregate burn. The exact rule burns 1% rounded down **separately on each gross payout**. No source treasury fee is deducted in addition to these payouts. No token market price or fiat realization rate is established here.

The worker deposits reusable stake and locks `max(floor(B/10), market.minimumStake)` for each bid. Losing bids unlock their bonds; an approved winner's bond unlocks. The minimum is a positive constructor parameter, not a universal hard-coded number. The historical October 18 snapshot reports 10 tokens for the market minimum and separately 10 tokens for the risk-validator minimum; using those amounts in a future simulation must be an explicit chosen parameter, not a current-chain claim.

Two current eligible rejections, or failure to submit by the assigned deadline, lose the full worker bond: `floor(bond/100)` burns and the remainder augments the client's full bounty refund. Submission followed by missing reviewer quorum instead returns the full bounty and unlocks the worker bond **without slashing**. No valid winning bid also returns the bounty. The original client must claim the refund; where MARK was that client, MARK collects it back into the campaign reserve. The risk oracle locks admitted validators' existing stake and capacity; it does not implement its own fee yield or slashing function. Ascension uses direct votes, not a commit/reveal non-reveal penalty.

Role admission requires owner-set expiring admission and current ownership of the prescribed ENS name. The committee excludes the client, business and executing agent. That structural separation does not demonstrate economically independent reviewers.

**Primary references:** [escrow, stake and bid bounds](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/f836f06e8351e64db1da770e16e304b5feb01f28/contracts/ascension/AscensionJobMarket.sol#L82-L140); [exact settlement and refunds](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/f836f06e8351e64db1da770e16e304b5feb01f28/contracts/ascension/AscensionJobMarket.sol#L183-L249); [validator stake and eligibility](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/f836f06e8351e64db1da770e16e304b5feb01f28/contracts/ascension/AscensionRiskOracle.sol#L39-L81).

## 4. AGI Jobs v0 JobRegistry / StakeManager / FeePool — $AGIALPHA

Keep the **quoted reward `R`** distinct from **total customer escrow `P`**. For the source path with a configured StakeManager and FeePool:

```text
F = floor(R*f/100)                  # posting-time fee percentage f
P = R + F                          # employer funds reward plus fee
V = floor(R*v/100) if validators exist, else 0
R1 = R - V
M = floor(R1*m/100)                 # worker payout multiplier m
worker_burn = floor(M*b/100)        # StakeManager burn percentage b
agent_net = M - worker_burn
fee_burn = floor(F*d/100)           # FeePool burn percentage d
fee_pool_pending_increment = F - fee_burn
```

Here `m` is the agent payout percentage snapshotted on application; the source permits NFT-related payout weights. If `M > R1`, the **existing operatorRewardPool must fund the excess** or settlement reverts. This is a transfer from a prefunded reserve, not extra customer revenue. The exact general `_finalizeJobFunds` implementation first adjusts reward/fee to available escrow and may return a fee to the employer when no FeePool is configured. The simplified formula above requires sufficient correctly funded escrow and an enabled FeePool; freeze those conditions explicitly. `v` and `b` are read at finalization; they must not be described as per-job posting snapshots. `f` is snapshotted at posting.

Validators divide `V` in proportion to their payout weights; integer remainder goes to the highest-weight validator. That branch does not apply the worker-payout burn again. FeePool applies its separate burn to `F`; subsequent accumulated net fees accrue to the configured boosted-stake reward role, default Platform. With no eligible boosted stake, pending fees are burned. Dust goes to the configured treasury or is burned. The shipped configuration's 5% fee, 10% validator allocation, 1% worker burn and 1% fee burn are **configuration examples** with zero-address placeholders, not verified live rates. At `m=100` and ignoring atomic rounding, worker receipts relative to the quoted reward are `(1-v/100)*(1-b/100)*R`; relative to gross customer escrow they are that numerator divided by `(1+f/100)`. Do not use the same denominator for reward, additional fee, worker burn and FeePool burn.

**Worker collateral.** Registry job stake is `ceil(R*jobStakeBps/10000)`, fixed on job creation. The example `jobStakeBps=1000` is 10%. A separate minimum agent-role stake applies on admission; example config is 100 tokens. StakeManager role minima separately specify agent 100 and validator 1000 tokens, with global minimum 100; these are configurable examples, not observed participant balances. Selected validators lock their snapshotted eligible stake, not a universal fixed 10% job bond. Identity, tax acknowledgement, role/stake, blacklist and pause checks apply.

**Failure is not interchangeable with the other two contracts.** A failed finalization or an assigned-job timeout sends `R+F` through `redistributeEscrow` and separately slashes the worker's job stake. The escrow itself is distributed by the configured penalty split; it is not necessarily fully refunded to the customer. In `_splitSlashAmount`, reserve a validator target from amount `X`, then allocate the remainder among configured employer, treasury, operator and burn percentages; unallocated residue is added to burn. Unpaid validator target goes to treasury when configured, otherwise burn. Treasury share also burns when treasury is zero. The shipped 50% employer / 50% treasury configuration is an **escrow/slash allocation**, not a profit-reinvestment policy. An unassigned cancellation instead calls `refundEscrow` for full `R+F`.

**Review non-reveal.** ValidationModule's current source defaults to a 50-basis-point (0.5%) penalty on snapshotted validator stake and a 7200-block exclusion for missing a reveal, and a 50% stake slash for a revealed vote disagreeing with the source-computed outcome. These parameters are owner-adjustable. The force-finalization branch can skip non-reveal penalties when required burn evidence is absent. Crucially, no-quorum `forceFinalize` records a failed Registry state; it does not itself transfer funds or prove the customer and agent receive full refunds. Later settlement follows the failed-state rules. Source comments about refunds must not substitute for this call-chain inspection.

**Primary references:** [posting-time escrow](https://github.com/MontrealAI/AGIJobsv0/blob/bc4abbd5c28f3672275b13300e40ea26c820b8ee/contracts/v2/implementation/JobRegistryBase.sol#L1481-L1562); [success and failed finalization](https://github.com/MontrealAI/AGIJobsv0/blob/bc4abbd5c28f3672275b13300e40ea26c820b8ee/contracts/v2/implementation/JobRegistryBase.sol#L2040-L2136); [worker payout and prefunded boost](https://github.com/MontrealAI/AGIJobsv0/blob/bc4abbd5c28f3672275b13300e40ea26c820b8ee/contracts/v2/implementation/StakeManagerBase.sol#L2327-L2416); [escrow penalty distribution](https://github.com/MontrealAI/AGIJobsv0/blob/bc4abbd5c28f3672275b13300e40ea26c820b8ee/contracts/v2/implementation/StakeManagerBase.sol#L782-L915); [FeePool](https://github.com/MontrealAI/AGIJobsv0/blob/bc4abbd5c28f3672275b13300e40ea26c820b8ee/contracts/v2/FeePool.sol#L239-L365); [non-reveal and outcome penalties](https://github.com/MontrealAI/AGIJobsv0/blob/bc4abbd5c28f3672275b13300e40ea26c820b8ee/contracts/v2/implementation/ValidationModuleBase.sol#L1305-L1469).

## Rules for prospective numerical use

Choose one settlement route per modeled job. Identify the enterprise's contractual role and actual beneficiary; do not sum fees paid to unrelated wallets into its receipts. Keep asset quantities, gas in ETH, currency valuation, collateral stocks, returned collateral, penalties, refunds, fees, cash operating costs, reserves and appropriated surplus in separate accounts. A burn destroys token units; it does not supply cash for model calls, prove a token-price increase or guarantee tokenholder returns. No inspected route automatically buys back tokens, distributes all enterprise profit, converts Manager USDC to AGIALPHA, or allocates 50% of retained earnings to research.

MARK's funded lots may redeem unused campaign reserve under its closure rules, and eligible Jobs FeePool stakers may claim protocol fees under that contract's rules. Neither is a universal tokenholder right to enterprise profit, par-value redemption, liquidity, or capital appreciation. The proposed enterprise reinvestment policy needs a separate authorized decision and a cash/reserve sufficiency test after all costs and obligations.
