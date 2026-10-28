# Scoped compiler review — final freeze v1

This review is limited to the additive `contrib/production_frontier` research compiler at parent commit `96a417cadcbb1d2e6887e9f7cedb0b59e5e129dc`. No production, worker, release, hosted workflow, wallet, provider, or held confirmation behavior was executed. No repository source was edited by this reviewer. The review used the assigned session reasoning model; an exact provider snapshot and billing are unknown. This is not a paid matched-provider experiment.

No blocking findings remain in the reviewed additive scope at freeze v1. The final manifest SHA256 is `610626444f6388241e13e759d27e8e6f8898da7d1e1ad2b31330fc09ff40defd`. All 100 frozen files, the full expected inventory, and the manifest digest matched before and after final tests/probes. HEAD remains the exact parent and tracked source remains unchanged. `final-freeze-precheck.json` and `final-freeze-postcheck.json` retain those checks.

The source changed during review, and no old pass was transferred to a later revision. The initial pass is bound to `source-hashes.json`; the first correction pass is bound to `followup-source-hashes.json`; the controlled comparisons carry their own source hashes in `controlled-parity-results.json`. The final pass is bound to the manifest above. Any later scientific source or input change requires a new freeze, new confirmation campaign, and renewed review.

Final engine SHA256: `4e20d39235776ba6c0c11e1617fbbefeecf8267243aa2fcdc46be213b728eb94`.

Final verifier SHA256: `690194df60ec32d38e601ba8d76969ccd657b02e3666e062edece394f91dc864`.

## Reproduced findings and corrections

| Finding | Reproduction | Observed correction |
| --- | --- | --- |
| Report-envelope claims bypassed witness verification | `probes.py` accepted forged physical-truth scope, extra retained-Alpha claim, missing/invalid candidate counts, duplicate candidates, and string steps | Strict result/witness schema and exact report checks reject these in `followup-probe-results.json` |
| Shallow frozen input mutation bypassed conservation validation | Mutate a nested recipe consumption to `-1`; compiler rejects, while initial replay/verifier accepted ore increasing from 1 to 2 | Verification and replay now revalidate a canonical snapshot; follow-up probes reject the mutated model |
| Write-once freeze followed a dangling destination symlink | Existing symlink target did not yet exist, so `exists()` was false and `write_text()` created the target | Exclusive `open("x")` rejects the symlink without creating its target |
| Valid capability union exceeded the first result-schema bound | Seven legal recipes providing 24 distinct capabilities each plus 24 initial capabilities produce 192 | Bound expanded to the legal maximum of 312; follow-up witness verifies |
| Caller scale declaration could establish credibility | Initial static `scale_audit()` set credible billion-plus from `verified_inputs=True` and arithmetic alone | It now returns credibility false, names the declared-evidence condition separately, and discloses no independent adjudication |
| Large legal scale output violated commitment integer bounds | Legal inputs yield `20000000000000000000000` micro-USD, which canonical commitments reject as a JSON number | Final output is an exact decimal string and passes canonical serialization |
| Offered best could ignore a cheaper offered candidate | Swap first two candidates and reassign best; initial result accepted 9.9B cost despite an offered 6.7B witness | Final result validation requires rank-sorted candidates; the forged report is rejected |
| External JSON allowed duplicate original-obligation keys | Pydantic JSON parsing silently selected the later obligation list; strict protocol parser rejected the same bytes | CLI uses existing `load_record()` and bounds policy input size; both brief and policy duplicate-key regressions pass |
| Optimized Python removed runtime acceptance checks | Static confirmation/economics gates used `assert`, but optimized execution removes assertions without changing frozen source bytes | Both modules now contain zero runtime assertions; the optimized-Python economics forgery regression raises `ValueError` |
| Conditional ranking ignored declared liquidity | A positive expected-profit model could outrank stop despite insufficient modeled cash | Ranking now filters on `liquidity_feasible`; positive but unfunded regression returns stop |

Exact original and follow-up outputs are retained beside this file, including `rank-forgery.json` and `duplicate-json-probe.json`. These records show historical findings; they must not be described as defects remaining in a later revision without rerunning them against that revision.

## Positive evidence and limits

The final frozen revision passed all **78 new contrib development tests in 4.03 seconds**, recorded in `final-contrib-tests.xml`. This includes new pure research/economic unit tests, malformed-manifest refusal before confirmation, duplicate-key CLI refusal, and optimized-Python acceptance refusal. No held confirmation seeds or existing native behavior campaign were executed by this reviewer.

Final boundary probes are in `final/followup-probe-results.json` and `final/boundary-results.json`. They reject all original report/input forgeries and the dangling destination symlink, preserve exact large arithmetic, keep caller-declared credibility false, and accept the maximum legal 312-capability and 1,300,000-stock witness. The maximum-bound probe uses a twelve-step mandatory chain with only thirteen visited states. The one-letter recipe probe confirms that a string step cannot masquerade as a list.

The initial 60 new contrib tests passed in 2.30 seconds; `contrib-tests.xml` records that earlier exact run. A further 200 tiny generated structural graphs matched the independent exhaustive comparator. An additional 200 controlled comparisons varied disabled recipes, conventional-only filtering, and original-obligation eligibility with no rank mismatches. These earlier comparisons used at most five recipes per generated instance and did not run confirmation seeds. Their historical hash bindings remain explicit; final review also inspected the unchanged search logic at its final hash.

The subset cache is justified by the declared model: each feasible subset has order-independent additive balances, monotone capability union, cost, elapsed time, and permission/component counts. Sorted breadth-first expansion retains the lexicographically first feasible ordering. Backward relevance is conservative because every prerequisite resource/capability of a selected recipe is traced; positive step durations and nonnegative costs prevent discarded irrelevant recipes from improving the objective. This reasoning depends on the finite, single-use, sequential, additive grammar and would need revisiting for capability revocation, stochastic yields, concurrency, or order-dependent costs.

The existing live adapter is a direct pass-through to the established signed connector boundary, with no exception recovery or simulated fallback. The unavailable-connector path reports blockers and raises. Only the unavailable path was exercised by the new tests; no live connector was run.

Witness verification establishes the supplied witnesses, not exhaustive completeness or global optimality. A manifest is not self-authenticating: the caller must retain its trusted digest and exact inventory separately. The new confirmation wrapper statically supplies both checks. Declared source hashes and labels do not establish physical truth, buyer demand, rights, commercial acceptance, retained Alpha, or deployment permission.

## Confirmation and authorization limits

The confirmation runner checks an externally retained manifest digest, the exact source/input inventory, and raw file hashes before the campaign; it rechecks frozen file bytes before emitting its final summary. Runtime evidence gates use explicit exceptions. The prospective campaign itself was left to the parent task, so this review makes no claim about its outcome. Files emitted before the final summary should be treated as provisional unless the final summary and matching freeze check are present.

Commercial outputs retain HOLD, unknown actual costs/profit/cash, zero actual receipts, and no investment authority. Hypothetical scale and recipe evidence do not establish a real buyer, a billion-plus opportunity, physical production, Operational/retained Alpha, live frontier access, or deployment readiness. Session reasoning configuration was a review resource, not evidence of a matched paid frontier-provider experiment.
