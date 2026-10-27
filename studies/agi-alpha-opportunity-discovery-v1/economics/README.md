# Conditional economics engine

This small engine prices no flagship by default. `scenario.template.json` leaves technical costs,
working capital, price, value caps, capacity and retention forecasts unresolved. No commercial advantage,
customer, sale, or market price is supplied by the implementation. The separate executed control packet
uses the **original Invent the Economy synthetic reference**, solely as a regression. It is not the
new edition's flagship or economic confirmation.

## Inputs and evidence

Supply measured technical work and its source identity separately from any assumed conversion to USD.
Buyer value caps, participation, payment likelihood, collection timing and business setup costs remain
explicit scenario assumptions until observed. The reference comparator should use equivalent human
service scope and a sourced rate where possible. A genuinely new offering needs willingness-to-pay
hypotheses. The engine imposes no percentage discount, reinvestment fraction or minimum training count.
Compare complete proposed quotes at the same resource envelope; the caller may enumerate a finite menu
of prices with separate buyer responses rather than manufacture a market price from production cost.

All money is integer USD cents; probabilities and bounds use exact rational arithmetic. A/B/C expenses
are disjoint by globally unique activity ID: A covers complete delivery, B additional retention/assessment/
sharing/upkeep, C optional work beyond the paid result. A common core needed for the current paid output
belongs to A; do not reclassify it as unpaid R&D or charge it again at retention. Each activity accrues once,
and later payable settlement does not create another expense. Opportunity costs are reported separately
and never deducted again from cash profit that already reflects displaced work.

## Cash and obligations

The event ledger distinguishes cash, capital, gross collections, earned collections, recognized milestone
revenue, receivables, defaults, refundable deposits, expenses accrued, expenses paid, payables, reserve and
available funds. Seed capital increases cash but not earned collections. A deposit stays a refund liability
until an accepted milestone applies it; it cannot fund construction in this conservative contract.
Accepted invoices are not collected cash. Defaults write off outstanding receivables without inventing
a second loss against collected-basis profit. Support obligations can be accrued on explicit supplier credit,
then paid later. Available funds subtract refund liabilities, unpaid costs and reserve. Every cash prefix is
retained. Negative availability under authorized credit is visible as a financing deficit, never profit.

Cash conservation is checked after every accepted event:

    cash = capital + gross collections - refunds - paid expenses

and earned collections reconcile gross collections less refunds and still-refundable customer funds.
Refund custody and nonnegative cash are enforced. Work also consumes a finite campaign capacity budget;
insufficient capacity leaves an incomplete/refused path. Counterparty acceptance here is an explicitly
simulated event, not an assertion about a real person or a grant of runtime authority.

## Mechanism experiment, not a frontier-model benchmark

`run_mechanisms.py` crosses shared technical construction with coordinated commitments. It preserves the
original reference's **restricted** single-binding-buyer comparator; it is a mechanism diagnostic, not the
unrestricted expert baseline. The unrestricted comparator can choose the same best package from all four
configurations. The script returns success, common technical failure, withdrawal, partial delivery failure,
default and payment-delay paths with identical initial beliefs and decisions; shocks are revealed only
in the realized event stream. No simulated sampling interval validates the assumptions.

For a natural flagship, justify any single-buyer restriction with its actual commercial setting or replace
that restriction with the appropriate contract comparison before freezing confirmation. Do not reuse this
reference merely to obtain a favorable factorial table. The beneficiaries, compatible core and arrangement
in these control fixtures are supplied by the investigator; selecting them is not autonomous discovery.

Private retention, network sharing and an ordinary library should receive the measured capabilities and
current permissions they actually possess. Their B costs must include extra packaging, qualification,
distribution, service invocation and requalification as applicable. Names cannot add performance.
Identical content, permissions and costs must produce identical accounting. The control packet checks
that invariance and charges sharing overhead without assigning it a free benefit; useful transfer is a
separate technical experiment. No graph-specific economic premium is demonstrated here.

`retention_decision` first checks whether the strongest declared per-use saving times forecast uses can
cover assessment and remaining lifecycle expense. An impossible hurdle rejects before new assessment.
A reachable hurdle returns `assess`, not admission. After a supplied fresh correctness result and lower
benefit estimate, it returns retain or reject; failed assessment remains charged. Returned charge amounts
describe the campaign total and must not be added twice if earlier assessment events are already recorded.
There is no mandatory learning or Gym action. A corrected policy must be frozen and tested on fresh paths;
this engine does not recover historical assessment expenses retroactively.

## Reproduce controls and run a new scenario

From this directory, use a new output destination:

```bash
python check_invariants.py --out results/new-controls
python run_mechanisms.py --scenario scenario.template.json --out results/unpriced-template.json
python economics.py --scenario populated-scenario.json --out results/new-ledger.json
```

The first command executes 24 conservation/adversarial controls and preserves all 24 reference paths.
The second returns four unresolved alternatives, not fabricated financial forecasts.
The third processes caller-supplied chronological events and stops at the first unsupported action while
retaining the valid prefix and refusal. Actual customer revenue remains zero and actual complete research
profit unknown in every research report.

The main remaining unknowns are actual prospective buyers, independently checked service scope,
willingness to pay, residual customer effort, realized API/tool/operator costs, authority/rights, capacity,
contract enforceability, support burden, renewal and collection behavior. Model confidence cannot fill them.
