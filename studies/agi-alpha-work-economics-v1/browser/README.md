# AGI ALPHA Work Economics — offline browser companion

Open `AGI_ALPHA_Work_Economics_Demo.html` in a modern browser. It is one self-contained
file with no network, account, wallet, model-service, or package dependency.

## Three clearly labeled evidence modes

- **Local computation:** edit, paste, or upload CSV exports and select both exact
  identifier columns. Original AGI ALPHA alpha/research/guide modules compute the
  differences. Download the complete differences, grouped actions, matched pairs,
  exact input/workspace JSON, and a readable HTML report. A saved workspace is
  checked by original deterministic recomputation and remains historical.
- **Recorded study:** inspect the frozen primary, public-release, successor,
  controls, and finite-concurrency observations. Download the actual public-job
  delivery archive, analysis, control summary, and an evidence subset. These are
  recorded machine observations, separate from current browser timings.
- **Modelled economics:** change explicitly illustrative assumptions for employer
  compensation, attempt durations, residual attention, allocated system costs,
  acceptance, and available attention. The equations expose cost per accepted job,
  break-even duration, and conditional attention capacity. No scenario duration or
  ratio is presented as an observed human experiment.

The retained `successor-tool.mjs` download is the exact artifact emitted by
`raw/showcase/output/successor-tool.mjs`, with SHA-256 checked during the build and
again on browser download. Its source implements the existing bounded procedure;
retention does not itself demonstrate invention of a new algorithm.

## Rebuild

From the companion root, after the measured campaign and analysis are complete:

```sh
python3 browser/build_demo.py
```

The builder verifies upstream source hashes against the existing manifest. Only
relative module import locations are rewritten into `data:` URLs for packaging;
the original module behavior is retained. `BUILD_MANIFEST.json` records the
HTML, source-module, retained-tool, template, builder, and analysis identities.
The embedded evidence subset has its own file hashes. The original Apache-2.0
license is included as `browser/LICENSE`.

## Browser validation

```sh
python3 browser/qa_demo.py
```

If Playwright's default Chromium is unavailable, set
`WORK_ECONOMICS_CHROMIUM` to an existing compatible Chromium executable. The study
environment used `/tmp/successor-chrome/chrome-headless-shell-linux64/chrome-headless-shell`.
This is a test-process choice, not a browser-profile or user-security modification.

The offline test checks catalog/inventory/public-input computation, exact downloads,
saved-workspace verification, corruption and wrong-key refusal, calculator arithmetic,
keyboard tab selection, no external network requests, and desktop/mobile layout.
Results and screenshots are in `browser/qa/`. Build and harness failures are retained
in `BUILD_ATTEMPTS.jsonl`; those are product-development attempts and are excluded
from the business-job acceptance denominator.

Publication status: **PREPARED LOCALLY**. This build does not publish a site or start
a remote or continuous executor. All frozen study source, protocols, and results
remain unchanged by the browser build.
