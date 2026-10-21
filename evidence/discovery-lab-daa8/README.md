# Discovery Lab: immutable daa8 browser evidence

These are the untouched JSON outputs of one complete, actual Chromium journey through the packaged Discovery Lab at Alpha commit `daa8e3d8f0fbad4a5bc9b25393f566601b0baf31`, tree `77fbbe881c544749e7a3c8ff19288610451f0697`. The validator finished on 21 October 2026 with all 12 required checks passing and four retained campaigns. This is packaged-local evidence: the page was served on a loopback HTTP server. There is no hosted-current run, public HTTPS acceptance, main-branch acceptance or release qualification in this dataset.

The source commit is [Alpha daa8](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/commit/daa8e3d8f0fbad4a5bc9b25393f566601b0baf31). These files are retained on the separate `evidence/discovery-lab-daa8-20261021` branch. Publishing this evidence does not merge or release the feature.

## Exact source and auditor

| Identity | Value |
| --- | --- |
| Source catalog aggregate `sourceHash` | `42b928d091dc60a6265836b1bbb641cb66dccea709583777cba0668685c83ebb` |
| Generated page SHA-256 | `2e9568507c04fe0cdc8b0870580848899f3fb94af181ac8d88e2141482244dc0` |
| Source catalog file SHA-256 | `4e6d772f761374e94896f97661ebfab3205eeabaa5d081d387ffe8efed743c55` |
| Axe version | `axe-core 4.10.3` |
| Executed Axe script SHA-256 | `880970c081707360e64f34cea25ff91892f5bc95675b0776925b9709dd8a68bb` |
| Browser package lock SHA-256 | `efb454a5cdb4ce3bf8082c57717649bfe6deb64f7857112f3ffbbeebb454024a` |

The catalog aggregate is a commitment to the catalog's source mapping; it is distinct from the catalog file hash and each raw download hash. The validator checked 26 committed source inputs, regenerated the exact page/catalog, and checked the entry bytes before and after the complete journey. It verified the actual pinned auditor bytes. The report retains the installed package integrity value.

## Retained journey and files

`report.json` is the complete validator report. `journey.json` is its separate, identical journey object. The eight other JSON files are actual downloads saved without rewriting, normalization or fixture rebinding:

| Files | Observed content |
| --- | --- |
| `manager-initial-review-draft.json`, `jobs-initial-review-draft.json` | The first accepted campaign's separate zero-cap route drafts. |
| `manager-retained-review-draft.json`, `jobs-retained-review-draft.json` | The earlier accepted campaign selected after a later rejected run, exported without a new run. Each route's retained draft is byte-identical to its initial draft. |
| `manager-review-draft.json`, `jobs-review-draft.json` | The stronger accepted successor's separate zero-cap route drafts. |
| `browser-workspace.json` | The complete original workspace with campaign states `inconclusive`, `accepted`, `rejected`, `accepted`. |
| `browser-account.json` | The exported session resource-account receipt. This is a recorded local observation, not a new measurement when imported. |

All files belong to mission/workspace `capability-07c1c997-6993-4457-8569-dbba136371d9`. The original workspace file SHA-256 is `42f62ebae2519e2d074b30688841da8874fad14401f76c4d17e41c1ede29d57d`. The first accepted campaign commitment is `8f560eeaf5d92f9460e19dd05d779d9c8b729a7a1627e563cf97435b2b49acb4`; the stronger campaign commitment is `e1f0017fd4f27948fb4f4ee683cab87fd67037b7a579bd263692884f1afa3e0a`. Failed/inconclusive campaigns remain in the same original workspace.

The 12 checks cover budget exhaustion, six-stage acceptance, both zero-cap drafts, edited-constraint rejection, retained-campaign selection, stronger succession, history reload, resolved accessibility, responsive widths 390 and 320, keyboard use, no external requests, and exact page bytes before/after. No browser page errors were observed. The three recorded requests all address the same local entry page.

Four actual Axe audits reported zero violations; remaining contrast incompletes were conservatively reviewed, with the minimum reviewed contrast ratio 7.528:1. The fresh retained-selection desktop and 320-pixel mobile captures were visually inspected: selection and later failure remain visible, and no horizontal clipping was observed. Binary captures and detailed audit files remain in the original local run, outside this browser-only JSON dataset. Their screenshot hashes and review scope are recorded in `manifest.json`; image dimensions describe captured elements and can differ from viewport dimensions.

## Scope and reproduction

The actual command was:

```sh
python -m scripts.validate_discovery_lab --site docs --output /workspace/scratch/ce7e013c0938/discovery-lab-exact-daa8e3d8
```

It used the existing Playwright environment and the real pinned Axe script, with no source edits or dependency installs during the run. `report.json` preserves the original local file path and loopback port as provenance; they are not public deployment URLs. A repeat journey creates different local mission IDs and elapsed observations, so it cannot replace these exact raw bytes.

Native receiver receipts are deliberately outside this browser-only dataset. Separate current candidate-scoped native inspections exist and may be added in a later metadata follow-up after exact peer public commits are known. This dataset itself does not assert public-byte-bound native compatibility, submission, funding, payment, settlement or external execution. Every route draft retains zero currency cap and draft authority.

Earlier evidence under Alpha `1665cb83f09bde3962f80942e2f1e54b789d9708` is historical and does not qualify daa8. It used different mission IDs and source/page hashes and preceded the complete native-envelope, elapsed, canonical-width and inspection-framing corrections. Historical hosted observations and native receipts must remain associated with their original source and limitations. This fresh local dataset does not inherit their hosted scope or conflate their raw payloads.

`manifest.json` records the exact ten raw JSON file hashes, sizes, Git blob identities, source and auditor pins, and origin. README and manifest are new explanatory metadata; the ten raw files remain byte-for-byte copies of the original run.
