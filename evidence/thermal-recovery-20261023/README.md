# Retained evidence and exact worker identity — 23 October 2026

This is the focused correction of PR #4871 review findings
[4355004521](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/pull/4871#discussion_r4355004521)
and [4355004532](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/pull/4871#discussion_r4355004532)
on predecessor `e5314c0676b64ce58ea21c12846ff95ac729ea73`.
It is local recovery/integrity evidence, not an independent acceptance, software
release, physical validation, payment or live deployment.

## Executed checks

| Check | Actual outcome | Raw evidence |
| --- | --- | --- |
| CLI export with the old family removed from the current worker | Three terminal-state regressions failed before the fix | [Complete failed output](export-before-fix.log) |
| First retained-export correction and unsafe/corrupt storage cases | 8 passed, 23 deselected, 3.12 s; before the later worker-binding and scalar-type additions | [Focused output](export-after-fix.log) |
| Complete native workbench selector | 19 Node groups, 39 Python cases; zero failed/skipped; 17.713 s | [Complete TAP and Python output](native-selector.log) |
| Complete-worker generator | 3 passed, 0.23 s; clean-copy reproduction and wrapper-only limit/dispatch mutations | [Original receipt](generator/receipt.json), [commands](generator/commands.jsonl), [JUnit](generator/generator-regression.xml) |
| Final type narrowing in the generator test helper | 3 passed, 0.66 s; production code unchanged after the combined selector | [Output](generator-final-typed-fixture.log) |
| Runtime typing | 54 files passed | [Output](runtime-identity-mypy.log) |
| Strict generator/test typing | 2 files passed | [Output](generator-mypy.log) |

The full selector used Node **22.17.1**, Python **3.12.14** and pytest **8.4.1**:

```sh
node examples/successor-workbench/test.mjs
```

The existing selector now includes the three generator cases in its existing
Python subprocess. No workflow, dependency or new release gate was added.
Affected Ruff lint/format and source/document whitespace checks passed. The full
staged whitespace check reports spaces in the original pytest failure traceback;
those raw evidence bytes are deliberately retained, with no check configuration
changed. The separate read-only
source audit found no new blocking defect and prompted a canonical bool/int
request-binding check. That audit is a same-session code review, not institutional
independence or the repository's configured review.

## What is bound, retained and refused

CLI `run` recovery and `export` reverify the signed journal and exact request/result
commitments. They check the retained v1 pack, artifact hashes, count/content bounds,
reserved names, traversal and case-insensitive collisions before creating an
output directory. They write the exact inert artifact bytes, lifecycle and signed
local receipt. They do not call the current worker, append an event, re-execute the
job, change its local review or create authority. An untrusted imported pack still
passes through the current worker's inspector.

The generator adds `workerSHA256` to the existing source manifest. Its value is
`50f09fdfb9b8b1f5a9e03e6a30af99181daf633a14c7e46a9c06154fd27c6ad9`, matching
the unchanged **125,843-byte** generated worker. New lifecycle freezes include an
`adapter-worker` source artifact. Before unfinished work reaches planning or
consumes another attempt, both module and worker identities must match; actual
worker bytes must match the manifest. Wrapper-only changes, corrupt manifests and
legacy unfinished records missing that commitment are refused. Completed history
remains available without consulting the manifest. The three-attempt budget,
explicit interruption recovery and stopped/retired refusals remain exercised.

Both execution and the freeze-time Node version probe scrub inherited preloads
and credential settings. No networking, identity admission or financial provider
is added. This is not arbitrary stored-format migration or inferred qualification
of old unfinished work.

## Unchanged evidence and public predecessor

The nine workbench source hashes, 53 mathematical capability source hashes,
native worker, both browser copies, generated license and four tracked service
workers are unchanged. The [generator receipt](generator/receipt.json) gives
their actual hashes. The first metadata capture had a nonexistent-path error;
that setup error is disclosed in the receipt and did not execute a scientific
campaign. The later type-only test-helper correction is recorded separately,
rather than rewriting that earlier receipt.

The 278 changed public files of `e5314c0` were actually downloaded: all **4,339,952
bytes** matched length, SHA-256 and Git blob SHA-1, with zero retries or failures.
The [complete compact receipt](published-e531-compact.json) is also published in
[PR comment 6354686911](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/pull/4871#issuecomment-6354686911).
This attests that predecessor's public source bytes, not the subsequent correction
or any release/install/browser outcome.

The [machine-readable follow-up](recovery-review.json) binds the affected source
files and precise check scopes. These later verification costs are not silently
assigned zero or included in the earlier mathematical operation ledger. Existing
scientific, EVM, held-facade and public-browser evidence keeps its original source,
identity, limitations and owner. No held implementation was copied, review state
fabricated or publisher restarted.
