[Project notice](../../../docs/DISCLAIMER_SNIPPET.md)

# Preserve the frozen execution receipt

The integration source omitted an existing owner correction: an experiment step
could freeze an execution-request digest, then submit a receipt-free research
observation. Its omitted or null `execution_operation` bypassed the request
binding. This change reuses the exact two-line guard from public owner commit
`a65387914777d9afe1a1d21a5b2d3e51cf37ed8d`, refusing that substitution before
observation, accounting, checkpoint or operation state is appended.

`OWNER.json` freezes the exact owner commit and source/test Git blob identities.
`owner-regression.py.txt` preserves the owner's original 12-way regression. The
integration copies it into the existing discovery tests and adds one assertion
for the current typed mission-cost-allocation namespace. All existing tests are
retained. No owner UI, other runtime, generated page, worker, publication version,
authority or ledger implementation is replaced.

The pre-fix campaign fails all 12 new cases specifically because no `ValueError`
is raised. It covers three interpretations, sealed/unsealed costs, and omitted/null
receipt fields. After the correction all 69 discovery-file cases pass, including
the previous 57. The new cases verify unchanged journal, complete cost report,
checkpoint bytes and bundle, plus absent observation/operation/allocation records.
The same observation identity then accepts a genuine exact execution receipt;
the synthetic fixture creates neither customer revenue nor operating authority.
Existing unpinned research, unknown-cost, checkpoint and identity boundaries remain
covered by the unchanged cases.

`pre-fix-tests.json` and `post-fix-tests.json` preserve exact output compressed with
zlib/base64, its raw byte length, SHA-256, command, exit code and source identities.
The earlier post-fix run before removing an excess separator blank line remains
in `post-fix-before-blankline-tests.json`. `ATTEMPTS.json` records the original
post-capture summary-count assertion error and the prerequisite environment
difference. No failed campaign is rewritten as passing. The original 12-failure
receipt was checked without running that known-failing source again.

Targeted tests use the existing minimal environment without bytecode writes and
without unrelated repository conftest/addopts. Its optional pandas and static
analysis tools are unavailable. The shared-runtime dependency check passes; no
packages were installed. Static checks use the existing shared tools, with exact
commands and scope in `typing-lint.json`; unavailable minimal-environment attempts
remain in `typing-lint-minimal-unavailable.json`.

Reproduce the targeted runtime scope from the repository root:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m pytest \
  -c /dev/null --noconftest --rootdir=. \
  tests/runtime/test_flywheel_discovery.py -q
```

These are local synthetic authority fixtures and a narrow integration regression.
Full combined-source qualification, source-packet refresh, public deployment and
live-operation acceptance require their own evidence. No publisher, source-history
rewrite, paid model call or retained-capability claim is created here.
