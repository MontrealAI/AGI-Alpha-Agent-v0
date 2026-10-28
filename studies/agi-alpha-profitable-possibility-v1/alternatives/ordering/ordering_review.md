# Post-confirmation row-order challenge

## Finding

The previously uncorroborated count for `capacity_20_variant_2` is now independently confirmed as **37,877,767,916**. A row-order-only change also removes the apparent large count-time advantage over the conventional reference on this case.

The original confirmation recorded compiler construction in 1.889793 seconds, while the independent reference, which always placed rows in decreasing-sum order, timed out at 30 seconds. In this follow-on, the same conventional dynamic program completed the count in 1.724348 seconds with row order `[3,0,2,1]`. The simple ascending-sum order `[3,0,1,2]` completed in 1.814321 seconds. The exact marginal sums are `[9,9,15,7]`; row permutations carry their cap rows with them.

These measurements show that the original timeout comparison is sensitive to ordering. They do not establish a general improvement from an ascending-row policy or a precise 9% speed advantage: the measurements are single local executions, and the best permutation was selected after trying all orders. The compiler also constructs its reusable graph, whereas this comparator returns a count and execution statistics; it does not supply the whole artifact or uniform-sampling service.

## Protocol and separation from the frozen campaign

The original independent source was copied to `ordering_reference.py`. Only two changes were made: adding the optional `row_order` argument to `orbit_count`, and using that order when provided. No pruning rule, recurrence, state representation, multiplicity, cache, or shortcut was changed. Exact before/after strings and SHA-256 digests are preserved in `ordering_provenance.json`. The copied source does not consult the compiler during its count calculation.

The harness and configuration were hashed and recorded before this follow-on executed. It attempted all 24 permutations in lexicographic order, with an equal 3.5-second wall budget per permutation and an 89-second total ceiling. The input order was attempted first. All attempts and housekeeping were charged to the full search cost.

| Measurement | Result |
|---|---:|
| Permutations attempted | 24 |
| Completed within 3.5 seconds | 8 |
| Timed out at 3.5 seconds | 16 |
| Completed counts agreeing with compiler | 8 / 8 |
| Best conventional execution | 1.724348 s |
| Best order | `[3,0,2,1]` |
| Best-order states / transitions | 1,891 / 106,689 |
| Ascending-sum order execution | 1.814321 s |
| Original input order | Exceeded 3.5 s |
| Full charged search wall time | **75.177102 s** |
| Recorded compiler construction time | 1.889793 s |

The conventional search therefore does not beat the compiler on total first-use search cost. Its purpose is to challenge whether the 30-second baseline timeout demonstrates an algorithmic advantage. A conventional recurrence with a different ordinary row order reaches parity on this observed case, so that interpretation is unsupported.

This is explicitly a **post-confirmation diagnostic**. The original campaign had 11 of 12 counts independently corroborated during that campaign. The remaining count is corroborated here after adaptation. Do not rewrite this history as 12 independently corroborated held-out counts in the original experiment. No general ordering heuristic was selected or claimed; therefore this investigation did not initiate a new six-case generalization campaign. Any later proposed fixed heuristic needs its own frozen source/configuration and fresh cases.

## Files and reproduction

`ordering_input.json` preserves the full original case record. `ordering_protocol.json`, `ordering_provenance.json`, and `ordering_results.json` preserve the declaration, exact source change, and every attempt. `ordering_challenge.py` is the executable harness, and `ordering_reference.py` is the independently implemented conventional DP with the optional order parameter.

From the workspace root:

```sh
python alternative_probe/ordering_challenge.py
```

No frozen study source or confirmation result was edited.
