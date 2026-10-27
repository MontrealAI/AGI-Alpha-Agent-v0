# Joint arrangement and cash-feasibility checker

This is a small exact instrument for the selected **S3 scientific-model reuse qualification** opportunity. It
checks a proposed package of shared construction, mission adaptation, counterparties, acceptance, rights,
withdrawal and dated payment. It does not establish that the new scientific instrument reduces costs, improves
quality, creates paying demand, or makes a real business feasible.

**Observed status:** no buyer commitments or customer receipts; complete instrument and mission costs are
unknown. **Default technical advantage:** zero assumed adaptation saving and zero quality uplift. An independently
useful common milestone is disabled unless its usefulness is explicitly supplied. Numerical diagnostic prices,
values and costs below are arbitrary test conditions, not estimates of this opportunity's market.

## What the checker keeps separate

A plan declares the common instrument, participant subset, a uniform mission price and one of three payment
arrangements. Required construction and mission work are charged in A exactly once. Extra retention/distribution
belongs in B; optional additional exploration belongs in C. Historical unpaid research is neither fictional
contract revenue nor a measured zero expense.

For each named outcome, the checker records complete costs, recognized acceptance, actual modeled collections,
defaulted invoices, earned refunds, buyer payments, participant net value and every dated cash event. Successful
contribution, scenario-weighted expected contribution, worst-case contribution, required opening cash, protected
reserve and available funds are different fields. The scenario weights are supplied stress weights, not estimated
technical-success or customer-payment probabilities.

Every participant must receive an expected net value at least as large as its supplied outside-option surplus.
The plan must also have positive expected provider contribution, authorized rights under its hypothetical terms,
and sufficient opening cash at every prefix of every declared scenario. HOLD is available. A positive expected
contribution alone never passes the funding gate. These conditions are conditional on the inputs; every result
retains `NOT_ESTABLISHED_UNMEASURED_COSTS_VALUES_AND_COMMITMENTS` as its actual-business status.

## Three payment arrangements

| Arrangement | Cash treatment | What can fund later work? |
| --- | --- | --- |
| Post-acceptance payment | An accepted invoice is distinct from its later collection; defaulted invoices provide no cash. | Collected accepted payments, subject to reserves. |
| Refundable escrow | Deposits increase cash and an equal refund liability. They do not increase available funds or revenue. | Only releases after acceptance. |
| Accepted common milestone plus remaining escrow | A separately useful common component is explicitly accepted; its share is released according to the stated date. Remaining deposits stay refundable. | The actually released, earned milestone amount. Independent usefulness and permitted use of the funds remain hypotheses requiring validation. |

Common technical failure returns unearned principal. Withdrawal after construction preserves the already incurred
common cost. Partial acceptance can earn only the independently useful accepted portions. Failure, later refunds
and support expenses remain charged. A funded escrow protects against the later post-acceptance default modeled
here; initial failure to fund escrow is outside that conditional funded contract and must prevent work starting.
No borrowing, token issuance, token-price assumption, or financing entitlement is inserted.

Let `C(t)` be cumulative cash inflows less cash expenses before opening capital, `E(t)` refundable escrow liability,
`S(t)` support reserve and `R` protected reserve. The necessary opening capital for a declared scenario is:

\[
L_{\min}=\max_t\{0, E(t)+S(t)+R-C(t)\}.
\]

The package requires the maximum of this amount over its stated scenarios. Cash available at a date is opening
capital plus `C(t)`, less `E(t)+S(t)+R`. Escrow cannot erase an unfunded prefix because its deposit increases
`C(t)` and `E(t)` equally. Accepted revenue is also not automatically freely spendable: support and protected
reserves remain unavailable.

For supplied outcome weights `w_s`, contribution is calculated exactly as:

\[
\Pi_s=\text{net collected earned payments}_s-A_s-B_s-C_s,
\qquad \mathbb E_w[\Pi]=\sum_s w_s\Pi_s.
\]

No external investment or principal deposit appears as earned contribution. Expected participant surplus above
outside option is the weighted value of genuinely delivered outcomes minus actual payment, less the supplied
outside surplus. Values of unresolved scientific claims are not automatically credited as validated products.

## Factorial and conventional comparison

The restricted four-way comparison distinguishes technical construction and coordinated commitments:

- Neither: a conventional route and a singleton commitment.
- Technical construction only: a shared instrument under a singleton commitment.
- Coordinated demand only: multiple commitments fulfilled through conventional methods.
- Both: the coalition and the constructed common instrument.

These are restricted mechanism comparisons. The **unrestricted conventional entrepreneur has every one of the
same alternatives**, prices, permissions and payment schedules. It may tie or dominate any restricted cell.
The checker does not claim that conventional entrepreneurs cannot coordinate, share costs or use an instrument.

The declared grid contains three core costs, two explicit assumed savings levels, two common-milestone usefulness
hypotheses, four uniform prices and every nonempty subset of three hypothetical participants. It generates 60
configuration records and enumerates 4,320 candidate plans including repeated plans appearing in restricted menus.
It is a finite comparison, not a globally optimal contract, market equilibrium, or estimate of real opportunity
prevalence. The positive 50% saving sensitivity is an unmeasured counterfactual; it cannot substitute for the
zero-benefit default.

With no new independently valued component, the full-success construction break-even condition is that measured
adaptation savings exceed additional core, coordination, retention and exploration costs. An assumed reduction
cannot establish that condition. An independently useful new component may support additional buyer value, but
that usefulness and willingness to pay must be elicited rather than inferred from the technical artifact.
Changing payment dates with unchanged receipts does not change successful contribution; it can change opening
capital. If separately useful partial milestones change receipts after later failure, the expected contribution
changes because of the explicitly different accepted deliverable and terms, not because principal became profit.

## Executed diagnostic, not a market forecast

The zero-saving reference diagnostic selects **conventional delivery**, coordinated commitments from P2 and P3,
$300 per mission, and fully refundable escrow. It does not select construction of the new instrument. Its supplied
conditions give $193.50 weighted expected contribution, $300 successful contribution, a $40 worst named loss,
and $230 required opening cash including a $50 protected reserve. The declared opening cash is $500. These values
are test inputs and exact arithmetic; none is measured demand, a real quote, or actual profit.

The selected plan and source were frozen before 32 fresh synthetic combinations of shared failure, withdrawal,
partial acceptance, default, refund and payment delay. **Seventeen combinations lose money**; none exceeds the
supplied $500 opening-cash cap. All losses remain in the data. This stress sample does not estimate a market loss
probability or validate the supplied scenario weights.

Freeze SHA-256:

`75525a260208efefc339dbe98530a3f5b4b6d5619ac50716bdce97b07a4cc15f`

A separate, explicitly post-confirmation arithmetic illustration holds successful total receipts and costs fixed:

| Payment arrangement | Release delay | Required opening cash | Successful contribution |
| --- | ---: | ---: | ---: |
| After acceptance | 0 days | $470 | $200 |
| Fully refundable escrow | 0 days | $470 | $200 |
| Explicitly useful accepted common milestone | 0 days | $370 | $200 |
| Any of the above | 10 days | $840 | $200 |

The milestone illustration assumes the common deliverable is independently useful and accepted before later
adaptations. It is not evidence that S3 customers would accept such terms. Equal immediate-prefix requirements
for post-payment and refundable escrow expose why escrow principal cannot fund the construction. Late release
removes the timing advantage.

## Historical foundation is a regression, not a new opportunity

`results/historical_regressions.json` cites and hashes `docs/Invent_the_Economy.tex`. Its four-buyer reference uses
a common 80% qualification probability, $600,000 construction, $300,000 conditional adaptation and $1,200,000
success receipts. The checker reproduces **$120,000 expected contribution**, **$300,000 successful contribution**
and **$900,000 opening cash** when all adaptations precede receipts. It also reproduces the distinct successor
conditions: setup $300,000 gives expected $60,000 and requires $450,000; setup $150,000 gives expected $210,000
and requires $300,000. The assumed savings and historical prices are not copied into S3.

## Reuse and verification

```sh
python opportunity/arrangement/test_checker.py
python opportunity/arrangement/audit.py
python opportunity/arrangement/evaluate_package.py \
  --input opportunity/arrangement/illustrative_request.json \
  --out /tmp/new-conditional-package.json
```

The reusable entry point accepts explicit `plan`, `inputs` and optional weighted `worlds`. It verifies the frozen
checker bytes and refuses to overwrite an evaluation. Users must supply the actual or explicitly hypothetical
costs, values, rights, dates and scope; missing real data cannot be repaired by selecting favorable defaults.

The ten tests cover escrow restrictions, useful-milestone prerequisites, cash timing, single charging of the
common core, A/B/C separation, default, withdrawal, partial failure, outside-option and rights gates, exact money,
and the separate historical cases. Ruff and strict mypy pass for the checker and independent auditor.
The auditor does not import the simulator: it reconstructs 38 complete fresh/historical ledgers, checks escrow
releases against prior acceptance, restores each cash prefix and verifies conventional same-menu dominance in
all 60 configuration records. Original papers, prior trial evidence and earlier economics are unchanged.

Before live use, the missing evidence is concrete: complete incremental construction/adaptation/support expense;
mission-specific scientific acceptance; buyer and outside-option interviews or quotations; explicit scope and
rights; actual payment and withdrawal terms; independent usefulness of any partial milestone; reserves and
funding authorization. This file grants none of those permissions or qualifications.
