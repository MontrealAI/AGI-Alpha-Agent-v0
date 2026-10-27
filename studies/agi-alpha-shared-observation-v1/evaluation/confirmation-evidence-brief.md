# Independent confirmation evidence brief

## Result and scope

The frozen retained compiler conforms to the independently written conventional exact evaluator on **48 of 48 fresh synthetic missions**. It accepts **36 finite contingent plans** and correctly refuses **12**. These are executed software results inside a supplied finite Bayesian model. They are not measured spacecraft safety, calibrated orbital predictions, frontier-model task trials, buyer acceptance, actual collections or demonstrated algorithmic superiority.

The independent reference receives the same mission information, rights and arrangement permissions. It ties the retained compiler throughout. Thus the result supports portable, inspectable construction and correct decision handling under the frozen contract. It does not establish a computational advantage over the competent conventional method.

## Freeze and independence

The evaluator author received the mission contract and output conventions but did not inspect the compiler, its profile or development outputs before freezing the independent implementation. The implementation uses rational arithmetic and explicit per-branch action enumeration. The source/generator/input commitment is `evaluation/reference-freeze-v1.json`.

- Retained compiler source freeze: `evidence/technical-freeze-v1_0_1.json`, 2026-10-27 17:03:47 UTC; compiler SHA-256 `7a15a72a727ee9b1c6bb715f0c609bf99194150d156851dcb91eed1f347ebb1c`.
- Independent reference, generator and input commitment: 17:03:54 UTC. The 48-case manifest SHA-256 is `e9678c6b1e022ae5ac153b1d563b4d17ca1a4fbd4d8122b5066195efcf1e930f`.
- Fresh confirmation: 17:04:26–17:04:29 UTC. Reference answers were computed during this execution and preserved alongside candidate outputs. They were not part of the retained artifact.
- All 48 inputs and every candidate, reference, check and process record are preserved. `evaluation/confirmation-v1/summary.json` is the machine-readable result authority.

The approximately 2.095 summed subprocess wall seconds are local execution telemetry including process startup. They do not measure engineering effort, provider billing, a human-equivalent service duration or frontier-model efficiency.

## Category results

| Fresh category | Cases | Independent conformity | Accepted plans | Correct refusals | Positive / zero / negative aggregate gross information value |
|---|---:|---:|---:|---:|---:|
| Shared information | 8 | 8 | 8 | 0 | 8 / 0 / 0 |
| Zero or negative value | 8 | 8 | 8 | 0 | 0 / 4 / 4 |
| Adverse information | 8 | 8 | 8 | 0 | 0 / 0 / 8 |
| Heterogeneous deadlines and timeout | 8 | 8 | 4 | 4 | 4 / 0 / 0 |
| Sensor prerequisite failures | 8 | 8 | 0 | 8 | Not applicable |
| Participant withdrawal | 8 | 8 | 8 | 0 | 8 / 0 / 0 |
| **Total** | **48** | **48** | **36** | **12** | **20 / 4 / 12** |

The checker inspects **594 operator branches**, including **12 unreachable branches** and **10 unsafe reachable branches** that remain visible in refused missions. Sensor-prerequisite refusals correctly retain baseline reporting without claiming contingent value.

The heterogeneous-deadline cases include an adversarial timeout: a fallback is acceptable under the prior but becomes unsafe when conditioned on the aggregate of all late and absent observations. Substituting the prior or revealing a hidden late-result label would incorrectly accept it. The compiler and independent reference both refuse the affected missions.

## Negative value is a commercial decision, not a software failure

Gross information value here means modeled baseline action cost minus modeled expected contingent action cost, before acquisition, service fees and extra qualification. It is **negative in 12 accepted missions**, zero in four, and positive in twenty. The range among accepted plans is approximately **−$60.33 to +$529.03 in assumed model dollars**.

Four negative missions have an already acceptable cheap coast action. Their mandated timeout fallback adds expenditure. Eight others also reveal adverse states in which the prior-optimal coast action is no longer acceptable under the original conditional risk criterion. Better information therefore does not guarantee lower action expenditure in this contract.

Under a buyer model valuing only avoided action expense, the 12 negative and four zero gross-value missions cannot support a positive acquisition/service price and should be declined. This does not exclude other independently established buyer values; those would require an explicitly different willingness-to-pay model.

Aggregate surplus is also insufficient. **Thirteen accepted missions contain at least one individually negative buyer**, although only twelve have a negative aggregate. Recipient mission `confirmation-041` is the additional case.

## Fresh recipient interpretation

The first withdrawal-category mission was selected as the transfer example because it changes the model dimension and active roster: five latent states, three remaining operators and eighteen branches. Selection did not maximize the observed gain. Its original six-operator roster loses three participants before the active mission is compiled; removed buyers contribute no benefits or commitments.

| Remaining operator | Baseline action cost | Expected contingent action cost | Gross information value |
|---|---:|---:|---:|
| operator-0 | $0.00 | $16.03 | **−$16.03** |
| operator-1 | $160.89 | $57.45 | +$103.44 |
| operator-3 | $75.95 | $27.12 | +$48.83 |
| **Total** | **$236.84** | **$100.60** | **+$136.24** |

These figures are conditional synthetic action costs, not market quotes or money earned. A positive-price full-roster offer is not voluntarily acceptable to operator-0 under the stated avoided-cost model. The correct continuation is to decline that arrangement, recompile a voluntary subset with its original obligations, or assess an explicit compensation arrangement. The compiler cannot infer consent from shared technical structure or aggregate surplus.

The separate recipient operator executes actual transferred compiler bytes in another process. Its evidence belongs to `evidence/recipient-transfer-v1_0_1/`; the independently checked result matches this reference. The identical-content ordinary-library comparison matches too. This establishes executable portability, with no graph-specific benefit or live authentication claim.

## Analytical information-value condition

Let the baseline action be

\[
a_0\in\arg\min_{a\in A_0}c(a),
\]

where \(A_0\) contains the actions that meet the prior risk bound and are available at time zero. For each reachable observation branch \(b\), let \(A_b\) contain the actions that meet the posterior risk bound, remain timely, and comply with any mandated timeout action. Let \(p_b\) be the branch probability.

**Sufficient condition.** If \(a_0\in A_b\) for every reachable branch, then

\[
\sum_b p_b\min_{a\in A_b}c(a)\le c(a_0).
\]

**Proof.** Inclusion makes \(a_0\) an available competitor in each branch, so each branch minimum is at most \(c(a_0)\). Multiply by nonnegative \(p_b\), sum, and use \(\sum_b p_b=1\). This proves the bound without any claim about realized physical risk.

The condition is sufficient, not necessary. Failure permits but does not force negative gross information value. Physical availability alone is insufficient: posterior evidence can make a prior-safe action inadmissible. A mandated timeout action can also exclude the baseline action. Acquisition and service costs can make net information value negative even when this gross-cost bound holds.

The post-confirmation analytical diagnostic finds that the inclusion condition holds for **90 of 130 accepted operator plans**, with **zero bound violations**. This is a check of the recorded outputs, not the proof itself and not another fresh confirmation cohort. `evaluation/information-bound-check.json` preserves the diagnostic, including the separate buyer-level negative values.

## Additional bounded checks

After fresh confirmation, the originating mission passed **102 independent comparisons**. Twelve separate malformed-input probes received structured exit-2 refusal without traceback: probability normalization, nonfinite probability, negative cost/time, likelihood normalization, missing fallback, duplicate/reserved identifiers, missing/oversized operator rosters, boolean cost and nonboolean prerequisite. These are post-confirmation diagnostics, not additions to the primary 48-case success denominator.

Evaluator and runner Ruff checks pass. The available Black installation failed before formatting because `pathspec.patterns.gitignore` was missing; Ruff formatting was applied before the independent source freeze. No core algorithm or protected input was revised in response to confirmation results.
