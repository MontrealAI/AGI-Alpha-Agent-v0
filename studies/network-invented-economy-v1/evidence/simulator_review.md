# Independent pre-confirmation simulator review

Review date: 2026-10-26. Scope: `src/simulator.py`, its direct use of the common
`src/alpha_assessment.py` gate, and meaningful regression checks in
`tests/test_simulator_review.py`. Initial findings were sent to the simulator owner for
repair without editing that code. The owner subsequently delegated the single
`alpha_assess` method to this reviewer for the matched-comparator repair; all other
simulator edits remained with its owner. Development outcomes and these repairs precede
the final protocol freeze. They must not be represented as successful confirmation of
the final economic hypotheses.

## Decision-relevant findings

The review found concrete errors capable of overstating retained-capability value or
available resources. The implemented repairs matter because a positive cash result is
insufficient evidence of an invention flywheel if failed transfer receives free benefits,
expired capabilities remain usable, or future obligations are available for reinvestment.

| Finding in the development implementation | Required behavior and repair | Independent check |
|---|---|---|
| A failed adaptation could remain selected, retain the falsifier validation discount, and disappear from reconstruction error accounting | Remove it from effective selection, reconstruct and charge recovery, restore ordinary validation, and count no successful transfer | Regression passes |
| A harmful adaptation could affect the first job but disappear on the next use without correction | Retain the harmful state or explicitly reject/correct it with corresponding costs | Regression passes |
| Selection checked current skill status at order time, without a fresh check at subsequent production | Recheck status, expiry, due revalidation and bundle/Beta eligibility before work advances | Revocation and due-revalidation regressions pass |
| Duplicate-control availability forced a recipient to use a more expensive retained artifact | Preserve optional selection; rationally decline a dominated reuse plan | Regression passes |
| Incurred unpaid obligations were omitted from available investment cash | Deduct unpaid obligations as well as reservations from free funds | Regression passes |
| Active production during runoff could escape normal infrastructure charges | Continue operating overhead while jobs or invention work remain active; separately charge collections/warranty winding down | Regression passes |
| Hidden true correctness immediately changed public trust and the generation of opportunities | Use observed delivery/validation for immediate updates, and discovered refunds/errors for subsequent updates; retain latent truth only for outcomes and latent artifact defects | Trust regression passes; candidate-generation path inspected |
| Bundled construction could use the maximum component latency while blocking only one owner | Charge aggregate construction resources and serial latency, reserve all participating producers, and charge the validator share | Code inspected after repair |
| A fixed bundle valuation bonus was present without a matching realized mechanism | Remove the bonus; model the joint contribution through explicit cost/quality/capacity consequences | Code inspected after repair |
| Revalidation perfectly detected latent invalidity | Add a declared revalidation false-negative parameter and continue reporting validation uncertainty | Code inspected after repair |
| Useful transfer counts could include unsuccessful transfers or merely selected artifacts | Distinguish exposure from actual use on useful recipient outcomes; remove failed adaptations from the transferred count | Transfer regression passes; outcome fields inspected |

The tests force only the conditions needed to isolate each accounting or lifecycle
invariant. For example, a test patches buyer choice to obtain a sale while testing failed
adaptation; that forced choice is not demand evidence and does not enter the published
economic estimates.

## Additional Beyond Beta gate finding

The first Alpha integration recorded the available capability set in a hash but computed
gain from aggregate ordinary reconstruction savings. Its 24 nominal paired gains were
random perturbations of that aggregate, rather than matched baseline/candidate mission
calculations. A same-owner, same-scope capability already available to the network could
therefore receive another positive Alpha assessment.

The regression `test_alpha_comparator_includes_already_available_equivalent_capability`
creates that exact redundant case. The requirement is that a comparator includes the
*usable consequences* of current capabilities, not only their identities. The recommended
repair is a deterministic recipient-by-depth matched probe: competent reconstruction or
the best current retained method in the baseline branch, versus the same resources plus
the proposed candidate/bundle in the candidate branch. Exclude only the exact capability
being reassessed for continuation. Then charge the declared incremental lifecycle costs
and uncertainty margin through the shared pure numeric gate.

At the review checkpoint with simulator SHA-256
`4ae6e4f3e1b4470a8a9be259614d3e944598d3eb5bd416c5dc9c8b79562f16d8`,
the eight earlier regressions passed and this ninth regression failed. That development
checkpoint is preserved here to avoid silently presenting the original gate as valid.

### Executed repair and regression result

The repaired method uses three task depths per modeled recipient, with explicit depth
probabilities and uniform recipient weights. Each probe chooses the cheapest competent
reconstruction or currently eligible retained method, then adds the proposed bundle as
an optional alternative. Existing known capability affects reconstruction effort and
whether imported material adds anything. An equivalent retained method therefore yields
no incremental advantage. Continuation excludes only the exact reassessed identities;
other currently available equivalents remain in the comparator.

Every probe records the two modeled delivery costs, the selected methods and the separate
incremental integration, failed-transfer recovery and risk costs. The gross difference
minus those incremental costs exactly equals the difference between the two delivery
costs. Weighted means flow through the common `evaluate_alpha` function. There are no
randomly generated pseudo-pairs and no latent technical-validity oracle. Remaining useful
lifetime constrains continuation, and distribution overhead is allocated to the whole
bundle rather than one component while excluding its reassessed copy from the denominator.

The completed independent regression suite passed **12 methods**. In addition to the
earlier eight and the redundancy test, it checks paired cost reconciliation, exact
continuation exclusion/remaining lifetime, and invariance to a hidden change in technical
validity. These are program invariants, not 12 successful economic or scientific trials.

At the successful repair checkpoint, the full simulator SHA-256 was
`e40c7f18542cd89eaa7350b2d49384ce9e5b3bcbff0fb33d42a65ca4d2424165`.
The exact `alpha_assess` source method, including its trailing newline, had SHA-256
`43f9af6a26ebd43688d12b7303a6828c7ba842e06f20848a2fb3340d8cecc0d5`.
Subsequent owner changes and the final frozen release may have different identities and
must retain their own test record; these hashes identify the reviewed development repair.

The direct probe intentionally excludes additional quality and queue-capacity upside.
It conservatively charges an unknown recipient's fresh-adaptation recovery expectation
on each modeled reuse; repeated failed attempts are not claimed as observed events.
Its residual risk term is an explicit proxy: harmful-transfer probability times correction
plus frontier revalidation cost. It does not establish actual expected customer damages
or price-refund exposure; those require a stronger task-matched calibration and are modeled
separately in the operating ledger. The 20% gross-benefit uncertainty margin is declared,
not a coverage guarantee. All probe values have `source_kind=simulation`.

## Causal estimands and interpretation boundaries

The simulator uses shared exogenous random keys, equal agent counts and resource quotas
across network and counterfactual arms. Those are useful controls. However, an adaptive
network-versus-isolated comparison also changes investment choices, selection, queues,
repeat demand, pricing feedback and expenses. Its estimand is the total effect of the
declared adaptive policy package under the modeled worlds. It is not a pure direct effect
of one transferred skill, and equal quotas do not mean equal realized compute expenditure.

The isolated investment forecast also divides future work by agent count while job
assignment can favor an owner who already holds an isolated capability. This is an explicit
forecast-policy approximation; it can understate an isolated owner's practical utilization.
Report this limitation, or add a fixed campaign/retained-asset schedule to isolate sharing
from differing investment foresight. A removed-capability arm with otherwise identical
resources supports a controlled causal question, but if later policy actions differ it
still includes those downstream policy responses. A frozen recipient-level paired probe
with the same resources and one capability removed is the direct mission-value estimand.

The task space in the economic simulator contains the same depth-one, depth-two and
depth-three offerings for competent Beta and the retained-capability network. Retention
can improve cost, reliability, capacity and feasible cash-funded delivery within that
space. It does not by itself prove an entirely new business category or a task impossible
for competent Beta. Any stronger claim of new scientific capability must come from the
separate executable witness and its bounded comparison, not the existence of another graph
node or an additive reconstruction discount.

The common Alpha gate is intentionally arithmetic rather than an intelligence oracle.
Strictly positive lower net advantage is required, but comparator competence, source
truthfulness, complete costs, recurrence/demand and the uncertainty margin remain declared
inputs that need independent evidence. The margin is not a statistical confidence interval
unless an external experiment actually supplies that interpretation.

## Remaining accounting and modeling qualifications

1. The detailed cash ledger separates collections, incurred expenses, paid expenses,
   reservations, unpaid obligations, refunds and receivables. Its cash identity and quota
   assertions are meaningful. Outstanding receivables are not spending cash or terminal
   profit. The reported `investment_cost` is a sum of committed campaign budgets, including
   reserved bounties that may be released after rejected constructions; realized expenses
   should be read from the expense categories rather than treating that field as cash spent.
2. `unique_invention_campaigns` counts distinct source jobs among retained admissions; it
   does not count every independent attempted campaign. Candidate events can include
   repeated proposals suppressed by a keyed store. Keep attempted, constructed, admitted,
   used and economically useful quantities distinct in results.
3. Role workload, reconstruction savings, failure dependence, demand, buyer preferences,
   trust, migration and lifetime remain scenario assumptions or task-matched calibration
   inputs. The Python program reasoning about them is not a frontier model actually solving
   the simulated customer missions. No benchmark score is an observed customer-acceptance
   probability merely because it has been entered into a scenario.
4. Price choice uses assumed population values and observed conversion rather than each
   buyer's hidden private willingness to pay. Urgency/deadline is available in intake and
   should be identified as observed. Subjective quality and error parameters are assumed
   beliefs, not facts magically learned by the simulated seller.
5. The graph software is separately tested with fixture identities, signed fixture
   attestations and public fixture keys. Economic records do not constitute real ENS
   authentication, production encryption, human validation, on-chain admission or a sale.
   A correct hash commits a claim; it does not establish its truth or net mission value.

## Reproduction

Run from the study package root:

```bash
python3 -m unittest discover -s tests -p 'test_simulator_review.py' -v
```

The regression suite is deliberately independent of whether central or favorable worlds
produce positive profit or whether an investment is made. Waiting, declining an uneconomic
candidate and retiring a skill after Beta improves can all be correct outcomes. The review
does not authorize a production deployment and makes no realized commercial-success claim.
