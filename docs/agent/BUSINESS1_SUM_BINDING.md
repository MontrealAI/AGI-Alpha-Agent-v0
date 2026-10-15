# Business1 portfolio report arithmetic qualification

Source baseline: `5e7588f63af0406b0ff8e1fd00380af919e9e522`.

## Reproduced failure before the correction

Accepted positions with quantity/price pairs `(1e8,1e8), (1,1), (1,1),
(-1e8,1e8)` produce notionals `[1e16,1,1,-1e16]`. These obey the evaluator's
individual quantity and price bounds. A genuine Python 3.12.14 evaluation
reported net `2.0`; emulated Python 3.11 left-fold summation reported `0.0`.
Both gross totals were `2e16`. The actual `bridge.submit_job` implementation,
with local legacy summation injected and AsyncMock HTTP transport returning
that genuine 3.12 report, rejected it with:

`Server response does not match the submitted-input evaluation`

This is actual bridge execution under **emulated** 3.11 local summation, not an
actual 3.11 interpreter run. `tests/fixtures/business1_sum_binding_baseline.json`
preserves source identity, runtime, input, both complete canonical report byte
strings and their SHA-256 digests. The regression verifies those bytes/hashes,
requires the corrected evaluator to match the peer, and still rejects the
historical differing report. No equality tolerance or fixture waiver was added.

## Correction and independent oracle

The only float reductions in the bounded `evaluation.py` are portfolio net and
gross totals. Both now explicitly use `math.fsum`. Products retain the existing
binary-float semantics; this is not decimal accounting. The oracle converts
already-rounded products with `Fraction.from_float`, sums exact fractions, and
rounds once back to float. It covers cancellation, gross-only precision loss,
input bounds, decimal products, permutations, and no positions. Empty totals
normalize from integer `0` to float `0.0`, changing their canonical report bytes.

Fixed complete-report hash expectations were generated before changing the
source, replacing only baseline portfolio totals with the independent Fraction
oracle results. Every supported CI Python version must produce these same hashes:

- Cancellation: `67378d3fce2c597fa2b00b184ed7fd56c16b6b60f0dc710680e756ca156c3aeb`
- Gross-only: `f4bb605ad7e602bbb0e43161ec09eb9933c1940a2e326105a0fe11513f1daea3`
- Empty: `e1d7ad7d1a2b23ff00690fe4ac5cdd9b65bae3321967810ed515e8b00d4989ae`

## Local checks and remaining qualification

- Actual Python 3.12.14: bridge, HTTP submission, offline bridge and release CI
  gate suites: 64 passed. The focused bridge suite contains 11 tests.
- Actual `/usr/bin/python3.13` (3.13.5): focused bridge unittest suite: 11 passed.
- No actual Python 3.11 interpreter was available locally. The existing required
  premerge smoke and release runtime matrices now explicitly run the focused bridge suite on
  3.11, 3.12 and 3.13, retaining JUnit evidence. CI execution remains required
  before claiming actual three-version qualification.
- Black and Ruff pass. Standalone strict mypy reports the same six preexisting
  typing errors on both the baseline and corrected evaluator; none is waived.

Reproduce focused tests from the repository root with `PYTHONPATH=.`:

```sh
python -m pytest --noconftest -o addopts= tests/test_openai_bridge_integration.py -q
# Stdlib runner is also usable without pytest:
python -m unittest discover -s tests -p test_openai_bridge_integration.py
```

The bridge still requires exact submitted-input report equality. Peers running
the legacy evaluator should upgrade together; incompatible historical reports
remain rejected. No Fleet runtime files or its frozen 26-file closure changed.
