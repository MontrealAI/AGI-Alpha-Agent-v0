# Evidence construction instrument 1.0.0

This is a bounded research tool, not a general autonomous reviewer or a new statistical method.

`read_jats(path, expected_sha256=None)` exposes exact JATS table cells and paragraphs. It expands explicit row/column spans but never silently fills blank cells. Coordinates are zero-based and include header rows. `cell_value(packet, table_id, row, column, part)` extracts an explicitly selected number, mean or parenthesized dispersion. A dispersion's statistical meaning remains unqualified.

`pool(groups, mutually_exclusive=True, same_endpoint=True)` combines conventional sample moments. Every group has exactly n, mean, dispersion, dispersion_kind (SD or SE). These Boolean declarations are assumptions to be checked against the new source. `mean_difference(a,b,design=...)` supports independent groups, or a point-only paired contrast with unknown covariance. It does not reproduce ANCOVA or clustered precision.

`rounded_mean_model(spec)` enumerates supplied positive integer four-cell count candidates and uses SciPy HiGHS linear programming to bound a descriptive mean difference under declared rounding intervals. It preserves the named scenario, assumptions and excluded source claims. It never chooses a favorable source subset. No feasible solution means INCONSISTENT_HOLD. Feasible bounds do not establish source truth, semantic acceptance or execution authority. The caller must record how the source facts and alternative scenarios were obtained.

CLI: `python evidence_engine.py inspect source.xml --output tables.json` or `python evidence_engine.py bounds scenario.json --output bounds.json`.

Prerequisites: Python3.12, NumPy and SciPy (the study records actual versions). New code Apache2.0. Underlying conventional XML parsing, pooled moments, finite enumeration and linear programming are supplied methods. This constructed combination is motivated by observed conflicts in a development report; it is not a discovery of those algorithms. No model weights were modified. The capsule excludes customer data, source articles and protected answers.

Requalification: every new report requires current purpose, units, population, group dependence, source version and rights checks. Model progress can remove any incremental economic value of this method. An ordinary library containing these same bytes offers the same arithmetic capability.
