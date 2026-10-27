# Odd-cycle zero-error communication: current threshold audit

Audit date: 2026-10-27. These are the strongest primary results identified in
the scoped search, not a guarantee that no unindexed or unpublished improvement
exists. The Myerson partition study subsequently became the active candidate.

## C7 threshold that a new construction would have to beat

Ravi Tandon, *Strengthening Recursive Constructions for Zero-Error Shannon
Capacity*, arXiv:2608.30273, submitted 2026-08-31, constructs an independent set
in the 500th strong power of C7 giving

    Theta(C7) >= 3.25883262035326630912153905181047543760538759432195...

Primary paper: https://arxiv.org/abs/2608.30273
Exact executable companion:
https://github.com/tandonravi/C7-Shannon-Capacity-Heterogeneous-Recursion
Pinned commit: `c753408492dde92a239708986d16c15dbf6c3235`.

The companion's 37 files have been preserved under `tandon/`, with the
Apache-2.0 LICENSE and NOTICE. All 196,068 source bytes were checked against
the Git blob hashes in the public repository tree. SHA-256 hashes are recorded
in `TANDON_SOURCE_MANIFEST.json`.

`python verify_arithmetic.py` was executed successfully: all headline claims
reproduce exactly. This is reproduction using the published finite-count
ledger, **not** a fresh independent proof of every finite certificate. The
more expensive `verify_certificates.py` and `--recomputed` paths were not run
during this audit. No Lean proof of Tandon's stronger result is asserted.

## Earlier baselines and rights

| Source | Identified C7 lower bound | Construction size | Source status |
| --- | --- | --- | --- |
| Itty et al., arXiv:2607.21517, July 23/30 | about 3.258020 | 134753 words in dimension10 | Public repo has no identified license; do not redistribute implementation without a grant |
| Gao, arXiv:2607.27869, July 30 | 3.25878915390869101619676501552067694008291485058374 | dimension200 | Paper source inspected |
| Buys, Polak, Zuiddam, arXiv:2607.29681 v1, July31 | 3.25880536988546557258297503062380675385567149800296 | dimension200 | Paper version must be distinguished from later repository |
| BPZ current Lean companion, Aug10 | 3.25882798592000703452647896579422134484566287064872 | dimension500 | Apache-2.0, pinned Lean proof |
| Tandon, Aug31 | 3.25883262035326630912153905181047543760538759432195 | dimension500 | Apache-2.0, exact Python certificates and paper proof |

BPZ repository:
https://github.com/spectra-research/shannon-capacity-lean
commit `aa21eeb12b75b0413d3fa9fb4208b5d0bf2c4d65`.

Itty repository:
https://github.com/nathanielitty/lower-bounds-for-shannon-capacity
commit `fe8966079013abaac21d1c08441500100f8e3b86`.

Terence Tao's optimizationproblems constant9a record was also checked; its
October15 update still lists Tandon as the identified C7 leader while adding
new C13, C15, and C19 results. Relevant primary record:
https://github.com/teorth/optimizationproblems/blob/main/constants/9a.md
latest inspected path commit `5fad33e4a172a7cfa710e2ed894b6224f6bdf791`.

September/October scoped searches did not identify a later C7 result. Queries
included exact current bound, odd-cycle Shannon capacity, the cited authors,
and the primary record's update history. This supports a dated baseline, not
a universal novelty assertion.

## Exact outcome and established construction space

For the strong product C7^d, vertices are d-tuples in {0,...,6}. Two distinct
words are adjacent/confusable precisely when, in every coordinate, their
cyclic difference belongs to {0,1,6}. An independent code requires every pair
to have at least one coordinate at cyclic distance at least2. Duplicate
codewords must be rejected separately.

BPZ already uses heterogeneous child constructions, substitution DAGs,
reindexing, and certified cardinality arithmetic. Tandon strengthens the
heterogeneous recursion using finite neighborhood-count certificates. Calling
heterogeneous composition, symbolic execution, or shared subexpressions new
would not establish novelty over these primary constructions.

Tandon's base gadget has profile (367,8,367,322,26,19), derived from the BPZ
five-dimensional code. The 367-word independent set itself originates with
Polak and Schrijver (2019). NOTICE preserves this provenance. The encoding is
little endian base7: coordinate k of integer w is floor(w/7^k) mod7.

No new C7 bound, code, production encoder/decoder, or operational model alpha
was established in this audit. The useful result is an updated, reproducible
conventional threshold that can promptly falsify a weak breakthrough claim.
