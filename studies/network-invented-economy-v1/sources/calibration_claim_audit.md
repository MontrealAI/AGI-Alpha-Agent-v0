# Independent calibration-to-claim audit

Audit date: 26 October 2026. Scope: source calibration, expert-model billing,
human-service equivalence, counterfactual interpretation and scientific
confirmation. This is an audit of a **development** simulator, not a final
qualification. The inspected `src/simulator.py` had SHA-256
`9287debb36c170dd7d2ef86296b6bf53a096fff4d27b09bbfe949c7f0c171bb1`
when the quantitative checks below were executed. Other study contributors are
independently checking cash chronology, program invariants and graph policy.
No simulator code was changed by this audit.

## 1. Claims justified by each layer

| Evidence layer | Defensible claim | Claim it does not establish |
| --- | --- | --- |
| Official current OpenAI documentation | The named aliases, supported settings, documented prices and listed limits exist as retrieved on the evidence date | The study's account has access or the models achieve the assumed task acceptance rates |
| Published mechanism-design and skill-transfer research | Executable mechanism construction and beneficial transfer are plausible within bounded settings; reconstruction, overfitting and negative transfer must be retained | A universal improvement coefficient, Astra-specific customer acceptance, or demand for this offering |
| Native-source accounting checks | Two unchanged source-pinned accounting helpers execute against their own schemas, with provenance and unknowns preserved | Native production integration, settlement, actual receipts or causal economic benefit |
| Local mechanism witness | The authored known-method implementation can be checked against finite oracles and certificate rules; its exact measured operation costs can be compared | A frontier model invented the algorithm, a recipient lacked the theory, or the measured Python operation count prices an AI job |
| Simulator confirmation | The frozen implementation and policy produce the reported outcomes under its stated assumptions | Prospective sales, calibrated acceptance probabilities or realized reinvestment success |

The source links and factual details supporting the first two rows are in
`calibration.json` and `calibration_notes.md`. No benchmark percentage should be
converted into an adoption, acceptance or invention probability.

## 2. Official-rate arithmetic is sound; task quantities remain assumptions

The inspected `Work.cost` uses documented Standard API rates: Astra input/cache/
output USD10/1/50 per million, Terra USD1/.05/5. There is no arbitrary expert-use
quality multiplier in that arithmetic. All role work should nevertheless be
described as **aggregate billed usage across multiple decomposed requests**,
including the underlying work counted by Pro. Visible response length alone
would undercount Pro and reasoning output.

The protocol should say whether it assumes every request remains at or below
272,000 input tokens and 128,000 output tokens. If a request exceeds the input
threshold, the documented full-request surcharge applies. A campaign's many
millions of aggregate tokens is not a single permissible context.

Cached reads need an operational explanation: cache reuse of previously paid
contexts with no optional explicit write tier is a reasonable declared scenario,
but is not a measured hit rate. Explicit 30-minute/12-hour cache writes have
their own prices and cannot silently be treated as free if used. A no-cache
sensitivity is useful. Weekly quotas are finite study-chosen effective capacity,
not evidence of account-level authorization, a subscription entitlement or a
fresh quota for each agent. Subscriptions and API bills remain separate.

The official pages exposed aliases rather than immutable dated snapshots. Use
the alias and retrieval date; do not manufacture a dated deployment ID. Future
live runs should capture any resolved model version and usage metadata.

## 3. Human-price equivalence is the main commercial assumption

The four hourly values are observed US service-schedule rates. All role-hours
and their equivalence to the proposed deliverable are assumptions. The resulting
USD25,329 / 49,857.64 / 98,114.56 are **derived reference estimates**, not observed
quotes. The middle scope is 196 team-hours, not 196 elapsed hours and not five
calendar weeks. Human delivery latency and procurement time are separate,
unmeasured assumptions. Neither rate-card source verifies human-only effort.

The bounded package must include the same requirements, implementation,
adversarial tests, evidence and integration guidance on both sides. It excludes
live integration, legal assurances, professional deployment responsibility and
ongoing operation. Pricing an untested idea against a completed human outcome
would invalidate the comparison.

The inspected central workload arithmetic gave the following **assumed variable
delivery costs**, before intake, fixed infrastructure, failed work, correction,
capability construction, upkeep and collection losses:

| Scope depth | Fresh unfamiliar delivery | Derived human reference |
| --- | ---: | ---: |
| One component | USD909.40 | USD25,329.00 |
| Two components | USD1,821.58 | USD49,857.64 |
| Three components | USD3,393.88 | USD98,114.56 |

This approximately 27–29-fold ratio is not an empirical productivity estimate.
It follows from assumed human-equivalent scope and assumed automated usage.
Doubling token prices alone weakly challenges that premise. Robustness should
include human-equivalent scope/value at 10–50% of the central reference, cheap
reconstruction by a competent recipient, weak trust and nearly zero leads.
Demand, collection and willingness to pay require prospective measurement.

## 4. Causal and metric interpretation

Prefer **isolated retained capability versus network retained capability** as
the main comparator. Both have the same frontier tools, initial experience and
finite resource budget. No-retention is an intentionally forgetting diagnostic;
it is not a faithful general claim about a competent system that learns during
work. Initial domain familiarity is currently fixed, so no-retention cannot be
used to infer that fresh frontier agents generally fail to learn.

Every job depth in the inspected model is initially feasible in principle. Its
capabilities avoid reconstruction or improve reliability/throughput. A claim of
new feasibility therefore needs an explicit budget, latency or accepted-quality
threshold and a paired crossing of that threshold. The simulation does not show
that existing frontier reasoning lacks the underlying mathematical methods.

Per-component removal arms may still evaluate and build the component they
cannot use. If retained, call this a policy-response intervention including its
wasted spend. A frozen-trajectory/local paired removal is cleaner evidence of
the component's marginal contribution with other resources held comparable.
Neither comparison is an external AI-market benchmark.

The inspected `useful_transferred_skills` counted valid artifacts selected by
any non-owner. Selection occurs at order time and can include failed adaptation,
rejected jobs or no marginal benefit. Rename that descriptive statistic or
replace it with a paired useful effect. Similarly `recipient_useful` is useful
output associated with transfer, not useful output caused by transfer. Growth
claims should use fresh-task cost, quality or feasibility effects, not entry,
invocation or recipient counts. Keep distinct source campaigns separate from
many descendants of the same artifact.

Complementarity should arise from executable dependencies, avoided coupled
rework or measured throughput effects. Free-standing USD250/USD400 forecast
bonuses, if present in a development version, are assumptions and should not
be treated as realized gains. A useful bundle need not make each component
profitable alone. Receiver-side verification and integration remain full costs.

## 5. Policy and confirmation scope

The inspected pricing rule is an approximate finite-grid contribution
best-response to assumed buyer utility and quality parameters. The investment
rule is a finite forecast/hurdle policy with optional waiting. Selecting a winner
among declared policies supports **best within the tested family**, not global
dynamic optimality or a proven equilibrium of a repeated market. Report cash,
profit, accepted outcomes and useful capability effects separately. A profitable
no-investment outcome is an economically coherent result.

Freeze source, adopted assumptions, arm definitions, policy candidates, objective,
selection rule, seeds, summary metrics and hypothesis criteria before final
confirmation. Preserve development results, including any changes prompted by
weekly scheduling artifacts or invalid complementarity terms. Confirmation must
not be silently rerun after inspecting unfavorable outcomes. A changed protocol
needs a new identity and fresh confirmation set.

Use the independent simulator world/seed as the replication unit. Hundreds of
jobs descended from one retained skill are not hundreds of independent invention
campaigns. Paired worlds and shared exogenous draws improve ablation precision;
do not mistake the resulting narrow within-model interval for uncertainty about
the real market. Fresh seeds test stochastic generalization within the same
model; parameter shocks test robustness to a different assumed environment.
Both are useful and must be labeled separately.

## 6. Accounting boundaries to disclose

Define the ledger's organizational boundary. A bounty paid to an independently
owned contributing agent is an operator expense; a transfer between agents owned
by one enterprise is not a consolidated network resource cost. $AGIALPHA utility
must not be conflated with USD operating earnings or token-price appreciation.

Modeled historical setup costs should remain charged, but they do not measure
the actual resource bill for creating this research package. That actual bill
is unmetered unless separately obtained. `live_model_calls=0` means no deliberate
role-execution API experiment occurred; it does not imply the assistant's own
research reasoning used no compute.

These recommendations were communicated to the study lead during development.
This file intentionally records their original status rather than claiming all
were resolved. The final protocol, source diff and result report must identify
which recommendations were adopted, which were scoped as limitations and which
remain open.
