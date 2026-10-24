# Writer 10: adversarial experimental-design review

This is advice before the root's final experimental specification. No outcome is assumed. It is not an independent execution result.

## Required design choices before evaluation

1. Define one primary objective, one horizon and one paired comparison. Useful output should be validated by the same external evaluator for every baseline. Track true simulated valid completions, deadline utility, and integrity of accepted receipts separately. Do not set the disclosed implementation's productive output to zero simply because it lacks the incumbent's receipt format.
2. State the world model fully: job releases, deadlines, processing times, values, calibration activation duration, validity window, switching costs, failures, and drift. Every comparator receives the same observed information at each time. If the expert can see the entire future, call it a hindsight bound; it is not a matched online competitor.
3. Hash the frozen specification and code before held-out results are inspected. Separate development seeds from held-out seeds; record any amendment with reason and timing. Bug fixes are allowed but invalidate a claim of untouched preregistration if they change the tested method. A local preregistration is a timestamped internal commitment, not independent external preregistration.
4. Declare compute/time limits for all methods on the same machine. Log failures and timeouts instead of silently dropping them. A stronger expert can use exact optimization on tractable problems, but charge its search work and provide both runtime and objective.
5. Include an actual full copy with independent installation/execution, fresh keys, current data, equivalent resource access, and equivalent mission authority. Also include a separately implemented expert builder where feasible. An exact source clone is an appropriate existence witness for copyability, but equality from identical deterministic code is expected, not a new scientific discovery or independent reimplementation result.
6. Report copying/setup wall time separately from operational compute and human construction time. Package extraction on a warm machine is a lower bound on real deployment effort. No measured seconds-to-copy result supports a market catch-up prediction without additional evidence.
7. Use paired seeds/common random numbers for comparisons. Predeclare a practically meaningful superiority or equivalence margin. Report paired bootstrap intervals across independently generated workload instances, and avoid treating thousands of jobs within one run as independent replicates. Exact equality in deterministic matched traces can be reported directly; a nonsignificant result alone does not establish equivalence.
8. Plot cumulative valid utility and per-window output for the full horizon, including the planned drift event, not only a final total. Specify whether the competitor enters at an exogenously assigned time. Any pre-entry incumbent benefit depends on that assumed delay.

## Perturbations with causal interpretation

- Capacity expansion: compare equal-cost choices between improved allocation and added simulated capacity. The dollar cost of a second instrument is not measured by the simulator; use a sensitivity threshold.
- Substitute service: apply the same accuracy/utility requirements. Relaxing quality only for the incumbent or competitor invalidates comparison.
- Demand drift: alter job mix or value without exposing it early to one participant. Separate policy adaptation from already knowing the test scenario.
- Measurement drift: use equally available calibration observations. An omniscient simulated oracle may evaluate truth but must not feed only the incumbent.
- Reliability failures: expose both runs to equivalent event processes, with retries/time loss charged. Report failure cost rather than counting discarded evidence as avoided physical execution.
- Evidence attacks: test payload mutation, stale mission replay, wrong authority, duplicate jobs, false durations, invalid calibration, and internally coherent false source observations. The last may pass if no trusted external sensor exists; that negative result is essential to describe the trust boundary honestly.

## NFT-removal counterfactual

Preserve exact scheduling, resources, evidence schema, validators and signature security when replacing local-EVM storage/ownership records with an off-chain signed registry. Compare registry costs separately from service execution. A local chain is not evidence of public-chain finality, censorship resistance, multi-party independence, or transaction price.

An off-chain signed log can authenticate issuer, bind payloads and reject replay when the verifier has a known state. A central operator can still equivocate or withhold history unless another mechanism exposes forks; a local EVM operator can also reset or present alternate chains. Explain both assumptions symmetrically. Do not ascribe public decentralization properties to a local EVM experiment.

## Limited disclosure

Use synthetic payloads under identical legitimate access rules. If the branch uses AES-GCM, require fresh nonces, separate keys and tamper rejection; explicitly label public metadata and ciphertext length leakage. Use no secret-dependent claims when all keys are published. A blinded outsider can check commitments and signatures but cannot validate withheld job semantics. If no confidentiality primitive is implemented, label the branch access limitation only and make no confidentiality claim. Demonstrate a small-domain hash dictionary attack as a boundary test if claiming that commitments hide information.

## Economics

Report measured CPU/wall time, bytes, verification latency, algorithmic work counts, local EVM gas and failed/retried operations as distinct units. State attributable model/API cost if observed; otherwise unknown. Human research/engineering time, opportunity cost, actual instrument cost, demand and willingness to pay remain unknown unless measured. Simulated job value units are not dollars; assigned prices produce modeled revenue, not settled proceeds. Do not call a difference in objective utility profit.

Define private advantage relative to the strongest available matched alternative after copying. If clone or expert matches/bests the artifact, report zero/negative residual advantage and retain any public productive gain versus weaker baseline as a separate result. A high-cost expert may have better utility but worse net utility under a cost model; show the threshold that reverses this ranking without pretending the cost coefficient was measured.

## Draft-level audit blockers

Before publication, check that the paper never: (a) labels replaying the same schedule an independent rebuild; (b) denies a competitor current inputs; (c) counts verification as physical truth; (d) counts failure rejection as extra completed work; (e) maps hypothetical price to real profit; (f) calls passing repository tests an end-to-end integration; (g) treats calibration batching or nonrival knowledge as a new economic law; or (h) represents source-only local contract execution as public-chain deployment evidence.
