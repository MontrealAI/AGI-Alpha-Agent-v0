# Economics adapter

This additive runner calls the existing Alpha `automated-costs.mjs` and `shadow-ledger.mjs` implementations in `discovery/canonical`. It does not substitute a new transaction system or claim that research accounting creates money. The CLI checks their SHA-256 identities before producing the results.

From the companion root:

```sh
node src/economics.mjs --metrics results/summary.json --metering metering --out results/economics
node --test tests/economics.test.mjs
```

The metrics file is consumed as a hashed evidence input. To prevent benchmark cases or repetitions becoming fictitious customer jobs, only an explicit `economic_input` mapping is interpreted. Alternatively pass an input file using `--input`. With no mapping, the runner produces conservative unknown-cost templates and does not infer accepted missions from arbitrary counters.

```json
{
  "schema": "value-compounds-economic-input/v1",
  "capability_id": "call-compatibility",
  "observed": {
    "collections_minor": 0,
    "missions": [
      {
        "mission_id": "fresh-substantive-source-change-1",
        "acceptance": "accepted",
        "reference": "Exact path and hash of independently validated useful dossier"
      }
    ],
    "resources": {"cpu_seconds": null, "requests": null},
    "limitations": ["Internal research workload; no paid customer demand established."]
  }
}
```

The example is an input contract, not observed evidence. Supply one row per genuine triggered mission, including rejected missions. Do not supply an accounting row for each assertion, test repeat, unchanged poll, or mutation negative control. The aggregate investment account is explicitly excluded from mission counts. All discovery and construction charges belong to that single capability account, rather than being charged again per reused mission.

Outputs are `economics.json`, canonical cost input/output, canonical shadow-ledger input/output, and `investment-grid.json`. Monetary projections use currency micros; shadow-ledger and investment calculations use cents. Unknown costs remain null. A hypothetical positive scenario never changes the observed zero collections, unknown capital/obligations, or economic HOLD.

The canonical cost API requires three scenario names. In the default output, `base`, `conservative`, and `stress` are all unknown templates; their names do not represent three fabricated forecasts. Its eight lifecycle-stage costs remain inclusive unknowns, plus unknown exception handling, attributable shared costs and the investment. A caller may supply a complete `canonical_cost_record`, accepted only for the same capability identifier; its forecasts remain conditional rather than bills.

The finite sensitivity grid uses 1, 4, 12, 52 and 250 **assumed future substantive missions**. No horizon is claimed to be paid demand or an amortization guarantee. With unknown costs, repayment is unknown. An optional sensitivity object can set `constructionCostMinor`, `failedConstructionCostMinor`, `maintenancePerReuseMinor` and `expectedSavingPerReuseMinor`, but all numeric inputs require `basis: "assumed"`. The canonical investment function charges failed attempts and maintenance. The same result can be checked independently as `N*(saving-maintenance)-construction-failed`.

Optional `human_thresholds` contain `kind` (`provider_cost` or `customer_price`), `currency` (`USD` or `CAD`), `amountMinor`, and a reference. Customer-price thresholds require the explicit `equal_customer_effort_assumption: true`; otherwise customer effort remains unknown. These are user-input what-if calculations, not invented prices, receipts, human task durations or attention savings. See `discovery/economics.md` and `discovery/sources.json` for current wage evidence and population limitations.

Metering records retain source file, line, hash and event contents without monetizing elapsed assistant time. The runner cannot recover unavailable inference billing, unobserved operator effort or future maintenance; it reports those missing quantities rather than interpreting them as zero.
