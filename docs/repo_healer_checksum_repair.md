# Bounded checksum-integrity repair

RepoHealer can propose a checksum-before-write repair when a PYTEST/SMOKE failure
explicitly mentions a checksum and a designated Python source file contains the
supported historical downloader AST window. The entire checksum window must
match; there is no whole-file fingerprint or cached replacement. Unknown shapes,
uncommon line separators and already-correct sources are left unchanged.

The public candidate generator retains triage and workspace/path checks. The
existing engine still applies patch safety, isolated application, targeted tests,
broader validation and promotion. This addition does not change those controls,
activate a scheduler, adopt an operator profile, or authorize financial actions.

## What it fixes

The supported old shape writes downloaded bytes before comparing their checksum.
A mismatch can therefore destroy an existing valid destination or create an
invalid one. Move that write into the validated-success path and the no-checksum
path; preserve the checksum rejection and successful return behavior. This does
not claim atomic filesystem writes or power-loss recovery.

Current `scripts/fetch_assets.py` already uses a temporary file, checksum checking
and `os.replace`. It is deliberately **not modified or downgraded** by this change;
a pinned current-source negative fixture confirms the candidate abstains.

## Recurring workload

On authorized changes to download/checksum/cache-lifecycle code, run behavior
checks for mismatch preservation (existing and absent destination), valid hex and
base64 checksums, and no-checksum downloads. Record exact source revision, failure,
candidate, full validation and final result. Unsupported/already-valid inputs
remain abstentions/no-ops. This is a change-triggered local procedure, not an
activated unattended production service or evidence of customer demand.

## Evidence and scope

The original engineering replay selected three real historical source snapshots.
The incumbent repaired zero; the added structural asset repaired all three, with
15 behavior checks passing after repair. Two complete-file blobs were unseen at
freeze; one was a previously seen control. **All three download functions had the
same AST:** this is one persistent defect pattern across versions, not three
independent bugs or novel-pattern transfer. Production integration is stricter
than the exploratory matcher: it matches the complete straight-line window.

Two exact historical fixtures and one pinned current-main negative fixture are
included under `tests/repo_healer_v1/fixtures/checksum/`; see their provenance.
Tests exercise the real generator and engine, including refusal to promote when
a broader test fails. HTTP transport is stubbed; no assets are downloaded.

The authoring/review was human-assisted. No autonomous innovation, commercial
savings, monetary payback or full Flywheel success is established. Failed
incumbent attempts are not equal-output cost comparators to accepted repairs.
Prior security, operator, merge, release and deployment gates remain in force.

Run the scoped suite with `python -m pytest tests/repo_healer_v1 -q` in the
repository's supported development environment. Scoped local success is not full
repository CI, Security acceptance, a merge, release or live deployment.
