# Fresh core/security verification

Source: `a163b5b3e34551e5dfdf2075c6f69c8cdb3e0c1f`; tree `f276927ce6ff188a729f40c4942b28bc9d4a2f88`. Checkout remained clean and no source was edited.

Fresh execution results:

- Legacy content identities, archive atomicity, source/copy fences and fixed-SQL rollback: **29 passed, 1 skipped**. The skip is the existing `src.self_edit.tools` dependency check; identity admission is covered by the other executed tests.
- Exact binary/enterprise/source/CLI security: **122 passed**.
- Public-source substitution and hardened XML readers: **62 passed**.
- Black, Ruff, strict typing of the copy-fence module and the actual binary gate against accepted1.43 source all passed. This is not a claim that every legacy module or the complete release campaign passes strict typing or security review.

Raw current logs and JUnit are alongside `verification.json`, `source-inventory.json`, and execution resource records. Earlier failed dependency/runner setup attempts and the DNS acquisition failure remain separate. The exact defusedxml0.7.1 wheel was later verified against the existing lock and installed only into the task QA interpreter. That environment explicitly uses provided QA/primary packages; no clean application installation is claimed.

The legacy test process denied all socket/process launches and observed none. Security tests permitted only fixed local Git and binary-gate CLI commands. Provider keys were cleared, optional clients/models were disabled, and generated patches, preflight and test execution callbacks were mocked. No Docker, native solver, held five-test scope, provider, PG service or model was executed.

`rollback-snapshots.json` identifies four preserved SQLite files under `legacy-fixtures/`: the old backup retains its legacy row; the upgraded backup retains both legacy and post-upgrade rows; the separately restored old database accepts the five-column writer and contains its own later row. Post-upgrade rows are not automatically imported or adapted for that old writer. This proves the stated stop/backup/restore boundary, not seamless rollback, reconciliation, or general crash-safe legacy merging.

Full lifecycle cost, human effort, assistant inference, integration/maintenance cost, monetary cost and revenue remain unknown. Per-run elapsed time, process CPU/RSS and allowed Git/CLI child CPU are QA measurements only. They are separate from declared mission work units and charged native invocation/solve allowances; no synthetic profit or cost-saving claim is made.

The scientific study, fixed worker, transport, server and installation-profile source are byte-unchanged from source739. Profile SHA256 remains `0542301599817d9907e606d6378d9a4eed2fe57eb41bfae86f8333d424aa395c` and still admits only its declared exactAlpha1.42 runtime/environment. This check did not freshly download/install the public wheel, execute the incumbent native solver, re-run confirmation, broaden supported products, or grant production authority. Existing restrictions and the accepted incumbent remain unaffected.
