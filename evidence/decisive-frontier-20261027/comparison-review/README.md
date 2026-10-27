[Project notice](../../../docs/DISCLAIMER_SNIPPET.md)

# Comparison review corrections

This packet reproduces and repairs the two configured #4987 review findings in
`flywheel_comparisons.py`. It changes the existing derived report; it creates no
registry, accounting store, execution permit, live authentication or acceptance.

A different execution controller, charge signer, seal signer or additional-B
accounting signer can now be revoked without erasing its historical observations.
The current report revalidates signatures, exact domains, journal identity and
accounting action/mission before qualifying matched outcomes or cost savings.
Historical execution digests, accepted counts, known totals and completeness
remain inspectable through distinct current-support validity fields.

Model evidence is selected from successfully bound execution cells. A declared
live-model plan without attempts, or a cohort whose sole receipt fails binding,
reports `no-executions`; all planned cells remain in the denominator. The bound
positive fixture remains labelled simulated. No actual frontier call is implied.

## Reproduction

```bash
python check_env.py --auto-install
python scripts/check_python_deps.py
python -m pytest tests/runtime/test_flywheel_comparisons.py --confcutdir=tests/runtime -q
python -m ruff check alpha_factory_v1/core/runtime/successor/flywheel_comparisons.py tests/runtime/test_flywheel_comparisons.py
python -m mypy --config-file mypy-runtime.ini alpha_factory_v1/core/runtime/successor/flywheel_comparisons.py
```

The original module at `de62cdcdbb1c6d0d73a4212f750510b6d2809bb6` fails six
corrected directed assertions and passes the positive control. Original output
is retained. An earlier invalid test attempt tried executing a simulated
transport under a live label; the existing executor correctly refused those two
calls. That first seven-failure receipt is retained separately and is not
presented as seven implementation defects. Corrected tests use a live declaration
only for the unexecuted-plan negative case; executed protocol cases stay simulated.

The final complete comparison suite passes 42 tests. Ruff and strict runtime
typing pass. The first format-check refusal and its automatic formatting correction
were local advisory feedback; source behavior is unchanged by formatting.
Complete monetary costs remain unknown, collections are zero, no live recipient
identity is established, and repository-wide/release qualification is separate.
