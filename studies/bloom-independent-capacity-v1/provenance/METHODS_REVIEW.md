# Methods consistency review after frozen execution

Review scope: `bloom_study/paper_drafts/methods.tex`, frozen `protocol/PROTOCOL.md`, `protocol/FREEZE.json`, `core.py`, `generate.py`, `independent/reference.py`, `run_study.py`, `analyze.py`, and the already inspected frozen confirmation/reproduction results. No source, analysis, protocol, or manuscript was edited. No additional experiments or plot tests were run.

## Overall verdict

The two certificate propositions and their proofs agree with the implemented checks. The distinction between competitive comparison and receiver artifact withholding is correct. The method draft preserves the supplied-graph scope, shared construction primitives, complete operational CPU, 48/24 world split, three-contrast family, approximate bootstrap coverage, and unknown commercial cost. Those core claims should remain.

## Required reporting correction: incomplete-input intervention

Frozen protocol line 31 describes removing “an edge.” Frozen `core.py` lines 376–379 remove **every edge whose dependent is the last application** and set the first query to node zero. `generate.py` already sets that first query to node zero and adds its direct edge to the last application. `run_study.py` line 64 explicitly records the stronger challenge design in each audit.

The paper should not describe this as a random single-edge failure study or interpret its 48/48 world omissions as a natural corruption rate. Suggested methods sentence:

> The incomplete-input challenge deliberately removes all incoming edges to the final application while retaining the complete graph as the audit reference. The first query changes node zero, which originally has a direct edge to that application. This targeted challenge tests an observability limit, not the frequency of accidental omissions.

Add a brief retained discrepancy in the deviations/limitations account:

> The frozen protocol's prose says “an edge,” whereas its simultaneously frozen implementation deletes all incoming edges to the final application. The executed stronger intervention and its audit labels are preserved. This out-of-scope diagnostic is excluded from the primary quality and timing gates.

Do not change the frozen protocol or source to erase the mismatch.

## Precise changes to the methods draft

1. **Memo verification is broader than the current wording implies.** After Proposition 2, the draft says supplied memo rows are independently replayed and “Uncached and direct outputs receive fresh BFS checking.” In fact, `execute_successor` checks **every query output** for both `partial_bfs` and `direct_program`, including cached memo outputs (`core.py` 357–363). Replace with:

   > Memoized operators advertise partial rows, each checked against independent BFS. Every memoized and direct query output also receives fresh BFS checking, including queries answered from a cached row.

   This matters for interpreting the measured fallback cost.

2. **State the second conventional policy exactly.** “Every policy can use” the full five-operator palette can sound as if the reverse reference is another optimizing selector. Candidate and expert consider the full palette. The fixed reverse policy deliberately chooses reverse, then memo, then walk according to availability, with the shared payload fallback (`core.py` 211–220). Suggested replacement:

   > The shared implementation exposes direct traversal, memoization, component propagation, reverse indexing and bitset Warshall closure. Candidate and expert policies choose from that full palette. The second conventional reference commits to reverse indexing with legal memoized/direct fallback. All receive the same workload information and qualification and storage rules.

3. **Report all diagnostic arms.** The intervention paragraph does not explicitly mention the one-run direct-walk ablation or delimit the unsafe arm. `run_study.py` adds one direct-walk stable trial and one BLOOM tampered-artifact trial with receiver verification disabled per world. Add:

   > Two additional diagnostic arms run once per world: a direct-walk policy and tampering with receiver certificate checks disabled. They remain outside the primary competitive and artifact-benefit estimands; all outputs are retained and independently audited.

   The unsafe intervention flips a bit in the first supplied row, and node zero is the first queried source. Its 48/48 incorrect outcomes are a deliberately targeted boundary test, not a general-world failure-rate estimate.

4. **Make the actual supported input bounds visible.** The draft states the study's six applications and ten tests. The reusable implementation separately enforces at most **ten applications and twelve tests** (`independent/reference.py` 15, 30–31), and `Graph` rejects nonpositive costs (`core.py` 57–58). Add those limits in the model/walkthrough so users do not infer arbitrary test-catalogue scalability. The paper already correctly declines to infer regression-fault preservation from finite coverage.

5. **Use executed tense for the freeze.** Replace “Protocol, source and analysis must be frozen and durably committed before confirmation” with an observed statement tied to `FREEZE.json`: the freeze was recorded at **2026-10-24T02:02:15.373234+00:00**, before confirmatory execution. The record's `confirmation_opened: false` is a historical pre-execution field, not a current-status assertion. Describe the independent reproduction as a separate agent/process within the same project and inherited runtime, not an outside institution or new hardware environment. Preserve the original analysis's pending G1 field and cite the later independent receipt overlay.

6. **Limit the linear-checking statement to the structural certificate passes.** The SCC and reverse certificate scans support the draft's stated structural bounds (with mask/integer costs explicit). The wrapper also validates inputs, sorts adjacency lists, serializes, hashes source and artifacts, and performs coverage checking. Suggested clarification:

   > These are bounds on the structural certificate passes; validation, canonicalization, adjacency sorting and other wrapper work are measured separately and remain in complete operational latency.

7. **Name the resource envelope narrowly.** The 1,200 CPU-second gate covers measured scientific campaigns tracked by the runner. Authoring, public-source retrieval, reporting/plotting and native integration costs require the separate ledger; unknown costs are not bounded by that number. “Scientific execution is capped” is acceptable when kept distinct from “total research cost.” The 256 MiB value is an evidence allowance, not a price or detector budget.

## Secondary reporting checks

- Protocol line 25 promises an optimistic conventional oracle lower bound. `analyze.py` reports the globally best conventional **mean**, which is not the per-world minimum oracle. The methods draft does not falsely claim that this oracle is already reported. If a later results paragraph uses “oracle,” either provide a clearly identified descriptive calculation from the frozen per-world medians or retain the omission explicitly; do not rename the best overall mean an oracle.
- The predeclared Wilson interval is over worlds for which all eligible trials were correct, not over 2,016 independent trials. The balanced factorial worlds and disclosed generator limit population interpretation; do not present a Wilson lower bound as universal software correctness or industrial representativeness.
- The three percentile-bootstrap intervals are a nominal simultaneous family, without a finite-sample coverage guarantee. The draft already says this correctly. Fresh reproduction must remain separate and cannot rescue failed confirmation by pooling.
- The phase plot uses the observed median-total-CPU replicate within each world, then averages all phases from that same record. Its stable totals exactly equal the primary world-median means. Do not describe that plot as the mean over all three repetitions or as independently medianed phase durations.

## Bibliography provenance

`project-references.bib` includes the required `boucher2026ti`, `boucher2026execute`, `boucher2026economy` keys, Writer #4/#5, four repository snapshots and exact native/source references. All five retained TeX sources were matched to pinned registry SHA-256 or Git blob identities; 34 integration-source SHA-256 values were rechecked. `Invent_the_Economy` exists at the inspected Alpha commit but is absent from the inspected publication index. Writer #4 attribution remains MONTREAL.AI / Writer #4; Writer #5 retains MONTREAL.AI with research direction by Vincent Boucher.
