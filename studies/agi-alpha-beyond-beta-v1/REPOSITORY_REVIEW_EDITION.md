# Repository review edition

This directory is an additive research contribution at `studies/agi-alpha-beyond-beta-v1/`, coordinated through [AGI-Alpha-Agent-v0 issue 4850](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/issues/4850). It is a reviewable subset of the complete **AGI_ALPHA_Flywheel_Research_Package.zip**, not a production release, deployment, security change, governance migration or claim of observed commercial activity.

The unchanged study README describes the full research package and its scientific findings. This file explains only how the compact repository edition is arranged. The main and evidence PDFs are directly readable under `paper/`. Every source file in the frozen executable closure is included unchanged, along with the active analysis, paper and demo generators, evidence registers, manuscript-source notes, canonical accounting modules and licenses.

## Restore tables, selected traces and the demo

The single `review_tables.zip` is a deterministic, lossless ZIP-LZMA archive containing scalar CSVs, larger result summaries, selected real simulation traces and machine-readable QA receipts at their original relative paths. The standard Python library reads it without installing a third-party decompressor. The final English/French demo is stored as `demo/index.html.gz`, also lossless and deterministic.

From this directory:

```bash
python3 review_unpack.py --check-only
python3 review_unpack.py
```

The helper verifies the archive and every member against `review_bundle_manifest.json`, rejects absolute/traversal/symlink paths and unexpected members, and refuses to overwrite differing existing files. After restoration, open `demo/index.html` in a browser and read `README.md` for the unchanged research and reproduction instructions. A restored CSV or trace is the exact original artifact, not a smaller fabricated substitute.

## What is supplied directly or in the review archive

- Complete `sim/` source, configurations, protocols and tests, including preserved earlier kernels required by the frozen source closures.
- Active analysis and publication source, editable LaTeX, generated sections, scientific figures and both final PDFs.
- All primary, 19-stress and single-prior-diagnostic summaries, frozen manifests and scalar CSV tables.
- Selected primary histories, the admitted-but-unused stress replay, the useful-but-unprofitable exploratory trace and the labeled directed QA fixtures.
- Source-linked calibration registers, foundation notes, lifecycle test traces, accounting/review receipts and final PDF/browser QA receipts.

The original negative results, the frozen recipient-policy limitation and the separately frozen one-run diagnostic remain distinguishable. Common random numbers are not presented as extra independent trials. Profit from ordinary delivery is evaluated separately from optional Alpha.

## Complete raw histories and historical preservation

The large `*_complete_records.jsonl.gz` files are intentionally omitted from Git. This includes all three primary full-history streams and the three exploratory-prior streams. They remain byte-for-byte in the accompanying complete archive, whose member prefix is `agi-alpha-beyond-beta-v1/`. `REVIEW_OMITTED_FILES.json` identifies each omitted file by original path, byte length and SHA-256, including preserved historical/development material. The archive's delivery manifest identifies the complete archive itself.

The full raw histories are needed to rerun the whole-history canonical accounting bridges, the cash endpoint extractor and raw-trace selection directly against published output. Either restore those exact members from the complete archive or regenerate them from the unchanged source, configuration and seed. The main README gives fresh-output commands for the 500-world primary run, 19 conditions at 200 world IDs each and the one 100-world prior diagnostic. Those commands preserve the published outputs. Do not run a new freeze over an existing result or substitute a changed experiment for the published one.

Examples after restoring the published complete histories:

```bash
node baseline/reconcile_v3.mjs results/paid_work_final results/paid_work_final/frozen_config.json qa/reproduced_primary_audit.json
node baseline/reconcile_posterior.mjs results/paid_work_prior_diagnostic results/paid_work_prior_diagnostic/frozen_config.json qa/reproduced_prior_audit.json
python3 analysis/commercial_cash_summary.py
```

The economic primitives and numeric results are the reproducibility target. Run timestamps, synthetic cryptographic nonces and gzip container timestamps may differ when executing the simulator anew; original delivered bytes have their own recorded hashes.

## Source rights and evidence boundaries

The all-rights-reserved Gym manuscript and its text extraction, the unlicensed V93 HTML draft and the V85 dashboard image are not redistributed here or in the complete archive. Their source URLs, editions, hashes and reading limitations remain in the evidence registers. Other bulky source copies and historical material can be obtained from the complete archive or the linked original repositories. Identity checks, capsule cryptography, graph admission and Merkle inclusion do not establish correctness or market value. Commercial outcomes, frontier job execution, buyers, collections and improvement effects remain simulated; executed local software tests are labeled separately.
