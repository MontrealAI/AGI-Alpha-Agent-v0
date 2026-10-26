# AGI ALPHA — The Investment Gate

## Measured discovery and an unselected investment

**Result: DISCOVERY/HOLD.** This is an additive research handoff for review. No productive asset
was selected or constructed, no untouched confirmation trial was run, and no positive
incremental economics, repayment or acceleration was established.

The record contains **nine scoped internal requests and eighteen operating evaluations**,
with two timing repetitions per scope. The underlying public material overlaps; these are
not eighteen unique customer jobs.

| Scoped requests | Measured local outcome |
| --- | --- |
| 5 source-assurance scopes | Foreground local reports, exports, verification and reconnect checks completed. |
| 3 catalogue scopes | Catalogue delivery, native delivery and history reopening completed. |
| 1 catalogue scope | Local catalogue artifacts delivered; both native attempts retained `ARTIFACT_POLICY` refusal. |

These are eight complete measured local delivery paths across two distinct execution modes.
Foreground source assurance was not authenticated native-transport execution. The prior-version
source check identified three existing version differences; profiling did not mutate runtime
checkouts. The larger catalogue's refusal preserves the existing per-file policy.

Whole-study monetary cost remains unknown, including research inference, authoring, verification,
integration, reporting and overhead. Study sales collections and financial transactions were
zero. Physical CPU use is not a complete bill, and elapsed time is not measured human attention.

## Artifacts

| File | Contents |
| --- | --- |
| [PDF paper][pdf] | Complete English paper, central figure, methods and limitations. |
| [Full companion ZIP][companion] | Source, useful outputs, raw evidence, ledgers, protocols, failures and review. |
| [Standalone EN/FR HTML][html] | Download and open locally to explore the recorded evidence. |
| [LaTeX source ZIP][latex] | Manuscript source and supplied figures for rebuilding the PDF. |
| [SHA256SUMS][sums] | SHA-256 checksums for the supplied artifacts. |

The full companion extracts to `agi-alpha-opportunity-screen-v1/`. Its `README.md` explains
the directory map and execution boundaries. The HTML displays recorded evidence; opening it
does not execute a fresh mission or qualify a service.

## Verify and reproduce locally

With Python, Node and Git available:

```sh
sha256sum -c SHA256SUMS
unzip AGI_ALPHA_Investment_Gate_Companion.zip
cd agi-alpha-opportunity-screen-v1
python3 companion/reproduce.py --audit-only --output ./new-audit
node accounting/build_accounting.mjs
```

Use a new output path. To additionally replay the existing catalogue/native paths on the
archived discovery inputs, run:

```sh
python3 companion/reproduce.py --output ./new-reproduction
```

The recorded environment used Python 3.12, Node 24.22.1 and Git 2.51.1. Included dependencies
and standard libraries support this offline replay; the companion records their provenance.
Replays reuse exposed discovery inputs, not fresh confirmation. Saved source deliveries are
rechecked with the unchanged verifier; historical source timings are preserved, not recreated.

## Review and ownership

Local offline reproduction, evidence checks, canonical accounting, demo code checks and PDF
typesetting checks passed within their recorded scopes. Browser visual QA and full-project
tests, pre-commit, lint, type and security qualification were **not run** for this handoff.
The same-session research review is not institutional or security approval. Required hosted
and owner gates remain applicable; this handoff requests neither merge nor a security waiver.

Coordination remains through [#4850][coordination] and the existing implementation/publication
owners in [#4899][engineering], [#4907][owner-route] and [#4915][recovery]. Earlier editions
and [#4916][earlier-companion]/[#4917][earlier-paper] proceed independently. Their artifacts and
adverse results remain preserved. Original Harness/Fleet holds and execution-profile limits
remain intact. This folder adds no runtime, catalogue, site or workflow change and makes no
claim of main-branch adoption or website publication. Executable companion content retains
its applicable review requirements.

This project is a conceptual research prototype; AGI terminology is aspirational.
See the [repository disclaimer](../../docs/DISCLAIMER_SNIPPET.md).

[pdf]: AGI_ALPHA_Investment_Gate.pdf
[companion]: AGI_ALPHA_Investment_Gate_Companion.zip
[html]: AGI_ALPHA_Investment_Gate.html
[latex]: AGI_ALPHA_Investment_Gate_LaTeX.zip
[sums]: SHA256SUMS
[coordination]: https://github.com/MontrealAI/AGI-Alpha-Agent-v0/issues/4850
[engineering]: https://github.com/MontrealAI/AGI-Alpha-Agent-v0/pull/4899
[owner-route]: https://github.com/MontrealAI/AGI-Alpha-Agent-v0/pull/4907
[recovery]: https://github.com/MontrealAI/AGI-Alpha-Agent-v0/pull/4915
[earlier-companion]: https://github.com/MontrealAI/AGI-Alpha-Agent-v0/pull/4916
[earlier-paper]: https://github.com/MontrealAI/AGI-Alpha-Agent-v0/pull/4917
