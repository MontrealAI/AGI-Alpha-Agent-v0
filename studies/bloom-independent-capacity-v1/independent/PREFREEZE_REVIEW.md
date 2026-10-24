# Independent preconfirmation source review

Scope: fresh release-impact study only. The reviewer inspected source and protocol, plus development fixtures; no confirmatory or reproduction cases were generated or inspected. This is same-session independent code/method review, not external organizational review.

## Findings raised before the freeze

1. **Portable execution was only an in-memory deepcopy.** This omitted an actual serialized restoration boundary and its parsing costs. Requested canonical JSON export/import with measured I/O/serialization phases.
2. **Authority-revoked trial stopped before creating a predecessor.** This did not test a restored predecessor failing to confer active receiver authority. Requested legitimate predecessor creation followed by receiver refusal.
3. **Component-outage semantics were ambiguous.** Availability was consulted only during reconstruction. A valid prebuilt data operator needs no constructor to run; requested an explicit constructor-outage interpretation plus a separate withheld-and-outage intervention.
4. **Missing replacement silently reused the original.** Requested an explicit error when a replacement treatment lacks its replacement artifact.
5. **Environment identity omitted the independent checker.** Requested its source hash alongside the runtime kernel hash.
6. **Replacement artifact production could be free in total-cost reporting.** Requested separately measured construction/qualification provenance and ledger reconciliation.
7. **General zero-cost lexical tie bug in the candidate coverage DP.** Keeping one lexical winner per partial exact-coverage state can discard the eventual lexical optimum after more tests are added. Counterexample: a covers A,B at cost1; b covers B at cost0; c covers C at cost1. The required lexical optimum for A,B,C is a,b,c at cost2. Requested a tie-safe implementation or a declared positive-cost experimental policy with explicit refusal of zero-cost inputs. The independent oracle remains general and tests the counterexample.
8. **Strategy/certificate label binding.** Requested an explicit allowed strategy-to-certificate mapping so a semantically valid certificate cannot falsely label which operator executes.
9. **Ablation scope.** Disabling only receiver proof still leaves other operational output checks. Requested the precise label receiver-proof ablation rather than claiming all verification was removed.

## Parent-reported intended corrections

Before confirmation, the lead accepted findings1–6 and specified: real canonical restoration; receiver-level authority revocation; explicit constructor-outage plus withheld-outage; absent-replacement error; separately measured replacement receipt; independent-checker environment identity. The policy-change arm will remove test t00 from eligibility, making the change operationally meaningful. The protocol now explicitly requires positive synthetic test costs and labels the receiver-proof ablation.

These are intended corrections pending exact-source verification, not a completed final review.

## Strong-comparator improvements completed before freeze

The independent policy now includes reverse traversal from each application, constructing all-node app masks in O(applications × (nodes+edges)). It has equal access to walk, memo, SCC and Warshall. Planning-memory estimates do not remove strategies; the common wrapper enforces actual canonical bytes and charges failed construction/fallback.

Independent operational proof checkers validate both SCC condensation certificates and reverse path-witness certificates. Thus the reverse competitor is not forced to pay for SCC decomposition. The original per-source BFS and brute-force finite-cover solver remain separate research oracles.

The new efficient independent finite-cover checker enumerates each complete test subset once. It matches the unchanged original solver on all64 masks of a six-application development fixture and on the zero-cost lexical counterexample. Fifteen independent development checks pass.

## Protocol quality-gate review

The current G2 definition uses every authorized, well-formed, complete-graph trial in its declared strata. It requires100% correct task resolution, including explicit correct infeasibility; an unexpected refusal does not count as resolution. Exact accepted answers, corrupted-artifact rejection, authority refusal and malformed-input refusal have distinct denominators. Incomplete observed graphs are evaluated separately against the full graph and are outside the supplied-graph exactness guarantee. This is an interpretable quality gate, provided the runner implements these denominators literally.

The confirmation factorial is48 worlds (4topologies ×4sizes ×3query counts); the fresh reproduction factorial is24 worlds (4topologies ×2shifted sizes ×3query counts). Graphs are the inferential units; repeated query/timing runs are not extra independent samples. G3's two superiority contrasts and G4's one causal timing contrast use one predeclared multiplicity family. CPU, wall time, serialized bytes, diagnostic operations and monetary assumptions remain distinct.

## Final source/runner review and remaining development execution

The lead's corrected source visibly implements the nine requested boundary clarifications, actual serialized restoration, checker identity, legal constructor availability, and distinct reverse-verifier counters. Operational latency includes producer, receiver, proof checking and successor checking. The research BFS/brute-force audit executes outside per-method latency and is included in campaign CPU totals. Replacement creation is measured once per world; its attributable cost is referenced on every replacement counterfactual without multiplying actual campaign cost.

The reviewer independently ran the requested remaining development seeds103–112 with the exact runner. Ten worlds produced530 records, zero verified failures,30 correct authority refusals,30 correct malformed-input refusals and470 completed executions. All ten unsafe receiver-proof ablations produced incorrect answers, preserved as diagnostic outcomes. Measured campaign CPU was3.37239189seconds, including0.423475748seconds of external audit and0.025185202seconds of separately measured replacement construction/qualification. Evidence bytes before manifest were492,000. All five audited source hashes remained unchanged during this execution. Exact receipt: independent_baseline/dev_v2_rest_execution.json.

Deterministic record-stream SHA-256: a2fb73e215f61fe9502c603e4e3f571632bc35d5fc93c5bb5ed79d4f83e1a1a2.

Final analysis/runner findings sent before confirmation:

- Verify the complete expected key multiset and ledger counts. Observed rows alone cannot establish complete G2 denominators; missing robustness rows could otherwise disappear.
- Missing or failed primary/withheld observations must yield explicit FAIL/INCOMPLETE instead of an uncaught median or absent-field exception.
- G2/G4 need explicit stale/corrupted-artifact rejection checks, not just final-answer equality. Coincidentally unchanged answers cannot validate an outdated world/policy receipt. Conventional replacement acceptance should be distinguished from fallback reconstruction.
- Rename the misleading primary_cpu_seconds_by_world field containing nanoseconds, or convert its values.
- Reconcile the1200CPU-second cap across development, confirmation and reproduction because the runner initially enforced it separately per campaign. Preserve per-campaign and accumulated figures without adding external-audit subsets twice.

The median-within-world pairing and geometric-mean ratios are correctly ordered, and the three fixed bootstrap seeds/Bonferroni interval family match the protocol. Deterministic record serialization removes timing fields while retaining semantic/source identities and recorded decisions. Final closure of the remaining findings requires reviewing the exact revised source; no confirmation or reproduction case was inspected.
