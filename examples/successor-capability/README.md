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

The replay writes packages, full comparisons, failed attempts, cost ledgers, source digests and retained exposure history.
Replaying into the same output directory retains prior runs and labels exposed cases as regressions.
An optional uint32 seed is a reproducibility control; public local cases are not protected remote holdouts.

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

## Evaluation and costs

Frozen-package reuse generates threshold-screening, inverse-design and constrained-selection tasks after freezing.
The constructor never receives their hidden response law or truth values.
Constructor evaluation separately freezes source identity and generates changed structural families.
Correctly rejecting an infeasible family does not mean a capability was constructed for it.
The successor introduces the reservoir operation, retains the old-plan failure, invalidates stale certificates,
and independently accepts both prior and added obligations.

Comparisons include a competent sensor/reference strategy, classical uniform-cost planning with the same
primitives and semantic deduplication, and construction from scratch. Classical ties and comparator wins are valid.
The budget input caps each construction and package-freeze run. Comparisons perform additional separately bounded
runs, with their costs shown separately. No aggregate benchmark budget is implied by the input.
Ledgers count unsuccessful candidate work, transitions, synthesis, installation, calibration, qualification,
independent replay, operations and decision checks in declared abstract model-work units.
They do not measure currency, wall-clock acceleration or every browser bookkeeping instruction.
Reports distinguish frozen package cost, further verification/evaluation work, cold-start and amortized costs,
and remaining versus cumulative lineage costs.

## Boundaries

The model supports at most eight nuisance channels, a nonnegative acyclic coupling graph, and declared finite
installation guards. Shields suppress recurring disturbance; routing disconnects declared nuisance paths;
attenuation changes preparation transfer; paired references observe nuisance independently of the useful signal.
The reservoir operation activates latent source support. Irreversible reservoir contamination of subsequent
standard operations, physical apparatus, arbitrary task domains and commercial outcomes are not established.
No general invention or superiority over competent classical planning is claimed.

This branch is based on the draft PR #4844 source `ee6950aa10f2ca4cf528b7190d59be1d66e6f670`.
It must be reconciled with the eventual released baseline and requalified before integration.
This implementation does not authorize merge, publication or deployment.
