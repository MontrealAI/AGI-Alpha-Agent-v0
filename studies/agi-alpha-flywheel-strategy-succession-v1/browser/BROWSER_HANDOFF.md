# Browser companion handoff

## Completed and frozen

The useful first mission, finite six-mission controller, explicit construction diagnostic, local persistence,
STOP/reload/resume, separate checker, evidence downloads and generic comparison-table renderer are implemented.
The default experience is one offline HTML file: **`browser/index.html`**. Select **Plan this mission** to compute
an actual schedule. No account, installation, server, API key or wallet is required for that path.

Scientific source: `7e5a1dd2dcf7eb00ec055f1858d5dd722cc950f15f33314bb94c456c753845a7`.
Top-level freeze: `6d0308707f3909fd18d086a950d237835dafd9ab6cfa9a559846715f46613827`.
The root freeze includes browser application logic, bootstrap, checker, fixtures and QA source. No executable
source was changed after that freeze.

The final source-bound HTML before recorded-results embedding has SHA-256
`60013139060365e1f122e98c9f87acc6b47ab7eac69fd897b3548928f9c4282e` and size **444,665 bytes**.
Its browser execution digest is `67fa72590db37750936fce825c34e1d207aa61a831f1678ded24a768d43dc407`.
`BUNDLE_MANIFEST.json` contains the complete imported module identities and separate presentation hashes.

## Verified behavior

| Record | Result | Scope |
|---|---|---|
| `CHECKER_QA.json` | 18 assertions pass | Binding, task coverage, durations, dependencies, capacity, target miss, false bounds/optimality, locked-work repair and proof/authority refusal |
| `BROWSER_QA.json` | 11 checks pass | Fresh first plan, downloads, target miss, malformed dependency graph, supplied-authority refusal, keyboard navigation, desktop/mobile layout and no network calls |
| `STREAM_BROWSER_QA.json` | 8 checks pass | Exact configuration stability, STOP/reload/resume, accepted receipt preservation without duplicate execution, uninterrupted selective refusal and separate bounded diagnostic |
| `RENDERER_QA.json` | 5 checks pass | Generic comparison table, escaped text, mobile scrolling and no network; explicitly synthetic fixture removed afterwards |

All three browser reports bind the exact HTML identity above. All browser processes were closed before the
main timed confirmation campaign. The source was inspected against the prior browser lock manifest with no
intervening browser source changes.

The useful nine-task synthetic example finishes at hour **23** against a target of **28**. Its global optimality
is not established. Full output is recomputed on request and independently reimplemented feasibility checks run
in the browser; the checker shares project authorship and local custody.

The final UI QA execution of the uninterrupted selective stream completed six missions with **186,244 browser
work units** and zero newly retained assets: the dispatch investment was correctly refused as uneconomic under
its forecast, and child construction was deferred. The separate diagnostic completed six missions with
**777,965 browser work units** and three retained assets. The first two were explicitly correctness-only laboratory
retentions; the repair stage passed its local forecast gate. These are **demonstration/QA observations**, not the
confirmatory study. They do not establish net enterprise growth. Browser and Python counters must remain separate.

Raw browser runs are in `qa-resumed-stream.json`, `qa-uninterrupted-stream.json` and `qa-diagnostic-stream.json`.
Screenshots cover desktop start/result, mobile result, selective mode and diagnostic mode.

## Preserved failure and correction

`development-failures/same-html-restore-03/` contains the failed snapshot, separate high-water guard, exact HTML,
manifest, screenshot and exact objects supplied to Web Crypto. A regenerated synthetic fixture setup-work count
changed from 6096 to 6115 across reload, causing the configuration guard to refuse recovery. No other configuration
field changed in that captured comparison. Fixed input bytes in `mission-fixtures.mjs` resolve the condition;
`FIXTURE_PROVENANCE.json` records their construction. The original failure is retained, and no unverified
engine/tiering cause is claimed.

## Data-only publication finishing

After the frozen study completes, the root can supply `browser/recorded-summary.json` and run:

```sh
python3 browser/build_demo.py
```

The renderer already supports `headline`, `description`, `metrics`, `tables` and `downloads`; the exact schema is
in `README.md`. A comparison table can contain primary coverage rows; a separate table can contain costs and
counter units. Full raw records can be downloadable JSON. These changes alter the HTML artifact hash and the
recorded-data payload; they do not change the executable module bytes or their execution digest. Record the final
artifact identity after embedding and visually check the actual study table. Do not edit `app.mjs` to tune the
story after observing results.

This is an additive local research companion over the exact released AGI ALPHA v1.42.0 workbench source closure.
It is not a maintained installed runtime, background service or verified website deployment. Browser history does
not execute after the tab closes. Current institutional proof and production authority remain empty. The normal
publication owner review and software-qualification gates remain applicable to any future public interactive copy.
