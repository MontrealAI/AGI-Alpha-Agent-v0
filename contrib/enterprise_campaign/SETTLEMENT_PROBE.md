[Project notice](../../docs/DISCLAIMER_SNIPPET.md)

# Commercial iteration: conditional settlement, not a profitability guarantee

This research-only extension addresses a recorded commercial failure in PR #5011: releasing useful output before
collection permits unilateral nonpayment. It reuses the sparse delivery/checker from exact #5025 `c46f16f3` and
imports the existing `Recorder`, balances and buyer-alternative functions from `operate.py`. The current #5022
integration of delivery/checker work is preserved; this does not replace its owner or the #5021 invention runtime.

## Executed result

A fixed price of 9 SIM USD and seven inherited scenario settings were held fixed before a 16-seed paired assessment.
The cohort is newly generated update-only work, not a replay of the original full-snapshot campaign. Both contract
arms see the same buyer/input distribution and competent conventional alternatives. Each artifact attempt actually
executes the retained producer and checker. A fee of 0.30 SIM USD plus 3% and buyer friction of 1 SIM USD are explicit
hypothetical mechanism costs, NOT sourced payment-provider rates or observed market participation costs.

| Scenario | Postpaid mean cash project return | Conditional mean cash project return |
| --- | ---: | ---: |
| reference | 439.43224225 | 375.3543656875 |
| competitive_race | 111.620176875 | 49.1046495625 |
| equal_tool_parity | -7.395766125 | -7.3957665625 |
| strategic_default | -8.3177609375 | 375.3543619375 |
| punitive_cost | 318.90456625 | 265.619607625 |
| supplier_disruption | 161.996192625 | 155.107971625 |
| thin_demand | 36.6405284375 | 28.96075175 |

All amounts are SIM USD per generated world, not real earnings. Cash return excludes opening capital and outstanding
receivables; modeled accrued profit and pending settlements remain separately recorded. Both development scopes are
charged (3.55 + 3.55 SIM USD), but these are counterfactual allowances, NOT metered research cost. Operational cost
estimates, acquisition, failed production/checking, corrections, support, warranty, maintenance, broker charges and
measured artifact/journal storage are included in the stated model. Actual complete monetary cost remains UNKNOWN.

224 primary worlds executed 6,211 artifact attempts and 5,983 accepted outputs. In strategic-default worlds, postpaid
produced 852 accepted outputs and collected none; conditional produced/collected 749. Buyer refusal and fees are
not removed to manufacture parity. Conditional settlement helps that scenario but costs money and reduces nominal
reference/competitive outcomes. Equal-tool parity has zero orders in either arm. Do not make conditional terms a
universal default or promote this operational probe to a transformational flagship.

Sixteen additional stress worlds retain failures: complete buyer-lock refusal, high trust friction and full warranty
refunds are loss-making. Static recost of every recorded resource/fee at 10x keeps the reference conditional mean
cash return positive (42.731156875); 100x makes it negative (-3283.50093125). These are sensitivity calculations on
unchanged trajectories, not new liquidity-feasible operating runs or empirical cost estimates.

## What the mechanism establishes

A simulated external custodian locks funds without making them seller cash. The original request and complete output
are checked before the finite transition exchanges payment entitlement and output. Invalid work returns the lock;
committed/refunded exchanges cannot be replayed. Warranty obligations remain. Ordinary database-style atomicity is
the developer-supplied structural pattern; autonomous analogy discovery or novel market mechanism design is not claimed.

The custodian is an IDEALIZED ASSUMPTION. No real escrow, payment API, secure private artifact channel, banking service,
on-chain contract or durable multi-party atomic transaction is implemented or qualified. Sequential file writes are
not production atomicity; incomplete records must fail audit. A trustworthy affordable custodian and withheld output
would need their own construction/qualification before deployment. Current local files are not secret from their host.

## Run and inspect

In the complete parent repository with the retained delivery modules:

```sh
python -m unittest contrib.enterprise_campaign.test_delta_delivery \
  contrib.enterprise_campaign.test_delta_packet contrib.enterprise_campaign.test_settlement_probe -v
python -m contrib.enterprise_campaign.settlement_probe \
  --seed-file contrib/enterprise_campaign/settlement_probe_evidence/seeds.json \
  --output /tmp/alpha-settlement-replay
python -m contrib.enterprise_campaign.settlement_probe_audit /tmp/alpha-settlement-replay
```

Use a new output directory. Reusing published seeds is reproduction, not fresh confirmation. Timing fields, file byte
length and rounded storage charges can vary slightly on replay; the fixed semantic obligations remain the comparison.
The full companion retains all primary/stress journals, artifacts, frozen source, original source version, tests,
source hashes, separate-process audit, resource sensitivities and the local bootstrap excerpt.

57 software tests passed (38 retained + 19 new). All 240 primary/stress worlds were independently reconstructed in a
Linux UID65534 process with CPU60s/address-space512MiB limits. An attempted write-open of the root-owned candidate
was denied; source bytes remained unchanged. Shared host/author/libraries mean procedural separation, not external
certification. These are finite model/engineering checks, not calibrated commercial statistical confirmation; no
confirmatory alpha was spent and these exposed cases cannot become fresh data in later iterations.

## Local scope and pending integration

The environment could not resolve GitHub for a full checkout. Local execution used the previously retained exact
producer/delta code plus explicitly marked transcriptions of the small upstream accounting/alternative helpers.
The excerpt is in the companion only and is NOT added to this repository or substituted for its complete `operate.py`.
Full-source native integration still needs its own exact-head tests. Full locked install, Ruff, strict Mypy,
pre-commit, repository-wide tests, installed distribution, hosted qualification and production financial authority
were not qualified. Normal parent/review/release gates remain intact. No workflow, permission, publisher, source pin,
wallet or production default changes are part of this experiment.

An unused imported name was removed after the v1 assessment; the original frozen source remains in the companion.
Final software tests and read-only reconstruction passed separately. No algorithm, threshold or economic setting
was changed to retune the observed assessment.

## Next evidence-driven decision

Retain conditional settlement as a candidate response to nonpayment; retain its demand/fee disadvantages as constraints.
Do not spend simulated surplus as real money. Unknown actual costs and unmeasured incremental successor benefit block
real reinvestment. No new profit-funded construction or causal invention-to-invention benefit was executed here.
Next establish complete accepted-job effort and a beneficiary who prefers the complete service to equal-tool options.
Only then test a separately frozen outcome-history-based contract policy or a justified enabling construction. Do not
substitute more synthetic nominal profits for that evidence, weaken success criteria, or erase this negative evidence.
