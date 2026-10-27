# Independent confirmation audit

**Verdict:** the bounded digital construction is supported on the declared finite test set. The expert operating checklist did not improve the primary acceptance count over competent ordinary use. Conventional methods remain sufficient after an explicit, separately recorded rounding correction. No discovery advantage, general Operational Alpha, customer acceptance, demand or complete-cost superiority is established.

## Primary evidence

All 98 files in `experiment/source_freeze.json` matched their hashes. All five evaluator-v2 source hashes matched. The protocol was frozen at 22:22:01 UTC; the three implementations froze at 22:30:53, 22:32:41 and 22:36:25; combined hashes were recorded at 22:40:20.056 UTC; the fresh bank was generated at 22:40:20.103 UTC. The known evaluator correction preceded fresh generation and did not change acceptance criteria.

The ordinary prompt is the complete common packet with only its assigned directory substituted. Expert and conventional prompts begin with the identical packet and then add their disclosed operating or method objective. Ordinary use was allowed planning, tools, verification and recovery. The conventional arm was allowed current Boost and arbitrary precision. The public report and log-domain recipe were supplied to all arms; their discovery credit belongs to the public source.

Independent rescoring agrees with the primary scorer: **64/64 accepted per arm**, comprising **56 numerical/endpoint requests and eight correct refusals**. Reference kinds were 51 numeric, three underflow, two endpoint, six invalid and two unsupported. This is one public mission with authored numerical cases, not 64 independent customer missions. All three recorded construction durations were below the 900-second allowance. Start timestamps are captured observations rather than a provider-attested complete execution trace.

Seventeen independent controls passed using separate Decimal500/Fraction equations: eight analytic inverses, four exact rational binomial-CDF enclosures, four closed-form Beta(1/2,3) enclosures and one Beta(1/4,2) underflow bound. These supplement, but do not turn, finite numerical validation into a global proof.

## Known post-confirmation failure and corrected comparator

The frozen conventional code still converted mpmath values directly to float. A specifically identified known midpoint regression was executed separately after primary scoring: q = 2^-1074, a = 1, b = 2. Ordinary and expert returned the correct positive minimum subnormal; the frozen conventional arm returned zero with `underflow` status.

The exact reason is inspectable. At delta = 2^-1074 and x = delta/2, the Beta(1,2) CDF is 2x − x² = delta − delta²/4, which is below the target delta. The quantile therefore lies above the rounding midpoint and rounds to delta. This case had already been discovered during development and is not a new blind confirmation case. It must not be added to the primary denominator or hidden behind the 64/64 result.

A separate conventional correction is preserved under `experiment/repairs/conventional_midpoint`. It uses 420-digit analytic evaluation for tiny probabilities and direct nearest-even subnormal lattice rounding, the same established technique already available in ordinary/expert work. Its replay passed **64/64 original cases plus the one known midpoint regression**. This is post-confirmation replay, not fresh confirmation. Recorded implementation-to-verification elapsed time was 23.10 seconds across two execution calls; model tokens and billing remain unknown. All original frozen files remain unchanged. No exclusive expert advantage follows because ordinary use also independently found and repaired the defect.

## Resource and causal limits

Raw CPU timings contain 33 exact-zero call measurements for ordinary, 63 for expert and 24 for conventional, despite nonzero elapsed wall times. The platform advertises a one-nanosecond clock resolution; the cause of the empirical zeros was not established. The common 163000-KiB peak-RSS measurement also cannot identify an arm-specific memory advantage. Do not infer a precise speed ratio or complete economic advantage from this tiny batch. Maximum observed per-call wall times were below 0.04 seconds in all arms, so bounded completion itself remains supported.

Tool totals also use differing conventions: the expert's 23 includes five communication calls; conventional's 13 counts execution/poll calls. Report raw manifests rather than an unnormalized tool-efficiency ranking.

The runtime model family label is not a provider-attested backend identity; temperature, token use and provider bills are unobserved. The conventional implementation was built by an assistant using established numerical methods, not by an observed human team. The reference evaluator received valid criticism from tested arms before confirmation. That correction is transparently preserved; the evaluator was not fully blinded to development feedback.

## Publication and reproduction

All 20 new top-level Python/C++ files in the original frozen arms lacked SPDX headers at audit time. Preserve those bytes as immutable research evidence. Any repository publication normalization should add headers only in clearly mapped copies, verify unchanged executable semantics, and retain original hashes. Corrected comparator sources already carry Apache-2.0 SPDX identifiers.

`python -B audit/independent_check.py` reproduces the hash audit, primary rescoring, 17 separate controls and labeled known regression. It writes nothing unless `--output PATH` is supplied. The known conventional regression is deliberately retained as a diagnostic failure, not silently patched by the audit. Separate repair verification is executable through `experiment/repairs/conventional_midpoint/verify_repair.py` after its recorded worker replay. The delivery engineering workstream owns clean rebuild and native integration verification.

Artifacts: `independent_preliminary.json`, `independent_confirmation.json`, `independent_known_midpoint.json`, `reproduction_independent.json`, `independent_check.py`, and the separately labeled repaired comparator directory.
