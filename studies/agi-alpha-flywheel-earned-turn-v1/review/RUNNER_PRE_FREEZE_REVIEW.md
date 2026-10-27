# Main runner: pre-freeze findings and minimal admission design

This review concerns the development runner first presented after development campaign1, not frozen confirmation evidence. No confirmation inputs were used and the reviewer made no runner edits. The original numerical failures and fixes are separately recorded in `NUMERICAL_REVIEW.md`.

## Findings requiring closure

1. **Asymmetric repeated operator hashing.** `action()` hashes the task and operator for every arm. The factor branch hashes the full operator again inside `solve()`, whereas the update branch performs no equivalent current-operator comparison. This can make a retained native factor appear slower than Woodbury for an integrity-accounting reason rather than a numerical one. Bind each branch to the same already validated current operator digest and perform the same inexpensive identity comparison. Keep full WORLD hashing charged once, commonly, and retain its binding to the workbench receipt. Do not remove real provenance obligations from only the favored branch.

2. **Incomplete fallback after a rejected constructor.** On invalid C, the development code clears `state['update']` but leaves `use_update=True`. It consequently skips the conventional C fallback and later passes the old-operator parent to changed-operator D, causing `STALE_FACTOR`. A callback exception can also leave `got` empty and abort the campaign. Preserve unsuccessful construction and its cost, mark the candidate rejected, then use a separate funded fallback request or a declared terminal refusal. Failed results must never be retained or used implicitly.

3. **Maintenance workload mismatch.** The development restart condition runs only when an update exists. Native factor reuse therefore faces no corresponding memory loss. A declared restart must apply to every arm: CG can resume using its legitimate permitted state; native factors can load or rebuild at measured cost; low-rank factors can load or reconstruct at measured cost. The cheapest valid recovery path should be allowed, rather than mandating an expensive historical reconstruction.

4. **Post-failure denominator.** `offered=len(useful_recorded_rows)` is insufficient for interrupted or exceptional streams. The offered mission count must be declared by the regime independently of attempted/recorded rows. Preserve missing attempts and failures in qualified-coverage reporting; complete artifacts and summary even on a terminal error.

5. **Full-cost boundary.** The development total is sampled before final solution compression and several raw files are written. Those operations are attributable cost. The final record should include this measured tail, with the small self-referential final-summary serialization boundary described explicitly. A total CPU field must not silently omit the largest artifacts.

6. **Source identity.** The default all-zero source hash is a development placeholder. A confirmatory entry point must reject it, verify the actual frozen source/checker/dependencies before task generation and attach the real digest to every stream. A syntactically valid hash is not evidence of source verification.

7. **Rank is applicability, not economic benefit.** The rule `rank<=4` does not compare construction, per-use, persistence or maintenance costs against a strong alternative, and it ignores declared recurrence. It can serve as a scope bound only. A separately frozen product forecast is required.

## Cheapest useful construction opportunity

The development workflow always solves A by CG and then executes a separate workbench P action to build and check a native factor for the already answered load. P costs roughly50–80ms in the first development campaign, mostly orchestration and evidence, whereas the actual numerical factor construction is several milliseconds. A native direct solver can already produce both A's useful answer and its factor in the same service.

That byproduct is a competent inexpensive builder and must be considered before forcing an extra research phase. It is not necessary to spend an extra workbench transaction to make an asset appear newly created. Compare the first mission's direct specialist choices with the declared subsequent workload in mind, preserve all extra qualification costs, and give conventional systems the same opportunity to retain the byproduct. If CG followed by P remains the selected design, explain and charge its opportunity cost.

The development cost table also contains both COLAMD and MMD sparse orderings. Their justified choice should be frozen from development rather than selecting a slower ordering for the strong baseline or rebuilding a cheap equivalent solely as an ablation. Confirmation results must not select the ordering after the fact.

## Minimal prospective product forecast

A valid minimal design does not require new algorithms. Use the already bounded candidate set and the remaining declared development campaigns to estimate a small cost table for the registered size/rank regimes. Freeze it before confirmation.

For each available method, the table should separate:

- construction, integration and persistence;
- per-load solve and method-specific retrieval overhead;
- correctness checking and common orchestration;
- a declared restart, restoration/rebuilding and subsequent slower portable solves if applicable;
- maintenance and retirement costs.

For `N` declared remaining loads and an optional maintenance event, compare the projected **full future costs** of retained low-rank response, native refactorization/reuse and the competent iterative alternative. Let `F_m(N)` be a method's construction cost plus future uses and maintenance. Build a new asset only if its registered forecast has a conservative advantage, for example20%, over the cheapest qualified alternative, and it fits its improvement or released-capacity account. The margin must be fixed before confirmation; it is a guard against unstable small timing differences, not a confidence interval or a theorem.

After construction, distinguish three records:

1. Correctness: the exact candidate and applicable task passed the independent numerical checker.
2. Marginal product adoption: future use and maintenance are forecast worthwhile, with already spent construction retained as sunk cost in the separate investment record.
3. Investment assessment: realized accumulated benefit against the specified comparator covers the entire attributable development and lifecycle cost; unknown human and monetary costs remain unresolved.

If a constructor is already funded and fails to recover its construction cost, continued use may still be rational when the asset is valid and its marginal future cost is lower. Conversely, a correct low-rank asset can be rejected prospectively when a native updated factor is cheaper. Report both decisions without treating either as an inconvenient anomaly.

## Feedback account interpretation

The proposed transfer of unused accepted-service CPU allowance into a separate successor account is an explicit resource feedback mechanism. It is **released externally endowed quota**, not new compute, cash or automatically an improvement-caused saving. The equally enabled conventional arms must receive the same release opportunity, and the released amount cannot simultaneously remain in the service account.

Comparison against actual paired direct cost can establish incremental savings only after the new experiment, separately from the quota transfer. Shadow comparator execution is research compute and remains charged. A no-reinvestment arm that solves C by native refactorization still constructs a useful new factor as a service byproduct; it is an ablation of the low-rank reinvestment route, not proof that all useful construction requires that account.

Admission failures and resource exhaustion must preserve the current service method within its remaining scope. If an improvement-account overrun sets a global terminal hold, state that service is also stopped for accounting review; do not claim independent service continuity under that condition. The fixed finite kernel and a post-execution CPU account do not constitute operating-system preemption or a hard real-time SLA.

## Timing and causal pairing

The first development campaign shows a material difference between numerically identical flywheel and conventional-reuse arms. That is host/process timing noise, not a method difference. Confirmatory arm order should be balanced or randomized prospectively, and uncertainty should use independent streams. Costs should be reported both end-to-end and by solver/construction/checking/persistence category.

Mission C's update selection should record the actual accepted B08 task, receipt, output and deterministic edge-selection rule. Independent aggregation must verify that lineage, not accept an event label. Where two valid methods produce slightly different floating-point B outputs, verify whether the deterministic selected updates remain the same; report any genuine divergent changed requirements rather than silently copying the favored arm's answer to the others.

A primary claim of superiority over the best conventional approach must be defined before confirmation. Do not choose whichever comparator happens to be cheapest afterward without accounting for that selection. A fixed strong policy, or a prespecified simultaneous requirement across the relevant conventional arms, is auditable. An identical conventional implementation is expected to tie; that limits AGI-specific superiority claims without negating ordinary useful reuse.
