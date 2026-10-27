# Conditional economics: accepted audit service before seed construction

This module models a proposed paid **audit report**, followed separately by optional capability investment
and hypothetical joint seed construction. It does not report a customer sale, plant delivery, validated
ecological outcome, actual model price, authenticated counterparty, or observed economic advantage.
All dollar inputs and scenario weights are assumptions. H uses estimated team hours and a stated rate,
not a market quotation. Complete actual research cost remains unknown; actual customer collections are zero.

`inputs.json` is frozen with `protocol.json` before the first model run. The source accepts external workflow
hours and a report-acceptance flag; the default flag is explicitly conditional. Equal workflow hours and
acceptance across U/E/E+ prevent assigning an empirical benefit to expertise or retention. E+ has additional
assessment/serving/development costs, so the default model can reject retention. A later measured input
file is a new prospective run, not a retrospective validation of these defaults.

## Accounting and decision boundary

* A includes all paid-job effort, including its listed learning subset, correction, failure support and
  receivable losses. The learning subset is descriptive and is never charged a second time.
* B contains additional capability assessment and serving. C contains optional development beyond the paid job.
* The modeled labor is paid cash labor. No extra opportunity cost is added for the same time.
* A deposit is cash and a refundable liability until accepted delivery. It is not earned revenue. The default
  reserve holds the whole refundable amount plus a stated operating reserve. Price or expected margin does
  not make an underfunded project liquid.
* Earned report fees, receivables, cash collections, refund liabilities, credit losses, costs, reserves and
  available funds are separate. Failed/partial/late delivery does not meet the full original report obligation.
* Payments defaulting after acceptance become an A credit loss, not a second cash outflow. Refunds discharge
  a deposit liability, not an extra expense. Financing is never revenue.
* Every scenario is a separate counterfactual campaign. Do **not** sum ledgers across mutually exclusive worlds
  or candidate prices as though they were additional customers. Expected figures use stated assumed weights.

The price policy enumerates three prices and two refundable deposits. A buyer can decline based on assumed
value, outside option and deposit tolerance. Investment stops for nonpositive complete contribution or a
reserve shortfall. Four configurations by six offers by eight worlds yield 192 service evaluations. Four
logical readiness cases by eight worlds add 32 construction stresses, for 224 total.

## Construction mechanism and prior art

The four construction cases toggle externally sufficient technical evidence and conditional pooled
participation. They are **logical prerequisite cases**, not randomized interventions or evidence of causal
discovery. A competent conventional expert receives the same evidence, prices, contract methods and rights;
its result must equal the combined case. The actual case has neither sufficient evidence nor confirmed
participants and stays blocked. The evidence-sufficient case is a counterfactual assumption, not a fabricated
seed-lot certificate. Construction is not authorized by the simulated calculation.

Conventional forward procurement and seed-lot requirements already exist:

* NASEM (2023), [Seed Suppliers](https://www.nationalacademies.org/read/26618/chapter/9).
* FHWA, [Roadside Revegetation, Chapter 5](https://www.environment.fhwa.dot.gov/env_topics/ecosystems/roadside_revegetation/ch05.aspx).
* BLM, [Native Seed and Plant Material Development](https://www.blm.gov/programs/natural-resources/native-plant-communities/native-seed-and-plant-material-development).

## Reproduce

Run from this directory with Python 3.11–3.13 (standard library only):

```sh
python economics.py --inputs inputs.json --output results
python -m unittest discover -s . -p 'test_economics.py'
```

`report.json` contains selected offers, costs, expected contribution, required prefunding, stop decisions,
mechanism cases and explicit observation labels. `transactions.csv` contains the selected service offers'
scenario ledgers. `cash_curve.csv` gives the nominal E offer's cash, liabilities and available funds over time.
`configuration_comparison.csv` is intended for the paper. Technical acceptance is conditional and independent
beneficiary acceptance, willingness to pay, model calls, operating time and demand must be measured before a
live-service claim. No token value or ecological benefit enters the cash ledger.
