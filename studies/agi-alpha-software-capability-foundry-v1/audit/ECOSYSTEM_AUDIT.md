# Software Capability Foundry: ecosystem audit

Audit date: 25 October 2026. Public repository reads are current to this session. Source files are pinned and SHA-256 inventoried in `source-manifest.json`; complete tree/release metadata is stored separately. This audit makes no new software-release or native-execution acceptance claim.

## Current sources and release windows

| Repository | Exact main commit | Public release observation |
|---|---|---|
| AGI-Alpha-Agent-v0 | `f836f06e8351e64db1da770e16e304b5feb01f28` | Latest stable API release `v1.43.0`; the existing Strategy `v1.44` window remains unqualified/unpublished. |
| AGIJobsv0 | `bc4abbd5c28f3672275b13300e40ea26c820b8ee` | Public prerelease `discovery-v2.1.0-rc.21` at that exact commit; latest-stable endpoint is absent because releases are prereleases. |
| AGIJobManager | `5d5670df9dbbc79da115e0a44b71989f34df58c1` | `v1.20.2` at that exact commit. |
| AGI-Fleet-Linux | `45759fb096faf8988f58ae5ea71248d0f35a97c7` | Local Skills `v0.1.0-local-skills-preview.5` at main; operator `v1.1.4-qualification` at `7b5dda3d7dbcb9700a1408cf19bd7cf18404e068`. Proposed operator 1.1.5 remains separate and unadopted. |

The authority map is [#4850 comment 6384166924](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/issues/4850#issuecomment-6384166924). The latest retrieved Strategy update is [6393676138](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/issues/4850#issuecomment-6393676138): existing PR #4899 remains with its owner, who is restoring required official `p/python` scanning after an exact-source review found its replacement. The bounded Strategy scanner is additive. Do not alter this release work or its evidence.

## Held operations and ownership

[Original decision record 6386746278](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/issues/4850#issuecomment-6386746278) distinguishes:

- Fleet #61 stopped review of `0b13d3ffb25381dc2ebf9c39abda24824660fd3b`, a narrower metadata follow-up, and unresolved P1 threads `4322083594` / `4323870690`. The original execution-platform decision payload, ID and complete scope remain unavailable. Another actor/ref/review does not clear the restriction.
- Harness #4863 original configured review of `c455ad4ce109c86df2fef09d19674810290b5185`, whose actual terminal result is unknown, and its distinct merge denial in comment `6347342683`. Neither is resolved by a new study.
- Five held Alpha source/test files are byte-preserved by `scripts/check_held_native_source.py`; finite excluded outcomes remain unqualified. This research must not invoke their held native objectives.
- The existing source owners and integration/publisher owner remain authoritative. Public study preparation is not permission for their held operations, a new production scheduler, mainnet transactions or release bypass.

## Supported environments and policy

Alpha `AGENTS.md` was read completely: Python >=3.11,<3.14, web Node 22.17.1, locked dependencies, Apache-2.0 headers, public type hints, lint/type checks, and honest failed/unrun-check disclosure. Draft/PR opening does not require successful local hooks, but hosted merge/release gates are retained. `FAST_RELEASE_POLICY.md` requires one full Python 3.12 offline regression with >=80% coverage, installed acceptance on Python 3.11/3.12/3.13, five platform-smoke cells, blocking security/integrity/type and source/artifact checks. Cosmetic advisory treatment cannot relax correctness. Official Semgrep `p/python` remains required.

Jobs package pins Node 22.23.3/npm >=10.8,<11; its installed release matrix also includes 24.21.0 on Ubuntu 24.04. Manager specifies >=22.23.2 and its current publisher uses 22.23.2; coordination records 22.23.2/24.21.0 bounded installed acceptance. Fleet native operator qualification explicitly has Linux x64 and ARM64 saved-archive cells; both remain required for a new operator release. No claim is made that this study executes all supported platforms.

Fleet requires exact saved-archive gates, canonical upstream/vendor inventories, preserved STOP and spend/authority journals, inactive restore, EN/FR checks, and eligible independent owner review for authorization/workflows/auditors/vendor boundaries. Manager requires its exact-head qualification workflows, permanent published assets/tags and no deployed contract changes.

## Predeclared development candidates

### A. Committed companion source retrieval

`scripts/strategy_engineering_release.py::_committed_files` reads a fixed companion package inventory. On pinned main it returns **37 files / 456,459 bytes**. It performs one `git ls-tree`, one `git show` to inspect pyproject, then one `git show` per returned file (pyproject is read twice): **39 subprocesses**. Three development-only observations of the unmodified function were 70.31, 64.80 and 70.79 ms wall, 63.90/59.10/65.02 ms child CPU and 7.94/8.06/8.74 ms parent CPU. These are diagnostics, not confirmation or hosted CI savings.

Potential improvement: a bounded, exact-object batched reader that preserves path/mode/size restrictions, byte contents and output mapping. Its reuse interface is a source-commit inventory, selected paths, bounds, and byte results. `git cat-file --batch` is a mature specialist; all comparators must receive it. Batching is a conventional optimization, not a new learning mechanism.

### B. Gallery cache source verification

`scripts/paper_changes.py::blob` issues `git cat-file -s` and `git cat-file blob` for every selected path. `expected_workers` verifies the catalog plus **437 cache assets / 16,135,527 bytes** selected by `build_service_worker.is_cache_asset`: **876 subprocesses** excluding tree acquisition and other transition checks. Changed inventory, file sizes and output structure distinguish this from A. The full correctness target is identical source bytes and all three `render_scripts` worker outputs, not merely a fast digest.

### C. Archive-versus-source drift localization

A distinct later tool can consume the retained reader to identify missing, unexpected, changed and mode-mismatched archive members without extracting or executing them. A direct native incumbent should also be allowed: `scripts/accept_public_strategy.py::core_payload` already compares archive bytes with Git blob identities **in process**, so it is an especially strong conventional alternative. It does not run `git show` for every core member. A new drift tool must preserve duplicate/path/size/symlink/refusal checks and cannot be credited as a successful successor merely for calling a parent in search; its selected served execution must use that parent.

### Distribution shift

Symlinks, gitlinks/submodules, missing paths, oversized members, invalid object IDs, line-break/path protocol hazards and mutated archive input require explicit refusal or a bounded supported fallback. Never bypass release/security checks to earn speed. Repeated reuse needs actual recurrence evidence; these repository call sites establish recurring demand, not market volumes.

## Eligible existing integration seam

`examples/successor-workbench/engine.mjs` exposes `createWorkbench(adapters)`, where each adapter has exactly `{manifest, validate, execute}`. Manifest fields are `{id, version, en, fr, scope, artifact}`. `execute(input, checkpoint)` returns `{decision, summary, evidence, artifacts, limits}`. `run(spec,{sourceHash,signal,onProgress,onCheckpoint})` creates a source-bound workbench pack and the existing seven-stage compilation, supports cancellation/checkpoints and enforces a 60-second bound. `inspectPack` checks pack/artifact hashes and recompiles the plan.

Existing pack semantics remain `PUBLIC_LOCAL_EXECUTION`, independent proof false, admission HOLD, zero provider/settlement spend, monetary compute cost and human effort unknown, and `NOT_CONNECTED`. A browser local computation through this seam is not the original held Harness, an approved external executor, live Jobs settlement or Fleet admission. An additive adapter may use this released seam unchanged and export inspected evidence while leaving these labels intact.

## Evidence inventory

- `source-manifest.json`: exact pinned URL, SHA-256 and byte count for audited policy/runtime/verifier sources.
- `development-portfolios.json`: exact A and B path inventories, modes/Git blob identities, sizes and A SHA-256 values.
- `development-committed-files-diagnostic.json`: three actual development-only timings.
- `issue4850.json`: retrieved issue and comments; complete HTML-free comment bodies.
- `coordination-*.md`: original restriction/ownership and bounded-delivery excerpts.
- Repository JSON files: raw source, tree, open-PR and public release metadata; source metadata read only.

No repository source, tag, release asset, reviewer disposition, deployed contract or production scheduler was changed by this audit. No external messages were sent by the audit agent.
