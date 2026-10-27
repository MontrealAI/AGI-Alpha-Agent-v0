[Project notice](../DISCLAIMER_SNIPPET.md)

# Accepted work. Accountable cash.

Vincent Boucher — President of MONTREAL.AI

The existing Flywheel now connects an accepted delivery to customer receipts,
earned service income, procurement custody, refunds owed and refunds paid. It uses
the same signed A/B/C CostLedger, Journal, accounting role and durable checkpoint.
It adds no payment processor, settlement authority, execution permission or second
accounting store.

This is a dependent engineering increment on discovery #4975 `13e89bc1`, preserving
executor #4960, specialists #4961 and enterprise #4963. The existing v1.46.1
publication owner retains its release and publisher sequence. The new local
payment journey is part of the existing English/French `/flywheel/` flagship.

## Bounded opportunity selection

The concrete unmet internal need is to distinguish money received from money
earned without detaching acceptance, costs and outstanding obligations. The
restriction is the old flat collection attestation: it cannot express a refundable
deposit, procurement custody or a pending customer refund.

| Candidate | Inexpensive test | Decision |
| --- | --- | --- |
| Relabel flat collections in the UI | Can a label hold a liability or reverse income once? | Reject: presentation cannot enforce the missing transition. |
| Add a separate settlement service | Does another store preserve the single Journal and accounting boundary? | Reject: duplicate infrastructure and custody. |
| Extend the existing ledger with typed receipt transitions | Can an unchanged accepted mission bind earning while deposits/refunds reconcile atomically? | Select the bounded implementation and conformance campaign. |

The unchanged useful obligation is the complete accepted deliverable. Neither an
invoice, customer savings, a tool's successful return nor a deposited amount can
replace acceptance. The decisive tests are wrong-mission earning, duplicate payment
evidence, over-refund, interruption, outstanding-refund settlement and simulated
acceptance presented as live.

This is established payment/accounting structure applied to a missing runtime
boundary. Stripe documents [idempotent requests](https://docs.stripe.com/api/idempotent_requests),
[bounded partial refunds and retained processing fees](https://docs.stripe.com/refunds),
and [separate live/test cash balances](https://docs.stripe.com/api/cash_balance/object).
Those capabilities are prior art, not new Alpha. No Stripe account, API, webhook,
payment or customer message is used here.

The discovery budget is these three approaches and the existing source/interfaces;
stop after a coherent ledger extension and exact-source tests. A failed acceptance
binding, cash identity or mode-isolation check blocks qualification. Further
market discovery remains with the existing opportunity owners.

## Signed transitions

Use the existing `flywheel account` command and `flywheel-cost-command` domain.
Commands still bind journal identity, unique operation ID, action and exact record,
signed by the configured accounting role. Public JSON import installs no signer.

| Action | Record | Effect |
| --- | --- | --- |
| `customer-deposit` | `CustomerDeposit` | Record an attested receipt and a matching unearned-service or procurement obligation. |
| `customer-earn` | `CustomerEarning` | Recognize collected service funds against exact current delivery and acceptance identities; no second cash receipt. |
| `customer-refund-due` | `CustomerRefund` | Reserve the amount owed. An earned-income refund reduces net income immediately and creates its unpaid obligation. |
| `customer-refund` | `CustomerRefund` | Record an attested completed refund, settle any matching amount due and reduce cash once. |

Schemas live in `flywheel_customer.py`. Amounts are integer USD micro-units. Each
service mission has one immutable total price across its deposits. Gross lifetime
service deposits cannot exceed it; a later refund does not reopen the old price
ceiling. Procurement receipts have zero service price and can never be earned.

Native research uses the existing completed/approved-delivery checker. General
execution uses the existing protected acceptance service, including its actual
tool artifact, independent finite checker and acceptance signature. Earning binds
the executor's actual mission ID and exact execution/acceptance digests. General
live earning additionally requires an originally live execution. This adapter does
not qualify native research as live commercial delivery.

The current general acceptance adapter remains the existing finite placement
adapter. Other general mission families still require their separately qualified
acceptance adapters. New payment records do not broaden supported production scope.

## Cash identities and evidence modes

For each receipt:

`net cash = gross receipt − completed refunds`

`net cash = net earned service income + outstanding customer obligations`

The second identity includes procurement custody, unearned service funds and
earned-income refunds owed. Paying an already-recorded refund obligation decreases
cash and the obligation together; it does not subtract income or delivery cost a
second time. Partial settlement preserves the unpaid remainder. Unearned funds
already earmarked for refund cannot subsequently be earned.

| Mode | Own customer-funds panel | Operating cash/revenue/available funds |
| --- | --- | --- |
| `live` | Yes | Attested cash and liabilities; income only after qualified live acceptance. |
| `recorded` | Yes | Excluded; historical playback does not fund current execution. |
| `synthetic` | Yes | Excluded. |
| `calibrated` | Yes | Excluded; calibration does not make a payment real. |

A mission cannot switch modes by adding a second receipt. Mode labels remain
accounting attestations, not bank verification. Existing signer/custody and
production-execution requirements remain necessary.

Existing `collection`, `capital`, `offer`, `invoice`, `pending`, `payment`, charge
and seal commands retain their historical wires and semantics. Reports expose
`legacy_attested_collections` separately from `accepted_service_revenue`; old
collections are not silently reclassified as independently accepted income.
Inherited balances require their own evidence audit before a real financial claim.

Customer payment evidence cannot be credited again through legacy capital or
collection commands, another customer receipt/refund, or an already-recorded cost
payment. Durable event/operation records survive working-cache compaction. Every
state change, evidence allocation and checkpoint update commits atomically. The
bounded 256-receipt index refuses additional deposits before its capacity is
exhausted; existing obligations can still be reconciled. The extension records
attestations and does not send or retry a payment.

Unknown A/B/C costs still make available funds and complete profit unknown. Global
cash, obligations and reserves retain the existing report scope; the per-mode
customer panels respect an optional mission filter.

## Connected execution and economics

`record_customer_funds.py` executes the existing finite resilient-placement
regression through the real local mission executor and unchanged acceptance path.
It records seven stages: accepted artifact, synthetic deposit, accepted synthetic
income, refund owed, refund paid, procurement custody and custody returned.
The artifact, mission, acceptance and all ledger snapshots are inspectable.

The commercial scenario concerns that same solver/plan/verification package.
It compares USD1,000/2,000/3,000 against the inherited **assumed** human-service
estimate: 40 team hours at USD100/hour, total USD4,000. It is a service estimate,
not a salary survey or observed quote. Geography, date, scope, quality and an
assumed USD2,000–8,000 uncertainty range are explicit in the packet.

There are four hypothetical buyers, no repeated purchases, a 90-day horizon,
USD500 estimated complete cost per attempted package, USD600 campaign business
overhead, USD120 incremental retention assessment, assumed processing fees of
3% plus USD0.30 on gross collections, USD5,000 seed cash and USD250 reserve.
Originating learning, verification, recovery, corrections and residual human work
are inside A. Rejected retention assessment remains B. No extra Gym C is imposed.

The exact existing arrangement calculator accounts for common acceptance failure,
payment default, a 20% partial refund, withdrawal stress, paid versus incurred
costs and collection delay. Processing fees remain after refunds. Selection is
frozen before four adverse confirmations; it is the best of the tested prices
under these assumptions, not a global price optimum. Missing commitments and
rights keep every arrangement at HOLD, independently of positive modeled margin.

Customer savings, expected contribution, assumed seed cash and hypothetical
collections remain separate. Actual customer collections are zero. Complete actual
authoring, model and research costs and actual profit are unknown. Operational
Alpha E−U and retained Alpha E+−E are unmeasured; retention remains rejected pending
incremental evidence. The existing conventional/library ties remain unchanged.

## Reproduction and publication

```sh
PYTHONPATH=.:tests/runtime python scripts/record_customer_funds.py --output NEW.json
python -m pytest tests/runtime/test_flywheel_customer.py tests/test_customer_funds_economics.py --no-cov
python scripts/generate_alpha_flywheel.py
```

The recorder refuses existing outputs. Economic policies, finite input and semantic
balances replay reproducibly; ephemeral signer keys, journal identities and times
are newly generated. Published fixture inputs are not fresh future holdouts.

All current embedded evidence packets are **re-executed** against the changed
runtime, preserving their hybrid/fictional status. Their prior exact bytes remain
in parent Git history and historical evidence directories. Old qualification does
not qualify this increment. No paper or finding is replaced.

Exact-source review, parent reconciliation, main/release coverage, installed-package
qualification and public served-byte verification remain required through the
existing publication owner. A branch preview or draft is not a live deployment.
Rollback is an ordinary reviewed revert after preserving the private Journal and
outstanding obligations; old binaries cannot silently interpret new payment rows.

Official OpenAI model/tool/pricing pages were checked on 2026-10-27:
[Astra](https://developers.openai.com/api/docs/models/gpt-6-astra),
[Terra](https://developers.openai.com/api/docs/models/gpt-6.1-terra),
[pricing](https://developers.openai.com/api/docs/pricing),
[computer use](https://developers.openai.com/api/docs/guides/tools-computer-use).
The inherited adapters remain account/profile/budget qualified. No new API call,
subscription inference entitlement, model comparison or calibrated performance is
asserted by this receipt-focused increment.

## Français

Le même registre relie les fonds reçus, le service accepté, les montants conservés
pour achats et les remboursements dus ou payés. Une obligation de remboursement
réduit le revenu avant son règlement ; le paiement ne retranche pas ce montant
deux fois. Les fonds synthétiques, calibrés ou rejoués restent séparés des fonds
opérationnels. L’acceptation et l’autorité originale de chaque mission demeurent
nécessaires. Le scénario commercial utilise des hypothèses explicites ; les
encaissements clients réels sont nuls et le bénéfice réel complet reste inconnu.
