<!-- SPDX-License-Identifier: Apache-2.0 -->

# Frozen capability → separately committed future tasks

`discovery-lab-future.mjs` adds a bounded causal reuse protocol to the existing Discovery Lab campaign.
It evaluates the actual accepted OUT-EVOLVE response table, rather than substituting another forecasting experiment.

1. `freezeCapability({bindings, charter, result, ancestors})` replays every ancestor and the construction campaign,
   checks mission/source/purpose/charter identity, and freezes executable, environment, obligations and evaluator.
   No future task argument is accepted. Nonaccepted and noisy exact-answer candidates receive a charged refusal.
2. `commitFutureTasks(capsule, tasks)` captures and hashes a complete bank only after verified freeze custody exists.
   Tasks have `id`, `kind` (`screen`, `inverse`, `select`), `parameter`, `maxActiveControls` and `regime`.
   Expected answers are not accepted. `publicFutureBank(capsule, seed)` is an explicitly public reproducible bank.
3. `evaluateFutureTasks(capsule, bank, {perTaskWorkLimit})` executes every task through every declared arm.
   `checkFutureOutput` is a separately implemented arithmetic checker with no producer/capability imports.
4. `verifyFutureEvaluation(capsule, bank, result)` reconstructs freeze, bank and the complete evaluation and compares
   all outcomes, invocation traces, costs and digests. Detached evidence grants no promotion authority.

The history integration records a freeze reference before accepting a future-bank event, then saves the exact
task-bank/work-limit reservation before execution. Interruptions retain an explicit stop with unknown spent work;
a later successful run does not erase that reservation. The complete evaluation closes its own reservation.
The protocol module has no persistence store. The host owns recovery, history limits and source custody.
Imported source digests alone do not authenticate installed code: the generated catalog and qualified repository
pins must include both the future runner and its checker before claiming installed-source compatibility.

## Arms and controls

| Arm | Actual execution |
| --- | --- |
| Frozen capability | Read the accepted evolved program's table and execute the new query |
| Capability removed | Call the supplied simulator for every state, remove the declared nuisance and execute the query |
| Construction from scratch | Reserve the complete charter budget, run the real six-stage constructor for every task and execute its result |
| Competent static | Execute a predeclared closed arithmetic expression for the supplied model; no capability table |
| Unrestricted same-primitive | Invoke the actual independently enumerated unrestricted witness retained by the campaign |
| Stale capability control | Deliberately bypass regime admission and test the old table against current semantics |
| Poisoned capability control | Attempt an altered detached replacement and refuse it before invocation |

The default six-task bank includes a changed-regime case. Ordinary stale admission refuses it; the deliberately
bypassed control produces a checked failure. A newly constructed changed-regime campaign may also fail. A rejected
successor produces a freeze-refusal receipt; it cannot replace the accepted predecessor. Public tests exercise all
three generations of construction and replay accounting, rollback, ties, cheaper baselines and budget exhaustion.

## Costs and interpretation

The matched **per-task** allowance sums acquisitions, search, checking and installations with declared unit weights
of one. It is a logical allowance, not VM instructions or money. Cold costs are reported separately and included in
totals: complete lineage construction, original campaign comparisons/failed attempts, and freeze admission replay.
Scratch work is executed and charged again on every task. An insufficient conservative scratch reservation is
inconclusive before construction, with any admission work retained. Exhausted checking is inconclusive, not a
completed negative answer. Per-task tables, cold totals and the explicit amortization denominator remain available.

The unrestricted witness can tie warm reuse. The competent fixed expression is substantially cheaper in total for
this small public model; there is no claim that capability construction beats an incumbent already given the model.
The protocol tests causal use of a frozen artifact and exposes those losses. It does not establish general capability
compounding, protected evaluation, independent organizational reproduction or economic advantage.

Campaign memory/storage remain in the original frozen resource vector. The host records future report bytes and
observed elapsed time. Organizational review, external coordination, energy and operational execution remain
unmeasured or unperformed rather than assigned invented zeros. Model calls, payments and settlement do not occur.

Run the focused regression suite:

```bash
node --test examples/successor-capability/discovery-lab-future.test.mjs
```
