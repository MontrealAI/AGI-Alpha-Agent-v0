<!-- SPDX-License-Identifier: Apache-2.0 -->
# AGI ALPHA FLYWHEEL — public teaching model v1.0.0

The public flagship combines a demanding engineering narrative with a transparent, deterministic
commercial simulation. It does not execute frontier models, sell work or enforce live network identity.
Its public capsules contain no customer material, protected skills, private evaluation bank or scorer secrets.

## Scope and provenance

Model identity: `alpha-flywheel-model/1.0.0`, evidence date **2026-10-26**, 90-day horizon,
18 synthetic prospective buyers, one enterprise, at most six modeled engineering deliveries
(four in the stress preset). Money is nominal **USD**, before income tax. The model is illustrative,
not a calibrated profitability forecast. No scenario count is a probability of commercial success.

The algorithm foundry proposes a 30-day package for a small satellite operator: an executable
ground-station scheduler, a checked plan, baseline comparison and constraint report. Its binding
restriction is conflicting observation/downlink windows. Reframing as weighted scheduling makes the
constraint explicit and creates a decisive finite correctness test. The human reference uses a 30-day
service period. Automated delivery is assumed within three days (four when late), with opportunities
five days apart; all completions fall within the 90-day horizon. Cash from a later completion is never
used for an earlier start. This timing advantage is assumed, not measured. Flight control and satellite commands
are outside scope. The tangible public sample actually enumerates all 32 subsets of five synthetic
windows: its feasible plan has value 17 versus 15 for a greedy baseline. Those units are objective
units, not dollars, measurements of frontier reasoning or proof of real engineering acceptance.

The matched human-service reference is an **assumed estimate**, not an observed quote: 160 hours
at USD150/hour, totaling USD24,000 over the same 30-day package. Scope: 60 hours of algorithm/software
work, 40 verification, 24 operations research, 20 domain analysis and 16 delivery. The reference
uncertainty range is USD16,000–40,000. Scope equivalence and price require customer validation.

Published foundations remain separate:

| Source | Exact edition and identity | Original population | What is transferred |
| --- | --- | --- | --- |
| [The Economics of Autonomous Work](../../docs/papers/agi-alpha-work-economics-v1.pdf) | v1, SHA-256 `8b9df6f5ef1887d6f972ccfbe26d61a5551962dea41ad7c6595d431dfacb2f51` | 36 fresh bounded reconciliation jobs; original paper horizon | Conceptual comparison against human-delivered work; no performance or profit figure |
| [From Useful Work to Reusable Productive Capability](../../docs/papers/agi-alpha-capability-construction-v1.pdf) | v1, SHA-256 `51ee8ded6860b6ab6b1a7bd1e0901fe864a96c30d40446c3743dd975ba139b28` | 42 fresh jobs across seven digital-work families; original paper horizon | Separate paid delivery, reusable invocation and incremental economics; no assumed positive inheritance finding |

The first study leaves complete costs and matched employer attention unmeasured. The second does not
establish net inheritance savings or self-acceleration. Neither is evidence that the space-engineering
venture performs at the assumed quality, demand or costs. “The Advantage That Survives” brief is research
direction; this implementation does not import unconfirmed findings or combine study horizons.

## Assumption register

| Input | Baseline | Stress | Frontier update | Evidence and sensitivity |
| --- | ---: | ---: | ---: | --- |
| Eligible buyer propensity | 0.90 | 0.40 | 0.90 | Assumed; range 0.35–1; affects realized demand, pricing and reuse |
| Initially correct delivery | 0.93 | 0.70 | 0.96 | Assumed; range 0.65–0.98; affects corrections/refunds and service quality |
| Base delivery cost multiplier | 1 | 2.1 | 0.85 | Assumed; range 0.8–2.2; affects profit/cash |
| Direct saving per subsequent reuse | USD650 | USD250 | USD30 | Assumed; range USD0–650; affects retention only |
| Delivery capacity over 90 days | 6 | 4 | 6 | Assumed bounded capacity |
| Initial capital | USD30,000 | USD16,000 | USD30,000 | Assumed financing; never counted as revenue/profit |

Every monetary input is assumed. Published paper observations are externally reported evidence about
their own workloads. The finite five-window sample is actually computed locally. There is no empirical
calibration of this engineering venture and no observed customer activity.

Demand is an explicit cohort model. Buyer budgets range USD6,500–21,800; urgency cycles over six
declared levels. Buyers choose our offer, a human service, postponement or no purchase. Fractional
expected demand is used only to choose a policy. Seeded execution draws a fresh demand realization
and separate quality/check/correction/latency draws; the policy does not see those future draws.

The finite price grid is USD6,000–18,000 in USD1,000 steps. A manually supplied price between
USD1,000 and USD24,000 is also supported. The policy search compares Beta-only, selective retention,
additional investment and a complementary bundle using equal prices and declared prospective
assumptions. Each price/policy is scored using the same complete cash, demand, quality and A/B/C ledger
simulator as the visible replay, on 16 predeclared development seeds: 1103, 2251, 3371, 4483, 5501,
6619, 7741, 8863, 9901, 10193, 11353, 12503, 13627, 14731, 15859 and 16963. The chosen replay seed
is never used to select its policy. The objective is the mean ordinary operating profit across these
development scenarios, subject to startup cash. The displayed development mean is not a true-world
expected profit, an untouched confirmation result or an empirical confidence interval. Minimum, median,
loss, cash-shortfall and quality-failure counts remain available for each candidate. “Optimal” applies
only to this finite model, grid and declared development set. Ties prefer the simpler policy. No fixed discount, investment percentage
or number of investments is required. Lower real demand or transfer, higher costs, correlated quality
errors and stronger Beta can reverse the decision. The bounded model does not establish durable
sustainability beyond its 90 days.

## Complete accounting and cash

The immutable account labels are non-overlapping:

| Account | Activities |
| --- | --- |
| A — paid delivery | Intake/clarification 180; reasoning, learning and development 1,600; sandbox/tools/compute 220; automated checks 360; packaging/recovery 120; business support 180, each multiplied by the preset cost factor. Corrections/recheck cost 450 × factor when attempted. Processing fees are 2.9% of gross collected receipts. Fixed business overhead is 1,500 per horizon. An additional unpaid support liability of 150 per accepted job is accrued as an A expense once, with `cashPaid:false`; it remains payable at horizon end. |
| B — incremental retention/reuse | Assessment 120 even if rejected; extraction 180, generalization 160, fresh validation 200, packaging 90, integration 70, sharing 60, revalidation 100 and upkeep 80 only if retained. Total 1,060, including assessment. No originating delivery cost is charged again. |
| C — additional investment | 3,600 for deliberate method development only when its forecast repays within the declared model. No automatic investment. |

Retained direct savings reduce subsequent A reasoning/development costs; they are not booked as new
revenue. Bundle-only additional development is assessed using its own joint forecast, with an assumed
extra USD700 per reuse. A standalone investment assumes USD400 per reuse. Neither component is
asserted to independently repay merely because a bundle does. In the baseline automatic search,
selective retention wins; the frontier update selects profitable Beta-only operation. A user can inspect
an assessment that rejects retention while the originating job remains profitable.

Cash must cover each full delivery, correction envelope and fee before the job begins. The USD2,000
reserve and USD150 per accepted-job support obligation remain unavailable for subsequent spending.
Retention and extra investment are paid after an eligible paid delivery and only from available cash.
There are no overdrafts, token appreciation receipts or manufactured surplus.

`net collections = gross receipts − refunds`

`profit = net collections − A − B − C`

`paid costs = A + B + C − unpaid support accruals`

`closing cash = seed capital + net collections − paid costs`

`available operating funds = max(0, closing cash − reserves − support obligations)`

All individual activity IDs are unique. The reserve encumbers cash without an expense. Support
obligations are accrued as expenses exactly once and remain included in cash until actually paid;
available funds deduct the payable, and profit already includes its cost. They are never charged twice. Failed candidates retain assessment costs. Failure and correction costs remain charged.

## Quality and uncertainty

A failed initial delivery falsely passes checking with assumed probability 0.12. A detected failure gets
one paid correction with assumed success probability 0.68, otherwise refusal without collection. A
false pass is later discovered and fully refunded; its processing cost remains. Late accepted work is
retained as an ordinary receipt but excluded from the quality-linked receipt sensitivity. Late probability
is 0.04 (0.18 under stress). No modeled false pass becomes an admitted skill.

Quality-linked profit includes only correct, on-time receipts and **all** A/B/C costs. Refunded false-pass
receipts are already absent from this measure; their refunds are not deducted a second time. Ordinary
accounting is always reported alongside it. Refusals, false passes, late results, cash shortfalls and
corrections remain visible even where total profit is positive. A pooled financial result does not establish
service quality in every run.

The pseudorandom generator and seed define reproducible worlds inside the model. Switching seeds
does not measure uncertainty about demand, correct model specification, human equivalence or real
transfer. The stress/frontier presets change assumptions; they do not represent real-world probabilities.

## Public skill lifecycle and authority

`createPublicSkillRegistry()` keeps canonical current state inside a closure. Exported records and
history copies cannot promote or resurrect a skill. The fixture lifecycle requires fresh public evidence,
net assessment and separate validation before admission. Reuse checks current status, scope, expiry
and versioned Beta. Model changes require fresh revalidation or mark a skill ordinary Beta/retired.
Compositions need their own evidence and validation, and a revoked component disables discovery/reuse.
Rejected candidates live in separate failure memory. Policies are versioned.

**These are public fixtures, not live identity enforcement.** `fixtureEligible` is explicitly an inert test
input for a public example, not authorization based on ENS or a wallet. The public browser has no
protected contents or authenticated private-capsule resource endpoint. Live members-only sharing needs
the existing approved wallet-control/current direct-label `*.agent.agi.eth` verifier and a protected service
boundary. That integration is unqualified. Nested-name matching, a typed name or a client flag cannot
qualify it. AGI Jobs `*.club.agi.eth` roles, deployed contracts and settlement remain untouched. Public
skill access grants no execution permission.

## Models

Simulation assumptions mention Astra-powered reasoning and GPT-6.1 Terra for suitable visual/computer
work. Executed model list is empty. Lump-sum assumed delivery budgets are not API quotations.
The actual stage model identifier/configuration, account access, current pricing, supported tools and
limits must be verified by a qualified runtime before real integration. Official documentation checked
on 2026-10-26: [GPT-6 Astra](https://developers.openai.com/api/docs/models/gpt-6-astra) and
[GPT-6.1 Terra](https://developers.openai.com/api/docs/models/gpt-6.1-terra); account-specific access
remains unverified. ChatGPT Pro is a plan, not a
model identifier or evidence of API access. No downgrade, credential creation or purchase occurs.

## API and verification

```js
import * as flywheel from './engine.mjs';
const result = flywheel.runSimulation({ preset: 'baseline', seed: 42, policy: 'auto', price: 0 });
const replay = flywheel.exportSimulation(result, 'fr');
const restored = flywheel.importSimulation(replay);
```

`result.unitEconomics` supplies the base delivery cost, correction envelope, fixed overhead, fee rate,
unpaid support accrual and exact maximum paid/complete one-job envelopes. The complete envelope
includes the entire horizon overhead conservatively and excludes optional B/C. Interfaces should
derive preparation budgets from these fields rather than copy monetary constants.

Presets: `baseline`, `stress`, `frontier`. Policies: `auto`, `beta`, `retain`, `invest`, `bundle`.
Price zero requests bounded search. Replay import contains only version, language and strict bounded
inputs; derived profits, admission states and permissions are recomputed rather than trusted. An import
cannot grant authority. EN/FR text is supplied for the mission and presets; interface labels are localized
by the maintained flagship template.

Run `node --test examples/alpha-flywheel/engine.test.mjs` from the repository root. Tests cover exact
replay, finite optimization, profitable Beta-only, rejection cost, A/B/C reconciliation, finite cash,
correction/refusal/refund treatment, fresh admission, terminal-state preservation, model updates and
composition revocation. Passing software tests do not establish actual profitability or live qualification.
