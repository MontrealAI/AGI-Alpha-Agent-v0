# Pinned native accounting reuse

`automated-costs.mjs`, `shadow-ledger.mjs` and `LICENSE` are unchanged files from
MontrealAI/AGI-Alpha-Agent-v0 commit
`c4a7febc02fb9d607e9da5ece2101c4b6b36fc64` (PR #4915).
The two modules are self-contained: their source has no imports and they require
no third-party dependency or running Alpha service. Their Git blob identities,
SHA-256 digests and original paths are recorded in
`../../sources/foundation_manifest.json`.

`project_scenario.mjs` is the new research adapter. It accepts a bounded JSON
string containing supplied simulated mission records and calls the unchanged
native `replayLedger`. Modeled collections enter the native assumed-price field;
they cannot enter its observed receipt field. The result is wrapped in an
explicit simulation envelope. The native default of zero automatic reinvestment
is retained. The study's separate economic engine owns chronological cash and
optional allocation; this snapshot projection does not replace that engine.

Run the local arithmetic and rejection checks from the study directory:

```sh
node vendor/native-accounting/verify_projection.mjs evidence/native_accounting_check.json
```

The constructed fixtures exercise complete eight-stage costs, unknown propagation,
missing-stage and duplicate rejection, modeled-versus-observed revenue separation,
failed-work accounting and negative investment economics. They are not a
measurement of production, invention, receipts or enterprise profitability.

The recorded run uses Node v24.22.1. It does not satisfy the complete upstream
Node 22.17.1 release profile or its hosted/native acceptance gates. No live
service, ENS lookup, wallet, provider credential or transaction is involved.
