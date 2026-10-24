# Pre-freeze scientific review

Review scope: source and analytic fixtures only. No holdout seed or result was accessed by this reviewer before the source freeze. This is an independently authored implementation review within the same research team, not third-party certification.

## Independent implementation evidence

`src/independent_evaluator.mjs` directly enumerates all 2,048 assignments without importing the Alpha finite model compiler or native optimizer. It independently replays raw simulation inputs, checks capacity, calibration occupancy and expiry, and separates model-feasible plans from useful realized measurements. The optional adaptive expert consumes only a prior publicly shared bias profile. Fourteen analytic self-checks pass.

Six additional hand-selected pre-freeze fixtures matched the native optimizer on objective and exact plan, with the replay checker confirming useful utility: ordinary, utility ties, short TTL, mixed TTL, expanded capacity, and instantaneous calibration. These are correctness checks, not held-out performance evidence. See `independent-pre-freeze-checks.json`.

## Findings communicated before freeze

1. **Past diagnostic data must actually be offered equally.** The first runner passed the previous profile only to the adaptive expert while labeling it offered to every method. Put the identical `pastQc` value in each planner-visible mission; static policies may ignore it.
2. **Complete cloning must include the evidence machinery.** The first runner gave the clone an independent copied native planner process, but generated its receipts through the original parent recorder/key/ledger. Use copied-source evidence code, fresh identity, and an independent ledger for the clone, or narrow the measured copying claim.
3. **Rejected plans must not be marked complete.** If the independent replay checker returns `valid:false`, fail the method and retain the rejection. Do not issue a completed operational receipt for a rejected schedule.
4. **Fatal discrepancies must preserve the failed mission.** Persist its rows or an explicit error record before aborting on native/expert or native/clone disagreement.
5. **Operational cost comparisons must match service capabilities.** Expert and greedy scheduler-only cost cannot be compared to the complete signed/verified service as if identical. Apply the same outcome-check and signed-registry path to matched operational competitors, or separate scheduler-only from evidence-inclusive costs.

The implementing owner resolved these before the confirmatory source freeze. A second source inspection and inspection of all 42 rows in pilot-03 found identical planner-visible prior diagnostic profiles, five distinct public signing keys per mission, five matching receipt-capable policies, and no invalid or failed schedules. The exact reviewed source hashes, pilot digest, checks, and resolution statuses are in `independent-pre-freeze-source-review.json`. Clone evidence code is copied and separately instantiated in the parent process; the optimizer runs in a separate copied-source worker. The shared OS, external evaluator, and parent-process evidence boundary remain explicit limitations.

## Interpretation limits

The model has four jobs and four ticks; shared-calibration batching and weighted selection are established methods. No scheduling novelty, formal-verification theorem, real instrument certification, or new economic law is established. A clone equality result is an expected copyability witness. Twelve epochs are repeated short synthetic missions. The adaptive result assumes a perfect delayed diagnostic channel that consumes four additional synthetic reference acquisitions per epoch; these are separate from contested instrument ticks and actual CPU work. Human/model authoring effort and full reconstruction cost were not instrumented.
