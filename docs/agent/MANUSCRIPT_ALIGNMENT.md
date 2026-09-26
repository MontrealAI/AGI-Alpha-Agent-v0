# Alignment with the 198-page AGI ALPHA manuscript

Version 1.8.0 treats [AGI ALPHA: A Scalable Substrate for Intelligence Organizations](../manuscript/index.md)
as the latest research specification. It preserves all earlier repository material and distinguishes an executable
local result from an independently established research claim.

## Implementation and evidence map

Page references are PDF page numbers. A bounded implementation supports only its documented input domain.

| Manuscript requirement | Implementation and demonstration | Evidence / remaining obligation |
| --- | --- | --- |
| Intelligence organization: objective → work → validation → memory | Native `core/runtime/{models,engine,store}.py`; [Proof Bloom](../bloom/index.html) and Insight Atlas | Persistent native missions, reviewed signed exports, browser replay and revocation; no claim of autonomous general intelligence |
| Objective-native compilation and proof obligations | Bloom `makeSeed`, `compile`, native Mission validation | Editable goals and bounded job plans; automatic general objective decomposition remains research |
| Distributed agents, nodes and markets | Existing native CLI/API, sandbox, signed returns and chain adapter | Native execution and reviewed handoffs work; no evidence of a production decentralized validator network or open market |
| Shared substrate, lineage and capability memory (pp. 69–70) | Bloom Chronicle and transfer capability passport | Hash-bound inputs, policy, learning scores, rollback and replay; general tool-contract composition remains open |
| Evidence ladder and honesty boundaries (pp. 36–38) | This map, release evidence, complete transfer docket | Local implementation/replay demonstrated; independent and delayed evidence remains pending |
| Evidence Contact Index (pp. 58–59) | Bloom ECI gate; transfer `core.evidence_contact` | E2 local execution only; no self-upgrade to independent E3 or external E5 |
| RSI baseline ladder B0–B5 and adjusted advantage (p. 60) | Compounding Lab B0, B3, B5 and additional treatment B6 | Actual predictions, full learning cost, explicit assumed rates and review time; B1/B2/B4 unmeasured |
| Move-37 novelty, advantage, risk, persistence and dossier (pp. 59–60) | Bloom's bounded stress gate plus transfer negative scenarios and docket | Local stress is not the complete high-novelty promotion protocol; novelty and external persistence are unestablished |
| Freeze learning before future-task evaluation | `core/runtime/transfer.py:freeze` and `assets/compounding/engine.mjs:freeze` | Learner has only A as an argument. B predictions actually invoke the frozen policy. Adversarial and cross-language tests enforce this |
| Useful transfer / local compounding | Four new B tasks per default trial; no-archive and regime-shift scenarios | Positive/negative effects computed from raw errors. Disclosed synthetic tasks are not a blinded public benchmark |
| Complete Evidence Docket (pp. 37–38) | `docket_files`, `export_docket`, `verify_docket`; browser ZIP export | All 13 canonical sections, raw artifacts, checksums, strict replay and tamper rejection |
| Action-Reason traces (p. 70) | Native journal; transfer `05_agialpha_runs/action_reason_trace.json` | Fixed experiment actions tied to commitments and outcomes; no claim of access to a model's hidden reasoning |
| Environment, validation, cost, safety and settlement records (p. 160) | Transfer docket plus existing native sandbox/ledger/settlement evidence | Exact call counts, observed whole-run time, review provenance; no transfer settlement occurs, no invented energy or monetary measurements |
| Human review and repair | Artifact-bound accept/reject/repair; separate review timers | Elapsed or operator-reported time is disclosed; identity and active attention are not externally attested |
| Capability promotion and rollback | Transfer separates local acceptance from manuscript HOLD; Bloom transitive revocation | All broad gates remain HOLD until missing comparators, scaling and independent evidence exist |
| Public task portfolios (pp. 158–161) | Custom integer-series inputs and existing native mission schemas | No claim that SWE-bench, GAIA, OSWorld or other public portfolios were run by this release |
| Scaling efficiency, coordination and risk | Explicit coordination assumption; full cost ledger | No measured multi-agent scaling law or S_N > 1 claim from a single-device experiment |
| α-WU calibration | Docket section `11_alpha_wu_calibration/status.json` | Explicitly uncalibrated, value null; forecast error is not relabeled α-WU |
| External economy and $AGIALPHA | Existing authenticated native invoice/payment verification, Ascension models | Existing local EVM checks remain; transfer lab spends no funds and establishes no external economic value |
| Independent, stressed and delayed outcomes | Separate pending fields and manuscript promotion HOLD | Requires actual independent processes, reviewers and real outcomes; local keys, hashes or simulated reviewers do not suffice |

## Two evidence ladders and two baseline profiles

The broad evidence ladder on page 36 (E0 architecture through E10 public benchmark) and the
**Evidence Contact Index** on pages 58–59 (E0 simulated, E1 probed, E2 executed, E3 independently replayed,
E4 stressed, E5 externally validated) serve different purposes. The UI's ECI labels refer only to the latter.
Executed replay on the same device does not claim E3. A signed result proves provenance under a pinned key,
not organizational independence or truth of a source.

The RSI comparator profile on page 60 names B0 null, B1 incumbent, B2 neighboring system, B3 static policy,
B4 strongest single agent and B5 current stack. The task-portfolio profile near page 158 uses B0–B3 for
single agent, unstructured swarm, fixed roles and routed constellation. These labels are not interchangeable.
The transfer protocol explicitly names `manuscript-rsi-p60`; its extra B6 is the treatment, not a new paper baseline.

## What changed in Proof Bloom

Before 1.8.0, the local gate labeled ECI measured executed advantage. ECI now means **Evidence Contact Index**.
The original positive-result requirement remains as a separate **ADVANTAGE** gate. Promotion still requires
all replay, review, benchmark, stress and lineage conditions. Existing v1 Chronicle events remain replayable:
their committed payload contains seed, bundles and reviews, not the display label of a derived gate.

Bloom's unchanged-benchmark reuse remains useful as a recovery/probe demonstration. The Compounding Lab adds the
separate question that unchanged-benchmark reuse could not answer: does a frozen policy help on **new tasks**?
Neither local path promotes the paper's broader claims.

## Pinned upstream inspection

The source publication is pinned to `bd920a6c52d820a087116bf59f2a4236d0494ac0` in
[agialpha-first-real-loop](https://github.com/MontrealAI/agialpha-first-real-loop/tree/bd920a6c52d820a087116bf59f2a4236d0494ac0).
That revision's `treatment_control.py:_treatment_prediction` calls `_expected(fixture["payload"])` and does not
use its `capability` argument. Its `capability_freeze.py` selects hard-coded rules by pair ID. Consequently, those
fixtures cannot by themselves establish that a learned frozen capability caused the reported future-task advantage.
Some other engine files at that revision are placeholders. These observations are specific to the pinned pilot;
they do not dispute the manuscript's proposed architecture.

This release therefore implements an original, bounded learning experiment rather than copying those reported wins.
Its treatment calls the learned forecasting policy, scores predictions against untouched suffixes and includes a
no-archive control and a changed-regime failure case. The source manuscript remains unchanged and fully attributed.

## Acceptance contract

The release requires native Python tests, independent Python/JavaScript implementations with exact cross-replay,
complete browser journeys, cost and failure gates, stale/tampered import rejection, dossier verification,
keyboard/mobile accessibility, offline recovery, byte-identical manuscript publication and all existing release gates.
Cross-language replay is engineering verification; authorship within this project does not make it an independent
scientific replication. See the [field guide](COMPOUNDING_LAB.md) for the exact method and limitations.
