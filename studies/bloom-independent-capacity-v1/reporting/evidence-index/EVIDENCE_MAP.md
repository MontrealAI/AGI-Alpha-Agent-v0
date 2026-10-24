# BLOOM evidence map

This index is a post-study description of immutable measurements. It does not edit the frozen source or promote a pending original gate in place.

## What the record establishes

- **72 unique scientific worlds**: 48 confirmation + 24 fresh reproduction. 48 worlds are additionally replayed; replay compute is real cost, not new statistical evidence.
- **G1 PASS in a later independent closure**; original analysis files retain `PENDING_INDEPENDENT_REPLAY`.
- **G2 PASS**: fresh datasets together resolve 3024/3024 eligible trials exactly and 432/432 boundary cases correctly.
- **G3 FAIL, G4 FAIL**: no declared 10% competitive win or established 20% receiver advantage. See exact paired intervals; a favorable point estimate is insufficient.
- **G5 incomplete**: no actual revenue, firm offer or demand validation; unknown full monetary costs remain explicit.

## Start here

[Frozen protocol](../../protocol/PROTOCOL.md) · [Source freeze](../../protocol/FREEZE.json) · [Independent replay closure](../../results/independent_reproduction_review/INDEPENDENT_REPRODUCTION_REVIEW.json)

| Evidence | Purpose |
| --- | --- |
| [confirmation analysis](../../results/confirmation/analysis.json) | Exact outcomes, intervals and original gate states |
| [confirmation raw records](../../results/confirmation/records.jsonl.gz) | Every trial, decision, failure and phase timing |
| [confirmation ledger](../../results/confirmation/campaign.json) | One top-level campaign cost and manifests |
| [reproduction analysis](../../results/reproduction/analysis.json) | Exact outcomes, intervals and original gate states |
| [reproduction raw records](../../results/reproduction/records.jsonl.gz) | Every trial, decision, failure and phase timing |
| [reproduction ledger](../../results/reproduction/campaign.json) | One top-level campaign cost and manifests |
| [confirmation_replay analysis](../../results/confirmation_replay/analysis.json) | Exact outcomes, intervals and original gate states |
| [confirmation_replay raw records](../../results/confirmation_replay/records.jsonl.gz) | Every trial, decision, failure and phase timing |
| [confirmation_replay ledger](../../results/confirmation_replay/campaign.json) | One top-level campaign cost and manifests |
| [Public-manifest local walkthrough](../../results/public-demo/index.html) | Actual 7-stage native demonstration, conventional reverse index |
| [Independent public acceptance](../../public_case/acceptance.json) | 1,136 nodes, 2,000 edges, 17 queries and explicit unresolved records |
| [Pinned source receipts](../../public_case/source_receipt.json) | Exact public Git commits, Git blobs and SHA-256 |

## Claim-to-evidence mapping

`CLAIMS.csv` and `publication_summary.json` bind every major claim to a source file, JSON pointer and SHA-256. The confidence intervals and practical thresholds are copied from the frozen analyses, not recalculated here.

## Negative findings are first-class evidence

The unsafe receiver-proof ablation falsely accepts 72/72 fresh cases. The missing-edge challenge produces 1,657/2,176 false-safe query instances in confirmation and 897/1,088 in fresh reproduction, identically for all 3 methods. These are deliberately incomplete observations, outside the supplied-graph guarantee, and must not be counted 3 times or interpreted as independent query samples.

## Cost reconciliation

Sum each top-level campaign once. The completed measured campaigns, including development and the repeated confirmation computation, consume 47.887703197 CPU seconds. External-audit and replacement-production fields are included subsets; nested cumulative budgets and duplicated review receipts are not additional costs. The public native demo is separately measured. Initial incomplete measurements, authoring, model/service fees, hardware ownership, additional integration work, reporting and future maintenance prevent a complete monetary claim.

## Archive layout

Place this directory at `reporting/evidence-index/` inside the complete study bundle. Links use `../../` to reach the retained protocol, sources and results. The generator accepts `--link-prefix` for a deliberately different bundle location. No network or server is required to inspect the HTML summary. Raw gzip evidence can be opened with ordinary gzip/Python tools.

## Regenerate

```sh
python3 reporting/build_evidence_index.py --study-root . --output reporting/evidence-index --link-prefix ../../
```
