[Project notice](../../../docs/DISCLAIMER_SNIPPET.md)

# Current authority at execution and inheritance boundaries

Three configured review findings on exact source
`6010e19bff857704827c3aa373121c98003d8965` concern current eligibility rather
than historical truth. `FREEZE.json` records the source identities, review threads
and requirements before the new counterexamples execute.

- The recurring execution guard now verifies the permit principal's current
  controller trust before subsequent provider/tool actions. Revocation during
  a provider return, a tool return, or the guard immediately before the next
  action stops progress. The durable attempted mission and unknown liabilities
  remain; no automatic retry or new authority is created.
- `accepted_general_origin` now verifies the original execution-permit signer
  against current trust before returning a currently eligible origin. Historical
  execution, acceptance and accounting records remain unchanged. The check does
  not require a completed delivery's historical execution permit to remain
  unexpired; a positive control advances the clock beyond that permit's expiry.
- Placement capsule eligibility now rechecks the exact accepted origin, including
  its current acceptance signer and execution controller. This covers controlled
  discovery, invocation, reuse acceptance and dependency eligibility. Internal
  capsule calls pass their existing transaction; compatible private callers may
  omit it. Existing live access proofs, expiry, replay, validator-role and cost
  checks remain in force. Catalogs exclude an ineligible capsule while preserving
  the authenticated catalog request.

The original campaign produces **10 failures and two passing controls**: four
revocation timings, two current execution-trust changes, four capsule boundaries,
historical permit expiry and fully reconciled reuse. The capsule fixture uses a
separate originating acceptance key. Its evaluation, admission and fresh reuse
signers remain trusted, so refusal is attributable to the missing origin check.

After correction, **67 tests pass** across the new 12 authority cases and existing
execution/specialist families. They verify no extra provider/tool call, preserved
unknown costs, unchanged historical acceptance and financial reports, and atomic
refusal after access-proof preparation. The fully reconciled positive fixture
continues to accept reuse with current signers. These are synthetic signers,
provider receipts and ENS fixtures; no live identity, actual frontier performance,
commercial revenue or retained Alpha is established.

`pre-fix-tests.json` preserves the original failed output. The first fixed run's
two new test failures remain in `focused-before-proof-order-correction.json`:
the test had captured its journal boundary before legitimate fixture access-proof
preparation. The corrected test creates that proof before the boundary and then
revokes the origin approver. No production guard, refusal or atomicity assertion
was removed. `ATTEMPTS.json` also records overlay exhaustion and the safe cleanup
of disposable local fixtures. Unrecorded static/family attempts during exhaustion
are unqualified; the later retained runs have their own exact source identities.

Commands, exit codes, timings, raw-output byte counts and SHA-256 commitments are
included in the receipts. Larger outputs use zlib plus base64 to preserve exact
bytes within the bounded evidence packet. `typing-lint.json` records strict
runtime-module typing and Ruff checks with the existing shared tools. No new
dependencies were installed. Reproduction uses the existing development setup:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m pytest \
  -c /dev/null --noconftest --rootdir=. \
  tests/runtime/test_flywheel_authority.py \
  tests/runtime/test_flywheel_execution.py \
  tests/runtime/test_flywheel_specialists.py -q
```

Full protected-module and combined-source qualification, regenerated source
packets, public publication and live-operation acceptance remain separately
scoped work. This correction does not commit, merge, publish, alter credentials,
delete an obligation or grant authority to a fixture.
