[Project notice](../../../docs/DISCLAIMER_SNIPPET.md)

# Gym controller eligibility at recurring checkpoints

This isolated child4be correction fixes a signed Gym plan that remained active
after its original controller lost trust. Existing environment, clock and control
checks did not revalidate the original plan signature/controller. The original
source freezes a candidate in all12 withdrawal cases; three controls complete.

The runner now preserves the original verified payload's canonical binding and
revalidates the same snapshotted signed plan at every active checkpoint, using
the existing trust API, exact domain/controller role, Journal identity and payload.
A final active checkpoint precedes candidate freezing. Authority withdrawal
produces a durable failed-or-uncertain attempt with no candidate; partial trials,
logical work, the original workflow and the original unknown C liability remain.
A still-trusted operator's new signature cannot replay the same campaign.
No shared callbacks, accounting model or reservation policy are mutated.

## Scope and checks

Only `flywheel_gym.py`, one uniquely named runtime regression and this packet are
owned here. The runtime formatter also normalizes existing Protocol ellipsis
layout; that hunk has no semantic change. The primary checkout, root-owned
`tests/test_held_native_source_guard.py`, owner reservation fix, pages, versions,
branches and publisher are excluded. Apply the decoded module diff, rather than
replacing a later owner's whole module, and add the new test/evidence files.
The final combined owner source requires its own qualification.

- Original4be:12 failures /3 passing controls, exact raw log/source preserved.
- Corrected:37 passes (15 directed plus22 existing specialist cases).
- Native strict module typing and owned-file Ruff lint/format pass.
- All five held source pins match before and after, by inert-byte checks only.
- None of the four held nodes is imported, executed, modified or qualified.

The directed cases withdraw controller trust, role or installed public key before
first action, within action, after a completed trial and before freeze. Operator
and accounting keys remain distinct and trusted. Positive controls preserve a
current planner, tolerate an unrelated revocation and keep the copied plan intact
when a caller mutates its original envelope. Failed/partial work and original C
cost identity are retained; no candidate, authority, admission or replay appears.

```bash
PYTHONPATH="$PWD" PYTHONDONTWRITEBYTECODE=1 python -m pytest tests/runtime/test_gym_current_controller_4be_regression.py tests/runtime/test_flywheel_specialists.py --confcutdir=tests/runtime -q
python -m mypy --config-file mypy-runtime.ini alpha_factory_v1/core/runtime/successor/flywheel_gym.py
python -m ruff check alpha_factory_v1/core/runtime/successor/flywheel_gym.py tests/runtime/test_gym_current_controller_4be_regression.py
```

`original-tests.json` and `SOURCE_PATCH.json` hold gzip/base64 exact bytes and
SHA256 identities, avoiding raw pytest/patch trailing-whitespace artifacts.
`ORIGINAL_SOURCE.py.txt` is exact base source. Models, funds and authority in these
unit tests are explicit synthetic fixtures; the finite workflow executes locally.
No API call, frozen canary, live identity, customer sale, paid demand, profitability
or retained Alpha is established. Actual complete monetary cost is unknown.
