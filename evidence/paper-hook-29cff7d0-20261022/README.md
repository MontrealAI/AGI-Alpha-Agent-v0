# Paper release hook correction evidence

This packet binds the nine-file correction in [PR #4854](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/pull/4854) to public commit `29cff7d0ba8df59491eaf881cacb23f3f1725025`, tree `9154e21dce81eb59edefb4be722da086138af665`, normal parent `bd98d353735a03969783f0255f07d9c9cfb8745f`. The unsigned public commit and local `ff8e7874` have exactly the same tree. The final nine source files match the independent annotation follow-up's raw hashes.

The validators retain exact builtin type checks, rejecting booleans, numeric coercion and integer subclasses. Three validator ASTs and the Out-Execute browser string AST are unchanged. A fixed field-tuple alias and a named homepage slice offset normalize to the original expressions. Narrow documented E721 exceptions replace no schema checks; no global lint or scanner rule is disabled.

| Evidence | Recorded scope |
| --- | --- |
| Sixteen final configured hooks | Each `--all-files` hook passes on clean local `ff8e7874` / tree `9154`; raw outputs and hashes are retained losslessly in `checks/hooks-final-9154.json`. |
| Environment limits | The installing `env-check` hook was not repeated against a shared runtime. `update-actions` was not run because this correction changes no workflow files. This is not an aggregate full pre-commit pass. |
| Focused regressions | The initial pre-annotation campaign passed 616 cases; independent pre-annotation review passed 329 scoped cases. The final three test annotations and equivalent patch target passed all 17 affected cases. Results retain those source-stage scopes. |
| Typing | Six production/browser paths pass strict mypy 1.17.0. The broader pre-annotation nine-path attempt failed with 145 diagnostics in three largely untyped test files; the complete failure remains included. |
| Additional Python scanner | The 151-rule scan reports nine files, one retained finding and four ignore-pattern skips. Its raw warning and rule metadata remain included. Independent source-specific review shows the matched lambda appends a Playwright URL to a local list and issues no request. No suppression was added. |
| Public state | The timestamped snapshot records a completed no-findings configured code review for exact `29cff7d0`, with fresh hosted checks still pending. It is not main, release, security-review or publication qualification. |

The first final-source ESLint attempt found the local ignored dependencies absent. The repeated check passed after restoring only the owned ignored directory's read-only references to existing dependencies with the exact same lock hash and an owned checksum stamp. No package installation or write to shared dependency files occurred. Both attempts remain in the packet. Earlier Ruff-format and Node-version failures are also retained.

`manifest.json` is a finite inventory of all other packet files with byte counts, SHA-256, Git blob SHA-1 and intended Git modes. The three hook JSON packets preserve the original log content as UTF-8 strings with its own byte count and digest. They consolidate transport only; decoding each `rawUtf8` string recovers the original complete log bytes. No source or evidence execution is needed to inspect these records.

Earlier direct-entrypoint/catalog evidence remains in the [14-file bd98 evidence packet](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/tree/a6117cd4038309093651de4a7148ede0f46d773e/evidence/paper-entrypoint-bd98-20261022). The current packet does not relabel those results. Prior bd98 workflows are recorded as historical completed runs, including optional skips; they do not qualify the new head.

Required hosted final-head checks, integrated-main checks, complete release environment and coverage, packaging, Pages and downloaded public-byte verification remain separate gates. Same-session AI technical reviews are not human or institutional approval. This evidence work performed no browser retry, prohibited execution probe, credential change or public mutation.
