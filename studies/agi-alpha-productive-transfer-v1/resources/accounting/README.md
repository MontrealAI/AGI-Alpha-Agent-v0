## Release accounting view

The finalized additive snapshot is [final-snapshot/cost-summary.json](final-snapshot/cost-summary.json), with tested asset identities in [final-snapshot/asset-cost-register.json](final-snapshot/asset-cost-register.json). Cutoff: 2026-10-26T18:09:00.809308+00:00. It contains 64 unique recorded command events, including 8 nonzero exits. Earlier snapshots below retain their historical pending statuses. Complete costs, residual human time and shared allocation remain unknown; transfer/publication after the cutoff is explicitly unpriced.

# Complete cost scope, partial resource measurement

This additive snapshot inventories all known cost categories, preserved failures and unresolved charges.
It does **not** claim complete monetary measurement. Original account openings and execution receipts are unchanged.

`resource-ledger.jsonl` records unique metered command events in physical units. `cost-summary.json` identifies
the phases, source receipt hashes, unknown money and remaining work. Command exit success is not scientific or
customer acceptance. Summed command wall time is activity, not elapsed study time or human labor. Recorded CPU
does not include unexposed model inference or all source-authoring activity.

`canonical-money-ledger.json` uses the unchanged existing shadow-ledger API. Actual study customer collections
are zero; complete cost, profit, obligations and available surplus remain unknown. CPU and wall measurements
are not forced into this monetary schema. The original canonical source hash is recorded in the projection.

`asset-cost-register.json` retains B's construction and the original unsuccessful conventional C as ancestry
of C2. Common discovery, integration, verification and complete-packager corrections form one shared cost pool.
Their unknown allocation must not be charged once per mission and again in each asset. Primary failed work
stays in the account. B/C2 final source identities and final fresh acceptance are explicitly pending.

`human-break-even.json` gives formulas using official BLS wage anchors and an explicit 2,080-hour conversion.
No human duration is invented. A dollar of full AGI cost cannot be called a wage saving until an equivalent
accepted human duration/cost comparison is established.

To append a later snapshot after final execution, billing and publication receipts exist:

```bash
python study/resources/accounting/build-accounting.py --output study/resources/accounting/final-snapshot
```

The builder reads resource receipts and construction-account metadata only. It does not read fresh source
task inputs, hidden oracles or extraction answers. The current snapshot excludes later receipts by design;
its source identity list makes that cutoff explicit. Finalize the source bindings and shared allocations,
or retain unknowns. Do not relabel the prospective market cost envelopes as measured costs.
