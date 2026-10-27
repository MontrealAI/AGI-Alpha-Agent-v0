# Independent review of the completed narrow study

Reviewed 2026-10-27. Scope: frozen instrument, confirmation runner and outputs, all three saved recipient answers, the 18-check rubric, original metadat text/build/documentation files and original crop notebook/readme. No web lookup, source edit or frozen-result edit was performed.

## Adjudicated outcome

All three recipient answers satisfy the frozen semantic rubric: U 18/18, E 18/18, E+ 18/18, with no material contradictory assertion found. Each preserves the teacher-expectancy source meaning, supplied effect/variance inputs, prior-contact meaning of weeks, uncertainty about independent study units and the need for new purpose qualification. Each refuses to relabel dimensionless crop SMDs as kg/ha, identifies inconsistent counts and missing physical observations, and distinguishes a network analysis from an independent intercept-only synthesis.

These are accepted **semantic control answers**, not three accepted paid scientific services. The crop outcome is a properly qualified refusal. No recipient produces a validated crop-yield answer, resolves cohort overlap, establishes current educational efficacy or demonstrates a sale. The equality of rubric results provides no superiority signal for E over U or E+ over E. One direct-use session does not estimate ordinary-user population performance.

Adjudication evidence is in `independent_assay_adjudication.json`; it binds answer and rubric hashes and records each criterion's source coordinate and answer field. The reviewer is a sibling AI agent with inherited context, not an independent human expert panel; filesystem separation was procedural.

## Numerical and conformance findings

The saved confirmation records contain 20 numerical updates, 4 unchanged numerical reproductions, 36 holds and 4 rejects. All 64 records are marked conformant with the predeclared dispositions. Every output has `commercial_acceptance=false` and `production_admission=false`; all hold/reject outcomes have no numerical result. Therefore the paper must not describe this as 64 accepted analyses or a population reliability estimate.

The REML implementation uses the ordinary intercept-only restricted Gaussian likelihood, supplied within-row sampling variances and a normal 95% interval. Its returned baseline estimates, standard errors and heterogeneity estimates agree with the runner's rounded references. Independent analytic checks added during this review pass for an equal-variance case with a known positive heterogeneity solution and a zero-heterogeneity boundary case. These checks complement the runner's separate score-equation solver; they do not constitute a new statistical method, validate study independence or replace live R/metafor verification.

The frozen source build scripts justify the writing correction/rounding and the teacher supplied-input distinction. The rendered documentation values called published rounded references are embedded in `run_study.py`; I did not independently obtain their rendered page in this review, and the inspected original `.Rd` files contain example code rather than rendered numerical output. Cite the parent's actually retrieved rendered source if claiming an external reference match; do not imply this reviewer executed R/metafor.

Construction/confirmation file hashes remain identical to their freeze manifests. The nine diagnostic observations and two analytic checks are preserved in `independent_review_diagnostics.json`; their reproducer is `review_diagnostics.py`. They are post-confirmation diagnostics, not newly preregistered confirmation cases.

## Material limitations uncovered by diagnostic execution

**Event meaning is supplied upstream.** The dispatcher correctly holds when the kind is explicitly `overlap_disclosed`. However, a `corrected_estimate` event containing an extra covariance field and `dependence_disclosed=true` still recomputes under the independent-row model. The event schema does not reject or interpret those contradictory extra fields. Likewise, a conflicting unknown `source_id` on a scoped correction does not stop recomputation. This is acceptable only under the narrow fixture premise that a trusted upstream party has already adjudicated and normalized event scope. It is not evidence of autonomous semantic change detection or robust arbitrary-notice ingestion.

**The CLI does not maintain cumulative history.** It applies each event to the original packet. A withdrawal followed by a correction on a different row gives 18 rows for the first output and 19 for the second. That matches independent single-event conformance fixtures, but is not a chronological evidence-continuity ledger. A production sequence must update and reauthorize the packet, bind event order and idempotency, and preserve all state transitions. That behavior has not been tested here.

**Missed external events are unobservable.** Missing event kind fails closed. A supplied no-change event, however, is trusted; the engine does not fetch a source or discover an omitted correction. Source byte drift is detected when `load_packet` is called, and packet edits are detected against an unchanged mission digest. These integrity checks do not prove that outside evidence is current, authenticate the issuer or prevent an authorized caller from blessing a new packet without adequate review.

**Source, purpose and authority controls are conditional.** Changed packet bytes with the old mission, a changed mission purpose and a nonboolean authority value all hold in executed diagnostics. Mission rights/authority booleans remain simulated claims. Cryptographic/protected-network behavior must be evidenced separately by the existing native integration; this numerical adapter cannot supply it.

The stronger behavior would require a new prospective version and new tests. Preserve v1 and its outcomes rather than silently amending frozen code and claiming all these cases were already covered.

## Paper classification

Classify this edition as an **opportunity-selection and instrument-transfer pilot with no demonstrated incremental quality advantage**, together with conditional commercial feasibility analysis. Its positive contribution is a working bounded adapter, preserved source meanings, authenticated-artifact transfer where separately executed, and evidence of correct refusal in a real incompatible-source case. Its negative or inconclusive result is that the present assay does not show incremental prompting/retention superiority or establish a commercially newly feasible offering.

Do not describe the study as validation of transformational discovery, autonomous source-to-claim dependency reconstruction, a cumulative production continuity service, market creation, graph advantage or commercial compounding. The source tables and preprocessing semantics were supplied, event categories were injected, and the remaining cohort/source questions were intentionally left unresolved. A future study could address the original ambitious hypothesis, but those future steps are not executed capability in this edition.
