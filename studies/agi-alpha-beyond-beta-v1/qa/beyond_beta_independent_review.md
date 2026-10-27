# Independent Beyond Beta review

**Historical v2 development review, superseded by the paid-work v3 charter.** The findings below are preserved as written during development. The active review is `qa/paid_job_independent_review.md`. No v2 confirmation was executed.

Review scope: new lifecycle, its simulation coupling, full costs, and evidence claims. Development review before final protocol freeze; this file is not a substitute for the final test receipts.

## Findings raised before confirmation

1. **Initial Alpha admission must include research costs.** The first lifecycle version required positive prospective value but could admit a new record with negative full-cycle expected value after construction. Requested correction: first admission requires positive expected full-cycle net Alpha; reassessment of an actually previously admitted record can use positive future avoidable-cost value. A rejected candidate must not bypass the full-cycle requirement by calling reassessment. The distinction preserves historical research losses without imposing a sunk-cost fallacy on continuation.

2. **Execute and export need distinct API behavior.** The first capsule API accepted an arbitrary caller callback receiving plaintext. Returning that plaintext would bypass an export prohibition. Requested correction: trusted executor registrations belong to setup; public execution selects an allowlisted identifier and cannot supply arbitrary code. The threat model still excludes a privileged attacker who can alter process memory or trusted executor implementations. This is a local research service, not a production sandbox.

3. **Policy bindings must survive mutable Python objects.** The initial policy/registry attributes were externally mutable despite a stored policy hash. Requested correction: defensive immutable/copying access or consistency checks, with authorized versioned update methods. Tests must ensure a changed dictionary cannot silently weaken a bound admission rule.

4. **Evidence hierarchy.** The exact assignment/flow prototype belongs in the appendix as a bounded local witness. Its 300 successful synthetic cases, and the unrestricted solver's identical results, cannot calibrate frontier semantic accuracy or establish net Alpha. The core new implementation is the lifecycle coupled to the network simulation. Its admissions are explicitly modeled, not operationally validated capabilities.

5. **Price, demand and project unit.** The human-team rates are published; matched effort is assumed. Full project fees apply to new buyer/deployment or new schema/integration contracts. Ordinary changed inputs in an installed parametric engine do not create a new full-price sale. Buyer response remains an assumption and is tested through thresholds and stresses.

## Final disposition

This edition was superseded before confirmation. In particular, finding 1's proposed construction-inclusive first-admission hurdle is **not the active v3 rule**. The latest paid-work framing correctly separates the pre-spend capital decision from prospective admission: source-job construction remains charged once in A, new retention spending is evaluated before commitment in B, and remaining future benefits are compared with remaining avoidable costs at admission or reassessment. Historical expenses remain in complete profit without being charged a second time. This clarification preserves the earlier reasoning rather than silently replacing it.

The execute/export and mutable-policy findings were corrected and tested; the v3 lifecycle receipt preserves exact source/test hashes. Final v3 accounting, resource and confirmation dispositions are in the active review and its linked receipts.
