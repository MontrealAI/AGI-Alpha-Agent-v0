# Final run design v1 — specified before training and confirmation

The dated `results/protocol_freeze.json` is the controlling manifest. Its source
hash check binds this design, the longer research protocol, adopted calibration,
source/test modules, and deterministic recipient design. Antecedent mechanism
evidence and graph fixtures retain separate identities and evidence status.

## Replications and policy decisions

- Training:24 independent worlds,seeds730001–730024,for each of32 policies in
  conservative,central,and favorable scenarios.
- Confirmation:64 fresh worlds,seeds740001–740064,for each of4 arms in each
  scenario:`beta`(B),`isolated`(I),`network`(S),`network_no_invest`(S0). The same
  selected scenario policy is applied to every arm.
- Price family:fixed human-reference ratios .35/.55/.75/1/1.15,or state-aware
  one-period responses over .25/.35/.45/.55/.65/.75/.85/1/1.15/1.30 with offsets
  −.10/0/.10,clipped to .15–1.40. Each combines with no investment or optional
  investment hurdles1/1.35/2:32 policies,not an exhaustive dynamic policy space.
- Objective:maximize mean collected operating surplus after accrued costs and
  closing commitments/refunds. Require observed training shortfall frequency≤.05.
  Within USD1,prefer no investment,then lexical name. This sample screen is not
  a certified real-world risk bound. No terminal value for graph nodes is added.
- The seller observes scope/urgency,queue,trust and order history. It uses declared
  population priors rather than buyers' private realized values. These priors are
  supplied assumptions,not an estimated market. Pricing is a bounded best response
  to fixed outside alternatives,not a solved market equilibrium.
- Investment appraisal includes full lifecycle costs,technical admission
  probability and estimated displaced delivery margin. Waiting is unpenalized.
- Fifty sensitivity cases are declared in `sensitivity_cases()`,each with16 fresh
  worlds,seeds750001–750016. Use central selected pricing for Beta and network;
  network optional investment is also enabled as a separate policy response.
  The focused/cheap-extraction case is a labeled joint assumption stress.
- Component removal,duplicates,and deliberate forgetting use the first16
  confirmation worlds per scenario. These are adaptive policy effects,distinct
  from frozen-recipient comparisons. Forgetting is not competent Beta.
- World is the replication unit. Means and paired differences use normal95%
  Monte Carlo intervals;binary rates use Wilson intervals. These quantify seed
  sampling conditional on assumptions,not empirical acceptance or demand.
- Preserve complete transaction ledgers for all768 primary confirmation runs.
  Full event traces also retained for the first prespecified seed per scenario/arm;
  every other trace regenerates from its source,parameters,and seed.

## Frontier configuration and billing

Modeled substantive producers,validators,correction agents,builders and investment
evaluators use `gpt-6-astra`,Pro mode,max effort. Qualified visual/computer-use
support uses `gpt-6.1-terra`,standard mode,medium/high effort. These are documented
aliases,not immutable snapshots or measured live task runs. Specifications,
source/tool context,decomposition,critique and correction are represented in the
assumed workload. There is no expert/superhuman quality bonus.

Per-request planning assumes≤128,000 input and≤32,000 output tokens. Campaign
budgets aggregate multiple requests,including all underlying Pro work and billed
reasoning. The simulator meters aggregate tokens and concurrent producers and
validators at five ticks/week. Effective weekly quotas are study constraints,
not account entitlements. Minute-by-minute provider scheduling is not emulated;
a paced broker would be required in operation. Subscription access is not API
credit and supplies no assumed subsidy.

With caching,every fresh input token is conservatively billed as a30-minute write:
Astra USD12.50/M,Terra USD1.25/M. Separately enumerated reads cost USD1/.05 per
million,and output costs USD50/5. Prior context is reused in decomposed call
bursts;latency includes workflow and queue delays. No-cache sensitivity bills all
input at standard uncached rates. No Batch/Flex discount is assumed.

## Complete costs and their boundary

`sources/workload_catalog.json` records assumed token,tool,and latency quantities.
Job tool budgets cover search,executable checks,extra compute and computer-use
support. Weekly shared infrastructure USD165 covers hosting/orchestration,
storage,automated operations and opportunity intake. Dedicated producer execution
support costs USD40 each. Network distribution/access costs USD70 plus USD4 for
each of24 members;local/isolated retention costs USD35. API usage is separate.
Storage/access remain charged with no admissions. USD9,500 bootstrap setup is a
modeled historical cost paid from USD60,000 seed,not measured research expenditure.

Construction packets include search,failed construction,confirmation and
migration. The prospective Alpha assessment partitions their actual modeled
amount70/20/10 without adding it twice. Creator bounties are external contributor
payments under this operator accounting boundary;an internal transfer would need
a different consolidated boundary. Maintenance,distribution,revalidation,
integration,correction,default,refunds and active runoff remain charged.
Available cash excludes unpaid obligations and funded commitments. Authorized
investment budgets and actual accrued expenditure are separate fields.

All competent arms retain ordinary learning. Exogenous copying/method diffusion
uses the same draws across arms. New Beta epochs require fresh Alpha assessment.
The actual assistant research-session bill is unknown,never silently zero,and
is not recouped by simulated receipts. Dollar results are prospective conditional
enterprise economics. AGIALPHA issuance/appreciation contributes zero earnings.

## Reproduction and decision rule

From the study directory run `python3 -m src.run_study all --out results/replay
--workers 4`. Phases `freeze`,`train`,`confirm`,`sensitivity` also run separately.
The harness refuses to overwrite the protocol,selected policy or confirmation.
Postfreeze source changes require a distinct protocol and fresh conditions.
The recipient panel is deterministic and was development smoke-tested;its replay
is an arithmetic reproducibility test,not unseen stochastic confirmation.
