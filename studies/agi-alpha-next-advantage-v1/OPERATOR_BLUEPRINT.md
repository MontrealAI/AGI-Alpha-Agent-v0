# Operating blueprint: a bounded manufacturing-planning pilot

**Status: proposed pilot specification, not a qualified live service.** Numerical learning, schedule verification and local transfer were executed; customers, operating latency, frontier calls and money were modeled. **Sourced** means external documentation; **assumed** means an input to the published enterprise model; **proposed** means a new operating choice below that has not been tested. The [paper](paper/enterprise-next-advantage.pdf) and [reproduction guide](REPRODUCE.md) contain the supporting evidence and its limits.

## 1. Exactly what to offer first

| Term | Proposed initial contract and evidence boundary |
| --- | --- |
| Buyer and purpose | A manufacturing planner seeking a feasible assignment and sequence for one approved planning batch at one facility. |
| Numerical scope | 32–64 nonpreemptive jobs and three or four unrelated parallel machines, with machine eligibility, processing estimates, releases, due dates, positive priorities and family-dependent setup times. These dimensions and constraints were executed on synthetic cases. |
| Deliverable | Input snapshot; machine/job assignments and start/completion times; machine-readable schedule; independent constraint verdict; objective comparison against the agreed reference; readable schedule chart; assumptions and exception dossier. |
| Quality contract | Every job exactly once, eligible machine, no early release or overlap, correct processing/setup times, and at least 3% reduction in the stated normalized tardiness/makespan objective against the approved synthetic EDD reference. Fix the inputs, objective and verifier before execution. A customer's stronger incumbent is a different comparison requiring fresh qualification; do not substitute EDD without agreement. |
| Turnaround | **Proposed:** two business days after automated input validation and the buyer's approval of scope/reference. No measured customer turnaround or service-level guarantee exists yet. If clarification is needed, give the buyer one consolidated exception list and reset the agreed start only with their approval. |
| Customer effort | Supply one rights-cleared CSV/JSON batch plus machine/setup and objective specifications; approve the input snapshot and acceptance contract; answer unresolved data questions; inspect the returned dossier. Required customer hours remain unmeasured. Do not invent routine review minutes. |
| Initial capacity | **Proposed pilot cap:** one active batch, at most two nominal batches per week. Measure the complete workflow before raising this cap. The separate enterprise simulation assumes four capacity hours/day and 0.75 hours/nominal job; these are not observed staffing or throughput. |
| Failure and payment | **Proposed:** invoice only after the agreed deliverable passes; payment due seven calendar days after acceptance. One correction may be offered within one additional business day if feasible; otherwise report failure and collect no delivery fee. Record all unsuccessful work and refund/dispute costs. Scope changes require a new agreement, not easier scoring. |
| Operating limits | No plant actuation, ERP integration, rolling rescheduling, machine-breakdown calendars, multistage job-shop precedence, worker-qualification constraints, regulated engineering signoff or unrestricted factory optimization. Decline or separately qualify work requiring these. |

The adjacent **risk-aware package** adds a duration-risk report and selection under uncertain processing times. Its tested contract retains nominal feasibility and requires at least 5% improvement over the same EDD reference under 64 fresh disturbance scenarios using the stated mean/CVaR objective. **Proposed:** three business days, at most one such batch per week during qualification. The empirical disturbance history and buyer's required risk statements must be agreed. Beta can deliver this package; specialist-exclusive product creation is not established.

## 2. Price to test, with an explicit search domain

The human-service references are **C$3,220 nominal and C$7,217 robust**. They combine sourced AFG Québec hourly categories (C$154 and C$189) with researcher-estimated scopes of 16+4 and 26+17 hours. They are not matched customer quotations. See [primary sources](provenance/primary_sources.json).

**Proposed first test quotes: C$3,542 nominal and C$7,938.70 robust, before applicable taxes.** These are the 1.10-reference boundary selected by the frozen model's initial development-only pricing calculation, not validated market prices. At the explicitly assumed USD/CAD conversion of 0.73, they correspond to US$2,585.66 and US$5,795.25. The boundary result is a reason to test willingness to pay, not evidence of a global optimum or entitlement to charge a premium.

The full declared price/reference domain is **0.35, 0.50, 0.65, 0.80, 0.95 and 1.10**. For the nominal scope this is C$1,127 / 1,610 / 2,093 / 2,576 / 3,059 / 3,542. Keep scope and acceptance fixed when comparing quotes. Record acceptance, selection of human delivery, deferral and decline; a technical pass is not a purchase. A new price or scope can be tested prospectively, but preserve unsuccessful quotes and avoid asserting demand from a cheaper price alone.

## 3. Complete accounting before recognizing surplus

All amounts below are **assumed USD costs**, except the explicitly measured numerical timing. Actual invoices and work records must replace these allowances in a live pilot.

| Delivery component, bucket A | Nominal | Robust |
| --- | ---: | ---: |
| Frontier-model token envelope | $6.20 | $14.26 |
| Tools | $22.00 | $45.00 |
| Automated acceptance | $12.00 | $24.00 |
| General compute envelope | $2.25 | $4.80 |
| Direct delivery subtotal | **$42.45** | **$88.06** |
| Expected residual exception allowance | $14.25 | $14.25 |

The subtotal is not a complete job cost. Also charge A for $38 per qualified lead, $38/day common operations, the one-time $2,400 automation setup, failed deliveries, corrections and any residual work. The residual allowance models a 0.10 event probability × 1.5 hours × $95/hour; it is not mandatory human review. The model charges correction at 45% of direct delivery cost and $18 administration on unrecovered failure, with an assumed 0.22 recovery probability. Collect no revenue for a failed outcome. Assign actual taxes, credit losses, insurance, liability and customer-specific integration costs before a live profit claim; those are not calibrated in this edition.

**B** contains additional retention/assessment ($120), sharing ($90), upkeep ($35 each 21 days while retained), and modeled recipient invocation ($3/use). **C** contains optional Gym ($420), composition ($180), new-offering development ($850), and capacity expansion ($1,400). Expansion's extra $16/day running cost belongs to A. New-offering assessment is a separate $150 B charge. Skipped actions cost zero only because they did not occur. Failed attempts are charged. The eight-job v1 formation is already within A and must not receive a second research bill.

The measured v2 search took 6.42 elapsed seconds. At the assumed $3/hour compute proxy its numerical floor is approximately **$0.00535**, excluding qualification and upkeep. The $10/$35/$120 complete-program alternatives and $420 Gym envelope are assumptions to audit, not observed costs. More ordinary search cost only about $0.00026–$0.00028/job under that proxy and must remain a competing option.

Maintain unique event IDs with one A/B/C assignment each. Report accepted-work receivables, collections, total expenses, accrued profit, cash profit, seed capital, obligations, reserves and available funds separately. The model starts with $8,000 capital and a $1,800 reserve; capital and token movements are not revenue. Native replay uses [the existing adapter](src/native_integration.py), as documented in `REPRODUCE.md`. Funding expansion requires collected cash exceeding initial capital plus reserve by the expansion cost; displacement affects selection, not a second cash expense.

## 4. Optional decision triggers

| Decision | Operational trigger |
| --- | --- |
| Deliver or decline | Valid inputs, feasible agreed contract, credible buyer acceptance, capacity and funding for the complete job. A useful Beta-only sale needs no training. |
| Retain | Rights-cleared executable candidate with a positive fresh advantage over the best affordable generic alternative. Count only additional assessment/retention in B. The experiment's eight-source-job gate preserves its lineage; it is not a prerequisite for recognizing production profit. |
| Train | Buyer-relevant remaining gap plus a bounded experiment whose anticipated incremental contribution exceeds complete additional cost and displaced work. Declare the artifact, feedback, update, budget and fresh evaluation first. Reject failed candidates. |
| Share or invoke | A recipient demonstrates useful transfer with compatible prerequisites and scoped authority. Include admission, failure/fallback, invocation and maintenance costs; a summary alone does not preserve the policy. |
| Combine or launch | The combination passes the unchanged buyer requirement and beats alternatives at complete cost; the buyer values the added deliverable. Otherwise use Beta, defer or abandon. |
| Retire or stop | Changed inputs, failed fresh checks, rights/authority revocation, an economical baseline upgrade, insufficient anticipated reuse, or expected avoidable operating loss. Preserve failure evidence and cash. |

For each optional program, compare anticipated eligible reuse times **incremental collected contribution after serving cost** against additional B/C and the value of displaced production. Avoid counting upkeep twice. The published controller uses a 50% margin above modeled investment cost, a 55-day evidence life and optional revalidation; these are assumed decision settings, not universal rules. At the 30% secondary contract, learned48 has negative contribution versus actual Beta144, so lowering its program cost cannot make that particular investment worthwhile. No optional campaign or fixed reinvestment fraction is required.

## 5. Gates before live qualification

1. Secure authorized customer inputs, the actual incumbent and a prespecified contract; validate demand through real quote decisions and a paid pilot.
2. Run and measure the complete competent generic workflow, then compare retained policies on fresh customer-relevant cases. Record provider calls, retries, bills, corrections and residual obligations; numerical solver speed is insufficient.
3. Resolve the current **protected-runtime scope blocker with its existing owner**. The pinned capsule schema permits bounded public-source selection and correctly refuses arbitrary scheduling admission. Local signed fixtures do not grant live ENS access. Do not create another registry or weaken ENS revocation, Jobs validators, governance or settlement boundaries.
4. Admit only rights-cleared, validated artifacts or authorized compatible components/services under the qualified extension, and expose eligible access to currently authorized `*.agent.agi.eth` members with separate execution permissions. Exclude customer secrets and protected evaluation material.
5. Reconcile actual collections and all obligations through the existing ledger before claiming profit or financing expansion. Publish through the repository's coordinated review/release process and verify the served artifact; this package is not itself live service qualification.

The primary demand–cost grid does not locate absolute enterprise break-even: all displayed mean profits are positive. The separate thin-demand stricter-contract sensitivity does show losses. Use both as directions for measurement, not as assurances that a pilot will sell or compound.
