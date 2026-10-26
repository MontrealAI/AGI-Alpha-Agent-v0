# An evidence-constrained repeated procurement game

This companion is a behavioral agent-based simulation with strategic posted-price responses. It is **not a solved equilibrium**, has no Nash or convergence claim, and uses no real financial transaction. Its question is conditional: can adoption of the exact already-built component-decision producer improve a finite enterprise after complete assumed costs, against competent alternatives?

## Players, information and timing

Twelve heterogeneous maintained projects face at most one newly changed-input opportunity per simulated week over 52 weeks. Arrival and supported-scope frequencies are unidentified scenario parameters. These opportunities are not observed customer jobs and are never obtained by multiplying six original missions or 61 test assertions. Buyers differ in wage opportunity cost, task duration, consequence of error, and prior trust. They observe posted offers and their own past outcomes. No provider observes the future random draws or private buyer values. Providers observe past sales and public posted prices.

Each week: invoices reaching their due date collect or default; due bills are paid or remain insolvency obligations; common business and asset upkeep accrue; an investment policy evaluates current funds and past sales; enterprise and competitors post prices; buyers with fresh supported opportunities compare feasible offers in keyed random order; finite delivery and residual-attention capacities bind; accepted work creates invoices, failed work retains its costs; trust and switching decisions update. A drain interval after week 52 resolves contracted collections and refunds without creating new missions. Cost bills remain separate from their cash payments.

The enterprise can retain the ordinary workflow, adopt the already-existing qualified producer, preserve reserves, or stop on insolvency. Competitors can change price and, when specified, pay from their own finite cash for conventional automation. This response is an explicit market assumption, not a claim that we built the competitor's technology. No second AGI ALPHA asset is assumed. Its next-investment action is HOLD until a separate actually constructed/tested worthwhile capability exists.

## Procurement rule

Each buyer also has a finite annual procurement allocation, varied by type. Accepted invoices consume that allocation; work outside the remaining authorized budget is unavailable. This is a purchasing budget, not a claim of observed buyer finances. For simplicity, an allocation remains committed after default or refund: this conservatively limits further purchasing. Task effort is separately constrained by the one-opportunity-per-week process.

True simulated quality is unavailable to buyers at delivery. An explicit assumed post-delivery verification signal arrives after one week (a configurable delay); only then can beliefs and churn respond. Some defects are detected at initial acceptance, while others generate refunds after collection. Full eventual revelation is an information-model assumption, not measured buyer performance.

For buyer i and feasible provider j:

`U(i,j) = q(i,j) × V(i) − posted_price(j) − wage(i) × remaining_effort(i,j) − (1 − q(i,j)) × error_loss(i) − delay_cost(i,j) − switching_and_integration(i,j)`.

All components have USD-cent equivalents. `V` is a declared assumed usefulness multiple of the buyer's wage-equivalent task duration. It is neither revealed willingness to pay nor revenue. Buyer beliefs `q` are scenario priors updated only from that buyer's outcomes using bounded Beta-style counts. Production's internally verified finite component success rate is not treated as an unbiased field reliability estimate.

Before selection, an offer weakly worse on quality, price, effort, delay and switching cost, and strictly worse on at least one, is removed. Deterministic selection takes the highest strictly positive utility. The alternate logit rule applies only to the positive-surplus, nondominated set plus defer (utility zero); random taste cannot make a strictly dominated offer win. Capacity, unfinanceable work and buyer-specific temporary exclusions remove unavailable offers before choice.

Alternatives are: competent human provider, zero-license-cost conventional DIY with real assumed buyer effort, competing AI service with subscription/work-allocation costs represented explicitly as a task price assumption, and defer. Posted subscription prices externally anchor alternatives but are not equivalent-deliverable quotations. Free tools are not assumed to have zero operator cost.

## Production connection and comparison

- A retains legitimate ordinary helpers and performs ordinary finalization. Its extra active minutes are unknown and swept including zero; six researcher actions are not converted into minutes by measurement.
- B may adopt `src/package_component.py`, SHA256 `0b4eb1ae2392176ff61ef91b7da0d13df3c6400ee0b3e317439238881adc182d`.
- C may adopt `src/conventional_package.py`, SHA256 `cd28579ecf72eba5bdfffa6b3b5483aaaa960322989d2a2369da5431062207ba`.

Both exact producers delivered 6/6 scoped historical assessments in the pre-existing frozen campaign. They receive identical modeled costs, quality, customer effort and capacity effects. B/C use the same semantic random draws and must tie exactly; no scientific superiority is granted to B. Their source identities differ, not their economic treatment. A/B/C begin with equal money, information, constraints and customers. Success probabilities and degradation under load are adverse-condition assumptions applied without an investment quality bonus. The retained producer can remove only the explicitly assumed ordinary finalization minutes; remaining buyer review is unchanged.

The source-pinned mechanical runtime bounds executable scope. Those seconds are not customer labor, billable service duration or complete monetary cost. Compute/tool money, human construction and residual work, authoring/inference, discovery, failed candidates, integration and maintenance remain assumed or unknown. No finite all-in upper bound is claimed.

## Pricing and competition

Enterprise actions use a finite posted-price grid. Initially untried affordable price actions are explored; thereafter an empirical conversion posterior and bounded exploration score rank contribution opportunities using only prior observed prices and choices. This is a heuristic, not an optimum. Alternate fixed-price and cost-pass-through policies test sensitivity. Competitors follow either fixed, finite-floor undercut, or sales-responsive policies. Human markup can compress toward cost; AI cost can fall after a cash-funded automation adoption. Capacity is finite for every external provider; each buyer's own DIY option is inherently limited to its single opportunity.

## Cash, costs and investment

The market state contains explicitly typed **simulated** invoices, collections, defaults, bills, refunds and cash payments. Cash never becomes negative. A due bill that cannot be paid remains an obligation and marks insolvency; further delivery stops. An invoice exists only for accepted work. A quality defect discovered after initial acceptance can generate a refund after collection; rejected work produces no invoice. Gross invoices, gross collections, defaults and refunds remain separate.

Money is projected through the unchanged canonical `alpha-shadow-ledger/v1` API. The native `collected` category requires observed evidence, so all such values stay zero. Modeled realized collections enter only the canonical assumed-price/scenario projection with a SIMULATED wrapper. Economic and liquidity projections are distinct: economic costs include paid and accrued expenses once, while liquidity subtracts paid expenses plus still-unpaid obligations once. Refund adjustments are explicit costs, not hidden net revenue. Seed capital is never customer revenue or profit.

Investment requires (i) forecast incremental cost savings after upkeep exceed full assumed cost, and (ii) that full cost fit currently available cash after obligations and reserves. The main financing rule further caps funding by accumulated collected operating surplus, excluding seed resources and uncollected invoices. Forecast uses only trailing eight-week accepted enterprise sales, a declared conservative multiplier, productive weeks after the known adoption pause and anticipated price pass-through. Expected forgone incumbent contribution during that pause is deducted using prior invoices and declared collection/correction assumptions. No mandatory reinvestment fraction is used. This heuristic can fail, invest too late, or lose to the no-investment enterprise.

`full-history` charges historical discovery/construction/failed-work/validation/integration/authoring assumptions plus prospective adoption cost to the exact asset. `adoption-only` is a separately labeled prospective-operator analysis that charges installation/validation and upkeep while excluding sunk research; it cannot claim historical research repayment. Both builders may adopt the already-public method and do not have to reinvent it. The historical total remains unidentified: reported cost thresholds are conditional bounds on viability, not a measured cost bound.

At the final horizon the principal causal outcome is B−A net enterprise economic value under common exogenous draws; C−A and B−C answer separate questions. Direct avoided operating cost is recorded separately from causal profit because competitive price changes, allocation, capacity and timing can absorb the saving. A profitable service alone does not prove that its investment repaid.

## Reproducibility and limits

**Historical timing boundary.** The primary full-history calculation accrues the entire assumed historical research cost at opening. The separately declared `retrospective-cost-allocation` sensitivity instead allocates and pays that cost at the counterfactual adoption date; it cannot prove historical research affordability. It must fit the same seed cash or creates unpaid obligations and insolvency; later operating proceeds cannot retroactively fund it. Original source authorship is always historically external to the market simulation. Adoption takes at least one week and `ceil(adoptionHours / engineeringHoursPerWeek)`; enterprise service pauses during that interval and the asset cannot serve work before availability. This explicitly assumed engineering-capacity limit makes even cheap adoption costly in forgone delivery. Adoption-only cases exclude sunk research and never establish repayment of that history.

**Measured capacity boundary.** A single sequential mission resource budget is constrained by the largest observed arm mean across the inherited and four new joint-tuple campaigns: 16.7994402940 mechanical wall seconds and 2.5392089200 local CPU seconds. The existing probe has two workers inside that one mission. Weekly wall/CPU availability, service delay, human attention and throughput slots remain scenario assumptions; these limits are not production-scale qualification.

Every stochastic draw is a deterministic function of seed plus semantic keys (week, buyer, phenomenon, provider). The arm name is excluded. Random consumption order cannot change another event's draw. Independent seeds vary buyer characteristics, arrivals, supported scope, realized quality, collection and churn. Scenario confidence intervals describe simulation uncertainty conditional on parameters; they are not empirical confidence bounds on a real market.

Primary analysis freezes source, scenarios and seeds before execution. Limiting cases include no demand, rejected work, free perfect DIY, dominated offers, identical B/C effects, zero attention benefit, price competition, low cash, delayed collection, high maintenance and failed integration. Independent review checks accounting and causal pairing without treating test counts as production jobs.
