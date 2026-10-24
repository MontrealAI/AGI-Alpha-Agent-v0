# Independent conventional reference and semantic checker

Version: fresh-study reference 1.4 (preconfirmation efficient independent finite-cover checker). This implementation was written independently of the candidate implementation in the same research session. It is code independence, not organizational or external reviewer independence. No confirmatory case or earlier writer artifact was inspected.

## Interface

`reference.solve(case)` consumes:

```json
{"nodes":["lib","app"],"edges":[["lib","app"]],"applications":["app"],"changed":["lib"],"tests":[{"id":"smoke","covers":["app"],"cost":3}]}
```

Edges point from dependency to dependent. A changed node is reachable from itself. The output fields are `affected`, `feasible`, `selected`, `cost`, and diagnostic counts. `affected` and `selected` are sorted lists. Test cost must be a nonnegative integer in the caller's explicitly declared units. No monetary interpretation is built in. Up to ten applications and twelve test options are supported. `queries` is an optional list of change-set lists; `solve_batch(case)` evaluates that list, while `solve(case)` always evaluates `changed`.

`reference.qualify(case, output)` independently computes the semantic answer and compares the four scientific result fields exactly. Diagnostics and timing are not compared for equality.

## Independently implemented exact semantics

Impact computation is iterative multi-source breadth-first traversal over dependency-to-dependent adjacency, with explicit cycle handling through a visited set. Retest planning enumerates all subsets of the finite test suite and selects the minimum cost covering subset. Equal costs break ties by the lexicographically smallest tuple of sorted test IDs. Consequently, a zero-cost otherwise irrelevant test can occur in the lexical winner. This deliberate corner case is covered by a fixture. An empty affected set returns an empty feasible plan with cost zero; unavailable coverage returns infeasible with no claimed cost.

This checker recomputes the result from the current graph and coverage table. It does not trust a serialized closure, digest, parent receipt, or candidate's chosen algorithm. Exactness is relative to the supplied graph and declared coverage: it does not prove real regression safety, completeness of a manifest graph, actual test effectiveness, or fitness for deploying software.

## Conventional expert-style selection policy

`choose_strategy(case, available=('walk','memo','scc','warshall','reverse'), memory_limit_bytes=None)` returns a dictionary with `strategy`, `reason`, `estimates`, workload `inputs`, the `memory_scope`, and measured `decision_cpu_ns`.

The reference can choose every candidate primitive. It sees the same complete query batch and graph. Its estimates are frozen engineering heuristics, not learned or tuned on confirmation:

- `n`: number of vertices; `m`: number of distinct directed edges.
- `q`: number of nonempty change-set queries; `u`: number of distinct changed sources across the batch; `c`: total source occurrences across queries.
- `a`: number of application nodes; `w = max(1,ceil(a/64))` is app-mask width; `g = max(1,ceil(n/64))` is graph-mask width; `b = max(1,n+m)`; output-mask combination estimate `c*w`.
- Walk work: `q*b`.
- Memo work: `u*b + c*w + 8*u`.
- SCC closure work: `3*b + (n+m)*w + c*w`.
- Warshall closure work: `n*n*(1+g) + c*w` (full intermediate reachability, then project to app masks).
- Reverse-index work: `a*b + c*w`. Independently traverse the incoming graph once from each application, then transpose ancestor memberships to per-node application masks. Few application sinks can make this much cheaper than computing every source's full reachability.

All available supported primitives remain eligible regardless of planning-memory estimates. The minimum work estimate wins, with deterministic order walk, memo, reverse index, SCC, Warshall for equal estimates. Unsupported primitives are excluded. A conservative per-row payload estimate is `64+8*w` bytes; memo adds 72 bytes per cached row, and complete closures add 16 bytes per row plus 256 bytes. Walk has zero retained operator-payload estimate. These are planning estimates for incremental operator storage, not canonical JSON sizes or measured peak process-memory bounds. The common wrapper must enforce the actual canonical serialized artifact byte cap and report measured peak memory separately. The policy does not use a Python-object estimate to disqualify a compact serialized artifact. The common wrapper attempts the selected construction, charges incurred work, checks actual bytes, and falls back under the same rule used by the candidate.

The selection decision's CPU cost is measured and should be included once in the wrapper's total. It is already part of any outer CPU measurement; do not add it twice. The policy is a competent transparent conventional hybrid, not proof of the globally fastest existing implementation. Where practical report the individual primitive results and a separately labeled retrospective lower-envelope diagnostic; do not confuse an uncharged oracle with an eligible prospective comparator.

## Development checks

Fifteen hand-constructed fixtures cover dependency direction, SCC cycles, normal empty termination, infeasibility, lexical ties, zero-cost irrelevant tests, semantic corruption, invalid identifiers/costs, batches, component unavailability, scarce retained-memory budgets, and large/repeated workloads. They are development examples, not confirmatory or independent reproduction cases.

Run:

```sh
python3 -m unittest discover -s independent_baseline -p 'test_*.py' -v
```

## Independent linear-time exact closure certificate verifier

`verify_certificate(case, certificate, rows)` returns `qualified`, a readable `reason`, diagnostic work counters, and measured `verification_cpu_ns`. It imports no candidate code and does not reconstruct source reachability for every node. Its certificate contains `components` (lists of node-array indices), `order` (a topological permutation of component indices), and `masks` (application bitmasks). `rows` is a list of one app mask per node. Application bit position is the application's position in `case['applications']`, without an implicit resort.

Checks are:

1. The component lists partition all graph vertices exactly once. All indices and masks are properly typed and bounded.
2. Within each proposed component, one traversal from a representative over forward induced edges and one over reverse induced edges reach every member. Thus the component is strongly connected.
3. Every intercomponent edge goes strictly forward in the supplied topological order, establishing an acyclic condensation.
4. In reverse topological order, the exact expected mask is the local application bits OR every outgoing component's mask. Every declared mask must equal this recurrence.
5. Every node row equals its containing component's mask.

Correctness follows because every node of a strongly connected component can reach its local applications and each outgoing component; induction over the acyclic condensation gives exactly all reachable applications and no others. The vertex partition, induced connectivity, topological edges, recurrence, and row equality are semantic evidence; a digest alone is insufficient. Work is linear in graph/certificate size plus bitmask operations. With at most ten application bits, mask operations are bounded small integers.

The all-node BFS oracle remains a separately charged research audit. It should not be silently included in operational verification for one arm but excluded for another. The certificate does not validate policy, authority, environment, pricing, or customer demand; the common wrapper must separately validate those applicability conditions.

## Independent exact reverse-index certificate verifier

`verify_reverse_certificate(case, certificate, rows)` uses the same output verdict fields. The certificate type is `reverse_witness`, with matrices `next[app][node]` and `ranks[app][node]`. A reverse BFS can construct these while constructing its app masks, so reverse indexing is not forced to pay for a separate SCC decomposition.

Every set app bit has a real outgoing-edge pointer toward that app and a strictly decreasing nonnegative rank, terminating at the application's self-pointer/rank-zero root. Unset bits have exactly `-1` for both fields. Local app ownership is required. Every graph edge `u→v` must satisfy `rows[v]` subset of `rows[u]`. Matrix dimensions, integer types (excluding booleans), node-index bounds, and app-mask ranges are checked.

Strict rank descent and real edges show each claimed bit has an actual path to its application (no false positives). Root ownership and forward edge closure show every actual ancestor owns the bit (no false negatives). Thus the two conditions establish exact masks without a repeated per-source traversal. Cost is O(applications × nodes + edges), with small bounded masks. The full canonical serialized certificate must be included in the same actual-byte cap and export/import accounting used for SCC certificates.

## Efficient independent finite-cover table

`efficient_cover_table(case, diagnostics=None)` enumerates each subset of the test suite exactly once. It calculates that complete subset's exact coverage, integer cost, and sorted test IDs, then retains the minimum `(cost, IDs)` for each exact coverage mask. Only after all complete subsets have been enumerated does it choose the optimum covering subset for each requested app mask. It does not reuse the candidate's coverage DP or discard a lexical tie before later tests are considered. This distinction handles zero-cost redundant tests correctly.

The result is a dictionary from integer required-app masks to `{feasible, selected, cost}`. Optional supplied diagnostics receive the number of enumerated subsets, distinct coverage masks, and coverage comparisons. The original `minimum_cover` remains unchanged as the slower external oracle. A separate development fixture checks equality for all 64 masks of a six-application, ten-test case, including zero costs; a three-test counterexample checks the nonmonotone lexical-tie issue explicitly. These cases are not confirmation or reproduction inputs.
