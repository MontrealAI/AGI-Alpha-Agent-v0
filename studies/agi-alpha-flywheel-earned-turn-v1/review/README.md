# Independent numerical checks and review

`checker.py` checks grounded weighted-network solutions from node balance and quadratic energy. It does not import NumPy, SciPy, a factorization routine, the candidate executor or its matrix assembly. It is independent software authored by a separate task owner within the same commission and machine; it is not an independent laboratory replication.

## Interface and scope

```python
from checker import check
report = check(task, solution)
```

Task JSON has `n`, `edges` as `[u,v,w]` triples, `ground` and `rhs` arrays. Each finite conductance must be positive, every grounding value must be at least 0.1, endpoints must be distinct integers in `[0,n)`, and vector lengths must equal `n`. Multiple edges add conductance. Isolated nodes remain solvable because they are grounded. The checker bounds inputs to 65,536 nodes and 1,000,000 edges; the study can impose a narrower scope. Invalid or unsupported input receives an explicit scope reason. Unknown metadata fields do not alter the mathematical problem.

For output `x`, the checker independently forms each nodal balance:

`r_i = g_i*x_i + sum_{(i,j)} w_ij*(x_i-x_j) - b_i`.

It uses `math.fsum` for each balance, energy and source work. Validity requires both:

- `max(abs(r)) / max(1,max(abs(b))) <= 1e-9`.
- `abs(E - sum(b_i*x_i)) / max(1,abs(E),abs(sum(b_i*x_i))) <= 1e-9`, where `E = sum(g_i*x_i*x_i) + sum(w_ij*(x_i-x_j)^2)`.

These checks test numerical consistency of the supplied finite model. They do not verify that a model describes a physical installation, certify real-world calibration, prove economic value, or provide interval-arithmetic guarantees. The energy identity is not a substitute for node balance: the deliberately wrong zero vector passes energy identity but fails residual whenever the RHS is nonzero.

Returned fields include `valid`, `scope_valid`, `max_abs_residual`, `relative_residual`, `energy_error`, `reason`, `tolerance`, `balance_nodes` and `balance_edges`. The last two are size telemetry, not CPU instruction counts or money. Overflow and nonfinite values fail explicitly.

For a line-oriented subprocess:

```bash
python3 review/checker.py
```

Each input line is `{"task":{...},"solution":[...]}`; each response line is one report. This CLI has no file writes or network access.

## Validation

```bash
python3 -m unittest discover -s review -p test_checker.py -v
```

Twenty tests cover a closed-form two-node solution, an independently calculated positive edge update, isolated grounded nodes, zero and scaled RHS, reversed/duplicate edges, stale responses after a grounding change, energy-only false reassurance, finite corrupt results, tolerance boundaries, malformed structures, negative/zero/unsupported conductances and grounding, nonfinite values and overflow.

`CHECKER_TESTS.log` records the initial successful run. `CHECKER_VERIFICATION.json` binds that run to the implementation and test hashes. Later confirmation aggregation should preserve all offered missions and failures and report confidence at the independent stream/network level.
