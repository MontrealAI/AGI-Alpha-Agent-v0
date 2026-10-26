# Companion inclusion and verified redistribution notices

This inventory describes the completed research source, records and dependency closure. It is a packaging snapshot, not a sealed-archive verification. The final archive must be closed, reopened and checked against a freshly regenerated complete inventory after the paper, demo and remaining reports are final.

## Exact distribution closure

The snapshot contains 26 unique exact wheels: 25 component-runtime wheel identities and the separately scoped Ruff 0.12.5 development tool. Each wheel hash matches preserved official package metadata. Every license/copying/notice member found under wheel distribution metadata is retained inside the exact wheel and indexed by SHA256; extracted copies are also retained.

| Distribution | Included versions | Metadata license expression |
|---|---|---|
| annotated-doc | 0.0.5 | MIT |
| annotated-types | 0.8.0 | MIT |
| anyio | 4.15.1 | MIT |
| fastapi | 0.141.1 | MIT |
| idna | 3.20 | BSD-3-Clause |
| pydantic | 2.13.2, 2.13.3, 2.13.4, 2.13.5, 2.14.0, 2.14.1 | MIT |
| pydantic-core | 2.46.2, 2.46.3, 2.46.4, 2.46.5, 2.50.0, 2.50.1 | MIT |
| ruff | 0.12.5 | Not declared in SPDX metadata; exact license notice retained |
| starlette | 1.10.0, 1.5.1, 1.6.0, 1.7.0, 1.8.0, 1.9.0 | BSD-3-Clause |
| typing-extensions | 4.16.0 | PSF-2.0 |
| typing-inspection | 0.4.4 | MIT |

Full wheel hashes, official metadata paths and hashes, download URLs, exact notice members, notice hashes and every included copy are in `publication/companion-inventory-draft-v1/inventory.json`. The compact machine-readable rights map is `publication/companion-rights-inventory.json`. The copyright and license texts themselves remain authoritative; this table does not replace their conditions.

## Original source notices

The Alpha source and new study code retain Apache-2.0 notices. The four unchanged AGIJobs JavaScript modules retain their MIT notice and exact upstream provenance. The canonical arithmetic closure retains its original source identity and Alpha notice; its held-source status remains unchanged. `native/SOURCE.json` and `canonical/SOURCE.json` identify exact files and commits. The four repositories and AGIALPHA/USDC roles are documented in `discovery/ecosystem-and-rights.md`; including source licenses confers no release, operator or financial authority.

## Inclusion and exclusion policy

The current snapshot includes all 83 frozen source files unchanged, all completed primary evidence, prior development and failed-control records, metering, exact wheels, licenses, reproduction helpers, canonical/native closures and source/publication provenance. It includes the V1 correction note and verification records as separately accounted historical context. It excludes the prior ZIP, its 1.31 GB extracted verification copy, installed virtual environments, installed Ruff cache, interpreter bytecode, build caches, screenshots, redundant Git API transport batches and private guidance identifiers. Private DOCX/TI input documents are not copied. Published scientific PDFs require an explicit filename allowlist so an unrelated private PDF cannot enter through a broad directory scan.

The preserved first source handoff and its manifest are historical editions. The later confirmation-only environment-builder amendment is explicit, with original builder bytes retained under `history/first-handoff/`; the final primary source freeze identifies the executed study sources. No historical manifest is silently rewritten to match a later source revision.

## Replay boundary

The executed host was Python 3.12.14, Node.js v24.22.1 and pip 26.2.2 on Linux x86_64 with glibc 2.39. Interpreter binaries are prerequisites and are not redistributed. The frozen component wheels target Python 3.12/Linux x86_64; other platforms or dependency tuples require separate qualification. The common source/dependency closure is needed to replay a mission; installed virtual environments must be reconstructed from exact wheels. Original source/environment/contract records remain unchanged, while replay relocation records and outputs use fresh directories.

## Final packing procedure

Run `publication/build_companion_inventory.py --out publication/companion-inventory-final-01` from the research root, adding `--public-pdf publication/FINAL_PUBLIC_PAPER.pdf` using the actual public filename. Output directories must be fresh. The helper itself does no installation or consumer execution. Do not treat a draft inventory as final while files continue to change. A ZIP writer should verify every selected current file hash against the inventory, finish and close a temporary ZIP, atomically rename it, reopen the final path, check unique names and `testzip()`, and compare each extracted entry length and SHA256. Its final completion receipt must be computed from the reopened completed archive. Preserve every older archive and hash.

The initial snapshot has 3783 selected files and 179592325 logical bytes, with zero included private-identifier hits. Later publication files are expected to change these counts. Monetary and inference costs remain unknown rather than being inferred from this inventory.
