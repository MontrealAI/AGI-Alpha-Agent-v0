# Independent internal accounting review

This review was performed by a separate same-session research agent with access to the shared workspace. It is an implementation and assumption review, not external peer review, market validation, an audit opinion, or a new empirical quality estimate.

## Executed checks

Run `python economics/review/audit_accounting.py` from the study directory. `accounting_audit.json` binds the reviewed runner bytes and records eight cases. Four cases use hand-calculated one-period ledgers: acceptance invoice and conditional deposit, each with full payment or default. Additional counterfactuals check that refundable customer principal cannot finance an otherwise unfunded attempt, increasing price cannot increase participation in a cash-unconstrained single period, common failure refunds every deposit while preserving expenses, and zero demand causes losses and shutdown.

All eight cases pass on the corrected reviewed source. The price-participation check covers250 supplied worlds; this is a software invariant check, not250 buyer observations.

An earlier observed reporting error is retained in `observation_history.json`: conditional-deposit minimum cash was recorded after releasing earned deposits. In the two-attempt test this reported CAD805.35 rather than the preacceptance unrestricted cash of CAD680.35. The corrected runner observes the low before deposit release and now reports CAD680.35. The selected acceptance-invoice policy's profit is unaffected by that deposit-comparator reporting correction. A separate initial float-allocation failure was handled by the root study author and is outside this review's first executed source.

The initial analytical threshold used a slightly conservative warranty/fixed-fee expectation. The corrected selected-arrangement formula gives central expected contribution CAD669.518299 per attempt and an approximate20.217521 attempts to cover the stated annual overhead, all invitations and launch. This is a conditional arithmetic check, not a demand forecast or liquidity proof.

## Accounting assessment

The reviewed model separates booked service revenue, net collections, bad debt, cash, opening financing, costs and planning reserves. Its gross customer-deposit records and failed-job refunds reconcile with earned deposits; no refundable principal is treated as service revenue. Delivery failures incur their expenses. Acquisition is charged for every modeled qualified invitation, including prospects who decline. Fixed business costs and launch are included. Incremental assessment, extraction/sharing/maintenance and optional Gym remain distinct from originating delivery. Closing profit reconciles with cash less opening financing under the model's explicit runoff assumptions.

`complete_cost_per_accepted` includes A costs and noncollection losses but excludes optional B/C. It is a baseline commercial denominator, not the entire research program's actual expenditure. `customer_savings` is the matched-deliverable price difference per accepted package. It is not complete buyer welfare: quality, delay, adoption and outside options appear separately in buyer utility.

## Material modeling conditions

- Qualified invitations, buyer values, budgets, conversion behavior and the existence of distinct repeatable jobs are assumptions. The central288 invitations/year are not observed prospects, messages, contracts or orders. Published parks/facilities data establishes technical material, not paid demand. The commercial result is conditional on a sufficiently broad recurring workload with equivalent scope.
- The human-service comparator is an employee-wage-based estimate with assumed8/16/32 hours, one composite overhead factor and a separate service margin. It is not a consultancy quote. Competent incumbent4h/8h stresses matter; repeat jobs should not indefinitely use a greenfield effort reference.
- Mission quality is assumed rather than calibrated by the local deterministic checks. The model equates drawn successful completion with acceptance. Latent defects incur a bounded repair cost and are assumed repairable; uncorrectable false acceptance and unlimited liability are not represented. Stronger warranty-cost and lower-quality/trust sensitivities should accompany the result.
- All invoices settle or default within one runoff month; warranty/support expenses are charged within the modeled job; there are no unsettled obligations after runoff. `runoff_months=1` describes this fixed implementation, not an arbitrary-duration receivable engine.
- The STOP policy cancels future overhead immediately with no termination fee or unavoidable subscription/lease commitment. The zero-demand test consequently loses CAD4,700 and closes with CAD300 after seven overhead payments. This is an assumed cancelable business structure.
- Spending is bounded before using deposits. The planning reserve is a buffer, not an expense or a claim to cover every possible tail event. Closing growth funds set aside opening financing, the assessment cost and that reserve; they are not realized distributable proceeds.
- The tested price is best only in the declared policy family and supplied market. In human-reference sensitivity, the human outside-option reference and offered price change while buyer values and budgets remain anchored to the central CAD market. A higher labor-based reference therefore cannot create higher buyer budgets or willingness to pay.
- Conventional GIS or an ordinary library may reproduce the technical output. That does not by itself eliminate a viable automated service margin, but it prevents attributing that margin to an exclusive retained capability. The separate E/U and retention panels remain assumed counterfactual effects unless measured later.

No remaining accounting defect was found in the reviewed cases. These tests do not establish that all inputs, every operating contingency or the proposed market are correct. The most useful next measurement is a matched human effort assessment plus metered E/E+ delivery on one new scoped source bundle, followed by a bounded market test only when separately authorized.
