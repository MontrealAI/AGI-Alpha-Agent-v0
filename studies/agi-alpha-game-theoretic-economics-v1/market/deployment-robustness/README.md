# Bounded deployment robustness and succession-availability extension

This user-authorized extension preserves all three earlier campaigns and uses the same frozen economic core. It evaluates the USD20 fixed-target policy in128 predeclared conditions using24 fresh stochastic seeds3001–3024. Initial adoption may use the same finite seed-inclusive cash; there is no capital replenishment. The experiment ends after3072 paired worlds (9216 enterprise histories), within120 seconds CPU/wall and the declared2026-10-26T18:10:33Z scientific cutoff. Partial output is retained if those budgets bind.

The newly disclosed funding-provenance view is implemented once in the pure browser-compatible `funding.mjs` module and reused by the runner and demonstration. It reads existing cash/cost records and changes no economic decision or ledger. An explicitly seed-paid opening historical R&D charge stays in full profit and cash but is excluded from prospective cost recovery. One reserve constrains liquidity. Outstanding unaccrued earmarks reduce both the cash and generated-resource bounds and are released when their bills accrue. The old stricter metric remains visible.

The actual bounded second-asset discovery ended NO-GO. Candidate=null, earmarks=0 and actual second investments=0 are frozen requirements. Its monetary cost D is unknown and is not in the original core bills. Consequently all reported funding values are labeled `BEFORE_UNPRICED_SECOND_ASSET_DISCOVERY`: ceilings, not all-in available funds. For attributed D>=0, remaining funds are at most max(0,G-D), and fixed-path profit is reduced by D. There is no default D=0 and no invented finite cost bound.

## Reproduction

Run from the market companion directory. Validation and synthetic controls execute no fresh market world:

```sh
node deployment-robustness/run.mjs --validate-only
node deployment-robustness/test-funding.mjs
```

The bounded wrapper used for the authorized original run is:

```sh
python deployment-robustness/execute-bounded.py --registration PUBLIC_FREEZE_COMMENT_URL
```

It invokes `node deployment-robustness/run.mjs --output deployment-robustness/results-01`, enforces a hard120-second child CPU limit and120-second wall timeout, and saves the exact registration and resource receipt. The registration argument is provenance metadata; root authorization and the public freeze precede the original invocation.

After the original completed archive exists, exact registered reproduction uses:

```sh
node deployment-robustness/run.mjs --replay-registered --output deployment-robustness/reproduction-01
```

That mode verifies the frozen source and original archive hash, permits only the same128 configurations and24 seeds, and requires every paired JSON record and final archive/summary digest to match the original exactly. It can run after the scientific cutoff because it creates zero new scenarios or independent evidence. It cannot change prices, seeds, conditions or model code, and it cannot overwrite the original output.

For original research, the outer command receipt enforces120-second wall and CPU limits; the runner also checks both limits between worlds and preserves any failure. Registered exact reproduction is identified separately and cannot be presented as another research campaign. No software installation, network, credentials or transactions are required.

The complete gzip archive includes the full enterprise histories, native competitor invoices/bills/cash events, original strict funding metrics, and the separately labeled resource-provenance view. Empty native competitor balance arrays are preserved honestly; full cash-event records support independent reconstruction. All simulated collected fields remain distinct from canonical observed collections, which are zero.

The extension's result is reported separately from the preserved primary and diagnostic results. Fresh-seed Monte Carlo intervals do not identify buyer value, true residual effort, total authoring cost or outside-market adoption. An affordable unqualified idea remains unqualified, and a positive balance is not evidence of a second capability or self-acceleration.
