# One exploratory recipient-prior diagnostic

Status: post-confirmation exploratory belief sensitivity, specified after inspecting the frozen zero-uptake result. This is not a replacement confirmation, empirical capability measurement, or tuned optimal policy.

## Question and motivation

Frozen v3 uses a Beta(2,2) recipient quality prior. Even 24/24 modeled component-test passes yield 26/28 = 0.928571, below favorable Beta's assumed 0.97 reconstruction correctness. At the favorable condition's minimum offered price, the recipient's resulting quality penalty can exceed the complete named reconstruction saving. Graph admission uses paired component-value evidence, so its valuation and the recipient's absolute-quality heuristic can disagree. This diagnostic tests one declared-prior calibration; all frozen negative results remain.

## Fixed design

- Condition: the already prespecified `compound_static_beta_large_pool_recurrence`, with its exact frozen economic configuration and activity-cost register.
- 100 fresh independent world IDs; seed 951557. All three arms share identical primitive random draws per world. This is 100 matched worlds and 300 policy histories, not 300 independent trials.
- Arms: `frozen_beta`, `frozen_network`, and `posterior_coherent_network`. Underlying receipt policy IDs remain `optimized_beta`, `optimized_network`, and `optimized_network` respectively.
- No changes to actual frontier correctness, construction/generalization success, transfer success, costs, capacity, agents, demand, prices available to the policy, collections, raw paid tests, source eligibility, ordinary local learning, cash/reserve rules, or competent Beta.
- No additional parameter sweep or retuning regardless of the result. Stop after this one run.

## Sole nonzero treatment

Retain four prior-equivalent component cases. Let q_good be the scenario's retained-component correctness and q_bad = 0.65, as in the frozen outcome generator. For a separately researched asset let pi = the declared asset-build success. For a paid-job capsule let pi = the declared reconstruction correctness multiplied by declared retention-generalization success. This deliberately does not use source latent truth, future transfer outcomes, or future customers.

Set q0 = pi*q_good + (1-pi)*q_bad and posterior recipient correctness = (4*q0 + observed component passes)/(4 + paid component cases). These prior means are uncalibrated decision assumptions. They are not evidence that actual capabilities improved. Reassessments retain the same paid batch sizes and refresh schedule.

The extension also makes the recipient quality valuation honor `alpha_quality_effect_fraction`. That multiplier equals 1 in this condition, so this correction has zero treatment effect here. It is documented because the frozen zero-quality-effect ablation does not disable this recipient valuation term completely.

## Outcomes and interpretation

Report all arms' adoption, component and useful capability-project use, funded retention, full and quality-adjusted profit, costs, collections, reserves and resource use. Compare posterior-coherent network with both frozen Beta and frozen network using matched differences; report means, medians, 5th/95th percentiles and frequencies of improvement. A retained asset's admission is not evidence of repayment. The strict paid-job feedback indicator additionally requires an operating-funded retained package, a useful collected source, a truly accepted fresh recipient use, no optional C campaign, and positive full/quality-adjusted total-policy differences from Beta. These are modeled outcomes, not observed sales or independent asset-level causal repayments.

Preserve every full financial/resource ledger and activity/source receipt. Any selected trace is a labeled illustration of an existing world and must match its saved scalar values. Report negative or ambiguous results without a second diagnostic.

## Reproduction

From the project root:

`python3 sim/run_recipient_prior_diagnostic.py --freeze`

`python3 sim/run_recipient_prior_diagnostic.py --run --workers 3`

The first command records code, protocol, economic configuration and cost hashes. The second verifies them before and after execution. Outputs are under `results/paid_work_prior_diagnostic/`.
