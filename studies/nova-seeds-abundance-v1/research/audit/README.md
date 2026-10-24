# Independent post-run audit

Run from the study root:

```sh
node audit/verify_results.mjs results/holdout-01
```

This read-only auditor replays every stored schedule against the disclosed synthetic world, verifies mission/payload/outcome bindings and Jobs signatures, checks Fleet ledger chains, checks equal planner-visible inputs and delayed-QC timing, recounts all policy groups, and checks clone semantic equality and nominal expert objective agreement. It establishes artifact consistency, not physical truth or independent organizational custody. It accepts the study's self-declared fixture trust stores and evaluates signatures at their recorded issuance time.

Inputs may be `missions.jsonl` and `ledgers.jsonl` or their `.gz` forms. Both are read as line streams; gzip decompression is also streamed, so the auditor does not materialize expanded logs. If both forms exist, the uncompressed file takes precedence and the selected paths are recorded in the report. `metrics.json` remains an ordinary small JSON file. Compression changes storage representation only and does not alter the policy, evidence, or verifier semantics.

The auditor is analysis code outside `src/` and `vendor/`; it does not change any experimental policy or generator. It was validated on pilot-03 before holdout results were accessed. An initial audit had 30 false ledger-binding rejections because this new checker looked for `evidenceSha256` at the record root; Fleet's actual schema places it under `record.event`. The checker was corrected to the inspected schema, and the original failed audit was retained as `evidence/independent-pilot-replay-audit-initial-checker-error.json`. The corrected pilot audit verified all 42 rows, 30 signed receipts, and 30 ledgers without error. No experimental result was changed by this correction.

After the pre-freeze storage correction, the same auditor also read `results/pilot-final` directly from gzip: 6 missions, 42 rows, 30 signed receipts, 30 ledgers, zero errors. Its inspected experiment source-inventory digest was `0011228ddfd4a2e822659a0286864211b6c8eb99b93a3e39b9ba2cd3a582d08a`. The earlier source review remains a historical record of the revision it inspected. This final pilot confirmed the same equal-input, delayed-QC, separately keyed receipt, clone-equivalence and nominal-expert checks for the compressed output path. No holdout result was accessed during these pre-freeze checks.
