# Public source payload: prepare, inspect and restore evidence

This is publication tooling outside the frozen scientific implementation. It prepares an isolated directory;
it never calls GitHub, creates a PR, deploys a site, changes a source manifest or executes the archived evidence.
The existing receiving coordinator owns publication. See `ADDITIVE_HANDOFF.md` for its distinct policy routes.

## What is public

The intended repository addition is entirely below
`studies/agi-alpha-flywheel-strategy-succession-v1/`. It includes all **52 original frozen files** and the original
`protocol/STUDY_FREEZE.json`, the complete editable companion/checker, offline browser, author PDF and LaTeX,
editable vector figures, completed result summaries, public audit material and inspectable raw evidence.
The preferred source-PR split keeps the raw ZIPs in a separate owner handoff and includes their exact index,
availability record and extraction helper in Git. The complete user-delivery archive still contains the raw data.

The public source tree has a different inventory from the complete user-delivery archive. Provider transfer
helpers, private file locators, original user DOCX/ZIP files, extracted predecessor copies, credentials,
environment caches and provider transport receipts are excluded. Historical source identities remain explicit;
replaying the historical Strategy Laboratory requires its separately identified original archive. Public custody
or intervention summaries are labeled projections, preserving hashes, costs, unknowns and evidence scope.

## Dry-run and final staging

Run from the original study root, using a fresh, nonexistent output directory outside it:

```sh
python3 publication/prepare_public_payload.py --output ../strategy-succession-public-payload --evidence-output ../AGI_ALPHA_Strategy_Evidence --plan-output publication/PUBLIC_PAYLOAD_PLAN.json
```

Dry-run planning verifies all frozen source bytes and reports selected file sizes and predicted archive counts.
It does **not** compress data, create the target directory or indicate publication readiness. The exact selection
can grow while unfrozen manuscript, audits and presentation files are being finalized.

Only after the author PDF has been rebuilt, every page inspected, all results terminal, and the public projections
reviewed, stage the package explicitly:

```sh
python3 publication/prepare_public_payload.py --output ../strategy-succession-public-payload --evidence-output ../AGI_ALPHA_Strategy_Evidence --plan-output publication/PUBLIC_PAYLOAD_PLAN.json --build
```

The builder requires the terminal confirmation marker and exact original source/freeze identities. It rejects an
existing output path, changed frozen bytes, nonordinary files, or provider/private-locator content. It copies
scientific files without modification. The public README and reproduction packaging preface are explicit,
unfrozen publication material. A failure leaves a marked incomplete output; inspect it and choose a new output
path after correcting the public selection. Do not publish a directory marked `BUILD_FAILED.json`.

With `--evidence-output`, the two output directories must be new and disjoint. The source tree contains no raw
ZIP blobs; its `evidence/AVAILABILITY.json` says `SEPARATE_HANDOFF_NOT_PUBLICLY_RELEASED`. The separate directory
contains the ZIP shards, an identical `ARCHIVE_INDEX.json`, a README and `RAW_HANDOFF_MANIFEST.json`. Omitting
that option instead stages the ZIPs within the source tree; this is not the preferred Git handoff for this edition.

## Raw evidence shards

The large per-trial `results/confirmation-v1/trials.jsonl` and earlier browser screenshots also reside in the
separate raw handoff, at their exact original paths. Only the final recorded desktop/mobile screenshots stay
as loose source files. Detailed independent JSON audits remain editable and directly inspectable in the PR.

Raw trial records are grouped by main work budget or diagnostic ancestry treatment; inputs, development,
challenge records and the preserved browser failure have separate groups. Shards preserve each file whole and
contain at most **4 MiB of input-file bytes** before container overhead. The compressed ZIP can be slightly larger
because its embedded manifest and directory are additional bytes. Already compressed `.gz` members are stored
without another compression pass; ordinary members use standard ZIP deflation.

Each shard has exact original relative paths and an embedded `SHA256SUMS.txt`. `evidence/ARCHIVE_INDEX.json` records
the archive hash/size plus every member hash/size. ZIP timestamps are fixed solely for deterministic containers;
they are not the execution time. Execution timestamps remain inside the untouched records. The builder reads back
and verifies every archive before declaring the payload staged. No archive is an independent signature or proof.

The existing `PAPER_UPLOADS.md` policy permits a distinct research release without replacing the software release.
Its catalogue permits one canonical repository release `.zip` companion with SHA-256 and positive size below
2 GiB; a `source_evidence` release-page link must use the same tag. The coordinator can package the complete public
companion or the exact evidence handoff as that immutable release asset. The owner must actually download and
verify it before a catalogue link is added. This preparation creates no release, upload, URL or publication index.
The source PR must not claim the raw evidence is publicly downloadable while the release remains uncreated.

## Restore exact paths safely

From the staged study root, inspect before extracting:

```sh
sha256sum -c SHA256SUMS.txt
python3 scripts/freeze_study.py
python3 publication/extract_evidence.py --archive-root ../AGI_ALPHA_Strategy_Evidence --check-only
python3 publication/extract_evidence.py --archive-root ../AGI_ALPHA_Strategy_Evidence
```

Replace the example archive-root path with the location of the extracted evidence handoff. Omit `--archive-root`
only when the archive files are already under this source tree's `evidence/archives/`. The helper checks the
source tree's index against actual external archive bytes; it never trusts an external index instead of it.

The extractor first checks all selected archive bytes and all existing destinations. It refuses traversal,
unexpected prefixes, duplicate destinations or ZIP entries, symbolic links, special entries, encryption,
oversized inventories, mismatched hashes and different existing bytes. It retains identical existing evidence.
Extraction writes only beneath `results/confirmation-v1/`, `development/`, `browser/development-failures/` and
`review/results/`, plus `operations/load-results/` and the bounded historical screenshot paths `browser/screenshot-*`
and `publication/verification/recorded-*`. It does not execute their code or import their claims as current proof or authority. Keep the
destination free from concurrent edits; the helper is not a concurrent hostile-filesystem isolation mechanism.

The browser and its first useful mission work without the raw shards. Restoring raw paths enables exact recorded
analysis and the complete preserved development-exposure scan. The frozen launcher tolerates a missing development
directory, so merely running it from the smaller source tree would scan fewer preserved development cases; that
is not claimed as exact exposure-check reproduction. Restore the evidence before making that claim. A fresh confirmatory
run always uses a new result directory and never replaces `results/confirmation-v1/`. Follow `REPRODUCE.md` for
the pinned environment and actual commands. Native timing, interpreted work units, browser counters and unpriced
human effort retain their separate meanings.

## Tool verification and handoff

`python3 publication/test_public_payload.py` exercises exact extraction and idempotent retry, refusal of differing
existing files before any writes, traversal, symlink destinations/entries, duplicate entries, corrupt archive
identity, whole-file shard bounds, locator rejection and restoration from a separate evidence directory. These
are packaging tests, not scientific evidence.

`PUBLIC_PAYLOAD_MANIFEST.json` records the final staged file identities, explicit projections, all 52 frozen
files' inclusion and verified raw archives. Its scope excludes itself to avoid circular hashing.
`SHA256SUMS.txt` covers payload files except itself and that final manifest. The exact final manifest hash must
be carried in the additive source commit/PR handoff. The receiving owner still needs the repository's required
review, qualification, release and served-file checks. A local staged payload is not a public deployment.
