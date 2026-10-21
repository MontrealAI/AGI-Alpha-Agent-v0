<!-- SPDX-License-Identifier: Apache-2.0 -->

# OUT-EXECUTE: bounded executable boundary contracts

This additive backend and the **Change-aware completion** panel in the existing
[capability workspace](../../../docs/successor/capabilities/index.html) implement a
finite instance of [OUT-EXECUTE](../../../docs/Out_Execute.pdf). The original PDF,
TeX and URLs remain unchanged. This is executable model code, not a universal
optimizer, an autonomous worker, a deployment, or proof of physical/industrial savings.

## Executable claim and assumptions

A model declares every variable, finite domain, factor scope and complete factor cost
table. Costs are nonnegative safe integers; `null` means infeasible. The objective is
exact min-sum optimization. No factors, side effects or observations outside this
model are covered. Domain order fixes deterministic witness tie-breaking.

1. The selector searches a bounded boundary grammar, including the empty boundary.
   Removing those variables from the primal graph determines private components.
   Factor scopes, not a caller's independence label, determine decomposition.
2. The compiler enumerates **every** interface row. Each contract contains its exact
   minimum and a current private witness, or an explicit infeasibility result.
3. A separately implemented mixed-radix checker builds tuple maps and independently
   recomputes all rows, minima and witnesses. It checks the complete factor partition,
   including hidden cross-component interactions.
4. On revision, unchanged source/domain/interface/local-factor bindings preserve a
   component; all other affected components are rebuilt and requalified. Imported
   archives are independently rechecked first. A digest is integrity metadata, never
   proof of behavioral equivalence or source authenticity.
5. Only pointwise-equal complete profiles, unchanged boundary factors/domains and the
   same decomposition permit reuse of the coordinator's previous selection. A scalar
   optimum or unchanged digest is not enough. Changed witnesses are rematerialized.
   A separate current acceptance scan still checks the full current result.

The local contract checker and full-model baseline deliberately do not call the
compiler's enumeration or factor lookup implementation. The shared validator and
serialization utilities are not an independent trust root. Source SHA-256 identities
bind bytes, not provenance, authorization, authenticity or external competence.

## Interface, bounds and recovery

`engine.d.mts` supplies typed model, contract, ledger and checkpoint interfaces;
`model.mjs` enforces strict schemas at runtime. `startExecution`, `advanceExecution`,
`restoreExecution`, `retainCompletion` and `execute` operate on JSON data without
network, process, payment or model calls. `installedSource()` binds the actual Node
compiler/checker import closures. The browser conservatively binds its entire
self-contained generated build. Any source/evaluator change invalidates reuse.

Maximums include 128 variables, domain size 5, 1,024 factors, factor arity 8, 100,000
total table entries, 512 boundary candidates, boundary size 3, 100,000 local
assignments per component, 10,000 profile rows, 10,000,000 counted work units and
2,000,000 canonical bytes. The default selector's search can reject a model well
below these independent maxima. Archives retain at most 16 complete revisions; the
full-enumeration baseline admits at most 1,000,000 assignments. The browser is tighter:
eight variables, 100,000 input characters and 1,000,000 counted work units.

Progress is checkpointed at component boundaries, not within one component.
`PAUSED` and `CANCELLED` can resume with the same frozen input/source/budget after
explicit independent restore. `INCONCLUSIVE` and unfinished attempts have no current
accepted artifact. An inconclusive budget is not silently increased. Validation or
unsupported-schema failures throw and are retained as failures by the workspace.
Boundary selection is reserved and charged before determining whether a current artifact
exists; materialization and independent acceptance then use the actual feasible or
infeasible outcome. Insufficient acceptance budgets retain already spent selection work.
Unpublished preview checkpoints that omitted this spent work may be rejected on import;
retain their original export rather than rewriting the ledger or claiming migration.

The existing Out-Evolve project history holds execution checkpoints, failures,
complete lineage, admission verification work and inert draft records. It retains its
256-event/8,000,000-byte bounds and reserves progress/recovery capacity before starting.
Reload/import rechecks evidence without automatically executing or granting fresh
acceptance. Histories cannot erase ancestors, roll back completed components or replace
a pending attempt. Storage failures retain an in-memory whole-history or explicit
unsaved recovery export; exporting before leaving remains essential. The existing import control accepts both whole histories and checkpoint recovery exports.
A saved wrapper must match its retained checkpoint; an unsaved wrapper independently
checks and appends only missing progress to its original history. Stale, divergent or
rebound recovery cannot overwrite a newer saved history. There is no second project-history database.

## Honest work and baseline accounting

The deterministic ledger counts table ingestion, selector candidates/scope visits,
local construction and independent qualification, complete imported-archive audits
(including their actual profile comparisons),
profile comparisons, coordinator choices, current artifact construction and separate
acceptance. Reopen/history-admission audit work is **additional** to the frozen run
ledger and exposed separately. A stopped coordinator does not imply zero verification,
zero witness construction, constant-time reuse or net savings.

The budget admits component construction and acceptance prospectively. Initial bounded
ingestion, selection and archive audit happen before their total is known; if they
exceed the selected budget, their actual counted work is retained and the attempt is
inconclusive. Thus the number is not a strict all-process/wall-time budget. JSON,
hashing, allocation, bookkeeping, operating-system work and unmodeled physical work
are excluded from logical counts. The study reports aggregate elapsed time and output
bytes separately; neither is attributed as industrial savings or converted to currency.

Baselines remain credible: independent full enumeration; an actually executed,
equally capable contract incremental baseline (an intentional tie); and an independent
fixed-proof runner. The fixed proof is cheaper when unchanged infeasibility support and
constant per-factor finite-cost shifts suffice. No imported self-declared certificate
can enter that runner's internally retained proof state.

## Reproducibility and manuscript distinction

The manuscript reports 576 snapshots (64 fixtures, nine snapshots each) and 158 of 512
updates whose externally relevant profiles remain equal. Its named companion
`code/` and `results/` artifacts were not found in the reviewed repository. These exact
numbers are therefore **not reproduced here**.

`fixtures.mjs` defines a fresh, retained `xorshift32-explicit-scopes/v1` protocol with
seeds 310000–310063. The study saves every complete model, both incremental archives,
independent oracle and fixed-proof outcomes, counters and a disk-reopen audit. It also
retains an identical-input case where the cheaper fixed proof wins. It refuses to
overwrite an existing output directory. With the repository's Node.js 22.17.1:

```sh
node --test examples/successor-capability/*.test.mjs examples/successor-capability/out-execute/*.test.mjs
node examples/successor-capability/out-execute/reproduce.mjs ./out-execute-evidence 64
```

Regression tests include changed private witnesses with equal profiles, a same-scalar
counterexample, interacting five-cycle infeasibility, changed domains/scopes/source,
rehashed corrupt rows, partial/interrupted runs, insufficient acceptance budgets,
history rollback, inert transport tampering and cheaper/equal baseline outcomes.
The existing capability CI adds a four-fixture smoke study and hosted browser journey,
recovery, export/import, accessibility, narrow-screen and no-network assertions. Node
checks do not substitute for the real browser gate.

## Separate Jobs and Fleet routes: proposal, not installed execution

`transport.mjs` creates a checked, source-bound **DRAFT_NOT_SUBMITTED** proposal containing
the exact canonical archive, expected source, complete ancestor binding, finite acceptance
obligations and all unresolved owner/reviewer/rights/runtime admission gates. It has no
submission method. Rehashed changes cannot pass `inspectWorkRequest` without matching the
independently supplied expected context.

- AGIJobManager stays USDC with six decimals and existing membership/escrow rules.
- AGIJobsv0 stays AGIALPHA with eighteen decimals and its distinct admission/contracts.
- Fleet stays separately qualified execution/review, with no currency route. Its inspected
  package-lock was unprovisioned; this proposal is explicitly blocked/not executable.

The reference commits and interface paths are frozen in `TARGETS`. They describe reviewed
interfaces, not ongoing freshness or installed compatibility. Those repositories do not
accept this new schema yet. No cross-token conversion, funding, signing, reservation,
transaction, deployment, membership change or external model call is performed. Existing
public interfaces are reused as boundary requirements, not bypassed with a generic task.
Fleet's separate interrupted-run/source-custody functional review is not cleared by this
work and must not be inferred from finite-model acceptance. Actual target adapters and
operational qualification are separate unresolved integration work.
