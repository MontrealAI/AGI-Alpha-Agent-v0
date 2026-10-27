# Prospective economic correction v1.1

## What the independent review found

The preserved v1 cash paths charge additional15-minute failed-correction work and30-minute support overruns, but omit those minutes from provider capacity. The money is charged once; the capacity counter is incomplete. The v1 source,20controls,17paths and72conditional worlds remain unchanged. They must not be described as complete capacity validation.

A second issue affects the expected-value price screen: multiplying the entire price by final-payment probability omits an accepted deposit that remains earned when the balance defaults. The event ledger already treats that deposit correctly; the screen is conservative byUSD0.95per reference order. It is not a missing realized collection in the cash paths.

## Separately frozen correction

`capacity-correction-plan-v1_1.json` binds the exact new `run_economics_v1_1.py` before execution. The new candidate counts/reserves each additional A labor obligation before performing and charging it. If capacity is insufficient, the affected unaccepted modeled contract is cancelled and its held deposit refunded. Already performed work remains charged. No unperformed extra labor is billed or represented as delivered.

The explicit prospective contract assumption is that failure to complete preacceptance obligations permits cancellation with a deposit refund. In the support-overrun stress, the extra obligation is discovered **before acceptance**. This does not model rollback or refunds after an already accepted sale.

Provider capacity covers declared internal A construction, delivery, verification, correction and support minutes. B/C are **assumed outsourced fees** in this bounded model; their suppliers' labor and capacity are not tested. Cash costs remain included. The model does not claim zero total labor, universal automation or a measured need for human review. The separate residual-obligations analysis varies verification requirements.

The reference cohort consists of three independently placed orders whose routine intake is included in A. The optionalUSD20joint-coordination fee appears only in the2×2mechanism diagnostic. It is not silently assumed to be a paid coordination service in the reference cash paths.

## Fresh capacity evidence

The fresh seed81926471 generates eight boundary cases:15-minute correction and30-minute support families, each with room for0,1,2or3whole obligations plus a random remainder. All**8/8pass**. Checks independently require exact charged labor, capacity conservation, only fully supported acceptance, deposit refunds and zero paid/performed extra work on refusal.

All**17previous reference paths** retain identical money and acceptance fields at the declared900-minute capacity. Three capacity totals change:

| Path | v1 minutes | Corrected minutes |
|---|---:|---:|
| Common failure |288|333|
| Partial delivery |288|303|
| Support overrun |288|378|

The success path remains440provider minutes,USD568.35modeled profit, andUSD23.30above E. No72-world campaign was rerolled or replaced. The original model still carries its earlier capacity defect; v1.1 is separately evidenced.

## Expected-price diagnostic

The pricing addendum and checker were frozen before evaluating:

`p_accept * (deposit + p_collect * (price - deposit))`.

The corrected finite grid still selects**USD325**. Reference expected E contribution before common C changes fromUSD274.755toUSD277.605for three orders; the difference isUSD2.85. Expected contribution afterUSD25C isUSD252.605under those same limited assumptions. This diagnostic is not a new realized profit and does not assign an empirical probability to the extra common-failure stress.

The historical quote decision and event histories remain intact. The actual complete-cost ledger already recognized accepted deposits correctly, so **no retrospective recovered profit** is claimed.

## Artifacts and reproduction

- Candidate source: `run_economics_v1_1.py`, SHA256 `e9140631370d2d8b3aede189ced3601c9ee0c38e6e3ee8ba618f49f91ccbcec7`.
- Prospective plans: `capacity-correction-plan-v1_1.json`, `checker-pricing-freeze-v1_1.json`.
- Checks: `check_capacity_v1_1.py`.
- Results: `results-v1_1/diagnostics.json`, `results-v1_1/fresh-capacity-cases.json`.

The checker writes to a new fixed directory and refuses to overwrite it. For a replay, copy this study to an isolated temporary directory or adjust the output destination in a separately preserved working copy. The earlier economic script supports a fresh `--out` path for its original study. No native lifecycle, Journal, authority, production scope or accounting implementation changed.

Actual customer revenue remains0; actual full research cost and profit remain unknown. Eight simulation boundary checks establish this implementation behavior, not real-market validity.
