# Economics evidence and scope

The frozen inputs in `assumptions-v1.json` precede technical results. Its raw-byte SHA-256 is
`69f3ad371291069563e751147c219eeea5cb41e0f69a2435830048a4f7d62775`.
All prices, effort, buyer behavior, costs and probabilities other than the two cited tariff/wage anchors
are declared research assumptions. No modeled payment is an observed collection.

## Primary calibration anchors

1. U.S. Bureau of Labor Statistics, *Aerospace Engineers, Occupational Outlook Handbook*.
   https://www.bls.gov/ooh/architecture-and-engineering/aerospace-engineers.htm
   Retrieved 2026-10-27; page modified 2026-08-27. May 2025 median annual wage: USD 134,960.
   Dividing by an assumed 2,080 working hours gives USD 64.884615/hour. Eight to twenty-four team-hours
   and burden multipliers 1.5 to 2.5 are explicit estimates, yielding USD 778.62 to USD 3,893.08.
   This wage is not a consultant quote, a demonstrated task duration or willingness to pay. The comparator
   covers a bounded decision-support package using the same inputs, not satellite operations or certified flight safety.
2. OpenAI, *Pricing*. https://developers.openai.com/api/docs/pricing
   Retrieved 2026-10-27. Standard short-context Astra input/output: USD 10/50 per million tokens;
   Terra: USD 1/5. A purely illustrative 30,000 input plus 10,000 output Astra-token workload costs USD 0.80.
   This component is INCLUDED in the frozen USD 60 fixed A budget, not charged again. The remaining USD 59.20
   is an explicitly assumed preparation, automated verification, infrastructure and correction budget, with no asserted
   measured labor minutes. The USD 20 per-operator A cash budget covers further adaptation and delivery operations.
   These aggregate budgets require live measurement before an operational claim.
3. OpenAI, *GPT-6 Astra Model*. https://developers.openai.com/api/docs/models/gpt-6-astra
   Retrieved 2026-10-27. A prompt above 272,000 input tokens doubles input/cache prices and multiplies output by 1.5.
4. OpenAI, *GPT-6.1 Terra Model*. https://developers.openai.com/api/docs/models/gpt-6.1-terra
   Retrieved 2026-10-27. Current model identity and tool support; tools require Responses API.
5. OpenAI, *Computer use*. https://developers.openai.com/api/docs/guides/tools-computer-use
   Retrieved 2026-10-27. Image/screenshot tokens and external environment costs must be added when such operations occur.

## Contract and ledger interpretation

The customer buys an accepted conditional decision-support package, including a valid fallback. There is no fee
contingent on recommending no maneuver. Technical `baseline_cost` and `contingent_cost` exclude observation acquisition;
their difference is modeled customer information value. It is never enterprise revenue.

Before commitment, every invited operator can withdraw. Remaining buyers recheck utility against their outside option
and the larger share caused by departures. The instrument declines invalid or nonbeneficial cases. An explicit
`customer_cash_available`, if provided, must preserve the full technical `peak_action_reserve`, adaptation cash and FULL fee.
When that field is absent, the program reports required cash without asserting buyer financing.

Acquisition is prefunded as pass-through money and the provider holds 30% of each service fee. Full supplier payment and
delivery expenses precede acceptance. The remaining fee is payable only on accepted packages. An idiosyncratic rejection
refunds the service deposit; a valid acquired observation is still charged at cost. A common package failure refunds ALL
deposits, including observation shares: the provider bears the sunk acquisition expense. This is a distinct commercial
failure, not another sensor-outage model layered on the technical no-result branch. Defaults preserve the prepaid fee
portion but lose the unpaid balance. Support obligations are paid at final settlement. Deposits and outstanding obligations
remain subtracted from cash when calculating available funds. Seed and buyer action reserves are never profit.

The provider cannot execute a branch requiring unavailable funding. The program enumerates those counterfactual paths to
calculate additional prefunding requirements and reports their probability; it does not turn them into completed orders.
Every attempted invitation pays the assumed quote cost, including canceled coalitions. Within a launched cohort, those
quote costs are part of the USD 60 fixed A budget. Mandatory outcome learning belongs in A. Initial B of USD 180, C of
USD 240 and per-use B upkeep of USD 2 are additional optional investments and appear separately in the retention threshold.

## Controls and interpretation

The factorial's T0 is **no constructed contingency instrument**. It is a component ablation, not U and not a competent
operator baseline. Existing individual-observation methods are not erased: T1/A0 supplies the identical conditional
information value but procures separately. A fully competent unrestricted E receives identical algebra, evidence and
coordination rights and MUST tie T1/A1 before any extra B cost. Thus a joint-procurement improvement is not proof of
Operational Alpha, new inference mathematics, agent-exclusive feasibility or autonomous invention.

U/E/E+ are a separate assumption grid. Primary first-pass acceptance is 0.90 for all; equal and negative gains are present.
Only rows with cost multiplier 1 carry the matched-resource-budget label. One/two-attempt rows include retry costs;
retry recovery is assumed at half the first-pass success probability, not independent guaranteed rescue. No rubric score
sets the success rate. The retention table varies unmeasured cash savings from USD 0 to 30 and calculates strict break-even
reuse; zero gain is rejected before paying an unattainable assessment. Feasible gains remain on hold pending new evidence.

## Execution

`python economics/economic.py results/origin.json --output results/economics`

Input JSON has `operators`, a list of one to six records with `id`, `baseline_cost`, `contingent_cost`,
`value_of_information`, `valid`, and `peak_action_reserve`. `customer_cash_available` is optional.
The runner writes deterministic results, the finite event tree and acquisition/fee sensitivity; it needs only Python's
standard library. The accounting tests check independent hand calculations, probability normalization, cash conservation,
refunds, default, withdrawal, liquidity, rejected negative value, false value identity, tariff units and equality controls.

## Frozen fresh confirmation and preserved correction

`python economics/confirm_economics.py evaluation/confirmation-v1 --output results/economics`

The fixed policy is applied to all 48 fresh cases, without selecting favorable economic instances. Twelve original missions
are technically refused as a whole; their partially valid operator outputs are not converted into partial successful
missions. The same USD 2 per-invited-operator preliminary quote cost applies even when the offer is refused. None of the
48 cases launches a paid observation order under the frozen cost/fee assumptions. Total modeled preliminary quote costs
are USD 346; service collections and observation acquisition payments are zero. Recipient 041 also declines. This is a
conditional result in a hand-designed test cohort, not a frequency estimate for satellite-operator demand.

The first economics source and full result files are preserved under `development/economics-v1/`. A review found that
the buyer cash check initially reserved only the deposited service fee. The corrected check reserves the full service fee
and technical fallback, because no later buyer cash inflow is assumed. A cash-level regression between the old and correct
requirements now refuses participation. Primary cases lack verified buyer cash and their monetary expectations remain
unchanged; buyer financing remains explicitly unverified. A separate postcommit-withdrawal diagnostic keeps sunk
acquisition/delivery costs, refunds the fee deposit and charges failure handling. No new withdrawal frequency was fitted.

`results/economics/summary.json` is the compact manuscript-facing result. It separates modeled cash costs from unknown
actual unpaid research effort and unknown residual customer attention. The USD 80 fee is a frozen illustrative hypothesis,
not a human-price discount and not an optimized price. Operational Alpha remains unmeasured; primary q is equal across
U/E/E+. The unrestricted competent expert ties the same technical and coordination mechanism.

If the originating scenario and all 48 fresh invitations are treated as one modeled campaign, their expected contribution
is USD 22.8294714 minus USD 346, or **negative USD 323.1705286**, before optional B/C and unknown actual research costs.
`campaign_summary.json` preserves that aggregate; the positive originating offering does not erase rejected-candidate costs.

`python economics/inverse_diagnostic.py` supplies a postconfirmation diagnostic without changing the primary policy.
At the fixed USD 80 fee, the origin's voluntary full-coalition acquisition ceiling is USD 706.342105263. Recipient 041's
best subset only supports USD 0.04175116 acquisition, with negative provider expected profit even at that boundary.
None of its 25 already-declared acquisition/fee cells yields a jointly viable order. These thresholds identify the next
real measurements needed: a quoted observation price, calibrated information value, actual package effort and participant
commitment. They are not a newly confirmed market or an excuse to assign more favorable priors.
