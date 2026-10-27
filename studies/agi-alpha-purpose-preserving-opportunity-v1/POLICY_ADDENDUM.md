# Corrected decision policy: feasibility before ranking

The internal review identified a real limitation in the original accounting control: it selected
the offer with the greatest assumed contribution and only then checked liquidity. It could stop
without choosing a lower-contribution feasible alternative. The original control and its 224
evaluations are preserved. This addendum introduces a separate policy with a prospective test.

`economics/feasible_policy.py` enumerates complete offer, configuration, production, retention and
development alternatives under a shared information set, starting cash and world distribution.
It requires attributed independent readiness and acceptance fields, complete disjoint A/B/C
monetary and opportunity costs, strictly positive expected complete contribution, and nonnegative
available funds at every cash prefix in every declared world **before** ranking eligible plans.
Unknown costs or evidence remain ineligible. There is no mandatory investment fraction, fixed
discount or guaranteed benefit from retaining a capability.

The source and contract were frozen at **16:57:39 UTC on 27 October 2026**, before the parent
researcher constructed six diagnostic sets at **17:00:05 UTC**. Source SHA-256:
`5a5bfb3ddd4ab6ea341e214b9cfc8177812e4e53534fc9d2cbeeb7c512ec0c28`.
The source was not changed after the diagnostic cases were seen.

## Observed diagnostic results

All **six of six** expected selections and complete eligible rankings matched. The six sets
contain twenty supplied alternatives. Every dollar figure below is a **constructed hypothetical
input or arithmetic consequence**, not measured demand, delivery cost, cash, profit or a forecast.

| Diagnostic set | Conditional decision | What it verifies |
| --- | --- | --- |
| Funding and evidence | Select the funded service: expected contribution $20, minimum available funds $50 | A $70-contribution plan with a $20 cash shortfall is excluded before ranking; unknown costs, self-attestation, incomplete cost/cash paths, absent acceptance and restricted cash also exclude plans |
| Retention can qualify | Select worthwhile retention: contribution $40, minimum available funds $30 | An affordable beneficial retained capability can pass; the policy is not a structurally impossible admission hurdle |
| Negative contribution | Stop | Funded plans with negative complete contribution do not qualify merely because they can pay their bills |
| Unknown demand/readiness | Stop despite a supplied $140 contribution | An attractive arithmetic result does not replace missing readiness evidence |
| Baseline progress | Select the improved conventional plan: contribution $75 | A stronger available baseline displaces the $40 retained alternative under the same initial resources |
| Zero-weight stress world | Stop at a $5 liquidity shortfall | The declared every-world liquidity rule also applies to a zero-probability stress case |

`review/policy_cases/FREEZE.json` preserves the cases, expectations and source commitment.
`review/policy_results/` preserves all actual outputs and validation, including input hashes and
freeze ordering. The current reproduction script verifies those hashes, replays the selector,
checks the expected decisions and compares full outputs to the preserved results. This addendum
does not retroactively make the original conditional accounting control a calibrated business.

## Interpretation and limits

The result is a software correction with fresh diagnostics. It shows that the selector can admit
a worthwhile constructed retention alternative, reject unaffordable or unsupported alternatives,
and change its selection when a better conventional option is supplied. It does not show that
this study's biological or audit capability earned the retained alternative's assumed benefit.

The selector checks supplied attestation fields and differing identity strings. It does not fetch
evidence, authenticate an attestor, establish willingness to pay, certify completeness of worlds
or validate an upstream ledger's cash conservation. All outputs explicitly retain
`actual_profit_established=false`, `external_evidence_verified_by_this_code=false` and
`production_authorized=false`. Real claims still require genuine independent evidence, complete
measured costs and fresh mission acceptance. The original audit's production stop remains in force.
