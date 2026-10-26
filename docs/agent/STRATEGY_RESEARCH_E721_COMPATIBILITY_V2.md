# Strategy exact-source E721 compatibility v2

This is a separate, review-required compatibility identity, not an amendment to
`STRATEGY_RESEARCH_LINT_COMPATIBILITY.md` or its v1 pin table. Acceptance requires
an independent eligible exact-source review of this effective CLI extension.
A successful guard or lint run is not that decision and grants no runtime,
security exception, production, profile-adoption, or scientific authority.

## Why this finite extension exists

The repository's existing pre-commit Ruff revision installs Ruff 0.2.1. It reports
51 E721 diagnostics on thirteen exact Python bodies containing intentional
`type(value) is int` / `is not int` and corresponding exact boolean checks.
Replacing these with `isinstance` can admit bool or subclasses; editing preserved
research bodies would invalidate their provenance. Modern Ruff's treatment does
not authorize changing the pinned tool or historical sources.

The v2 JSON binds all thirteen bodies, the unchanged v1 guard and pin table,
root configuration, non-Ruff package metadata and three engineering manifests.
The original 241 scientific bodies remain validated by the unchanged v1 guard.
No original body, published result, engineering manifest, v1 pin, Ruff tool pin,
root Ruff configuration, or security scanner is modified.

## Effective lint behavior

The pre-commit Ruff hook retains its existing pinned environment, target selection
and exclusion, but enters through the fixed v2 adapter. `scripts/ruff_targets.py`
retains its original target discovery and uses the same adapter, which executes
the unchanged v1 preservation check from verified captured bytes. The adapter invokes its interpreter's `-m ruff check --force-exclude`
with thirteen fixed `--extend-per-file-ignores path:E721` options. They add to,
not replace, the original fourteen-path E701/E702/F841 compatibility map. Every
original selected target is still linted; unlisted files get no new exception.
Direct Ruff remains stricter and may still report these historical diagnostics.

Only canonical relative filenames are accepted by the adapter CLI. Configuration,
ignore, select, root, pin, executable and regeneration selectors are not accepted.
The entry point derives the repository root from its own source location. Profile
bytes, all bound source bytes and relevant configuration ancestors are checked
before lint and again afterward, including an empty target list. The v1 guard is
executed from its verified captured bytes, not from an unchecked module import.
The same existing interpreter supplies Ruff; no executable is selected via PATH.

The checks refuse missing files, symlinks, changed bodies/manifests/pins, profile
expansion, nested overrides, and concurrent changes detected during capture or by
the post-run check. They do **not** create an atomic filesystem snapshot spanning
Ruff's reads; a hostile modify-and-restore race is outside this static-check claim.

## Reproduction and review evidence

At preparation, the full 241-body / 7,538,898-byte scientific closure passed the
unchanged v1 guard with zero integrity or configuration errors. Actual Ruff 0.2.1
reported 51 E721 diagnostics before the extension, and zero after linting the
union of all thirteen v2 and fourteen v1 exception paths (23 distinct paths).
An unlisted file containing `type(value) == int` still failed E721. All original
source bytes and strict bool/subclass rejection behavior remain unchanged.

Run the current tests and guard from a full checkout:

```sh
python scripts/check_strategy_research_source.py
python -m pytest -q tests/test_strategy_research_source.py \
  tests/test_strategy_research_compatibility_v2.py tests/test_ruff_targets.py
pre-commit run ruff --all-files
python scripts/ruff_targets.py --run
```

The v2 tests exercise each bound body, profile expansion and duplicate fields,
missing/symlinked sources, nested configurations, caller options and traversal,
empty selections, batching, and post-lint identity drift. Exact-source independent
review must explicitly evaluate the **new effective E721 policy**, not assume the
old compatibility approval covers it. Future source/configuration changes cannot
inherit this identity; they require another reviewed compatibility decision.
