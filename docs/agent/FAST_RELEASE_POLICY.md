# Fast release qualification

This policy reduces repeated work, not authentication, financial authority or artifact integrity.

- The optional paper-upload preview runs in its own advisory workflow. Trusted pre-change paper classification remains unchanged. PR lint and smoke execute independently and both feed blocking verdicts.
- Agent release acceptance owns the one full offline Python 3.12 regression/coverage campaign, including notebooks and the 80% coverage floor. Integration CI runs focused integration smoke instead of repeating full coverage on Python 3.11 and 3.12. Installed runtime acceptance still runs on Python 3.11, 3.12 and 3.13 in Agent release acceptance.
- Compatibility smoke uses Ubuntu Python 3.11/3.12/3.13 and macOS/Windows Python 3.12, on PRs, main and manual runs. These five cells exercise focused boundary, ledger, installed-entry-point and simulation behavior; they do not claim exhaustive testing of all nine OS/Python combinations.
- Black, Ruff formatting and duplicate Flake8 style feedback run in an independent advisory checkout. The workflow action updater is not a release prerequisite. Blocking hooks retain Ruff lint, Semgrep, ShellCheck, Actionlint, syntax, secret scrubbing, binary-integrity and environment checks. This advisory exception is limited to the named hooks: Ruff lint (including configured E-style rules) and existing type checks still block. A report's `passed` field applies only to its explicitly recorded blocking-hook scope.
- Mutation and benchmark checks in Integration CI are manual advisory diagnostics. They do not block ordinary release development. Existing substantive regression, authentication, financial boundary, dependency-audit, browser, signing, exact-source and artifact verification remain blocking.

The existing three historical workflow identities and qualification-marker names are retained for compatibility. A successful marker means the selected policy's checks passed, not that the former duplicated campaign ran. Every required failure, cancellation or unexpected skip still prevents qualification. Advisory formatter outputs are excluded from the packaged acceptance evidence.

This first reduction does not implement feature-risk tiers, reusable historical test evidence, skipped feature acceptance or any change to deployment permissions. No unperformed check is reported as passed. Current release-source and artifact bindings remain intact. Future component-level reuse requires matching source, tests, toolchain, dependencies and validation policy and truthful attribution, not merely an earlier green run.

This workflow change must be integrated with the package manifest's corresponding hook-scope and five-cell compatibility descriptions before publishing a release. Publication claims must describe this policy, not the superseded nine-cell matrix or all-style-hooks-required policy.
