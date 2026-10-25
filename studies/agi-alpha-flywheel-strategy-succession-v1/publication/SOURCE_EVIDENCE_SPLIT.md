# Editable source PR and separate research evidence

## Decision and policy basis

Prepare the complete executable source, author paper, result summaries, public QA and evidence index in
`studies/agi-alpha-flywheel-strategy-succession-v1/`. Hand the raw ZIP shards separately to the existing research
publication coordinator. Do not put the roughly 242 MB raw input inventory in the main repository simply to make
the source PR appear complete. The full downloadable user-delivery package independently preserves every original
raw record and the authoritative author PDF.

This split is supported by [PAPER_UPLOADS.md at commit 54994959](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/5499495911bf8822ac0aa8c9007f00789c1132b5/docs/agent/PAPER_UPLOADS.md),
whose optional-research-resource section permits a distinct research release without replacing the latest
software release. It does not require raw measurements in Git. It requires actual download verification before
cataloguing a release asset and preserves the software owner's qualification and Pages sequencing rules.

## The three artifacts have different inventories

| Artifact | Contents | Actual status before owner publication |
|---|---|---|
| Additive source PR | All 52 frozen files and freeze; runnable browser/Node/Python companion; author PDF/TeX/figures; summaries, original independent audits, finite-load/fault summaries, QA; exact raw archive index and safe extractor | Draft source and inspectable results; full raw ZIPs explicitly absent |
| Public evidence handoff | At most 4 MiB whole-file-input shards; exact raw paths; per-member and archive hashes; matching index; manifest and extraction guide | Prepared locally for the existing research-release owner; no public URL inferred |
| Complete user package | Full original sources, raw records, historical originals, custody receipts, author PDF and runnable companion | Authoritative delivered archive; its broader private/custody inventory is not automatically a public release asset |

The separate public handoff omits private file locators, provider transfer data and original user uploads.
Historical identity/audit records remain available; historical replay still needs its separately identified
original archive. Exclusions do not authorize removing unsuccessful measurements or changing scientific bytes.

## Reproduction without misleading availability

The source-only browser works immediately and the source verifier checks all frozen bytes. Original raw analysis
needs the matching archives. The frozen launcher scans whichever development records are present; its tolerance
of a missing directory is not evidence that a smaller source tree repeats the full original exposure check.
Restore the recorded development files before claiming exact exposure-check reproduction or rerunning the full
confirmatory procedure. A new run must always use a new result directory.

`evidence/AVAILABILITY.json` states `SEPARATE_HANDOFF_NOT_PUBLICLY_RELEASED`, while the exact index identifies each
expected archive. From the source tree, run `publication/extract_evidence.py --archive-root PATH_TO_EVIDENCE`
after obtaining and extracting the separate handoff. The helper validates against the source tree's index,
rejects differing destination bytes, restores exact original paths and executes no archived code.

## Owner's later release receipt

The catalogue supports one canonical repository release `.zip` companion, with lowercase SHA-256 and an exact
positive byte count below 2 GiB. The coordinator can place both the modest public source and the raw handoff in
one immutable companion ZIP, or make a clearly described evidence ZIP; a release-page `source_evidence` link
uses the same tag. Additional shard files may be ordinary release-page assets, but the catalogue does not accept
an invented array of arbitrary raw URLs. Use the existing metadata/importer rather than a new publisher.

Before any public link is reported, the existing owner must verify the downloaded asset's hash and size, the
inner archive index and all frozen files, and retain that receipt. A prospective URL, local digest, draft PR or
prepared ZIP does not establish public availability. Adding source or interactive HTML remains the full software
lane; this evidence split grants no paper-only classification, held-review clearance or deployment authority.
