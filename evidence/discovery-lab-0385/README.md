# Discovery Lab: immutable 0385 browser evidence

These are the untouched JSON outputs of one complete, actual Chromium journey through the packaged Discovery Lab at Alpha commit `0385df4c9728db19c396e039cd04678eebfddb9e`, tree `8340ffc1b0dc61ff02f55118c36cf412d68820b6`. The validator finished on 21 October 2026 with all 12 required checks passing and four retained campaigns. This is packaged-local evidence: the page was served on a loopback HTTP server. There is no hosted-current run, public HTTPS acceptance, main-branch acceptance or release qualification in this dataset.

The source commit is [Alpha 0385](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/commit/0385df4c9728db19c396e039cd04678eebfddb9e). This source-scoped bundle is prepared for the separate `evidence/discovery-lab-0385-20261021` evidence branch; it grants no merge or release approval.

## Exact source and auditor

| Identity | Value |
| --- | --- |
| Source catalog aggregate `sourceHash` | `46858f3b1e5e2b5cc00f0118b0ec3660d8d701cfa726e097475757efd141442a` |
| Generated page SHA-256 | `77c20a44751b937180c271d8c4aa4f782d4afe6d865c935f9461f10034a3f196` |
| Source catalog file SHA-256 | `d5986ba2908f2c9f741a69dbde10e677d00225b7a0f6aa96756a609e3a5fba45` |
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

All files belong to mission/workspace `capability-14e2314c-f9c3-4e54-a1fc-4e1d8cc28540`. The original workspace file SHA-256 is `fb255c1bf33db82b240c452bcdd1334260d7934d5d2eed984f261109f34bd340`. The first accepted campaign commitment is `6a5a522e4cf4cd0152c3c8580c42c6a0fc8ceead1ae093d5de17819e34f3ca9f`; the stronger campaign commitment is `4be51597afbe948cd935415866ca9e4f25dafe30b1985ffda0b0b41ef3e127cc`. Failed/inconclusive campaigns remain in the same original workspace.

The 12 checks cover budget exhaustion, six-stage acceptance, both zero-cap drafts, edited-constraint rejection, retained-campaign selection, stronger succession, history reload, resolved accessibility, responsive widths 390 and 320, keyboard use, no external requests, and exact page bytes before/after. No browser page errors were observed. The three recorded requests all address the same local entry page.

Four actual Axe audits reported zero violations; remaining contrast incompletes were conservatively reviewed, with the minimum reviewed contrast ratio 7.528:1. The fresh retained-selection desktop and 320-pixel mobile captures were visually inspected: selection and later failure remain visible, and no horizontal clipping was observed. Binary captures and detailed audit files remain in the original local run, outside this browser-only JSON dataset. Their screenshot hashes and review scope are recorded in `manifest.json`; image dimensions describe captured elements and can differ from viewport dimensions.

## Scope and reproduction

The actual command was:

```sh
python -m scripts.validate_discovery_lab --site docs --output /workspace/scratch/ce7e013c0938/discovery-lab-exact-0385df4c
```

It used the existing Playwright environment and the real pinned Axe script, with no source edits or dependency installs during the run. `report.json` preserves the original local file path and loopback port as provenance; they are not public deployment URLs. A repeat journey creates different local mission IDs and elapsed observations, so it cannot replace these exact raw bytes.

Native receiver receipts are deliberately outside this browser-only dataset. Separate current candidate-scoped native inspections exist and may be added in a later metadata follow-up after exact peer public commits are known. This dataset itself does not assert public-byte-bound native compatibility, submission, funding, payment, settlement or external execution. Every route draft retains zero currency cap and draft authority.

Earlier evidence under Alpha `1665cb83f09bde3962f80942e2f1e54b789d9708` is historical and does not qualify 0385. It used different mission IDs and source/page hashes and preceded the complete native-envelope, elapsed, canonical-width and inspection-framing corrections. Alpha `daa8e3d8f0fbad4a5bc9b25393f566601b0baf31` evidence is also historical: its positive literal-JSON browser/native observations remain honest for that source, but it predates the direct-object descriptor/semantic snapshot correction. Earlier receiver callback-report boundaries also required an independent inert-report correction. Neither earlier positive JSON journeys nor callback doubles establish all adversarial direct-object boundaries. Historical hosted observations and native receipts must remain associated with their original source and limitations. This fresh local dataset does not inherit their hosted scope or conflate their raw payloads.

`manifest.json` records the exact ten raw JSON file hashes, sizes, Git blob identities, source and auditor pins, and origin. README and manifest are new explanatory metadata; the ten raw files remain byte-for-byte copies of the original run.
