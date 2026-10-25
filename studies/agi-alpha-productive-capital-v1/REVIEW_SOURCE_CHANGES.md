# Formatted review copies for source PR #4909

These 19 files are a new presentation of the browsable `review-source/` tree, based on head `c9813094a012748662a18e7513e9b23bc254584a`. They are not replacement frozen scientific sources or a second executable distribution. The complete canonical companion archive remains byte-for-byte unchanged.

## Exact scope

`MAPPING.json` lists each remote repository path, original archive SHA-256, formatted SHA-256, byte counts and transformation rationale. Only listed Python files should be uploaded from this staging directory. No lint rule, configuration, extension, workflow, exclusion, permission or gate was changed. Comments, license identifiers and all right-hand evaluations are preserved.

Black 25.1.0 (line length 120, Python 3.11 target) reformatted all 19 files. That formatting alone preserved the complete AST of every file. Nine identifier changes then addressed unused or ambiguous bindings; a local `req` lambda became a named closure with the same arguments, captured values, return expression and side effects. Reversing only these declared transformations restores every original AST exactly.

Unused bindings were renamed with an underscore, retaining their original evaluations. This specifically preserves both `a.integer(...)` validation calls in the copied native checker. The paper's ambiguous `l` bindings are now `loaded_rate` and `ledger_row`. The lambda-to-function change alters function introspection/traceback naming from `<lambda>` to `req`; this helper is not inspected or serialized by the program. Variable names also differ in hypothetical `locals()` inspection; the affected scopes do not perform that inspection.

## Verification

- Local Ruff 0.12.3, using the unchanged repository configuration: zero findings across the 19 files. Hosted CI uses Ruff 0.12.5 and remains authoritative; its new-head result is not claimed here.
- All 52 economic scenario/policy runs retain identical business outcomes. `events.jsonl`, `ledger.csv` and `family_results.csv` are byte-identical. The four JSON outputs differ only in their truthful `provenance.engine_sha256` value for the formatted copy.
- The changed named closure passes the complete saved-evidence audit: 15,127 assertions.
- Original and formatted native checkers return identical receipts for 72 saved plans and 144 invalid numeric perturbations: 216 comparisons.
- Original and formatted paper generators produce 14 identical textual assets. Binary plot bytes are not used as a semantic equivalence claim.
- Final companion ZIP remains SHA-256 `293db5a4ea0ef5ff44bfe3d3f73ca33afc7f603e4e750b8e2eb8366262c1cda5`.

`VALIDATION.json` records these checks and their limits. The first differential check assumed source provenance appeared only in the economic summary; it was corrected to account for the same source identity in all four JSON outputs. No model behavior was changed to resolve that verification-harness assertion.

## Suggested publication wording

Describe the tree as **selected formatted review copies**, linked to the **unchanged exact executable/frozen sources in the complete archive**. The review tree is not independently runnable. Its displayed freeze records describe canonical archive members, not reformatted presentation copies.

The root publisher should update the study README and SOURCE_INDEX to distinguish original and formatted identities, include this mapping/receipt, push only the listed review copies and await the unchanged hosted gates. This staging work did not mutate the remote branch or assert full software qualification.
