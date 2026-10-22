# Release queue and scoped qualification

## Implemented queue deferral

The historical-CI proof job starts only after all substantive package prerequisites have succeeded.
GitHub holds dependency waiting without assigning that job a runner. The proof still requires the
latest successful exact-main attempts of Integration CI, PR CI and Smoke, including their full
qualification markers. Its finite 120-minute polling limit and 125-minute job timeout are unchanged.
This avoids occupying a historical-proof runner while release producers are still working; it does
not promise a shorter end-to-end release or turn a failed, cancelled or skipped producer into success.

Formatting remains advisory and is not added to the dependency barrier. No permissions, tokens,
release requirements, artifact identities or historical-source claims change in this first slice.

## Subsequent scoped qualification

Component selection and cross-commit evidence reuse are not enabled by the queue change. They require
a trusted pre-change policy and an explicit conservative input catalog. Unknown paths and changes to
shared security, financial, build, dependency or validation inputs must fall back to full qualification.
A newly introduced policy cannot authorize its own reduced path.

Before any component can reuse evidence, its complete source, tests, locks, toolchain, environment,
build and validation-policy closure must match. The original successful authenticated producer's
source, run, attempt and artifact digest must remain recorded, with a separate binding to the new
source. Current external state and authorization checks cannot be reused. Existing exact-source
report validators require reviewed provenance-aware adapters before reuse can become operational.
No old result may be renamed or rewritten as newly executed evidence.
