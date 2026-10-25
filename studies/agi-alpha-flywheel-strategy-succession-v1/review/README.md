# Independent release-plan review

This directory supplies a separately implemented artifact checker and a development-only challenge/regression diagnostic. It does not import the producer's solver, strategy interpreter, or primary checker. It was authored from the public `release-plan/v1` task/result contract and its two development examples. The authoring agent shares the same project commission; this is code-level separation, not third-party certification.

## Use the checker

```sh
python3 review/check.py < task_result_pairs.jsonl > independent_checks.jsonl
```

Each line contains `{"task": {...}, "result": {...}}`. The response is:

```json
{
  "valid": true,
  "qualified": true,
  "lower_bound": {"value": 6, "critical": 6, "load": 5, "locked": 0},
  "counts": {"input_bytes": 0, "input_fields": 0, "job_scans": 0,
             "dependency_edges": 0, "calendar_slots": 0, "interval_slots": 0,
             "comparisons": 0, "arithmetic": 0, "map_operations": 0,
             "total": 0},
  "errors": [],
  "optimal_if_bound": true
}
```

The counts shown above illustrate the output fields, not a measured run. `valid` means the supported task scope, complete feasible schedule, registered bound components, movement accounting, dispatch provenance and explicit empty proof/authority fields all pass. `qualified` additionally requires the deadline and movement target. A feasible schedule can be valid but unqualified. `optimal_if_bound` is true only for a valid feasible schedule whose makespan equals an independently derived lower bound. A bound gap does not establish that the schedule is suboptimal.

Task scopes: 1–18 jobs, 1–128 integer calendar slots of capacity 0–4, durations 1–12, crew requirements 1–4, unique job identifiers `J1`–`J999`, and an acyclic dependency graph. Releases default to zero; supplied releases are integer starts in 0 through horizon−1. An optional explicit horizon must match the calendar length. Deadlines default to the horizon.

A repair requires baseline starts for exactly all jobs. Baseline starts need fit the horizon, but are **not** tested against changed calendar/release constraints: repair exists because the old plan can become infeasible. Locks must match original baseline starts and form a predecessor-closed set. Locked jobs retain their exact starts. Plan mode permits an empty `locked` mapping and rejects nonempty locks, baseline and movement-limit semantics. Repair movement is the sum of absolute deviations from baseline starts. Its optional limit is an integer in 0–2304.

The result schema is `release-plan-result/v1`. It requires `task_id`, one `schedule` row per job, exact makespan and movement, `lower_bound`, `optimal_by_lower_bound`, a dependency-respecting `dispatch_order` containing exactly the unlocked jobs, `lookahead_steps` in 0 through job count, and explicit `proof:[]` and `authority:[]`. Additional metadata has no semantics and cannot alter scope or acceptance. A strategy digest, if supplied as metadata, is not evidence that its associated program actually ran.

### Independently derived bounds

1. **Critical path:** process the DAG in a simple topological pass. Each unlocked job starts no earlier than its release or any predecessor's earliest finish. A locked job finishes at its exact locked start plus duration; that finish propagates to descendants. Inconsistent locked timing is refused.
2. **Calendar work:** sum duration × crew for all jobs. The earliest calendar prefix whose cumulative capacity covers that work is a relaxation lower bound. Insufficient total capacity refuses the task within this finite horizon.
3. **Latest locked end:** the maximum end among fixed jobs, or zero.

The registered value is the maximum of those components. Reported bound components must equal these particular registered bounds. Rejecting a different claimed value means that the registered certificate was not reproduced; it is not a theorem that every stronger mathematical bound would be false.

Every actual scheduled job-slot is checked against the original capacity calendar. Endpoint checks alone cannot conceal a temporary calendar outage. All dependencies, releases, durations, locks, missing/unknown/duplicate assignments and worker-time totals are inspected. JSON input rejects duplicate object keys and nonfinite numbers.

## Reference work and reservations

`counts.total` is the sum of a **declared reference-operation model**. It is deterministic for an identical JSON value. It does not count Python bytecodes, every interpreter allocation, hardware instructions, elapsed time or money. Compound validation predicates are single declared checks. Incidental language-runtime overhead must be measured with end-to-end wall time separately.

| Counter | Charged action |
|---|---|
| `input_bytes` | UTF-8 bytes of canonical complete task/result JSON, including metadata |
| `input_fields` | Every object member and array item traversed while accounting for the input |
| `job_scans` | Explicit job, assignment, topological and dispatch-loop visits |
| `dependency_edges` | Each dependency visit, including repeated topological scans |
| `calendar_slots` | Calendar validation, prefix-capacity and final-load visits |
| `interval_slots` | Each scheduled job-slot whose crew demand is accumulated |
| `comparisons` | Declared validation predicates, integer-scope comparisons, bound maxima and target checks |
| `arithmetic` | Explicit bound, duration, movement and load arithmetic |
| `map_operations` | Explicit graph/mapping accounting operations beyond input-field traversal |

The runner must reserve before invoking the checker, charge the actual returned count, and preserve a failed invocation's spent cost. `operation_reserve(envelope)` provides the conservative bound

`2B + 4n² + 220n + (2n + 50)E + 18H + 1024`,

where B is canonical input bytes, n is job count capped at 18, E is declared edge count capped at 17 per job, and H is horizon capped at 128. Malformed scopes exit before unbounded loops. The calling system charges reservation calculation and transport within its own bookkeeping. This module cannot enforce the parent run's total budget, cancellation, expiry or process lifetime; those are runner responsibilities.

## Challenge, adjudication and regression assets

`challenge.py` reads the original task and creator artifact. It identifies concrete duration, missing-job, dependency, lock and slot-capacity objections. Each objection is bound to the hash of the exact original evidence and includes a reproducible witness. It does not grant final proof.

`adjudicate.py` independently checks the original artifact and the specific witness. It returns `SUBSTANTIATED`, `REFUTED` or `UNSUPPORTED`. A mismatched evidence digest, unsupported criticism or inappropriate scope cannot compel revision. Its regression-admission path refuses protected confirmation inputs; only explicitly development evidence can become a regression asset.

`run_regressions.py` executed three **seeded defective creator-output** chains:

- Ignored calendar dip → actual slot overload → corrected timing → passing regression.
- Moved fixed prefix → exact lock violation → restored prefix → passing regression.
- Unpropagated late locked predecessor → incorrect registered critical-path bound → corrected certificate → passing regression.

The first two objections were generated by the bounded challenger. The third was specified by the independent review agent during pre-freeze scope review. It is not claimed as an automatically discovered solver defect. A fourth case supplied a deliberately false claim that overlapping jobs necessarily overload a pooled crew calendar. Adjudication found demand equal to capacity and **refuted** the claim; the correct creator artifact was not revised.

The complete chains, original artifacts, objections, adjudications, revisions and ledger are in `regression_assets.json`. The exact saved file is 27,177 bytes. Its declared acquisition reference work is 14,608; acquisition plus retained bytes is 41,785. Research design, code authoring and reviewer reasoning are unpriced. These figures do not establish full enterprise or monetary cost.

## Frozen development screening probe

`PROBE_PROTOCOL.json` and `PROBE_FREEZE.json` precede the one executed run. The freeze binds source, retained assets and all 14 new diagnostic input commitments. Seven deliberately seeded fault variants are compared with no early assets, retained counterexamples, and a conventional regression suite given **identical assets**. No main confirmation input was used.

The unchanged independent checker remains the gate in every arm. Asset arms screen the three retained development cases first, then the same fresh diagnostic cases. Screening stops at the first reproducible failure. All outputs and failure cases are retained in `PROBE_EVENTS.jsonl`.

| Arm | Checker calls | Screening work | Retrieval | Acquisition + retention | Total declared work |
|---|---:|---:|---:|---:|---:|
| No early assets, ablation | 70 | 105,994 | 0 | 0 | 105,994 |
| Retained counterexamples | 37 | 53,721 | 27,177 | 41,785 | 122,683 |
| Conventional regression suite | 37 | 53,721 | 27,177 | 41,785 | 122,683 |

The assets expose familiar failures earlier but produce a **16,689-unit first-batch loss** after their declared acquisition, retention and retrieval costs. The conventional suite is exactly equal. All three arms admit the same one valid variant and reject the same six defective variants. No improvement in final correctness is established.

The correct variant takes 17 checker calls with assets instead of 14, and the new root-release fault takes 10 instead of 7. The probe preserves these cases where prescreening is overhead. If an identical seven-variant batch recurred with the same detection savings and retrieval charge, two batches would cover the fixed acquisition/retention cost. That is a modeled crossover for this artificial fault mix, not evidence of demand, profitability, general transfer or increasing growth rate.

The full diagnostic run made 144 checker calls in approximately 0.020 seconds in the observed environment. That elapsed time is a separate measurement and not a hardware-normalized performance result. The finite small sample, deliberate fault families and predeclared case order do not support population significance tests or a general claim of autonomous strategy discovery.

Reproduction of the original frozen run should use a fresh copy of this directory with existing `PROBE_RESULTS.json`, `PROBE_EVENTS.jsonl` and execution transcripts moved aside as preserved evidence. `python3 review/probe.py run` verifies the original source freeze and refuses to overwrite evidence. Do not revise source in place and claim the same frozen experiment.

## Verification and independence limits

```sh
python3 -m unittest discover -s review -p 'test_check.py' -v
```

Fifteen tests pass, including 47 targeted invalid mutations, valid-but-unqualified outcomes, false-criticism refusal, protected-confirmation refusal, deterministic counts, and a dense 18-job reversed-order DAG within the reservation bound. This is evidence for the tested contract, not formal verification of all Python behavior.

`INDEPENDENCE.json` records source provenance and module identities. Candidate generation, the checker and the project remain under the same administrative commission. The main runner must protect frozen evaluator files and authority controls, verify exact source and result identities, and enforce budget, STOP, restart and finite expiry. The checker itself grants no production authority and asserts no operational qualification across Alpha, Manager, Jobs or Fleet.
