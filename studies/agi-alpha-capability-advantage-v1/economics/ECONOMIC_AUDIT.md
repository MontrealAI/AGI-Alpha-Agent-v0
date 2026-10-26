# Capability Advantage: economic reuse audit

Read-only audit of the frozen strategic market and second-investment companion. No fresh production or market outcomes were run. Exact inspected source identities are in `source-audit.json`. This is a study-design note, not a financial result.

## Preserved starting evidence

The previous study's registered 1,920 paired worlds comprise 5,760 enterprise histories. Each treatment finances 114 research attempts, but zero second investments qualify, zero repay the second cost directly, and zero pass the complete financial gate. All 78 priced group means are negative. Among 1,872 priced worlds, 1,870 project-inclusive treatment differences are negative and two positive; 48 actual-cost worlds remain unidentified. Neither individual positive path nor available cash established a worthwhile second capability.

All three full-lock production comparators accepted six of six tasks. The retained implementation averaged 1.339685 seconds, versus 1.135234 seconds for the incumbent and 1.175498 seconds for the conventional builder. The model credits no unmeasured human/customer saving. At the explicit, hypothetical USD1/core-hour tariff, B's measured -0.2436346257 CPU-second difference is a slowdown, not an economic benefit.

The previous favorable first-asset diagnostic remains conditional: mean prospective B profit USD183.28, paired B-A USD184.97, full-history B profit -USD178.24 after a USD361.52 historical allocation. The later fresh reference gave USD151.70 prospective profit, USD173.67 paired gain, and -USD209.82 full-history profit. These results did not establish actual receipts, recovered research cost, or financeable second investment. The second study's inherited reference yields mean incumbent full-history profit -USD149.73125 and prospective profit USD211.78875; these are distinct cohorts, so their numbers should not be mixed.

## Reusable canonical interfaces

### `alpha-automated-costs/v1`

Source: `market/upstream/canonical/automated-costs.mjs`.

Exports `AUTOMATED_COST_SCHEMA`, `AUTOMATED_STAGES`, `inspectAutomatedCosts(raw)` and `evaluateAutomatedCosts(raw)`. The record requires USD/CAD/EUR, an offering identity and exactly three scenarios (`base`, `conservative`, `stress`). Every fact is `{value, basis, reference}`, with basis measured/sourced/estimated/unknown; unknown values must be null. Integer microcurrency quantities and exact rational intermediate calculation avoid premature rounding.

All eight workflow stages must be represented: preparation, planning, execution, verification, correction, packaging, reporting, recovery. Operations state request/attempt/accepted frequency; residual human exceptions carry frequency, minutes and tariff; shared monthly cost carries allocation; setup/development investment carries allocation and amortization. Distinct cost identities prevent duplicate shared inputs. Output separates next-request, marginal, recurring and fully loaded per-accepted costs and reports all unknown inputs.

For the new study, maintain a parallel *resource measurement index*, not a second financial accounting engine: instrument compute/elapsed time, reconstruction attempts, validation, adaptation, retries and failures, link evidence hashes, and pass priced scenarios through this unchanged interface. Unmetered authoring/inference/active attention must stay null in the observed-cost view. Elapsed agent wall time is not human labor time.

### `alpha-shadow-ledger/v1`

Source: `market/upstream/canonical/shadow-ledger.mjs`.

Exports `appendEvent`, `replayLedger`, `planMission`, `calculateInvestment`. Ledger is `{schema,currency,events}` and accepts at most 4,096 events. Every mission has one acceptance event. Cost categories delivery/business/capability/maintenance must all be present or the full cost remains unknown. Revenue `collected` may be observed (or unknown); `price` is assumed. Reserves and obligations are separate events. Capability events mark invoked/admitted/rejected/retired but create no execution authority.

`planMission` takes missionId, reference, currency, acceptance, totalCollectedCents, priceAssumptionCents, totalOperatingCostCents, operatingCostsComplete, capabilityCostCents, reserveCents, obligationCents, costBasis, reinvestmentBps and optional human comparison inputs. The latter are conditional arithmetic, not measured customer value. No simulation should populate `collected` with simulated receipts: use `totalCollectedCents:0`, and put modeled collections/receivables in `priceAssumptionCents`, with `costBasis:'assumed'` and an explicit SIMULATED reference.

`calculateInvestment` requires constructionCostMinor, failedConstructionCostMinor, maintenancePerReuseMinor, expectedSavingPerReuseMinor, remainingReuses. It accepts signed savings. Its break-even formula is ceil((construction+failed)/(saving-maintenance)) when the denominator is positive; nonpositive denominator gives no finite break-even. Report finite useful lifetime and the entire charged validation/integration cost in the fixed and recurring terms.

### Strategic market choice and finite cash

Source: `market/upstream/src/market.mjs`, SHA256 `52b7d83b57de1ca1cf43e444cedb3639193c91b2d6816f3ba86f9463dd904f27`.

Reusable exports include `randomDraw(seed,...keys)`, `chooseBuyer(offers,buyer,config,u)`, `pruneDominated(offers)`, `validateConfig`, `simulate`, `pairedSimulation`. `chooseBuyer` compares quality-adjusted useful outcome value with posted price, buyer effort, delay, switching/integration, and expected error loss; allows defer and deterministic/logit response. Competent alternatives are independent DIY, human/conventional delivery, AI supplier and enterprise. This is a repeated procurement model, not a demonstrated equilibrium.

The existing core maintains finite seed cash, accrued costs, due bills, receivables, collections, refunds, insolvency, budgets, capacity, delayed quality feedback, churn, responsive/undercutting competitors and explicit paid imitation. All flows reconcile against canonical `planMission` projections. Cash = opening cash + signed realized cash events; economic profit = cash + collectible receivables - obligations - opening cash. Customer savings and internal transfers do not enter that identity.

Important limitation: original `ASSETS` are hard-bound to the dependency-packet production scripts, and the two-asset continuation changes only provider time, compute cost and customer review time. **Do not relabel this core's old jobs/assets as new demanding numerical work or claim network transfer merely by changing its title.** A new source-bound capability adapter is required for task-family eligibility, agents' retained state, compositions and acquisition. Retain its choice and ledger primitives byte-for-byte; do not invent a competing cost calculator or an unrelated accounting schema.

### Existing second-capability continuation

Source: `market/continuation.mjs` and its generated `continuation-core.mjs`; nine exact transformations preserve no-hook equivalence with the old core.

Exports `validateProfile`, `generatedResources`, `createSecondHooks`, `simulateContinuation`, `pairedContinuation`. Profile binds exact asset/acceptance SHA256, actual tested status, constructed-prototype status, adaptive or completed-research-replay policy, finite construction pause/useful life, integration failure, forecast discount, cap, explicit effects and eight one-off categories: priorDiscovery, discovery, rejectedCandidates, construction, verification, integration, researcherContribution, modelAndTools. Weekly maintenance is separate. Any unknown complete category prevents affirmative financing.

`generatedResources(firm,config)` is the reusable financing boundary:

`available = max(0, min(cash - unpaid_obligations - reserve, collected - all_accrued_costs + eligible_seed_paid_opening_R&D))`.

The R&D addback recognizes only exact identified opening bills paid before any collection from the original seed; it restores no cash and remains in full-history profit. A single reserve is deducted through the cash bound, avoiding double charging. Search/new construction/upkeep never receive the historical addback. No future receivable, customer saving, hypothetical token appreciation or new capital is spendable.

The adaptive gate forecasts reuse from only trailing eight-week accepted demand, discounts it, subtracts complete cost, upkeep and foregone production during construction, and checks affordability at decision time. Completed-research replay can fund an unqualified research attempt but must not call it a worthwhile investment. The unfinanced part of an already-built research prototype remains an external research contribution in project-inclusive profit; it never enters enterprise cash.

## Proposed preregistration for demanding-capability economics

Freeze production design before cases/outcomes. Freeze the market code, all parameter cells, calibration mapping and seed list before running market outcomes. Production data may calibrate accepted coverage and measured resources only. It cannot identify willingness to pay, actual model bill, human active effort, recurring demand or future reliability without separate observations.

Use four production arms with equal tasks, verifier and allowable public tools: A independent accumulated experience/reconstruction; B strong validated registry; C graph using the identical skills/evidence/dependencies; D strongest conventional implementation. Any homogeneous worker execution fixtures remain fixtures; actual independent constructors must be separately identified. Agent-count extrapolations are simulated populations, not actual agents.

Candidate primary design (requires root approval/final freeze): 52 weeks; 32 paired seeds 12001-12032; one reference and predeclared stresses for no demand, quarter recurrence, fourfold recurrence, high initial overlap, homogeneous agents, harder complementary tasks, short lifetime, acquisition failure, stale/incompatible skill, poor retrieval, tenfold cheaper reconstruction, immediate competitor copying, 20% integration friction, delayed collections, small/large network. Use actual observed family acceptance/cost mappings. Avoid a giant factorial whose favorable cells can be selected afterward. Report all cells and both deterministic and logit choice where feasible.

The *actual-cost* analysis retains nulls and cannot pass Level3/5. Separately predeclare complete low/reference/high cost **assumptions**, not empirical bounds, with each category and tariffs visible. Primary comparison reports cost thresholds and unknown-cost intervals rather than giving free construction to B/C. Shared construction and validation are charged once at network level; individual allocation is a distributional view, not another net expense. Skill already retained by an agent earns no acquisition benefit. Ordinary reconstruction may be selected and kept for later jobs. A successful reconstruction can erase scarcity permanently for that agent until new requirements appear.

Each buyer/recipient selects among validated acquisition, independent reconstruction, conventional service, own retained capability and abstention using full expected accepted-outcome costs. Skill creators compare contribution reward with incremental extraction, packaging, validation and opportunity cost. An internal access fee is recipient expense and creator receipt with zero consolidated enterprise revenue; external buyer receipts remain the only customer revenue. Free riding/copying reduces future access rents, and contributor withdrawal can reduce new validated supply. Token utility, if modeled, is an access/permission mechanism with explicit costs; zero issuance/appreciation revenue.

Per transfer: accepted-work difference, recipient best-alternative cost, acquisition/adaptation/verification cost, reconstruction avoided only when actually needed, finite break-even reuse, failure/staleness, net recipient value. Network: union of validated useful family/scoped coverage, completed high-difficulty jobs, accepted economic surplus and full costs. Do not infer growth from number of graph nodes.

Financeable succession requires one actual tested later-generation asset, complete incremental cost, decision-time operating-generated resources, future fresh accepted uses, and positive paired project-inclusive value net of its full costs. Reserve-preserving liquidity alone is insufficient. Level6 requires measured and difficulty-adjusted development/validation improvement over successive actual generations; it cannot follow from a shorter script, larger graph or modeled finance alone.

## Material limitations to preserve

- No actual customer receipt or transaction is established; actual observed collections remain zero.
- All-in authoring/inference, active labor and future maintenance costs were not measured in the predecessor. Scenarios are not invoices or cost bounds.
- Original ordinary baseline and prior copied assets remain available; failed constructions and negative results stay in historical accounting.
- The original finite market is not enough to substantiate multi-agent scarce capability. Its semantics must remain explicit if reused as a diagnostic.
- Within-model profit can be a valid outcome, but must be paired with the measured calibration, assumptions, downside, failure paths, sensitivity to copying/stronger tools and the actual-cost unidentified boundary.
