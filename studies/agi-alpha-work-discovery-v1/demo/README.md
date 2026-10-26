# Offline English/French evidence companion

`index.html` is a single offline page: no backend, remote fonts, sign-in, transactions or deployment.
The English/French control, delivery tabs, comparison metric selector and finite-cash scenario selector operate locally.
Relative evidence links work when this directory is kept inside the study repository.

The completed page embeds the official production, transfer, discovery and economic results. The original
pending template and its freeze receipt are retained. `frozen-data-nonmarket.json` preserves the nonmarket
assembly; `frozen-data.json` adds every declared economic cell.

```sh
python demo/assemble_demo_data.py
python demo/build_demo.py demo/frozen-data.json
```

Run from the study directory. The renderer writes `demo/index.html` and retains `index.template.html` unchanged.
It embeds the supplied JSON and escapes `<` before insertion into the script block.

## Evidence object

Text fields may be plain strings or `{ "en": "English", "fr": "Français" }`.
Numbers must be actual JSON numbers. Use `null` for unknown monetary or measurement quantities; the page renders
them as unknown. Do not substitute an allowance or compute-only price for full cost.

- Top level: `studyId`, `frozenAt`, `conclusion`, `conclusionScope`, `evidenceStatus`, `commercialStatus`,
  `authorityStatus`.
- `jobs`: each item has `tab`, `title`, `verdict`, `outcome`, `buyer`, `trigger`, `action`, `scope`,
  `metrics` (`value`, `label`) and `links` (`label`, `href`).
- `comparison`: `scope`, `note`, and `arms`. Each arm has `label`, `cases`, `accepted`, `wallSeconds`,
  `cpuSeconds`, `fullCostUsd`. The scope must say whether times are sums, means or medians and which stages are included.
- `transfer`: `conclusion`, `observations` (`label`, `value`) and `links`. State whether recipients were
  already capable and whether reconstruction was charged once. Distinguish new capability from execution savings.
- `cash.scenarios`: each has `label`, `conclusion`, `assumptions`, `seedCapitalUsd`, `collectionsUsd`,
  `operatingSurplusUsd`, `closingCashUsd`, `reserveUsd`, `capabilityInvestmentUsd`, `availableFundsUsd`,
  `ledger`, `allSeedSummary`, `fixedLedgerSeed` and `links`.
- Ledger rows: `period`, `collectionsUsd`, `deliveryAndBusinessUsd`, `accruedOperatingCostUsd`, `investmentUsd`,
  `reservesAndObligationsUsd`, `cashUsd`, `availableUsd`. `deliveryAndBusinessUsd` is cumulative noninvestment
  costs paid, including historical discovery and ordinary setup at opening; it is distinct from accrued operating
  cost. Use the actual frozen finite-ledger accounting; the page does
  not recompute assumptions or silently invent a buying response.
- `sources`: evidence links (`label`, `href`). Accepted link prefixes are `../`, `./` and `https://`.

The finite-cash section always labels scenarios as modeled and disclaims actual receipts. Seed and internal
transfers are not counted as enterprise earnings. No token appreciation is included.

## Economic selection and conservation

All 24 cells appear in protocol order. Each uses seed 1, policy A for its weekly cash ledger and reports the
corresponding 16-seed summary. This is a fixed display selection, not a best-case selection. The assembler checks
that all 384 paired worlds have identical weekly rows under policies A/B/C/D; their investment gates never pass,
so all remain at the retained conventional capability A. The 1,536 histories are alternative enterprises, not
pooled profit or a shared capital account.

For all 1,248 displayed weekly rows, the assembler checks integer-cent cash conservation and the exact
operating-earned investment constraint before converting to dollars. An additional opening row shows historical
and ordinary setup expenditure. The chart distinguishes cash remaining from seed capital, the declared reserve,
and earned funds available for capability investment. `data-provenance.json` binds all economic inputs and the
assembled data by SHA-256. These data transformations do not rerun or modify the economic experiment.

## Qualification

The template's JavaScript passes `node --check`. The renderer passes Ruff and strict mypy.
Browser interaction and layout records belong in `evidence/`. Preserve failures before fixes.
The first browser launch failed because Playwright was installed without its Chromium distribution; that failure
is recorded in `evidence/browser-attempt-1.json`.

After data insertion, verify English/French text, every delivery tab, each metric, every scenario, desktop and mobile
overflow, evidence-link existence and console errors. The static chart is backed by its numeric table.

The original renderer freeze predates result insertion. Later renderer receipts record accessibility, cash-display
and mobile-layout changes separately from outcome data; no frozen experimental implementation is changed.
