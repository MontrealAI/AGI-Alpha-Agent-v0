# Campaign audit repair

## Delivered scope

`engine.audit(packet)` is a sequential, in-memory, read-only auditor for the exact `campaign-audit/1` contract in `CONTRACT.md`. It replays the supplied Scheduler, Journal, ArtifactStore, and AccountBook implementations and checks that their records describe the same declared campaign. `engine.py` was repaired; `test_regression.py` was added. The four component implementations and canonical `test_public.py` were preserved.

The supplied `expert_v1.json` method was used to map identities and transitions, identify invariants, reproduce failures before repair, keep replay state local to one audit, and test successful histories, exact retries, conflicting retries, partial progress, boundary values, and caller mutation. It supplied an engineering workflow, not additional model access or private acceptance answers.

## Identity and transition map

| Evidence | Identity and ownership | Replay and release requirement |
| --- | --- | --- |
| Declaration | Globally unique job ID; owner exists; unique `(owner, artifact)` | Positive cap and cost, cost within capacity, distinct earlier dependencies of the same owner |
| Scheduler | Declared job, asserted owner, globally scoped lease | Component-valid claims, finishes and cancels; every declared job finally succeeded; no used capacity |
| Journal | Event ID for retries; globally scoped job bound to owner and cap | Reserve then settle under the component API; every declared job settled; exact retries add no consumption |
| Artifacts | `(owner, upload)` | Exact declared set, already committed, complete, verified SHA-256; each artifact contributes bytes once |
| AccountBook | Literal `settlement:` plus job ID; request identity for retries | One logical positive-consumption batch per job, one exact owner-to-usage transfer, ordinary revision and retry checks |
| Audit packet | Entire supplied canonical JSON document | Digest includes every field and retry; key order is irrelevant and list order is retained |

All release invariants hold together. A successful replay in one component cannot compensate for a failure in another. Zero-consumption jobs still require succeeded execution, a settled Journal record, and their committed artifact, but have no settlement batch. Owners with no jobs retain their balances and appear with zero settled credits.

Each audit builds fresh component instances from a copied packet. No state persists between calls. A failure after earlier replay progress returns `hold`, descriptive stage-qualified reasons, and an empty summary. A completed audit's output is isolated from later input edits and from later audits.

## Corrected behavior

1. Require all scheduler jobs to finish succeeded. Previously, zero used capacity also admitted pending, failed-to-pending, or canceled jobs.
2. Compare artifacts by both owner and upload ID, require the exact set, and reject active records before any commit read. Previously, the auditor accepted the same upload name from another tenant and promoted complete active evidence into committed evidence.
3. Bind each settlement's route and amount to the job identified by its request. Aggregate balances alone previously admitted swapped per-job charges and swapped tenant attribution when the final totals happened to agree.
4. Preserve the required full-input SHA-256 on both release and hold. The previous release path replaced it with a derived-summary hash.
5. Make structural validation and final reconciliation explicit: numeric integers exclude bool; declared dependencies are earlier and tenant-owned; consumption comes from the Journal's accepted log; per-owner spent, available, reserved, and account balances are compared; sink credits equal total actual consumption.
6. Preserve component retry semantics. Exact Journal events count once. AccountBook receives original batch payloads and expected revisions, so a retry after later activity can return its original receipt without applying a second debit. Changed content under a used identity still holds.

The auditor rejects on the first detected violation. It does not promise an exhaustive list of all packet defects.

## Executable evidence

Commands are run from this task's directory with Python's standard library:

```text
python test_public.py
python test_regression.py
```

Observed before repair:

- The unchanged canonical public smoke test passed: 1 test, exit code 0.
- The new regression suite ran 22 test methods and reported 15 failures, including subtest failures. These reproduced false releases for scheduler states, artifact identity/state, swapped settlements, and incorrect packet hashes.

Observed after repair:

- `python test_public.py`: 1 test passed, exit code 0.
- `python test_regression.py`: 22 test methods passed, exit code 0. Table-driven subtests cover multiple values within those methods.

Regressions cover multi-tenant artifacts with shared upload names, idle owners, exact credit/capacity boundaries, empty artifacts and zero consumption, valid recovered attempts, active-claim/finished-lease retries, old settlement retries after later batches, changed-intent conflicts, malformed packet and nested record shapes, missing/extra records, numeric bool/float rejection, unauthorized dependencies, incorrect hashes/cells, full-packet canonicalization, Unicode, non-encodable input, input/output isolation, and successful auditing after a late failed replay.

No private evaluator or hidden-feedback result was available or consulted. Passing these finite tests is evidence for the exercised contract cases; independent finite acceptance remains the specified external gate.

## Limits

This prototype relies on the supplied verified components and asserted owner identities. The audit checks evidence consistency, not its real-world truth or authenticity. It performs no network requests, live remediation, customer notifications, filesystem durability, concurrent operations, physical delivery, or financial settlement. Real authentication, signatures, remote execution, hostile Python objects, large production workloads, and crashes or partitions are outside the contract. No universal correctness guarantee, observed customer demand, sale, or price is claimed.
