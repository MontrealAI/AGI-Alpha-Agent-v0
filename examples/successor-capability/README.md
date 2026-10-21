<!-- SPDX-License-Identifier: Apache-2.0 -->

# Out-Evolve capability constructor

This additive workspace constructs executable preparation interfaces for a finite synthetic apparatus.
It preserves the original v1 proposal, witness and event-history modules.
It does not execute generated JavaScript, payments or external actions.

Use Node.js 22.17.1 from the repository root:

```sh
node examples/successor-capability/replay.mjs /tmp/out-evolve-evidence
node examples/successor-capability/replay.mjs --verify /tmp/out-evolve-evidence/shielded-capability.json
node --test examples/successor-capability/*.test.mjs
python scripts/generate_successor_capability.py
python -m http.server 8080
```

Open `http://localhost:8080/docs/successor/capabilities/` for the constructor and preserved workshop.
The generated page is self-contained and prohibits network connections through its CSP.
Browser acceptance uses the repository's pinned Playwright and Axe dependencies:

```sh
python tests/browser/test_out_evolve_browser.py
python tests/browser/test_successor_capability_browser.py
```

The replay writes packages, full comparisons, failed attempts, cost ledgers, source digests and retained
exposure history.
Replaying into the same output directory retains prior runs and labels exposed cases as regressions.
An optional uint32 seed is a reproducibility control; public local cases are not protected remote holdouts.
One replay directory retains at most 100 reports. A full directory rejects another run before evaluation or
writes; use a separate output directory and retain the earlier evidence.

## What executes

`apparatus.mjs` supplies three channel graphs. `typed-runtime.mjs` validates the finite AST and interprets
installations, sequential primitives and bounded repetition. It derives conservative recurring nuisance bounds
and treats productive-state preservation and the apparatus tolerance as hard requirements.
`independent-checker.mjs` implements its own validation, transitions, graph analysis and certificate checking.
Certificates concern the supplied mathematical model.

`constructor.mjs` searches installations and compositions using uniform primitive-cost ordering.
Deduplication retains all future-relevant semantics; dominance also accounts for cost and remaining program capacity.
Search has explicit instruction, state, retained-memory, modeled-cost and wall-time bounds.
Qualification stops at the first independently checked point; the report does not claim a complete Pareto frontier
or global optimality of total synthesis-plus-operation costs.
Exhausted search reports that no qualifying construction was found within budget.
Finite infeasibility is reported only for a fully explored bounded program language or an explicit independent
structural obstruction proof.

`capability-package.mjs` freezes the AST, executable interface, model/catalogue/objective identities,
scope, certificates, fixtures, attempts, costs and compatibility-scoped parent assets.
Import replays search and independently recomputes the executable claims; recomputing a hash cannot legitimize
tampered semantics, erased attempts or discounted costs.
Versioned Out-Evolve events use separate device storage and preserve v1 history behavior.
Importing another package retains an unfinished search with its original apparatus, bounds and costs.
Construct cannot replace a pending checkpoint, including through form submission. Resume or finish the retained
search when its original bounds permit. **Start separate history** saves and archives the existing history before
creating another identity; reopening the earlier history restores its checkpoint unchanged. This also provides
a separate construction path when a qualified candidate cannot fund acceptance within its frozen budget.
An accepted checkpoint can finish package qualification after a failed save when its original budget and
remaining history capacity fund acceptance; it does not rerun construction. Imports and saved-history switches
must extend any stored history with the same identity, and storage transactions reject older or divergent
archives before overwriting them. Export remains the recovery path when a save cannot complete.

Reuse and successor actions reserve room for their complete report before generating cases or running model work.
The local history permits 256 events and 8,000,000 canonical UTF-8 bytes; finite JSON node and depth limits also
apply. A conservative reservation can refuse work before the history is full. Start a separate history when its
package and report reservation fits; otherwise export the package for separate evidence storage.

Stored successor reports use compact constructor tokens instead of duplicate attempt and frontier arrays.
Replay with the original parent package reconstructs their exact programs, attempts, frontier and charged work.
Accepted package canonical content and digests, task results, exposure records, obligations and costs remain
intact. Public evaluator return values keep their original format. Compact JSON exports keep valid bounded
histories importable.

If a report unexpectedly exceeds its reservation or cannot be appended, the complete generated report, source
package and original history remain available as an **unrecorded evaluation** export. This fallback is held in
the current session until exported; it is not a saved history or a fresh verification of imported evidence.
Export it before continuing or leaving the page. A successful history-save retry does not erase this report.

## Evaluation and costs

Frozen-package reuse generates threshold-screening, inverse-design and constrained-selection tasks after freezing.
Their task algorithms are prewritten. The generated capability controls modeled measurement nuisance;
it does not invent those downstream algorithms.
The constructor never receives their hidden response law or truth values.
Constructor evaluation separately freezes source identity and generates changed structural families.
Correctly rejecting an infeasible family does not mean a capability was constructed for it.
The initial successor introduces the reservoir operation, retains the old-plan failure, invalidates stale certificates,
and independently accepts both prior and added obligations.
A repeat attempt with an already covered scope does not establish another scope expansion, even if its
package qualifies.

Comparisons include a competent sensor/reference strategy, classical uniform-cost planning with the same
primitives and semantic deduplication, and construction from scratch. Classical ties and comparator wins are valid.
The budget input caps each construction and package-freeze run. Comparisons perform additional separately bounded
runs, with their costs shown separately. No aggregate benchmark budget is implied by the input.
Ledgers count unsuccessful candidate work, transitions, synthesis, installation, calibration, qualification,
independent replay, operations and decision checks in declared abstract model-work units.
They do not measure currency, wall-clock acceleration or every browser bookkeeping instruction.
Reports distinguish frozen package cost, further verification/evaluation work, cold-start and amortized costs,
and remaining versus cumulative lineage costs.
The sensing comparator charges candidate work and terminal qualification/replay against one total cap.
Its qualification result and search completion are separate: an exhausted or truncated search cannot establish
a completed negative result, and a qualified incumbent does not establish complete enumeration.
Ancestor accounting includes every frozen package construction ledger in the parent chain. Separately recorded
earlier task evaluations remain in history and are outside package ancestry.

The default matched comparisons retain these results in abstract model-work units:

| Apparatus | Constructor / classical planner | Planner relation | Sensing work | Sensing qualification |
| --- | ---: | --- | ---: | --- |
| Shielded | 591 / 591 | Tie | 42 | Qualified |
| Routed | 439 / 439 | Tie | 67 | Qualified |
| Common reference | 1020 / 1020 | Tie | 20 | Did not qualify; independently rejected, error bound 0.5 |

The 20-unit common-reference attempt is a completed negative result, not a cheaper successful alternative.
An optional planner or scratch comparison that cannot fund package freezing is inconclusive. Its actual search
work stays in the ledger and aggregate totals; it cannot discard an accepted inherited successor or establish
a successful baseline, cost advantage or saving.
A primary successor candidate that cannot fund its complete package acceptance is also inconclusive.
Its raw candidate work and checkpoint remain in the report, acceptance replay is not run, and the earlier
accepted parent remains the available package. A candidate found within the search cap is not yet an
accepted successor.

## Boundaries

The model supports at most eight nuisance channels, a nonnegative acyclic coupling graph, and declared finite
installation guards. Shields suppress recurring disturbance; routing disconnects declared nuisance paths;
attenuation changes preparation transfer; paired references observe nuisance independently of the useful signal.
The reservoir operation activates latent source support. Irreversible reservoir contamination of subsequent
standard operations, physical apparatus, arbitrary task domains and commercial outcomes are not established.
No general invention or superiority over competent classical planning is claimed.

This additive implementation follows PR #4844's capability workspace in
`MontrealAI/AGI-Alpha-Agent-v0`; its separate integration PR is #4845.
Integration requires the predecessor's qualified merge followed by reconciliation and qualification against main.
Fleet release verification remains separate. Merging does not establish release or deployment.
Accessibility evidence includes review of reported ARIA and contrast incompletes, keyboard and viewport checks;
zero automated violations alone is not a claim of complete accessibility or assistive-technology coverage.
