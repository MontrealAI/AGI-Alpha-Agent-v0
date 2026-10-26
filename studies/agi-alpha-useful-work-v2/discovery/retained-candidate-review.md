# Independent retained-candidate review

**Recommendation: the two confirmed source-level blockers are corrected. Freeze only after the corrected legitimate development delivery is retained, then evaluate untouched confirmation under the predeclared common scope. This review does not establish economic repayment or authorize production adoption.**

The reviewer is separate from the retained candidate's author, but also authored the shared independent contract and observation verifier. This is independent implementation scrutiny within one research team, not a blinded external audit. The reviewed development evidence is `results/development/retained-delivery`; primary confirmation outcomes were not opened. Original source snapshots, failed controls and post-fix controls are preserved.

## Confirmed defects and corrections

| Finding | Independent evidence | Correction and result |
|---|---|---|
| **D1: the retained packager could accept incomplete provenance.** | Its initial receipt loop checked `inputs_unchanged` and an output hash, without verifying required input bindings, exact output path/size, worker identity or job consumer hashes. Five isolated malformed-copy controls still returned accepted `SCOPED_COMPONENT_PRESERVED`: removed execution prebindings, stale verifier binding, wrong output path with matching hash, stale pair worker hash, and incorrect job consumer hash. | The candidate now explicitly checks job/source/worker/arm/schema/required-manifest identities and adopts the conventional builder's stronger `receipt_check`. All targeted malformed cases now refuse acceptance. |
| **D2: a valid behavioral mismatch was misclassified as missing custody.** | The original `run_pair.py` predicate allowed only exit codes 0 or 1 for every receipt. The independent verifier deliberately exits 2 on a behavior mismatch. Evaluating the exact predicate with an intact after-verifier exit-2 record returned false, preventing the promised regression decision. | The controller now uses typed, phase-specific worker exits 0/1 and verifier exits 0/2. A labeled one-observation semantic fault passed through the real independent verifier, produced child exit 2 and `BEHAVIOR_MISMATCH`, and reached `COMPONENT_REGRESSION` with no custody failures. |

The first control set passed **3 of 9** controls: valid copied evidence accepted, and missing/tampered observations correctly held; the five provenance cases and the regression-exit predicate failed. The corrected implementation passes **14 of 14** focused controls. Additional controls cover wrong arm, a missing required manifest entry, an unstarted command and a boolean masquerading as an integer exit code. Source hashes were stable across the post-fix control run.

The semantic fault and relocated receipts are synthetic control fixtures. Only the independent verifier was actually executed for that semantic control; the original consumer was not re-executed or shown to have a new dependency defect. The manufactured observation cannot be counted as a primary mission, defect discovery, customer demand or successful repair. Each control directory contains an explicit notice.

## What the conventional comparison contributed

`src/conventional_package.py`, `receipt_check`, checks the command schema, launch/timeout status, typed allowed exit code, empty missing-output list, equal before/after binding inventories, and the exact path, size and SHA256 of each required input and output. These were useful retained assets constructed by the independent conventional builder. The retained candidate imports that stronger component with an attribution comment. Its construction, review, failed first integration and adoption are part of this capability's lifecycle costs.

This is a successful correction through the use of an available conventional method. It does not support a claim that the retained method independently invented stronger validation or outperformed an equally capable builder. A later tie can still yield a useful enterprise component; algorithmic or economic superiority requires separate evidence.

## Delivery and Workbench scope

The delivery controller measures paired execution, independent verification, packaging and integrity as one enclosing local process interval. The pair and command receipts are nested evidence and must not be added to that outer interval again. Environment construction, discovery, failed builds, scrutiny, correction, publication and upkeep remain additional resources. The before/after probes run concurrently on both arms; earlier completion does not increase the number of eventual accepted outputs.

The Workbench adapter admits only registered mission IDs and exact job hashes, bounds its local delivery child, and binds the returned decision to its receipt. It labels execution as a local research adapter and retains the native Workbench's unauthenticated history, empty authority and `HOLD` admission. `reviewMinutes: 1` is a required unfunded schema allowance, not observed human attention or a priced service cost. This review does not claim an exhaustive process-cancellation, hostile-recorder or installed-binary attestation audit.

## Freeze and admission rule

1. Preserve the corrected legitimate development package and pin all observer, verifier, shared validator, controller, packager, contract, projection and native-closure files before untouched confirmation outcomes are inspected.
2. Compare the actual study-created manual incumbent, retained method and strong conventional builder under the declared equivalent deliverable. Give both reusable builders the same source, environment access, caches, concurrency and permitted construction resources. Charge each new construction and all failures.
3. Require complete, source-bound before/after observations, successful independent scrutiny, a meaningful scoped action, runnable evidence, valid package integrity and correct refusal under negative controls. Missing or stale evidence cannot become a positive compatibility decision.
4. Count a changed source, dependency, requirement or artifact once. Repeated unchanged requests are no-ops; assertions, repeated measurements and controls remain separate from substantive missions.
5. Compare complete declared delivery-resource envelopes and retain incomplete/failed work in the numerator. Do not extrapolate unmeasured attention, future utilization or new eventual output from a shorter run.
6. Treat operational improvement, complete investment repayment and financeable expansion as distinct gates. Monetary cost, price, demand, reserves, approved allocation and available funds remain unknown; actual collections are zero. Engineering usefulness does not by itself pass the economic gate.

## Inspect and reproduce

- Pre-fix evidence: `results/review-controls/retained-custody-v1/controls.json`; exact original sources in `discovery/review-snapshots/pre-custody-*`.
- Post-fix evidence: `results/review-controls/retained-custody-v2/controls.json`.
- Structured adjudication and source hashes: `discovery/retained-candidate-review.json`.

From the complete companion root:

```sh
python tests/retained_custody_controls.py \
  --pair results/development/retained-delivery/pair \
  --out NEW_CONTROL_DIRECTORY \
  --semantic-control
```

The post-fix controls recorded 7.698354 seconds of wall time and 7.517537 seconds of controller process CPU; the actual verifier subprocess has its own retained receipt. These are measured scrutiny resources, not the complete monetary cost. Review/model inference remains unbilled and unknown.
