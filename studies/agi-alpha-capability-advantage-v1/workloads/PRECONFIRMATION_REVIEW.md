# Independent preconfirmation source review

Scope: production bridge/worker/checker/campaign/source-freeze scripts, retained numerical skill modules and declared study design, inspected before primary generation. No shared source was edited by the reviewer. Primary cases remain ungenerated at review time. This is same-session independent authorship/review, not organizational certification.

## Concrete corrections required

1. **Complete elapsed-budget acceptance:** `workbench.mjs` starts its bridge timer after initial input/source identity reads. Its native engine checks 60 seconds before final pack hashing/inspection; `run_campaign.invoke` accepts exit 0 + numerical acceptance + pack existence without checking full elapsed time. A path that exceeds the declared inclusive 60-second budget can therefore count accepted. Start the complete-task clock before source/input/selection work and require full invocation elapsed <=60 plus completed pack inspection. Keep the existing native budget; do not extend it. Count extra cleanup duration as incurred cost while refusing late acceptance.

2. **Acceptance must assert retained native boundaries:** `invoke` does not currently require `pack.evaluation.admission == HOLD`, empty authority, `settlement == NOT_CONNECTED`, and inspection's empty activeAuthority. The unchanged native engine presently emits these values, but the scientific acceptance gate should assert them rather than merely record an arbitrary inspection JSON. Root should add precise field assertions alongside numerical acceptance.

3. **Nonfinite input yields a misleading complete solver status:** The predeclared `CONTROL-NONFINITE-LOAD` case returns `status: complete` with NaN state values from the shared forward method. Independent verification rejects the task, so no accepted invalid engineering outcome was found. However, `worker.py` serializes strict JSON outside its exception handler, causing an unrecorded serialization exception instead of a structured failure result. Add shared finite-load validation and guard strict result serialization into a finite failure record. Preserve this original failed control. Other eight adverse controls refused or raised an error, and all nine were rejected by independent numerical acceptance.

4. **Outer-timeout cleanup:** `subprocess.run(..., timeout=70)` kills/waits only the immediate Node child. An active Python grandchild is not explicitly terminated/reaped by this outer cleanup path. Normal Node execution has its own child timer, so this concerns the abnormal outer-timeout path, not observed normal execution. Launch this task's own process group and terminate that group on outer timeout; do not touch unrelated processes. Record unresolved descendant resource accounting as unknown if complete reaping cannot be demonstrated.

The root already identified that staged primary paths and inverse-seal structure needed adaptation. That known correction is not counted as an additional finding.

## Additional catalogue review before primary freeze

5. **Current implementation not tied to validation:** The initial `validate_evidence.py` checks archived result JSON against bound tasks/oracles but does not execute the admitted implementation or verify an archived execution/source-closure binding. `build_catalog.py` hashes current skill files, so a changed or broken implementation can be paired with an old correct answer and still receive admission. Reexecute the exact current declared method on bound discovery cases and independently verify the fresh output, recording its implementation closure. Archive replay is separately useful, but cannot by itself validate the newly named executable.

6. **Tautological scope selection:** Initial `run_one.mjs` obtains scope/environment/rights digests from the selected record and passes those same values to `store.select` without checking the actual task. Add trusted job-schema/numerical-domain/size checks before selection and bind the actual job identity to the local execution receipt. Keep algorithm limits/research-trial permission separate from empirical 225/400-node evidence and pending larger-scope confirmation. Identical B/C checks are required.

7. **Avoidable repeated admission biases the sharing comparison:** Initial `run_one` rebuilds the catalog, independently revalidates all three skills and both compositions, then publishes another root for every B/C task. Unchanged source/epoch does not require a forward task to repay all inverse/design admission. For competent registry reuse, perform one source-bound admission and charge it once; reuse only a trusted exact admission receipt after identity/freshness checks. Each fresh production result still gets the identical independent numerical verifier across all arms. Preserve cold rebuilding as an implementation/development diagnostic rather than quietly replacing its cost evidence.

A legitimate cached receipt must bind the complete dossier, current implementation and verifier source closure, evidence/task/oracle identities, policy/scope/environment and actual independent verdicts. It must be frozen before primary execution. A caller-provided PASS flag, unbound file or stale receipt must never suffice.

Root subsequently corrected findings 1-4 in the inspected source: complete invocation elapsed gate and native boundary assertions, early/final bridge clocks, guarded strict serialization, finite-load rejection, and a task-owned session/process-group kill on outer timeout. The corrected nonfinite path was executed. The budget/process-group changes were reviewed in source; no claim of a deliberately forced 60/70-second timeout experiment is made.

## Confirmed source properties

- Shared numerical modules read the task passed to them; no hidden oracle/seed/result-file read was found. Oracle files go to the separate acceptance process. Initial input arrays and preserved source bytes are guarded around execution.
- The retained inverse and design methods call the shared `Network` numerical core. Design materialization uses actual accepted upstream parameters, with parent hashes and independent true-network assessment.
- Independent acceptance checks actual numerical vectors, feasibility, prediction and finite-model global design bounds; it does not trust optimizer status.
- The native bridge uses the unchanged local Workbench adapter interface. It leaves native admission HOLD, no native authority and settlement disconnected in the source inspected.
- No credential, wallet, live ENS, deployed contract or installed Harness/Fleet action is introduced in these files.
- B/C share the same numerical method. Their additional selection/validation costs must stay included in complete execution, with equal evidence and competent dependency planning for the registry.
- The declared protocol correctly identifies synthetic engineering scope, zero observed collections, unknown complete authoring/attention cost, chain-level sample dependence, limited current-session model population and absence of demonstrated initial scarcity.
- The source freeze covers local Python/MJS implementation files. The final production freeze must also bind the actual policy/fixture/catalogue JSON and permitted runtime/environment identities used in confirmation; a code-only hash is not the complete experimental treatment.

## Actual control evidence

`controls-results/first-run-summary.json` records the observed nine-control verdicts. The original report serialization failed because it attempted to write the candidate's NaNs as strict JSON. Root corrected shared finite-load validation after receiving the finding. `controls-results/nonfinite-output-diagnostic.json` is a separately labeled corrected-source one-case diagnostic: the candidate now raises `INVALID_FINITE_LOADS`, and independent verification rejects the invalid task. The original failed control remains preserved. These are adverse software controls and count as zero valuable jobs.
