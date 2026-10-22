# SUCCESSOR Ω Harness

[Research-prototype disclaimer](../DISCLAIMER_SNIPPET.md)

**Activate. Evolve. Scale.** A thin launch interface over the existing SUCCESSOR
runtime, not another service or agent framework. It launches the maintained local
workbench adapters, keeps each enterprise's request and execution in the same signed
journal, and derives new configurations from an explicitly accepted parent.

## What runs now

Five fixed work families: reliability, performance, documentation, public-data and
numerical. These execute actual bounded local computations and produce inspectable
artifacts. They do not execute arbitrary uploaded code, call a paid model, create a
legal company, collect revenue or imply independent qualification. A successful local
result still awaits an explicit result-bound review.

Requires the installed `alpha-agent` package and Node.js 22+. No wallet or paid account
is required for the local path. Examples use synthetic/public inputs; edit the `work`
fields to an admitted input before activation. The configuration has an immutable UUID.
Changing a running configuration is refused; derive a new enterprise instead.

## Activate and operate

```sh
alpha-agent successor-harness new numerical --name "Quadrature service" --output enterprise.json
alpha-agent --home ./operator successor-harness activate enterprise.json
# Copy the enterprise_id printed above as ENTERPRISE_ID below.
alpha-agent --home ./operator successor-harness operate ENTERPRISE_ID
alpha-agent --home ./operator successor-harness show ENTERPRISE_ID
alpha-agent --home ./operator successor-harness export ENTERPRISE_ID --output ./inspection
```

Inspect the output artifacts, stated limitations and result digest. Accept or reject
that exact result; acceptance is an attributed local decision, not independent proof:

```sh
alpha-agent --home ./operator successor-harness review ENTERPRISE_ID \
  --result-digest RESULT_DIGEST --decision accepted --note "Inspected exact artifacts and limitations"
```

Repeated `operate` on completed work reads the retained result instead of executing
again. Different IDs remain isolated. `control --state paused` interrupts ongoing work;
`operate --resume` explicitly resumes interrupted/paused pure work, subject to the
existing three-attempt limit. `control --state stopped` and `retired` are terminal.
Use a new enterprise for a fresh mission. The existing operator-wide pause also applies.

## Evolve without claiming unmeasured improvement

```sh
alpha-agent --home ./operator successor-harness derive ENTERPRISE_ID \
  --name "Next quadrature service" --output successor.json
```

This reuses the accepted parent's editable work template and records its exact
configuration and result digests. Edit the new work inputs, then activate and operate
the successor normally. Use `--work another-work.json` to select a different admitted
work specification, including another family. Each successor starts planned, with no
result, acceptance or external permission. It must earn its own review.

Template reuse is not proof that capability or intelligence improved. The harness
preserves the comparison inputs and each run's actual costs; compute and human costs
remain unknown where the existing worker cannot measure them. It does not automatically
promote code, modify a running enterprise, or claim RSI, speedup, profit or population
scale. Compare actual accepted outcomes before calling a proposed change an improvement.
A Cambrian-scale family is the direction; the local examples do not establish it.

## Existing repository adapters

```sh
alpha-agent --home ./operator successor-harness adapters
```

This reads the existing installed Studio profile status without contacting the network.
It reports the free local path and the companion roles: Fleet execution/review,
AGIJobsv0's AGIALPHA route, and AGIJobManager's separate USDC route. Listing a route is
not evidence of a connected, commissioned or funded service.

For an independently prepared compatible Ascension plan, produce the *existing*
Studio request, not a new bridge protocol:

```sh
alpha-agent --home ./operator successor-harness handoff ENTERPRISE_ID \
  --plan compiled-plan.json --index 0 --output studio-request.json
```

The existing plan verifier checks its structure. This binds the exact enterprise work
specification to that plan index with the enterprise UUID as project/cycle identity.
The `successor-cycle` interface owns prepare, seal, bind, run, acceptance and settlement
records, using separately installed trust, profiles and explicit grants. The handoff
itself neither installs profiles nor grants authority. It is the Ascension/AGIALPHA
transport; do not relabel it as a USDC request. The Manager USDC integration remains
its existing separate adapter and is not invoked by this command.

No contract address is copied into the harness. Current deployment inventories and
installed instance-specific adapters remain authoritative. No signing, funding,
unpausing or live settlement is performed by these local commands.

## Compatibility and verification

The implementation adds `successor-harness` to the existing CLI. Existing workbench,
Studio, Computer Use, journal, portable evidence and flagship interfaces remain intact.
The Autonomous Enterprises foundry and browser work in the coordinated flagship lane
are not replaced. This CLI slice is not a claim that their full operational pilot or
four-repository paid journey has completed.

Run focused tests with:

```sh
python -m pytest tests/test_successor_enterprise_harness.py tests/runtime/test_successor_workbench.py
```

Tests cover real numerical/public-data work, immutable configuration, distinct IDs,
accepted-parent linkage, interrupted recovery, stop, exact-result review and preserved
exports. Imported examples cannot select executable paths or create permissions.
