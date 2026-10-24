# Post-study reporting deviations and clarifications

This post-study note preserves frozen protocol, source, cases, analysis and thresholds. It records discrepancies found during manuscript/economics review and makes no new confirmatory claim.

## D1. Missing-edge challenge is stronger than frozen prose

PROTOCOL.md says the challenge removes an edge. Frozen core.py removes every incoming edge to the last app; generate.py ensures source0 has a direct edge to that app and that the first query contains source0. False-safe counts therefore describe an intentionally adversarial all-incoming-edge removal, not random single-edge deletion or ordinary omission prevalence. All methods share the challenge, excluded from in-scope quality and primary timing. Frozen implementation and data remain unchanged.

## D2. Native overhead is outside scientific campaign timers

Protocol prose says separately measured native overhead is included in campaign cost. run_study.py does not invoke the native dispatcher in scientific trials, so campaign.json excludes five separately executed native journeys. This reporting ledger includes their 6.198259305 CPU seconds in the documented project subtotal and retains the 47.887703197-second scientific/development campaign subtotal. No native overhead is silently amortized per query. Primary timing is not the complete seven-stage native runtime.

## D3. Promised descriptive conventional oracle was not derived

Protocol promises an optimistic best-observed conventional bound. Frozen analyze.py exposes paired median arrays and separate references but no per-world minimum. ECONOMICS_SUMMARY.json now derives that descriptive minimum from unchanged arrays. It is not a deployable policy, its selection cost is unknown and no interval, test or threshold is added. Original analyses remain byte-identical.

## D4. Earliest development calls have incomplete raw retention

development/v1/INITIAL_SMOKE.json retains command, seed101, exit, choices and three CPU observations totaling 0.180152431 seconds. Full return values were not serialized. Exact source/generator/reference versions remain. This limitation is disclosed without inventing missing records or promoting development to confirmation. Later version2 trials have full retained raw records.

## D5. Value-per-use sensitivity grid was not specified or run

Protocol prose promises CPU-price, engineering-hour and value-per-use sensitivity. Frozen analysis implements CPU prices and engineering hours but no value-per-use grid. No supported demand/value was obtained. This report discloses the omission instead of inventing willingness to pay after results. Common value cancels in the equal-quality comparative formula; full monetary viability stays incomplete.

## D6. Original G1 status and later evidence closure differ by design

Frozen analyze.py emits PENDING_INDEPENDENT_REPLAY. The later independent receipt closes G1 after exact deterministic case/operator/record/source comparisons. Publication may report the later PASS while linking original pending analyses and the later closure; it must not edit originals retroactively.

## D7. Budget scope excludes unmetered surrounding work

The automatic 1,200-second guard sums completed campaign.json receipts under development/results. It excludes three early summary-only calls, native integration, human/model authoring, analysis/bootstrap/reporting, retrieval and publication. This ledger adds separately metered early/native work to reach 54.266114933 documented CPU seconds and flags other compute/costs unknown. The guard is a scientific-execution envelope, not a complete project CPU or monetary budget.

## Controls

- Frozen source/manifest hashes remain unchanged.
- Original confirmation retains primary timing status; replay timing is separate.
- Replayed worlds, native stages and development do not enlarge scientific sample size.
- Audit/replacement/nested timers and duplicate archived receipts are not double-counted.
- No new cases, threshold, confidence interval or hypothesis test is introduced.
