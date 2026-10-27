# Local research-release packaging

`build_release.py` uses only the Python standard library. It packages and verifies local files; it does not
publish, create a tag, push a commit, contact GitHub, change Pages or qualify production software.

After the publication owner has frozen the final source and obtained its exact commit SHA, run from the study root:

```sh
python publication/build_release.py --output /absolute/new/release-directory --source-commit EXACT_40_CHARACTER_SHA
```

The output directory must be absent or empty. Earlier packages are never overwritten. The source SHA is supplied
by the caller; offline packaging does not pretend to verify remote Git state. The planned research tag is
`study-capability-creates-opportunity-v1-2026-10-27`.

## Output

- `AGI_Alpha_Complete_Research.zip`: complete original study source, data, generated documents, figures, HTML,
  reviews and provenance, under `agi-alpha-capability-opportunity-v1/`.
- `AGI_Alpha_LaTeX_Source.zip`: all LaTeX inputs, figure PDFs/PNGs, publication builders and the recorded data
  needed by those builders. Explicit LaTeX input/figure/bibliography references are checked before packaging.
- `AGI_Alpha_When_Capability_Creates_Opportunity.pdf`, `Executive_Brief.pdf`, `Evidence_Companion.pdf`.
- `Browser_Edition.html`, `English_French_Demonstration.html`, `Evidence_Companion.html`, `Executive_Brief.html`.
- `PACKAGE_VALIDATION.json`, `release-manifest.json`, `SHA256SUMS`.

The complete archive retains original HTML bytes and relative links. Only the standalone HTML copies rewrite
relative hyperlinks: document/PDF links point to the planned release assets, while source/evidence links point
to the exact declared source commit. Existing fragments, external citations and embedded images remain usable.
Those planned remote destinations are not claimed to be published or downloaded by this script.

Transient caches, Python bytecode, TeX compilation intermediates, build logs, temporary directories and prior
publication output directories are excluded. Symlinks are rejected. Original study files are checked again after
packaging to detect concurrent changes. Archive metadata uses a fixed timestamp and permissions for reproducibility.

## Integrity structure

Each ZIP contains `RESEARCH_MANIFEST.json`, which hashes every archive payload except itself. Both archives receive
CRC checks, complete member-coverage checks and byte-for-byte restoration checks. Standalone PDF copies retain
their original bytes; HTML rewrite receipts bind original and rewritten identities.

`SHA256SUMS` is the outer index and hashes **every emitted file except itself**, including `PACKAGE_VALIDATION.json`
and `release-manifest.json`. The release manifest records payload/validation hashes and lists the checksum index's
role. The two metadata files do not falsely purport to hash each other: mutually recursive cryptographic digests
cannot be constructed in this format. No validation file is silently omitted from the outer index.

The publication owner must separately verify the actual source commit and public asset downloads, and preserve
the existing software release and Pages qualification process. Package verification is not PDF visual QA, scientific
replication, external security review, customer validation or production authentication.
