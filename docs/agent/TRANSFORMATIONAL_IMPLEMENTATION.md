# Transformational Intelligence: implementation and evidence register

This is a software implementation record. The original manuscript, its PDF,
LaTeX source, companion archive and existing public URL are unchanged.

Specification source: Alpha commit `d0d18127e3d75b2b1bd13ca448265ba7e75fc21e`.
Original paper: <https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/main/docs/Transformational_Intelligence.pdf>.

| Immutable artifact | SHA-256 |
| --- | --- |
| `docs/Transformational_Intelligence.pdf` | `d7170e8217e3bf6aa1b84868c1c76c5994c6995c5297ed092d7e72a6430c664f` |
| `docs/Transformational_Intelligence.tex` | `9d4a664d951d6b97f5136bf0b44f1ca458e90d585434a6a27a542694bb2ece5f` |
| `docs/Transformational_Intelligence_LaTeX.zip` | `49b89b4ca5a0db766d4e38af27d39c2ccbe98c4eec2e9b52af023fbbbca0e9b1` |

## Capability and limitation register

Paths beginning `successor/` below refer to
`alpha_factory_v1/core/runtime/successor/`. An implemented row is not a claim
that a PR is merged, a release published, or a live service qualified.

| Paper section / obligation | Implementation | Test / retained evidence | Supported scope / remaining limitation |
| --- | --- | --- | --- |
| Sections 2 and 4: separate purpose, formulation and measurement | `successor/transformation.py`: intent charter, typed assumptions, formulation, executable selection language and witness | `tests/runtime/test_transformation.py`; full native envelope and shared JS inspector | Bounded public-source fixed-summary task. Supplied annotations require auditing; no automatic truth extraction. |
| Section 5 Algorithm 1: diagnose, construct, compare and retain unsuccessful attempts | `DiscoveryLoop`, installed operator registry, signed existing Journal | Native phase, budget, interruption and stale-binding regressions | Installed closed-language operators; deterministic discovery is explicitly labeled. General learned operator invention is not established. |
| Complementary edits | Graph representation plus compatible closure construction; isolated edits and unchanged-frame controls | Native development observations and browser comparison | Constructed mechanism example; unrestricted exact search can match it. No advantage over all automated discovery methods claimed. |
| Section 6: original-outcome bridge and structural attribution | Fixed summary artifact, source clauses and dependency checker, common structural score, unrestricted comparison | Native full-object envelope; browser downloadable summary | Structural support under supplied graph. Reader understanding and practical utility lack calibrated evidence. No unknown ceiling certificate. |
| Section 7: evaluator revision | `successor/measurement.py`: signed verifier disagreement evidence plus separate configured controller approval, immutable measurement epochs | `tests/runtime/test_measurement.py`, `test_measurement_review.py` | Distinct locally configured principals are role separation, not independent organizations. Signatures attest provenance; they cannot establish semantic truth. |
| Appendix B: confirmation arithmetic and error accounting | `MeasurementLedger`: journal-wide attempt sequence, explicit claim estimands, width-two paired bound, calibration correction | Arithmetic, failed/parallel attempts, renaming, immutable fixed sample and adversarial signature-mutation tests | Requires valid sampling and independently controlled custody. One journal covers its projects; cross-journal/global service coordination and external checkpoints remain operational requirements. |
| Missing calibration | Outcome bound remains null unless a separately supported bound is supplied; calibration error events accounted per instrument epoch | Explicit unknown-calibration and corrected-margin tests | Agreement among models is not accepted as calibration evidence. No empirically calibrated reader-understanding instrument supplied. |
| Level 3: improve discovery across fresh complete campaigns | Frozen campaign identity, initial-agent/archive commitments and campaign experimental unit in `ConfirmationDesign` | Global reservation/terminal-observation tests | Infrastructure for campaign comparisons; no completed learned-discovery-policy superiority study. |
| Level 4: purpose-grounded formulation change | Versioned executable transformation and comparison record | Public-source pilot, complementary controls and retained incumbent | Scoped structural result only; independently measured real-world benefit remains open. |
| Continuous reuse and SUCCESSOR Ω | `successor/transformation_library.py`: versioned native archives, separately signed local review/promotion, retirement, rollback and scoped cost-aware routing | `tests/runtime/test_transformation_library.py`; existing successor state suite | Local selection confers no spending, publication or execution authority. Declared logical costs are not monetary economics. Learned router transfer and independent outcome evidence remain open. |
| Appendix A: exact finite-model study | Original immutable companion archive; separate reproduction command | 50 original tests; all 15 manifest entries; byte-identical regenerated results; independent 13-horizon and 12-threshold checks | Passive 1/2, active 8191/8192 with at most 12 queries, unrestricted equality and cost controls. Not an LLM result or autonomous causal-model discovery. |
| Appendix C: public-source understanding | Guided EN/FR fixed-summary workspace, audit map, credible controls, artifact export, pause/cancel/recovery | Native tests, browser journey, accessibility/viewport checks | Browser source annotations are local data. Interactive-understanding outcome is not substituted for a fixed-summary request. |
| Computer-mediated work | Existing Alpha Computer Use engine; Fleet #53/#54; native receipts and separate Manager/Jobs adapters | Existing native/browser qualification workflows; real result-shape export regression | Scripted local execution and independently inspectable state are distinct from live-model performance, broad desktop support and economic independence. |
| Mathematical/scientific investigation | Original exact finite-model laboratory remains available | Companion tests and arithmetic checks | No unsolved-problem solution, formally checked mathematical discovery or general scientific breakthrough claimed. Further native investigation adapter is outstanding. |
| Actual model/tool adapters | Existing `successor/mission.py` model supplier and Computer Use runtime remain intact; new source discovery exposes an installed bounded operator boundary | Existing provider/runtime qualification; new stale-operator and unauthorized-proposal regressions | New source-discovery v1 is deterministic. A configured-model formulation adapter and its complete campaign comparison are not yet qualified; existing aggregation inference must not be relabeled as this capability. |
| Ecosystem boundaries and money | Manager #1607 USDC inspection; Jobs separate AGIALPHA adapter; existing versioned receipts | Native zero-cost envelope compatibility and separate disposable currency fixtures | Current native transformation charter has zero USDC and zero AGIALPHA allowance. Positive paid drafts must refuse it. Policy doubles do not establish native paid support. |

## Workstream dependencies and ownership

| Priority | Work | Owner / dependency |
| --- | --- | --- |
| P0 | Finish existing Jobs security remediation, keep coverage and authentic scanner gates | Existing Jobs #3991 lane; no duplicate security edits |
| P0 | Qualify current four-repository execution/payment interfaces | Existing integration lane: Alpha #4836, Fleet #53, Manager #1606, Jobs #3992 |
| P1 | Correct Fleet native artifact export | Fleet #54, independent source review and automated review; hosted workflows required |
| P1 | Correct exact-Alpha-source qualification closure/index bypass | Jobs #3993, independent source review; actual byte/mode comparison and exact-head checks |
| P1 | Add durable transformation discovery and guided source pilot | Alpha discovery owner; extends existing runtime and flagship |
| P1 | Add independently revisable measurement epochs and global attempt accounting | Alpha measurement owner; separate engineering reviewer |
| P1 | Add separate inert transformation request inspection | Manager #1607 and Jobs corresponding follow-up, dependent on exact native Alpha schema |
| P2 | Qualify a compatible immutable release set and all four published sites | Integration lead after exact-source checks, reviews, finite source profiles, packaged installation and live verification |

Coordination: <https://github.com/MontrealAI/AGI-Fleet-Linux/issues/52>.

## Reproduction and operator boundaries

```bash
python scripts/reproduce_transformational_paper.py
python -m pytest tests/runtime/test_measurement.py tests/runtime/test_measurement_review.py --confcutdir=tests/runtime -o addopts= -q
python -m pytest tests/runtime/test_transformation.py --confcutdir=tests/runtime -o addopts= -q
python -m alpha_factory_v1.core.runtime.cli --home ./local-ti successor-transform demo --output ./local-ti-result.json
```

Use a new local runtime directory for a disposable run. Existing journals and
deployments remain read-only. Stop/pause and export semantics are tested per
module; imported evidence never restores trusted approval. Retain an independent
journal checkpoint and export before changing versions; hashes and local
signatures cannot detect every rollback if the checkpoint is also lost.

The native source pilot makes no paid model calls and no payment transaction.
Logical search/execution units are counted separately. Device electricity,
engineering effort, human review, migration, maintenance, and a justified reuse
horizon are not measured, so an economic break-even claim is unsupported.

Initial deployment remains Ubuntu Terminal / Hardhat with a hidden, local,
ephemeral deployer-key prompt. Keys must never appear in command arguments,
`.env`, history, logs or artifacts. Governance remains the Mac Studio Ledger.
Software publication grants no Mainnet, ENS, signing, approval, funding,
activation or on-chain authority permission.

## Publication state

Implementation and scoped tests are under review. This register does not certify
a merged four-repository set, a published fresh release, installed mixed-version
compatibility, or live website acceptance. Each final claim must name its exact
commit and actual workflow/artifact evidence. Open research and unsupported
capabilities above must remain visible in releases and product copy.
