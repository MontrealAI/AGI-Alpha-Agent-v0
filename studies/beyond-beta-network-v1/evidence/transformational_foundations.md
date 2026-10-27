# Transformational venture research: independent foundations readout

## Source and status

The supplied manuscript is **Vincent Boucher, _Transformational Intelligence: Learning to Change the
Game_, October 2026**, 24 pages. Its complete text, references and appendices were read; page 6 was
also rendered and visually checked to confirm the mathematical definitions and decomposition.

- Current inspected source: [immutable PDF at Alpha commit
  098117379f2920ebe37ab23dad77b7314a32518c](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/098117379f2920ebe37ab23dad77b7314a32518c/docs/Transformational_Intelligence.pdf).
- PDF SHA-256: `d7170e8217e3bf6aa1b84868c1c76c5994c6995c5297ed092d7e72a6430c664f`.
- Git blob: `1f95db3b087d8dd0712012d34ba700d7dd2e1382`; 305,040 bytes.
- Identical blob at earlier inspected Alpha commit `cb1d232668564fec281dfb0ac834ddbb83ab5115`.
- Local originals: `Transformational_Intelligence.pdf` and full page-marked text
  `Transformational_Intelligence.txt`. Detailed identity: `manuscript_source.json`.

This is a fresh research charter. The previous human-market documentation study's workload, prices,
review allocation, skill definitions and two-investment criterion are not calibration or constraints
for the new venture study. Its frozen outcomes remain intact. The already registered adverse campaign
continues under its own old freeze; no old publication was performed by this research agent.

## Organizing principles supplied by the manuscript

| Principle | Manuscript location | Consequence for the new study |
| --- | --- | --- |
| Separate purpose, formulation and evaluator | pp. 2–3; §2.1; p. 6 equations (5)–(8) | Write a new intent charter, distinguish the inherited commercial/workflow assumptions from actual user requirements, and specify the outcome instrument separately. |
| Diagnose a binding restriction | pp. 7–8; §5.1 | Identify which missing information, discarded distinction, repeated reconstruction, coordination rule or evaluation proxy prevents useful progress. Repeated heuristic failures do not establish a frontier-model ceiling. |
| Build an executable alternative | p. 7 equation (10); pp. 8–10 | A transformation includes construction, realization in the original environment, an outcome bridge and a falsifiable mechanism witness. A persuasive proposal is not an executed invention. |
| Permit complementary changes | p. 9 equation (12) | A representation and its compatible producer/checker may be jointly worthwhile even when each isolated edit loses. Preserve bounded unfinished alternatives and charge their costs. |
| Preserve purpose; allow authorized new comparisons | pp. 10, 12; §6.1 and §7.2 | A new authorized venture objective can replace inherited means. Preserve the earlier experiment and describe the new charter; do not retroactively improve its score. |
| Compare utility and structural attribution separately | pp. 10, 13–14; §6.2 and §8.2 | A commercial positive case can be studied against its relevant service/outcome alternative. A stronger claim that a particular formulation change caused the benefit needs a matched ablation and strong same-permission controls. |
| Count the whole lifecycle | p. 11 equations (13)–(14) | Include search, failed builds, construction, confirmation, migration, execution, verification and maintenance. Buying better evaluability may be useful; cheaper checking cannot be assumed. |
| Validate changes to measurement separately | pp. 11–12, 21–22 | A candidate cannot choose a lenient judge and self-approve. A newly validated instrument creates a new measurement epoch; rescore both alternatives and preserve old results. Model agreement and hashes are not calibration. |
| Fresh campaign is the unit for discovery-policy improvement | pp. 14–15; §8.4 and equation (16) | Many jobs in one venture simulation do not become independent demonstrations of learning to invent better businesses. Replicate complete discovery/selection/terminal-evaluation campaigns for that claim. |
| Compounding is conditional | p. 15; §9.3 | A useful asset may lower the cost of later discovery, but no exponential, monotone or universal transfer follows. Retain obsolescence, failure, overlap and the option to stop. |
| Retain the full witness | pp. 23–24; Appendix D | Record purpose, restriction, transformation, bridge, falsifier, comparator, confirmation and reuse/retirement conditions. Winner-only lineage is selection bias. |

The paper's seven operators concern representation, information acquisition, dependency structure,
production, task boundaries, coordination mechanisms and evaluation (p. 8, Table 3). Its most ambitious
example of a change is to remove the condition that makes a task recur. That matters economically:
a new service may sell a qualified reusable instrument, a changed outcome or maintained access rather
than assuming permanent revenue from work the invention eliminates. The buyer's authorized outcome
and total lifecycle expense remain the reference.

The exact finite example establishes an information ceiling only in its supplied two-hypothesis model:
passive observations yield 1/2 identification accuracy; at most twelve interventions yield 8191/8192.
An unrestricted ordinary optimal planner matches the active policy. The model family, action set and
candidate distinction were supplied by the investigator. Query accounting excludes unmeasured discovery
and construction costs. These results do not demonstrate frontier-model discovery, general invention
or commercial superiority (pp. 4–6 and 19–20).

## Existing assets inspected at exact source identities

Fourteen relevant current-Alpha documentation/source files were downloaded and their Git blob identities
verified. `source_inventory.json` records exact paths, URLs, byte lengths and SHA-256 values. Reading
scope was full manuscript and relevant documentation, plus public APIs and relevant source invariants;
no full runtime, model call, EVM or service deployment was executed for this inspection.

### Native transformational records and library

[`alpha_factory_v1/core/runtime/successor/transformation.py`](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/098117379f2920ebe37ab23dad77b7314a32518c/alpha_factory_v1/core/runtime/successor/transformation.py)
already defines `IntentCharter`, typed `Assumption`, `Formulation`, `TransformationWitness`,
`TransformationPackage`, `DiscoveryRequest`, `OperatorRegistry` and `DiscoveryLoop`. The witness
already contains purpose, restriction provenance, prerequisites, fallback, outcome bridge, falsifier,
comparators, frozen confirmation evidence, supported reuse, failures and retirement triggers.

**Compatibility limit:** the implemented native charter is a bounded fixed-summary pilot. Its artifact
literal is `fixed-summary`; its policy language is `source-clause-selector/v1`; its construction and
realization are exact source-clause operations; monetary allowances are zero. Do not silently widen
that domain or present it as a generic venture executor. Reuse its established interfaces where they
actually fit, or keep a new simulation's additional records explicitly outside that native authority.

[`transformation_library.py`](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/098117379f2920ebe37ab23dad77b7314a32518c/alpha_factory_v1/core/runtime/successor/transformation_library.py)
already retains versioned archives, current behavior digests, scope/prerequisites, failure conditions,
retirement, signed role-separated review/promotion and cost-aware routing. `ReuseCosts` uses declared
logical units, not money. `TransformationLibrary` binds to the existing signed transactional Journal
and TrustRegistry. Import or selection does not create execution, spending or publication permission.

These are better foundations for preserving lineage and review boundaries than another competing
authority or archive implementation. Their domain-specific policies are not new venture criteria.

### Actual capability construction and scoped reuse

[`examples/successor-capability/capability-package.mjs`](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/098117379f2920ebe37ab23dad77b7314a32518c/examples/successor-capability/capability-package.mjs)
exports `freezeCapability`, `importCapability`, `verificationCostCapability`,
`projectedFreezeCostCapability`, `prepareCapability`, `measureCapability` and `qualifyCapability`.
It freezes typed executable ASTs, model/catalogue/objective identities, scope, attempts, costs,
certificates, fixtures and compatible parent assets. It delegates semantics to the existing
`typed-runtime.mjs`, `constructor.mjs` and independent checker. A hash alone cannot make a tampered
program or erased attempt valid.

The apparatus and constructor are finite synthetic mechanisms, not arbitrary frontier-model skill
invention. Existing README comparisons preserve classical planner ties: 591/591, 439/439 and 1020/1020
abstract units in the three supplied apparatuses. The 20-unit failed common-reference sensing attempt
is a completed negative outcome, not a cheaper accepted alternative. These are reusable engineering
assets and boundary examples, not monetary calibration or proof that every construction repays.

[`examples/autonomous-enterprises/history.mjs`](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/098117379f2920ebe37ab23dad77b7314a32518c/examples/autonomous-enterprises/history.mjs)
already implements construction/invocation reservations, frozen future-task commitments, source/checker
identity, unresolved expenditure, complete treatment reservation and successor history. Its event
kinds are retained in the existing capability workspace. **Its settlement is explicitly
`SIMULATED_ONLY`, currency `none`, collected cash `0`, external submission `NOT_SUBMITTED`.** Its
finite-domain admission rule requires all retained future outcomes to qualify before its own successor
phase. That existing rule must not become an unexamined criterion for the new venture simulator.

### Existing venture portfolio planner

[`alpha_factory_v1/demos/alpha_agi_business_3_v1/enterprise.py`](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/098117379f2920ebe37ab23dad77b7314a32518c/alpha_factory_v1/demos/alpha_agi_business_3_v1/enterprise.py)
and the matching browser
[`docs/assets/business3/engine.mjs`](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/098117379f2920ebe37ab23dad77b7314a32518c/docs/assets/business3/engine.mjs)
already provide bounded scenario validation, `economics`, exact `solve`, and recomputing `verify`.
The Python module also emits source-linked dossiers, briefs, job specifications and immutable bundles.
It enumerates subsets of 1–16 supplied candidate ventures under capital, staff, review, dependency,
evidence, downside and separate job-token constraints, with a no-investment option. Its three-year
NPV uses integer/basis-point arithmetic and no terminal value.

This is an actual reusable allocation algorithm and reviewable packaging format. Its twelve built-in
ventures and their costs, evidence scores and cash flows are constructed assumptions. It is not a
customer-demand model, financial forecast, equity value or economic proof. It should not be copied as
new market calibration or used to turn supplied attractive cash flows into discovered opportunity.

### Earlier integrated enterprise result to preserve

The existing
[`studies/transformational-autonomous-enterprises-v1/COMPANION_README.md`](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/098117379f2920ebe37ab23dad77b7314a32518c/studies/transformational-autonomous-enterprises-v1/COMPANION_README.md)
reports a finite measured engineering result: scoped generic module qualification falls from 1,600
to 64 cases per trial, with fresh per-mission semantic checking. The supplied direct specialist has
the same accepted answers and a better final median time, 54.921 ms versus 59.867 ms. The 96% figure
describes repeated generic qualification cases, not full costs, dollars or human effort.

Its four-repository route and five-contract disposable local-EVM settlement are separate source
integration evidence. Mock-token flows are not revenue. The documented $100 → $10,000 commercial
target, external demand, firm offers, realized profit and complete historical development cost remain
unproven. Preserve those boundaries; they do not restrict what a newly authorized study may model.

## Neutral accounting and authority assets already pinned

The following exact files were inspected. Only the canonical shadow ledger, automated-cost schema
and graph authority/commitments are imported into the new study; fundingView is not reused. The old
prices, review policy, workloads and succession criterion are not imported:

| Asset | Exact source | SHA-256 | Reuse scope |
| --- | --- | --- | --- |
| Canonical shadow ledger | Alpha PR #4940 `daac40ee9e02a1b1bb100d7b9fcfa5caab04c297`, `studies/agi-alpha-second-investment-v1/market/upstream/canonical/shadow-ledger.mjs` | `cdc7c5a73593050a9af79b54589462e27f61b868e88ca6985d5cb639f3066d21` | Scenario versus observed revenue, complete cost/reserve events, incremental investment arithmetic. |
| Funding view | Same source, `market/upstream/deployment-robustness/funding.mjs` | `7c017e77f26ca7c755e8fb832ec4e7eddfe241c758b769931e72fadedbb3e083` | Inspected prior-study attribution semantics only; NOT imported into the new venture model. |
| Graph authority | Alpha PR #4942 `c9f2892c06e173cb0f9d5ae710cffc4a6f1fa723`, `authority.mjs` | `5229ee523cc6280debed2c55aff922d7d1192c848ade43676a9db86121294de1` | Distinct eligible-agent attestations, publication authority, scope, freshness and revocation. |
| Typed commitments | Same graph source, `commitments.mjs` | `454175c59be23ca5c8d86162403ca8a21a37b9ffddfceebd0f453b1730dd917e` | Byte commitments/inclusion and composition bindings, never economic value or execution permission. |

The exact accounting/graph files and detailed provenance remain in the earlier study's `upstream/`
directory and `research/foundations/`. Their source identities can be reused directly or vendored
unchanged into a separately named reproducible companion. The new scientific model should disclose
its own new parameters and charter rather than modifying the old frozen records.

## Suggested minimal reuse decision

Reuse canonical bookkeeping/investment arithmetic and the existing authority/commitment APIs. Do not
import the prior fundingView attribution semantics into the new venture model. Reuse
an actual constructor or portfolio solver only where the newly selected venture's semantics fit its
documented scope. Follow the manuscript's witness fields and retain exact upstream identities.
Keep simulated economics separate from the real-world runtime's permissions and known domain limits.
Do not deploy, sign, settle, publish a shared catalog, or represent a mock attestation as authenticated
live identity merely to make the simulation appear integrated.

No production implementation, authoritative graph, contract or settlement route was changed for this
readout. Earlier adverse findings and old study criteria remain unmodified.
