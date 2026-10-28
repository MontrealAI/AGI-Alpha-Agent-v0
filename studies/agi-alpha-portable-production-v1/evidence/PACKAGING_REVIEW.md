<!-- SPDX-License-Identifier: Apache-2.0 -->
# Packaging review

Review date: 28 October 2026. This is a retrospective packaging review of the current files, not a scientific preregistration, a clean-install test, a new geometric trial or external peer review. The reviewer previously repaired the supplementary verifier; that authorship overlap remains disclosed in `independent_audit.json`.

## Verdict

No blocking packaging, supported-replay or evidence-scope defect was found in the reviewed files. The documented reproduction and economic commands match their actual argument signatures. The author corrected the working-directory ambiguity and cache-exclusion issue identified below; the revised source was inspected. One optional inventory-sidecar safeguard remains. Only this report was written by this reviewer for this task; frozen sources and records were not changed, and geometry was not rerun.

## Commands and paths checked

| Documented operation | Actual interface and behavior | Result |
|---|---|---|
| Known-case replay | `python reproduce.py DESTINATION` takes one positional destination, refuses an existing path, and copies packaged inputs into its new `study/` child. | README and sample guide agree. |
| Supplementary verification | `python verify_study.py --output REPORT_JSON` writes a JSON report; optional `--root` selects the study. The caller must choose a new output filename to preserve a previous report. | README correctly recommends a new report path. |
| Economic reconstruction | `python model.py --output RESULT_DIRECTORY` creates a new directory and refuses an existing one. | README agrees. |
| Economic audit | `python audit.py --output RESULT_DIRECTORY` reads `results.json` and `histories.csv.gz` from that existing model directory and writes `independent_audit.json` there. The option names a directory, not a JSON filename. | README correctly passes the same directory after model execution. |
| Archive construction | `python package_study.py OUTPUT_ZIP` accepts a new archive path outside the study tree. It creates a manifest, writes the ZIP, then checks CRCs and each recorded member hash. | Source inspected; archive construction was not executed by this reviewer. |

The frozen historical constructor still has an external default `research_inputs` path, and its source recipe retains historical manifest-path metadata. Those records should remain unchanged. The supported `reproduce.py` entry point explicitly supplies the copied `data/public/` path, so those historical defaults do not break the documented standalone replay.

The verifier's read-only `frozen_errors` check returned no errors. This check binds the current protocol, constructor, canonical feature program, checker, public source manifest and retrospective historical seal to exact bytes; it also checks the declared public-source and archived-file identities. It does not make these bytes an authenticated signature, confer authority or prove physical correctness.

## Inventory and local-reference checks

- Scanned 19 Markdown/HTML documents and 31 local file links before adding this report. Every linked local target existed. This was a file-target check, not a remote-URL availability or browser-navigation test.
- The full browser paper contains five embedded images; the executive browser brief contains no external image dependencies. Both editions' relative companion links require the extracted package as the README explains.
- The package selector included 159 files at review time, before this report. All 52 checked replay-critical files were selected: exact bound inputs, the replay and verification entry points, public sources, sealed historical files and current construction/confirmation outputs. Python bytecode caches were intentionally excluded, not missing source dependencies.
- The five referenced LaTeX figure PDFs and all four locally referenced DejaVu Serif font files exist. DejaVu Sans and DejaVu Sans Mono remain installed-font dependencies, as disclosed in the README.
- Package construction must occur after this report and any accepted documentation corrections so the final manifest covers the actual delivered edition. The packager's own post-write CRC/member-hash checks, and the final archive/inventory receipts, are separate from this inspection.

## Findings and corrections

1. **Publication-regeneration working directory — corrected.** The README first instructs readers to run XeLaTeX from `publication/`, then shows `python publication/make_figures.py` and `python publication/build_publication.py`. It now explicitly instructs readers to return to the study root before that second block. The corrected text was inspected.
2. **SyncTeX cache exclusion — corrected.** The original selector compared `Path.suffix` against `.synctex.gz`, but the suffix of that compound name is `.gz`. The revised selector uses `p.name.endswith(suffix)` for the excluded suffixes. The revised source was inspected. No `.synctex.gz` file existed during this review, so this correction changes no observed archive member.
3. **Consider refusing a pre-existing inventory sidecar.** The packager refuses an existing ZIP but unconditionally writes `OUTPUT.inventory.json`. A new ZIP basename paired with an older sidecar could overwrite that sidecar. A preflight refusal for both paths would preserve prior delivery inventories. No such collision was observed or created during this review.

These recommendations do not require changing frozen experimental files or rerunning geometry.

## Scope consistency

The README and sample guide consistently identify educational public CadQuery programs, manually authored nominal feature recipes, shared OpenCascade geometry, trusted frozen inputs and the unresolved feature-ID defects. They disclose loss of parameter dependencies, missing physical units for Ex019, absent material/tolerance/manufacturing authority, and absence of customers, collections or established incremental Alpha. The commercial and expansion quantities are labeled conditional assumptions. The supporting-artifact decision, flagship stop and commercial hold are consistent across the reviewed entry points. Requirements are observed direct dependency pins, not a clean-install-verified lock; the README discloses that limitation. This inspection does not assert repository-wide CI, draft qualification, release qualification or peer review.

## Reviewed file identities

These hashes identify the versions inspected at the conclusion of this review, including the two corrections above. Any later edits require their new identities in the final delivery inventory; they do not retroactively change this review record.

| File | SHA-256 |
|---|---|
| `README.md` | `a5b3dd3c0290f1e571db75e72d9e84849b708df848788870234a23d0700e9111` |
| `SAMPLE_DELIVERABLE.md` | `682dfb0c152fdb3dfcdab528e787566ceb5411a5c74a91b8e661b9fe1a0903e4` |
| `package_study.py` | `bddaead7583fe303b3509aec7d60598beed64b3c95fbbf193416c8c1bad6c874` |
| `reproduce.py` | `05b3af953a862c636372d3ea92cea53f9c86887d36f9f04f7ed73dffced3fa2e` |
| `verify_study.py` | `5f50127b0318a754b8042d445bd0ae0d059ee9946781298a9adcc27a65ae6241` |
| `economics/model.py` | `a16e69353d8dad0e0d6891e0e6d6b7db563039798771b0757c16af602228ac51` |
| `economics/audit.py` | `04b0e2c9a3380219d26889d0040e00b75ed65440be6becfc5449e41868ff97ef` |
