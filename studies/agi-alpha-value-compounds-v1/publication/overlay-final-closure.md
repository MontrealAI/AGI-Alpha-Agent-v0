# Final overlay and reproduction-documentation closure

**Reviewed at:** 2026-10-26T14:09:05.787260+00:00

**Artifact:** `publication/demo/AGIALPHA_The_Next_Upgrade.html`

- Complete HTML SHA-256: `51702f91946a524a683efb59e5e35bd711a2ab538a4955df25c889133d4eff92`.
- UI markup/scripts SHA-256, with only the contents of the embedded `script#data` JSON element removed: `aae1b451cfe656e45d65cd5c9981f5f12252530c3166dfbf2125d1b1c7e4c0fa`.

This closes the four requested publication-layer clarifications from the earlier textual review. It does not alter the frozen experiment, its rejection or economic hold. Browser interaction and visual QA remain the publication lead's separately recorded checks.

## Four fixes verified

| Requested fix | Verified current behavior/content | Status |
| --- | --- | --- |
| Distinguish a transition summary from the complete raw packet | Both languages call the selected download a transition summary; its filename ends in `-summary.json`. Both evidence paragraphs explicitly place complete raw packets and evidence in the companion ZIP. The all-outcomes export likewise contains transition summaries, with that same raw-evidence boundary. | Closed |
| Identify the fixed historical snippet when switching outcomes | Both languages label the panel as the historical Starlette 0.36.3 call. The explanation names the failing Starlette 0.36.3 / HTTPX 0.28.1 pair and says that the known Starlette 0.37.2 remedy removes the forwarding. It no longer ambiguously attributes failure to the selected successful configuration. | Closed |
| Translate the authorization boundary precisely | The French footer now says `engagement payant`, matching no paid commitment, and no longer says `dépense nouvelle`. It does not claim unknown execution/inference costs were zero. | Closed |
| Display the unresolved consumer scope | The selected transition renders the strict mapper's unresolved-call count and direct dependency-import-reference count in both languages. All twelve embedded conventional summaries report 10,172 unresolved captured calls, so that limitation is visible rather than confined to the downloadable JSON. | Closed |

The central boundaries remain: conventional 12/12 scoped assessments; custom 9/12 and rejected; no primary affected consumer call established; native 35 accepted inputs, 102 refusals and one absence kept distinct from the local extension; zero collections, unknown complete money costs and economic admission on hold. The four fixes do not enlarge those claims.

## Reproduction documentation corrected

Only `README.md` and `support/README-reproduction.md` were edited. They now distinguish original-study reconstruction, isolated replay and a separately registered local assessment.

The support guide gives an explicit command for repeating the original twelve-transition campaign from the already staged `study/` copy with its verified virtual-environment Python, writing to a new external directory. It directs the reader to that directory's own `runs.json`, completion marker, packets and raw evidence. These are new replay measurements of the existing historical missions, not fresh held-out confirmation. Newly registered local mission IDs are run explicitly through the Workbench; the fixed campaign does not automatically include them.

Inspection of `analysis/summarize.py` confirms a material usability limit: it has no campaign-path or output-path option. It always reads companion-relative `results/confirmation/runs.json`, the original completion marker, the registry and `metering/campaign-process.json`; it requires 108 timing evaluations and writes `results/summary.json` and `results/outcomes.csv`. Extra command-line paths do not redirect it. The documentation now states this explicitly and never presents that utility as an analyzer for a new campaign directory.

Original-table reconstruction is confined in the instructions to a disposable complete copy retaining the original study inputs and process record. The supplied original evidence remains preserved. New-run aggregation would need a separately identified analyzer with explicit input/output paths and its own timing provenance; no such configurable feature is claimed. Source registration and index regeneration are also documented as working-copy operations.

No campaign, table aggregation or new experiment was executed for this documentation closure. `analysis/summarize.py`, frozen files, the paper, the demo and its templates were not modified by the reviewer. No additional metering entries were appended, as requested for final publication closure.

## Final packaging hash boundary

The complete HTML hash above identifies the exact data snapshot reviewed here. A later rebuild that changes only embedded economic provenance will change that complete hash. The UI-only hash permits the publication lead to verify that the reviewed labels, explanatory text and render logic remain identical: remove only the JSON element's contents, retaining its opening and closing tags, then hash the remaining UTF-8 HTML.

A matching UI hash does not preapprove arbitrary embedded-data changes. Any final economic-provenance refresh still belongs in the sealed companion's final file manifest and integrity checks. No material textual issue remains among the four requested fixes; the summarizer's fixed original-study paths remain a documented implementation limitation rather than an advertised replay capability.
