# Current coordination and one internal maintainer decision

Read-only discovery began 26 October 2026 at 14:23:44 UTC. The final bounded check refresh was at 14:31 UTC. The earlier `value-compounds` package and PR #4931 were not modified. No new confirmation source/wheel body was acquired or evaluated.

## Material coordination change

After the [v1 delivery handoff](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/issues/4850#issuecomment-6418171108), a [new 14:30 product/integration continuation](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/issues/4850#issuecomment-6418571671) proposed ownership of the complete source-pinned Python-upgrade offering and consumer-call/next-action evidence. It explicitly leaves research question, comparators and economics with the writer, and runtime/profile adoption and publication with the existing integrator. This is material proposed overlap, not permission to replace user instructions or a new execution gate. Coordinate the bounded contract experiment with that owner; do not build competing runtime, ledger, scheduler or release infrastructure.

Main remains `804e1afeb78ea48fb4807d76b336803aa0906a20`. The v1 experiment remains `eb07086ac42799ff45f7b1c946a2f7c514bd3bbc`. Root AGENTS.md has the unchanged blob `87359bec27ec868b99cc973507e495575918b9cb`; no new instruction identity was observed.

## PR #4931 is still a draft with a real blocking failure

[PR #4931](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/pull/4931) remains open, draft and unmerged at exact head `f019a1d2d1c1c678c7363bf9cde61dab6ec0de12`. The review read returned zero submissions; no approval is inferred. Its refreshed 24 check runs comprise **19 successes, two failures, one in progress and two skips**. The remaining active check is `offline-qualification`; `bounded-discovery` became successful during this audit. The two `Full software qualification` skips do not establish completed full qualification.

Both `Full lint (ruff)` and its `Lint (ruff)` verdict fail. Exact decoded logs are retained in `pr4931/full-lint.log` and `pr4931/lint-gate.log`, with structured diagnostics and original freeze membership. The full lint log is 204,127 bytes, SHA256 `b0abd3bfda55deb4d09a062fb0d0a5d2074b055a1842f82cf0fc2873084a2cb9`. It reports **98 diagnostics**: 75 E702, 22 E701 and one F841. The verdict log explicitly records full scope and a failed underlying result.

| Affected study path | Diagnostics | In original 20-file freeze? |
| --- | ---: | --- |
| `analysis/ablate_context.py` | 5 | No |
| `analysis/summarize.py` | 23 | No |
| `curation/fetch_confirmation.py` | 27 | Yes |
| `curation/register_local_mission.py` | 19 | Yes |
| `src/worker.py` | 9 | Yes |
| `support/verify_companion.py` | 3 | No |
| `tests/test_pipeline.py` | 12 | Yes |

The [current fast release policy](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/804e1afeb78ea48fb4807d76b336803aa0906a20/docs/agent/FAST_RELEASE_POLICY.md), blob `3e83a4c2d29004a4003b598ea4d8c5c5b442ffc9`, explicitly makes **Ruff lint, including configured E-style rules, blocking**. Only the separate named formatting/duplicate-style feedback is advisory. The [PR workflow](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/804e1afeb78ea48fb4807d76b336803aa0906a20/.github/workflows/pr-ci.yml) invokes `python scripts/ruff_targets.py --run`. Describing these failures as cosmetic exceptions would contradict the actual policy.

No repair was attempted. A future correction must preserve the sealed v1 archive and explicitly identify any post-study source revision. Four failing files are frozen; a silent restyle would destroy their original identity. Full release, Security, binary admission, approved operation, runtime adoption and publication remain separate requirements.

The connector rejected the annotations endpoint and a workflow-file listing endpoint as unsupported URLs. The advertised decoded job-log tool supplied the lint evidence. No restriction was bypassed; no missing release qualification was inferred.

## One real internal maintainer decision

**Assess whether a proposed refresh of the native Agent's locked dependency tuple preserves its actual request-boundary and input-model behavior.** This is a concrete internal readiness decision grounded in current Alpha source and requirements. It is not asserted to be an existing paid customer order or pending dependency-bump ticket. The bounded open-PR search found no bump-title PR; older broad requirements/CI PRs do not manufacture present demand.

The correct incumbent profile is [requirements-agent.lock](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/804e1afeb78ea48fb4807d76b336803aa0906a20/requirements-agent.lock), not the older general `requirements.lock` or the prior research machine's installed environment:

| Native Agent dependency | Exact locked version |
| --- | --- |
| FastAPI | 0.141.1 |
| Starlette | 1.7.0 |
| Pydantic | 2.13.5 |
| pydantic-core | 2.46.5 |
| pydantic-settings | 2.15.0 |
| HTTPX | 0.28.1 |
| anyio | 4.15.1 |
| cryptography | 50.0.1 |
| uvicorn | 0.53.0 |

The complete native lock is preserved at `requirements/requirements-agent.lock`: 85,690 bytes, Git blob `d450350998018b691f04fa99093d2fef68b929f0`, SHA256 `d58df2a38d099f8123d7445f62fec4684d029e588ce4b615151387c4decd1392`. The same blob exists at both the experimental and current main commits. The newer display URL does not change the consumer revision.

The general/core lock instead pins FastAPI 0.116.1, Starlette 0.47.2, Pydantic 2.11.7, pydantic-core 2.33.2 and cryptography 45.0.5. Native pyproject requires cryptography >=50.0.1,<51, whereas legacy core requirements specify ~=45.0. These profiles must not be silently combined or substituted to create a weak baseline. This audit has not established that every documented legacy/full installation path combines them.

## Useful bounded acceptance surface

The already exposed [RequestBoundary source](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/804e1afeb78ea48fb4807d76b336803aa0906a20/alpha_factory_v1/core/runtime/api.py), Git blob `6defd24dc48b6e0324dc60e8a3cff9582f330d1c`, accepts an ASGI callable directly. Its contracts include security headers; forwarding of non-HTTP/nonmutation traffic; ambiguous-framing rejection; valid Content-Length; declared and actual body-size limits; same-origin mutation; exact length agreement; timeout/disconnect; and exact body replay. These are observable consumer behavior, not merely upstream signature changes.

The repository test location is `tests/runtime/test_api_boundary.py`, blob `ce8df8ce4157b4f0dba2f45dfc5c9935f000ccaf`, unchanged between both source commits. The v2 copy is 5,089 bytes, SHA256 `afa41ae0e428e9be048544e03daaf7a4e2c3e45a0b83d889d6883e8121fdcd45`. This audit did not execute those tests. General development metadata declares pytest 8.4.1 and separate helpers, but the full legacy dev environment is not silently substituted for the native profile.

A bounded component harness can supply an inert in-memory ASGI application and explicit input-model cases. It must not construct `create_app`, activate Engine, create/open Journal, generate credentials or cross a held operator path. Any source extraction must be labelled; component compatibility is not complete application/profile installation qualification. Acceptance should report actual responses/model results, supported source identities, failures and unresolved full-app obligations. A later changed release tuple can warrant another representative mission; repeated unchanged checks do not count as new customer jobs.

No new upstream candidate source bodies, wheels or confirmation outcomes were inspected in this discovery. Exact costs of research-model inference remain unknown; read calls, failures and local actions are recorded in the v2 metering lane.
