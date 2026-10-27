# Bounded zero-error channel construction search

This directory preserves a falsifiable discovery attempt, including unsuccessful runs. The target was at least 384 independent vertices in the third strong power of the 15-cycle. A larger cardinality would be a finite block code improvement relative to the retrieved 383-word reference, not necessarily an improved asymptotic Shannon-capacity bound.

## Reproduce

Use Python 3.12, NumPy 2.3.2 and SciPy 1.17.0 (the captured environment). From the workspace root:

```bash
python challenge/channel_search/c15_search.py global 30
python challenge/channel_search/c15_search.py local 180 20261027
python challenge/channel_search/c15_search.py local 180 20261028
python challenge/channel_search/independent_verify.py
python challenge/channel_search/profile_hull.py 7
python challenge/channel_search/profile_hull.py 11
```

The frozen time ceilings are solver/search ceilings. Import and graph preprocessing time are outside the per-function seconds field. Exact solutions and validity are reproducible, but time-limited search trajectories and iteration counts need not be identical across machines. The starting 383-codeword source is preserved, so verification does not need network access.

## Interpretation

The strongest ordinary baseline is the published 383-word witness, available to both search approaches. The unseeded global MILP is an additional computational attempt; it must not be used to claim an advantage from withholding the known witness. No live model API experiment or cost comparison is present.

The separate verifier reconstructs circular distances directly and also constructs the inverse map for every admissible received word. It is algorithmically separate from the solver; it was authored by the same workstream and should not be described as an independent-human review.

Data attribution and the precise channel model are in SOURCES.md. Global and neighborhood raw results are retained even if no larger construction is found. A search failure is not an infeasibility proof.
