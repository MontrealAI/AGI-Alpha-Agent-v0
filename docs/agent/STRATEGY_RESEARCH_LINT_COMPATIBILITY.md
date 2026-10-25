# Exact-source Strategy research lint compatibility

[Project notice](../DISCLAIMER_SNIPPET.md)

The additive Strategy research edition preserves all 239 original study bodies from
`d69133291d72942c7d5f6be8ee0571cd83267110`. Formatting those files would change the
scientific freeze, source bindings and delivered payload manifest. Two identical
Python copies used by the separate engineering worker preserve the same identities.

The proposed compatibility table contains 14 exact Python paths. It accommodates
only the observed `E701`, `E702` and `F841` findings for their exact pinned bodies.
It excludes no directory and suppresses no other rule family. All other Ruff,
security, integrity, behavioral, scientific-source and release checks remain required.
The pin table and its configured use require eligible exact-source review before
acceptance; a successful static check supplies no review disposition or execution authority.

`scripts/check_strategy_research_source.py` binds its fixed JSON table by SHA-256.
Before Ruff, the supported lint entry point must compare every listed regular-file
body and the complete Ruff configuration with that table. Missing or changed bytes,
symlinked files or ancestors, broader exceptions, changed global lint scope and
overriding Ruff configuration files fail closed. The command accepts no source,
root, pin-update or regeneration arguments. It reads inert bytes and does not import
the research source or rerun the experiment.

The engineering package has one separately pinned ancestor metadata file,
`contrib/strategy_succession/pyproject.toml`. Its exact body contains no `tool.ruff`
table, so Ruff continues to use the repository configuration. This is a single
metadata identity, not a rule exemption or general allowance for nested project
configuration. Changing or removing it, adding a Ruff table, replacing it with a
symlink or introducing another ancestor configuration fails the guard. Future
metadata changes require a new reviewed pin-table and guard identity.

The three original `F841` findings were inspected separately. In `review/check.py`,
the unused `makespan_ok` and `movement_ok` variables receive the return values of
`a.integer(...)`; those calls still record invalid-value errors and counted checks.
In `review/results/audit_main.py`, the unused `protocol` variable receives a required
JSON read; the read still checks file presence and parsing, and the audit separately
asserts its declared protocol/source identities. The vendored checker preserves the
same two validation calls. These explanations apply only to the recorded bytes.

Future edits cannot inherit these exceptions: the static guard rejects changed
source. A legitimate source or policy change needs a new reviewed identity and
compatibility decision. Historical papers, results, freezes and original action
restrictions retain their existing scope.
