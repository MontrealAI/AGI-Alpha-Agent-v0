# Independent evaluation plan: cash, capacity and reinvestment

**Status: prospective method; no new financial scenario has been evaluated.**

This is a separate evaluation of a forward financial simulation. It does not
reconstruct historical invoices, change the frozen operational-cost amendment,
establish actual customer demand or revenue, or authorize a transaction. The
public freeze must cover this plan, the final protocol, all numerical inputs,
the prior-model anchor and the contract-source register before scenario
calculation. An explicit subsequent GO is required. Producer implementation
corrections after that point must preserve previous attempts and cannot change
the frozen assumptions silently.

## 1. Independence and identity

The evaluator will implement arithmetic from the frozen specification without
importing the producer's financial functions. Decimal arithmetic will be used
for cash and rates; contract waterfalls will use integer atomic units. The
evaluator may read the producer's result schema to align field names after its
independent equations are fixed. Producer code can subsequently be inspected to
locate a discrepancy, but an agreement obtained by copying that code is not an
independent check.

Every numerical report will identify the exact input, protocol, model, result
and evaluator hashes. The old operational result is an input anchor with a
declared evidence class: most of its costs and reliability values are already
modeled assumptions. Its native receipt remains the sole specified observed
task-time component; task-time model calls, historical authoring, full company
cost and cash receipts must retain their distinct meanings. The anchor's
partition into provider and customer accounts must sum back to the prior
audited components without duplication or omission.

Static schema and source consistency checks are allowed before the freeze;
calculating new cost, demand, investment or cash-path outputs is not.

## 2. Three accounts and their reconciliation

The audit separates (a) provider cash and obligations, (b) customer total cost
and residual attention, and (c) physical/time/resource capacity. An employer's
released labor capacity is not provider revenue. A supplier's fee is a
customer payment and provider receipt; it must not also be added as an
independent resource cost in a consolidated calculation. Paid provider labor
is a stated cash-cost assumption, not evidence of an actual payroll payment.

For each operating month, cash must reconcile exactly:

    closing cash = opening cash + cash collected + other authorized cash inflows
                   - refunds - collection charges - paid operating costs
                   - paid investment - actual tax or other payments.

Reserves are restrictions on remaining cash unless the protocol explicitly
models a remittance. A reserve must not be both deducted as a payment and
subtracted again from availability. Initial capital, returned collateral,
customer escrow, uncollected receivables and unrealized token appreciation
cannot become earned revenue or available reinvestment surplus. The final
month's unpaid invoices must remain separately visible; no terminal-value or
early-collection credit may be invented to make the horizon profitable.

The audit will independently reconcile billed accepted units, invoice face
value, collection fraction, refunds, processing percentage and per-invoice
charges. Percentages must use their specified bases. Receivables and expected
bad debt must reconcile with invoices and collections. Unaccepted or refused
work earns no accepted-delivery invoice unless a separate explicitly frozen
charge says otherwise. Failed work and repair costs remain in expenses.

Tax assumptions are modeling reserves, not jurisdiction-specific tax advice.
The protocol must define the income base, loss treatment, timing and whether
discretionary construction is deductible in that base. The audit will not
silently substitute another tax rule. Unquantified consequential loss is
unknown, not zero; high-consequence service remains outside supported claims.

## 3. Finite timing, allocation and investment state

The frozen protocol must specify the month order: outstanding collections,
service and resource admission, costs, invoicing, reserve calculation,
appropriation, candidate construction and delayed promotion. The evaluator
will reproduce that order explicitly and record each transition. Setup occurs
before the stated operating horizon; its cash and human-resource requirements
must still be accounted for, with its timing separately disclosed.

Available surplus must exclude all protected reserves, recovered-capital
requirements and unpaid obligations specified by the protocol. A cumulative
allocation ceiling is distinct from current available cash. Prior investment
spending and earmarks must be subtracted consistently so that the same surplus
cannot finance two projects. A chosen reinvestment fraction is a ceiling; it
does not compel spending or prove that a feasible project exists.

Every frozen candidate must have a durable state: not yet considered,
temporarily deferred, permanently rejected where specified, constructed and
awaiting evaluation, failed, or promoted. The simulation may not skip a failed
cost, promote before the declared delay, rerun a failed candidate for free, or
use a future outcome in the prospective investment gate. A deterministic
outcome world is an assumption, not an observed evaluation or estimated
probability. In the no-gain world, construction may consume resources but
must not reduce subsequent production costs.

Expected-payback gates must use the frozen forecast probability, remaining
feasible demand, cash contribution or savings base, construction cost and
upkeep. Actual outcome flags may determine promotion only after construction
and the evaluation delay. Provider hours already included in a candidate's
cash price must count once in money and once in the resource account, never
as a second labor charge. Construction and qualification consume resources
that could otherwise produce deliverables. Capacity purchases need a real
modeled bottleneck, remaining complementary resources and a stated payback
test; an extra executor cannot manufacture customer or provider minutes.

## 4. Capacity, demand and completeness

The evaluator will recompute each monthly constraint from the declared
utilization, working days, provider time, customer time, executor capacity,
model/token limits where included, demand and cash/reserve rules. Omitted
resource limits must be named as omitted, not treated as established unlimited
capacity. Fixed maintenance, candidate work, evaluation and capacity upkeep
must be charged at their specified times.

Demand admitted to the Agent, accepted work, failed/refused work, unserved
demand, backlog or lost demand, and any human fallback must remain separate.
The protocol must state whether unmet demand carries forward. Comparisons of
different admitted cohorts cannot be described as full-demand substitution.
When customer full-demand completion is reported, every unresolved or unserved
unit must receive its explicitly charged fallback or remain marked incomplete.
The fallback does not erase the Agent's already incurred failed-work costs.

Expected path consumption provides a planning calculation, not a hard
stochastic budget guarantee or demonstrated monthly schedule. The report must
retain tail-risk, reliability and scheduling limitations. An enforced STOP in
a simulation is not evidence of a deployed paid-call spending control.

## 5. Customer benchmark and economic claims

The prior traditional-work comparator remains competent human work with
ordinary non-AI tools and an unknown matched productive duration. Its declared
duration sensitivities are hypotheses, not newly observed worker times. The
separate supplied $200 human-cost and $0.50 Agent-cost proposition is a
hypothetical opportunity scenario, not a measured headline ratio or a sourced
occupational task estimate.

Customer cost comparisons must include price paid, customer preparation,
approval, checking, correction, fixed readiness where attributable and human
fallback. Provider economics must include delivery, fixed operations,
acquisition, administration, successful and failed construction, support,
maintenance, collections and reserves as specified. Provider cash margin,
customer modeled savings, resource-cost advantage, released employee time and
funds available for reinvestment are distinct outputs.

Finite-volume break-even price, reuse and investment results must identify
their denominator and horizon. The evaluator will independently substitute
reported roots into the relevant equation, cover zero/negative margins,
unequal slopes and absent finite thresholds, and distinguish a continuous
threshold from a smallest integer feasible request count. A threshold above
available demand, cash or resource capacity is not a practical payback result.

## 6. Contract routes: source arithmetic, not live settlement

Ordinary USD invoicing, Manager USDC, Ascension AGIALPHA and Jobs-v0 AGIALPHA
are separate routes. The evaluator will inspect the referenced source passages
and independently check the explicitly modeled waterfalls in atomic units.
The route parameters, numerical examples, roles, failure assumptions, currency
valuation and gas treatment must be frozen before example calculations.

Manager checks include validator allocation, 30/10 beneficiary shares,
remainder, duration-sensitive worker bond and separate collateral returns or
penalties. Neither wallet label establishes ownership by the modeled provider.
Ascension checks include nested rounding for the two reviewer payments, the
separate burn on each gross payment, buyer bounty remainder and bond stock.
Jobs-v0 checks distinguish quoted reward from reward-plus-fee escrow, the
worker's payout weight, its reserve-funded excess, worker burn and FeePool
burn. Source-defined failure distributions must not be replaced by an assumed
full customer refund. Failed Jobs-v0 economics remain NOT MODELED unless all
necessary branches and configuration are explicitly frozen.

Every supported example must conserve the relevant token quantities across
customer escrow, recipient payments, refunds, burns and separately identified
collateral or reserve transfers. Returned capital is not profit. Burned tokens
are not cash for model calls. The source does not establish current on-chain
state, actual authority, token liquidity, tokenholder profit rights or an
automatic 50% reinvestment policy. Source-inspected tests are not executed tests.

## 7. Audit coverage, corrections and publication gate

All frozen scenario, price, allocation and outcome-world combinations must be
retained, including zero investment, losses, refusals, infeasible starts,
declining gains and idle earmarks. Frozen sensitivity cases cannot be selected
after seeing favorable results. The evaluator will check all numerical rows,
component totals, monthly transitions, final summaries, CSV derivatives and
figure/browser bindings, using an explicit numerical tolerance for producer
floating-point outputs and exact checks for identities and integer tokens.

Any discrepancy will be recorded with inputs, expected and actual values,
location, materiality and resolution. An evaluator adapter error will not be
misreported as a producer error; both are preserved. A post-result diagnostic
must be labeled separately and may not silently change primary results.
Publication requires a hash-bound audit that states both arithmetic findings
and scientific limitations. Passing arithmetic does not validate the assumed
demand, prices, collection rates, capability gains or market performance.

No simulation establishes self-acceleration. Changes in methods, search
efficiency and transfer need separate observed evidence after complete costs;
more capital, agents, compute or accumulated artifacts cannot substitute for
that evidence.
