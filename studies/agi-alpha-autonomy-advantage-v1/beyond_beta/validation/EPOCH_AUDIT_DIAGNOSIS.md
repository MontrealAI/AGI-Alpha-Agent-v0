# Post-freeze independent auditor diagnosis

The frozen auditor and all economic histories remain unchanged. The original training report is FAIL: 51 of 1,728 histories stop at `New relevant admission cannot be bypassed`. The original confirmation report is PASS for all 4,560 histories.

## Minimal counterexample

Training record index 136 (line 137), `policy-02 / high-repeat / efficient / seed 1 / network-alpha`, contains `job-33-1`, completed at week 36. The exact historical graph prefix includes a `BETA_ADVANCED` event at week 26 (event 12), followed by a contracts `CANONICAL_ADMISSION` at week 33 (event 30). The permit and signed admission carry comparison epoch 2. The frozen graph increments every declared function's comparison epoch for a Beta update and increments the relevant function for an admission, so 1 + 1 = 2. The frozen auditor counted only relevant admissions and inferred 1.

The separately authored native/source review independently confirms this counterexample in `native-temporal-source-review.json`.

## Narrow diagnostic

`audit_epoch_diagnostic.py` verifies the exact frozen auditor SHA-256 and replaces one arithmetic expression in memory. It adds preceding `BETA_ADVANCED` and `POLICY_ADVANCED` events to relevant canonical admissions. It refuses any inventory update whose function-specific effect cannot be reconstructed from the retained log. No inventory/policy event is silently assumed or guessed. Every other original accounting, signature, freshness, access, capacity, cash and source-binding check executes unchanged.

Eight designed controls check the initial epoch, Beta advance plus admission, stale epoch refusal after Beta advance, stale epoch refusal after a competing admission, unrelated-function handling, policy increments, revocation history and refusal of ambiguous inventory updates.

## Recorded results

- Original training audit: FAIL; 1,728 histories read; 51 epoch flags preserved; 1,677 histories finish all checks.
- Original confirmation audit: PASS; 4,560 histories; 7,471,202 completed checks.
- Separate training diagnostic replay: PASS; all 1,728 histories; 5,796,284 checks; 690 historical reuse receipts. All 51 flagged worlds and 529 affected use checks are explained exactly by the epoch arithmetic omission.
- Separate confirmation diagnostic replay: PASS; all 4,560 histories; 7,471,202 checks; 56 historical reuse receipts; zero changed epoch classifications.
- Combined diagnostic replay: 6,288 histories, 13,267,486 checks, 746 reuse receipts.

No economic world was generated or modified. No policy selection, price, workload, accounting value, acceptance result or training choice changed. This is a post-freeze instrumentation diagnosis, not a new confirmatory experiment. The original failed audit is retained and must be reported alongside the diagnostic result. Passing audits establish internal trace consistency under the declared simulation and fixture rules; they do not validate real customer demand, actual model competence or commercial performance.
