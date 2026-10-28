# Independent scientific challenge: exact bounded-table construction

Review date: 2026-10-28. This file records technical due diligence performed
by a separate agent before inspecting the flagship kernel. It is an internal
independent implementation check, not external peer review or a human trial.

## Decision

A finite exact compiler for tables with fixed row totals, fixed column totals,
and individual nonnegative integer caps is buildable. Its output is a real
generative capability: a compact representation from which feasible labeled
tables can be drawn with an exactly specified law. It is not enough to call
this a new mathematical invention, a practical implementation of the recent
OpenAI theorem, or an economic breakthrough.

The strongest conventional challenge already constructs an equivalent count
capability by grouping interchangeable columns. A meaningful flagship claim
must survive this comparison and complete costs. Enumeration failure alone
is an inadequate baseline. A successful count of an astronomical number of
tables alone is also inadequate: prior art already did that.

## Recent frontier: exact scope and decisive finite-cost obstruction

OpenAI's family 115 distinguishes two results:

1. Exact uniform sampling and bounded-time approximate sampling for tables
   with fixed margins **without individual cell bounds**.
2. An FPRAS for **counting** tables with individual bounds, including structural
   zeros. This companion result is not an exact uniform bounded-table sampler.

The actual source for the first result prescribes an outer chain length
`T = d^200 (k+b)^2`, with `d >= 14`, and further nested subroutines. This
literal algorithm is computationally inapplicable here. Its asymptotic theorem
does not establish an affordable instrument at practical sizes. Replacing it
with a finite dynamic program does not execute or validate the new theorem.

Primary sources:

- OpenAI, formalization scope: <https://github.com/openai/math/blob/main/lean/docs/115.md>.
- OpenAI, exact sampling algorithm source:
  <https://github.com/openai/math/blob/main/preprints/Exact-Uniform-Sampling-of-Contingency-Tables-with-Arbitrary-Margins-September-24-2026/build/sections/algorithms.tex>.
- OpenAI, collection qualifications and release provenance:
  <https://github.com/openai/math>.

The source was read directly. The Lean toolchain was not executed in this
campaign; no independent formal-verification claim is made. The frontier
release supplies a research lead, not the implemented algorithm's correctness
or its practical speed.

## Existing constructive methods that must be credited

Miller and Harrison's 2013 algorithm counts fixed-margin binary or nonnegative
integer matrices, quotients column-sum symmetries, retains the count DAG, and
uses child counts and multiplicities to sample exact independent uniform
matrices. These features are prior art, including reuse of the count lookup
table. Their published Darwin finches example has exactly
67,149,106,137,567,626 matrices. The independent conventional implementation
in this study reproduces that number.

The specific extension to per-cell caps can use each column's remaining cap
vector as its signature. At a fixed recursion depth, columns with identical
future signatures are interchangeable, but columns that differ in future
restrictions are not. Applying permutation symmetry to these equivalence
classes is a natural conventional construction. This review found no basis
for claiming it is globally new. It also did not establish that no earlier
implementation provides the same combination of operations.

Scharpfenecker and Windisch's October 9, 2026 revision encodes table fibers,
structural zeros, and bounds in SAT and uses SAT proposals in hybrid chains.
It supplies a contemporary strong alternative with different sampling
guarantees. Its approximate or stationary-distribution results are not exact
finite-run IID guarantees. Conversely, our finite exact compiler has no
general polynomial complexity guarantee.

Primary sources:

- Miller and Harrison, *Exact sampling and counting for fixed-margin matrices*,
  Annals of Statistics 41(3), 2013, 1569-1592;
  <https://arxiv.org/abs/1301.6635> and
  <https://jwmi.github.io/publications/Exact_matrix.pdf>.
- Scharpfenecker and Windisch, *SAT-sampling for statistical significance testing
  in sparse contingency tables*, revision 2026-10-09;
  <https://arxiv.org/html/2511.05709v2> and
  <https://github.com/scharpfenecker/sat_fiber_walks>.
- Dobra, *Computing Exact P-values in Incomplete Multi-way Tables*, arbitrary
  marginals plus entry bounds and structural zeros via a Markov chain;
  <https://stat.uw.edu/research/tech-reports/computing-exact-p-values-incomplete-multi-way-tables>.

## Independent reference implementations

`independent_reference.py` contains three correct, separately implemented
references and one intentionally wrong negative control:

| Implementation | Purpose | Essential distinction |
| --- | --- | --- |
| `enumerate_tables` | Exhaustive tiny-instance oracle | Cell recursion; no memoization or column symmetry |
| `labeled_cell_count` | Conventional exact DP | Cell-wise residual recurrence; retains all column labels |
| `orbit_count` | Strong conventional exact DP | Groups equal future cap signatures and residuals; counts multinomial multiplicities |
| `unsafe_sorted_count` | Negative control | Illegally exchanges columns with different future restrictions |

The strong comparator reorders rows conventionally by decreasing row sum
while carrying each row's caps. It aggregates row allocations by value
histograms in each equivalent column group. Its integer multinomial factors
count labeled choices. It does not import the flagship kernel.

The references were checked on 96 generated tiny binary and bounded-integer
instances plus eight nontrivial fixed cases, including infeasible instances,
against exhaustive enumeration.
The published 13-by-17 binary finch count was also reproduced. Runtime and
state counts are in `results/independent_reference.json`; runtimes are local
observations and are not portable speed guarantees.

The actual authors' Python implementation from EXACT v0.3 is also retained in
`vendor/miller_harrison_exact.py`, with its BSD license and a provenance file.
Only two Python 3 compatibility edits were made: dictionary membership and
conversion of a mutable range to a list. This code reproduced the published
finch count and generated 100 samples satisfying all original margins. Its
binary scope excludes individual structural-zero constraints. The benchmark
must not count that unsupported extension as an incorrect answer.

### Why unconstrained sorting is wrong

Take row and column totals `(1,1,1)` and cap matrix

```
0 0 1
1 1 0
1 1 0
```

There are exactly two tables. Sorting residual column totals globally while
retaining the original cap positions returns zero. This is a concrete
correctness failure, not only a loss of precision or performance. The preserved
counterexample can catch an invalid symmetry shortcut.

### Correct symmetry argument

At row depth `i`, let the signature of column `j` be the cap vector
`(u[i,j], ..., u[m-1,j])`. If two columns have the same signature, permuting
their residual totals induces a bijection of future completions by exchanging
their cells. Counts therefore agree within that signature class. Permuting
columns from different classes is not licensed by this argument.

For a group of `h` identical columns, allocating `h_v` of them value `v` in
the next row has multiplicity `h! / product_v(h_v!)`. Multiplying the child
completion count by this multiplicity preserves the labeled count. Counting
each orbit once without this factor would bias sampling and undercount.

### Exact uniformity is a specification

Uniformity over feasible matrices is an explicit choice of law. It does not
make the matrices realistic or represent the true unknown world. Conditional
independence generally induces a different law. For example, SciPy's
`random_table` samples the fixed-margin independence law using Patefield or
Boyett, not the uniform-over-integer-tables law. It must not be scored as a
failed implementation of a specification it never claimed to satisfy.

Source: <https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.random_table.html>.

For integer counts `C(s)` on a correctly constructed DAG, choosing each branch
with probability proportional to its labeled child count yields the uniform
law by induction. Rank/unrank can make this especially auditable: a bijection
between `[0, C(root))` and all feasible labeled tables, combined with uniform
integer generation, is sufficient. Tiny-instance exhaustive bijection tests
are stronger correctness checks than an isolated frequency test.

## Successor experiment: a substantive trap

Counting additional statistics from an inherited graph must preserve every
state attribute on which the statistic depends. A statistic invariant under
within-class column permutations can often be propagated by a polynomial
semiring over the existing transitions. A statistic naming one particular
column may break that symmetry. In that case one must refine signatures or
retain enough label information; simply attaching a statistic to a quotient
state can return the wrong distribution.

An inherited count table is already conventional prior art. The successor
test should compare at least: rebuilding from scratch; inheriting the asset;
and a conventional system given the same asset and resource allowance. It
must include the time, storage and validation cost of constructing and
transferring the asset. A faster query after paying for compilation is an
amortization benefit, not automatically an expansion of scientific possibility
or an AI-specific retained advantage.

## Protocol recommended before the final evaluation

- Freeze code hashes, admission budgets, and price policy before new cases.
- Evaluate binary tables, bounded integer tables, structural-zero patterns,
  repeated cap signatures, all-distinct signatures, empty fibers, and hard
  resource-limit cases. Preserve the limit outcome as `budget_exceeded`,
  never convert it to an infeasibility certificate.
- Check all outputs against the original labeled margins and caps. Count
  agreement should use exact integers. Check complete rank/unrank bijections
  on tiny fibers and independent sampled ranks on larger ones.
- Keep the conventional orbit implementation in the performance comparison.
  Include its compilation and lifecycle costs under equal reuse allowances.
- A fixed seed produces reproducible pseudorandom samples; it is not a proof
  of independent physical randomness. State the random-source assumption.
- Price claims require customer evidence. A technically valid synthetic
  dataset does not establish willingness to pay, accepted commercial work,
  or the billion-dollar potential requested in the mandate.

## Current claim boundary

The achievable result is a verified finite construction and a falsifiable
commercial experiment. A transformational flagship requires additional
evidence beyond this result. The prior-art challenge is a substantive part of
the outcome and must remain visible even if a conditional financial simulation
earns positive profit.

## Executed adversarial review of the constructed kernel

After the independent references were written, the kernel was inspected and
checked against them. The initial loader accepted a recomputed-digest asset
with a false collision annotation; a hash alone did not validate the numerical
meaning of a transition. The corrected loader checks transition semantics,
root and terminal states, multiplicities and collision statistics. It also
requires complete reconstruction when there is no separately retained trusted
issuance digest. The initial defect and its repair are part of the record.

The independent review exercised 104 small fibers and all 2,838 feasible table
ranks in those fibers. Ordinary rank/unrank and concentration-conditioned
unrank reproduced the complete exhaustive table sets. Restored instruments
gave the same results. A separate fresh semiring DP reproduced every exact
concentration histogram. All six recomputed-digest mutation checks were
rejected: incorrect collision, multiplicity, root groups, a self-loop,
terminal count, and a missing edge with a self-consistent reduced count.

The review result records exact kernel and reference source hashes in
`results/kernel_independent_review.json`. This establishes correctness on the
tested cases and supports the accompanying recurrence argument. It does not
constitute a universal formal proof, independent external review, or an
ordinary-versus-expert frontier-model experiment.

## Successor findings after full transfer costs

The direct conventional successor comparator computes the full concentration
histogram in a fresh orbit semiring dynamic program. It need not first build
and serialize the original artifact. A second comparator exploits the fact
that zero collisions is exactly the binary-cap problem: replace every cap by
its minimum with one. Rejection sampling is therefore not the strongest
alternative for this successor request.

Single local observations for the repeated four-row product family were:

| Columns | Portable asset size | Load, parse, digest and semantic checks | Inherited full-histogram query | Combined successor | Fresh conventional full histogram | Direct zero-collision count |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 8 | 79,214 bytes | 0.01563 s | 0.00043 s | 0.01606 s | 0.01616 s | 0.00113 s |
| 12 | 729,873 bytes | 0.16272 s | 0.00294 s | 0.16566 s | 0.14341 s | 0.00364 s |
| 16 | 5,045,642 bytes | 1.14040 s | 0.02557 s | 1.16597 s | 0.93840 s | 0.00820 s |
| 20 | 27,316,366 bytes | 7.26815 s | 0.16017 s | 7.42831 s | 6.01660 s | 0.01771 s |

These figures include a local file read, not remote network transfer. The
predecessor's compilation and export times are separately recorded and would
increase a full lifecycle comparison. All full distributions matched exactly.
The eight-column apparent near-tie is below the resolution needed for a robust
performance claim. At the three larger sizes the tested transfer route lost
to the direct conventional full-histogram computation. At every size the
zero-collision shortcut was faster than the inherited full-distribution pass
plus loading. The warm query alone does not establish transferred advantage.

An adversarial case with 23 distinct future cap signatures correctly hit the
declared 100-state/200-transition construction budget and raised a resource
refusal. It did not masquerade as an empty-fiber certificate.

Detailed observations: `results/successor_complete_cost_reference.json` and
`results/successor_conventional_probe.json`. These developmental probes are
separate from any later frozen fresh-case campaign. They constrain the claims
that campaign can make; a change of serialization or policy must be evaluated
anew and must not erase this failure.
