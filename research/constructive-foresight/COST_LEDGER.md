# Cost ledger

This ledger reconstructs recorded research costs. **Full study cost is unknown.** Authoring inference, labor, review, maintenance and opportunity costs remain null. No profit or monetary Mission Alpha follows from the measured compute intervals.

## Recorded scopes

| Scope | Wall work (s) | CPU (s) | Coverage |
|---|---:|---:|---|
| numerical-calibration | 78.506722 | 78.515728 | Complete named timer scope |
| numerical-confirmation | 117.347161 | 117.282993 | Complete named timer scope |
| native-initial-and-restoration-demo | 6.551944 | 6.427498 | Complete named timer scope |
| decision-calibration | 1.375608 | 1.359650 | Complete named timer scope |
| decision-confirmation | 3.928196 | 3.927692 | Complete named timer scope |
| independent-numerical-audit-v1 | 0.686200 | 0.689114 | Complete named timer scope |
| independent-numerical-audit-v2 | 0.732810 | 0.734038 | Complete named timer scope |
| independent-decision-audit | 3.589036 | 3.587500 | Complete named timer scope |
| post-confirmation-numerical-controls | 0.590060 | 0.589546 | Complete named timer scope |
| numerical-development-retained-batches | 9.952940 | 9.947654 | Partial measurement; lower bound |
| harness-engineering-003 | 0.919065 | 0.868861 | Partial measurement; lower bound |
| harness-negative-001 | 1.052564 | 0.997760 | Partial measurement; lower bound |
| engineering-decision | 0.020112 | 0.052781 | Partial measurement; lower bound |
| engineering-decision-v2 | 0.018608 | 0.056158 | Partial measurement; lower bound |

Complete named timer scopes total **213.307738 wall-work seconds** and **213.113758 CPU seconds**. Adding documented, disjoint partial measurements gives lower bounds of **225.271027 wall-work seconds** and **225.036971 CPU seconds**. These are work sums, not the elapsed session duration.

The numerical phase timers exclude startup/shutdown and final summary serialization. The development run completed36batches and then failed serializing environment metadata; only batch costs are recoverable. Its full phase cost and diagnostic outcomes remain unavailable. The two failed native proof constructions also lack complete timing records.

The native initial-and-restoration demo uses its full external **6.551944s wall /6.427498s CPU** measurement. Initial and restored checks, dispatch, Node bridge and restoration segments are already inside that timer.

## No double counting

- Numerical phase totals include factorization, preflight, solve, validation, RHS formation, metadata, orchestration and retained CG diagnostics; never add their subcomponents again.
- rhs_generation_shared_seconds repeats in every row of a matrix/block. Count it once in a component audit, never once per row and never on top of phase totals.
- The external native-demo timer includes initial proof, restored proof, numerical checking, Node bridge, dispatch and actual restoration; all internal segment timers are nested evidence only.
- Decision process timers include actual fitting, policy calculation, simulation, bootstrap and output. Per-policy preparation allocations and simulated compute fields are not additional actual spending.
- Simulation failed_compute_seconds and late_numerical_wall_seconds are subsets of charged work, not extra charges.
- Independent numerical audits v1/v2 are separate actual inspections and both are included; neither re-runs a solver.

## Unknown costs

- Authoring inference token counts and provider charges, including agent and subagent reasoning: **null; unmeasured**.
- Source/literature searches, information acquisition and failed download attempts: **null; unmeasured**.
- Engineering labor and supervision, including failed native proof construction: **null; unmeasured**.
- Human review, required external review and beneficiary acceptance effort: **null; unmeasured**.
- Future maintenance and opportunity costs: **null; unmeasured**.
- Figure generation, typesetting, page inspection, publication and packaging outside listed processes: **null; unmeasured**.
- Unretained development overhead and process startup/shutdown outside numerical phase timers: **null; unmeasured**.
- Additional unmetered read-only analysis, primary-stratum arithmetic review and ledger construction: **null; unmeasured**.

## Measured work versus modeled value

The decision model uses a single **0.047096737755s clock unit**, one assumed credit per qualified on-time request, and one assumed cost credit per clock unit. Service-time resampling, information cost and competitor build shares describe model counterfactuals. They are not additional measured CPU consumption, customer spending or currency.

Per-policy preparation allocations represent independently deploying each hypothetical policy. Actual research spending includes the model fit once in each measured process. Failure and late-work columns identify subsets already charged.

Retained failures include both native proof-construction errors, the development summary error, missing GNU-time launcher, rejected pattern-only matrix, intentional corrupted solution and every retained CG diagnostic. Expected refusals and simulated late requests are not observed customer failures.

No paid commitment, financial transaction, on-chain transaction or payment receipt was recorded for this study. Complete cash spending is unknown because authoring inference and infrastructure are not invoiced here. Recognized external revenue is zero; external beneficiary acceptance and full-cost Mission Alpha are unestablished.

Every included measurement's file and SHA-256 appear in [COST_LEDGER.json](COST_LEDGER.json). Rebuild the snapshot by running python build_cost_ledger.py. Scientific outcomes are read only.
