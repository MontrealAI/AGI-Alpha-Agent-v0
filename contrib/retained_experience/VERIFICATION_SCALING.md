# Verification cost diagnostic

This additive experiment measures a specific unresolved cost in PR #5024. It
does not change the candidate, numerical checker, accounting ledger, runtime
defaults or frozen historical evidence. Its input is the preserved 64-case,
ten-arm, three-repeat panel at evidence seal
`a1eee42f8701ebceaa53b88d1f59fd15744121317ce1fcb0df1213529295736c`.

The input tasks are already exposed. Derived balanced subsets contain 4, 16 and
64 historical tasks. Each subset retains all ten methods and all three timing
repeats. Neither repeats nor subset overlap creates additional independent work.
No scientific confirmation allowance is allocated or reset.

## Run

Use the existing supported Python development environment and Linux seccomp.
This diagnostic itself needs only Python's standard library and the existing
checker/filter. It does not need a model, network service, wallet or Docker.

```sh
python -m pytest -o addopts='' contrib/retained_experience/test_verification_scaling.py -q
python -m contrib.retained_experience.verification_scaling \
  evidence/retained-experience-20261029/prospective-v1 \
  --seal-sha256 a1eee42f8701ebceaa53b88d1f59fd15744121317ce1fcb0df1213529295736c \
  --output /tmp/NEW-verification-scaling --samples 3
```

Existing output paths refuse. Preserve the printed output seal separately.
Partial results and process transcripts remain if a check refuses. The campaign
allows three samples per mode, a 120-second subprocess limit, a 900-second total
deadline and a two GiB free-disk reserve. These ceilings do not renew any broader
campaign allocation. No paid call or external transaction is performed.

The input seal and every archived source hash are checked before execution.
The archived verifier, Decimal checker and kernel filter must match the current
trusted implementations. Unchanged archived source runs in a separate process;
it qualifies that archived reproduction, never a changed current runtime.
The metered process adds delegating timing wrappers around the original output
and memory checks. Both processes must actually refuse writes and new sockets,
must not import the candidate, and must agree on every acceptance decision,
denominator, output hash and memory identity. No acceptance threshold is reduced.
Source and evidence identities are checked again after measurement.

## Interpret the costs

Raw native timings remain authoritative; metered timings contain wrapper
overhead. The report preserves the ratio and all timing observations. Process
CPU includes startup. Named native output-check CPU and separately measured
historical-output, development-comparator and memory-check CPU remain distinct.
The remaining cost is unclassified and is never silently called fixed or zero.

Historical validation is fixed with respect to the delivery count **within one
audit of this exact history**. It recurs for each full audit or process restart.
The existing source interface admits at most 64 tasks per panel. Projecting a
single audit's fixed cost across an unrestricted lifetime is not a demonstrated
deployment policy. Batching, persistent verified state and any future workload
require their own source-bound acceptance and measurement.

This diagnostic can identify where to investigate. It cannot promote retention,
establish human effort savings, resolve full monetary costs, validate customer
demand, turn seed capital into earnings, or authorize reinvestment. Preserve the
original negative lifecycle finding and the conventional default. A commercially
successful simulated flywheel still needs causal benefit against the strongest
complete means, accepted delivery, complete-cost profit, unrestricted earned
funding, new capability construction and fresh successor benefit.
