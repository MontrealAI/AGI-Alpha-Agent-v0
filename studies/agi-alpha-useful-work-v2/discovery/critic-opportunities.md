# Critic discovery: make a consumer decision executable

**Decision:** select a requirement-linked, executable consumer assessment with a mechanically derived decision as the next structural production change. Consumer-first signature closure is a useful supporting repair, but a larger static call census is not the acceptance endpoint. Do not build a general Python dispatch analyzer in this allowance.

This recommendation uses only preserved Next Upgrade v1 inputs/results and the already captured Alpha consumer slice at commit `eb07086ac42799ff45f7b1c946a2f7c514bd3bbc`. No new confirmation input or outcome was inspected, no candidate was constructed, and no frozen v1 file was changed. These inspected histories are now **exposed development evidence for v2**. The critic helped build v1's conventional comparator; this is disclosed, not a claim of outside blind review. Exact input identities are in [critic-source-identities.json](critic-source-identities.json). A separate verifier must adjudicate the critiques below; creator–critic agreement is insufficient.

## Consequential discrepancies

### C1. Change-first construction starves the consumer analysis

**Location:** v1 [`src/pipeline.py`](../../value-compounds/src/pipeline.py), `assess`, lines 79–102, builds reports only inside `for path in changed`. [`src/consumer.py`](../../value-compounds/src/consumer.py), lines 507–511, requires a producer report to supply every resolved target's signature.

**Observed discrepancy:** in the preserved first FastAPI conventional packet, the four reported modules are `fastapi`, `fastapi.dependencies.models`, `fastapi.dependencies.utils`, and `fastapi.routing`. Of the 57 direct dependency-import references in Alpha's consumer slice, 38 resolve to captured modules that are unchanged and therefore have no report:

| Captured consumer target | References | Producer module | Why the v1 signature is absent |
|---|---:|---|---|
| `FastAPI(...)` | 1 | `fastapi.applications` | Unchanged module omitted from report construction |
| `Header(...)` | 6 | `fastapi.param_functions` | Same |
| `Depends(...)` | 23 | `fastapi.param_functions` | Same |
| `HTTPException(...)` | 8 | `fastapi.exceptions` | Same |

The raw packet records successful import-target resolution for these references followed by `source-pinned-supported-signature-unavailable`. Its manifest confirms all three modules are unchanged. The captured declarations are direct, undecorated and contain respectively 38, 32, 3 and 4 parameters; this inspection does **not** substitute for the complete scope checker. The other 19 references are `FileResponse` (14), `JSONResponse` (4), and `Request` (1): the trace leaves FastAPI and stops at uncaptured `starlette.responses` or `starlette.requests`.

Evidence: [`0003-fastapi-1-conventional.json`](../../value-compounds/results/confirmation/repeat-1/evidence/0003-fastapi-1-conventional.json), SHA256 `898723b41ecec47a305ea104c7be21ca695491a27c8d72efa126582e7f38e848`. Example: captured [`api.py`](../../value-compounds/data/development/alpha-consumers/alpha_factory_v1/core/runtime/api.py):131 resolves `FastAPI` to `fastapi.applications.FastAPI.__init__`, but no signature is supplied.

**Purpose relevance:** a source change can alter routing/serialization behavior while the application's entry-point declaration remains unchanged. Conditioning all evidence construction on changed declarations prevents the system from assessing the application entry points needed for an upgrade decision. A source-bound demand closure should collect the declarations required by the declared consumer contract, including unchanged modules and explicitly pinned transitive reexports. It must preserve unresolved status where source/dispatch remains unsupported.

### C2. Report acceptance is disconnected from the user's acceptance criterion

**Location:** v1 `pipeline.py`:109–121 computes `ASSESSMENT_READY` from upstream report-validation agreement. Consumer coverage does not determine that status. The same first FastAPI packet is ready with **10,172 unresolved calls, zero preserved bindings and zero established affected calls**.

**Consequence:** this is a valid bounded source report, but it cannot answer whether an actual Alpha function still delivers its required outcome. A successful report checker and a complete call census cannot supply missing behavioral evidence.

**Purpose relevance:** the next production representation should bind the maintainer's question, required acceptance assertions, source/environment identities, executed evidence and allowed decision in one machine-checked record. A missing, failed or stale required assertion must prevent a positive scoped decision. Mere agreement between agents or a favorable prose summary must not be an alternate admission path.

### C3. The apparent denominator hides the actual dependency surface

**Location:** v1 `consumer.py`:310–368 resolves import-name chains but leaves instance dispatch outside scope. Captured [`provider.py`](../../value-compounds/data/development/alpha-consumers/alpha_factory_v1/core/runtime/provider.py):147–172 uses `AsyncClient`, streaming, HTTP status checking and byte limits; constructor binding alone does not test these outcomes. Captured [`af_requests/__init__.py`](../../value-compounds/data/development/alpha-consumers/af_requests/__init__.py):18–34 dynamically loads the installed Requests distribution or a fallback and rewrites module bindings.

**Consequence:** zero directly attributed Requests/urllib3 calls is not evidence of no use. Conversely, the 10,172-call census includes builtins and unrelated code, so reducing that entire unresolved count is not a meaningful customer acceptance target. The known Starlette/HTTPX development demonstration establishes one historical runtime incompatibility, not a current Alpha failure or a fresh v2 result. Its HTTPX 0.27.2 baseline also lay outside Alpha's then-declared >=0.28 range, as v1 [`consumer-methods.md`](../../value-compounds/discovery/consumer-methods.md) discloses.

**Purpose relevance:** start with a named application contract and its real dependency environment. Report the unresolved remainder without treating it as proved risk, proved safety, or completed work.

## Bounded opportunity screen: three candidates

| Candidate production change | Useful outcome and recurrence | Strong conventional alternative | Assessment |
|---|---|---|---|
| **1. Consumer-first signature/source closure** | An attributable report for actual imported targets, including unchanged modules and pinned transitive exports; warranted by a changed consumer, dependency lock or acceptance requirement. | Griffe snapshots/export resolution plus ordinary source traversal and the existing conventional witness checker; equally allowed to retain assets. | Well-supported orchestration repair. Likely removes some avoidable uncertainty, but does not establish behavior. Retain only the scope needed by candidate 2; do not claim all 57 resolve without running it. |
| **2. Requirement-linked executable probe and decision record** | A maintainer receives an exact environment proposal, the actual consumer outcome, a verified scoped decision, and reproducible next action. Reuse the probe contract on a substantively changed lock/source/requirement. | Ordinary project integration tests using pytest/unittest and isolated version environments, with Griffe/release review when useful. Give this builder identical package execution, fixture, cache, source and construction rights. | **Recommended primary.** It closes the missing evidence-to-action bridge. The reusable asset is the actual probe/decision contract and its runner, not the historical success or a generic dashboard. |
| **3. General instance, dynamic import and whole-program dispatch inference** | Broader static impact discovery across wrappers/frameworks. | Established static analysis, targeted grep/source review, and direct project tests. | Reject in this allowance: difficult soundness and environment assumptions, uncertain coverage/maintenance, and no need to solve it before delivering one bounded consumer decision. |

This screen identifies an observed internal project capability and a representative maintenance need, not a paid order. Recurrence is plausible when relevant source/locks/requirements change; frequency, human effort and demand remain unmeasured. No savings or payback follows from selecting candidate 2.

## Proposed first useful job and finite acceptance

Use Alpha's existing **request-boundary behavior under a declared dependency environment** as a concrete development job. The source describes an authenticated local operator API; `api.py`:35–112 already specifies how requests are framed, bounded and rejected before reaching mutations. This is more consequential than a health-check-only smoke test.

The first accepted deliverable should answer: **Does this exact environment preserve the declared request-boundary contract, and what should the maintainer do next?** Exercise the unchanged captured `RequestBoundary` through in-process ASGI, using the real pinned framework libraries and a harmless recording downstream application. Require normal-body forwarding exactly once, byte-for-byte body preservation, required security headers on successful and rejected responses, and the documented malformed-length, over-limit, mismatched-length and cross-origin rejections with zero downstream invocation. The critic does not prescribe observed results; record failures honestly.

This tests a real Alpha component, but does not test all `create_app` routes, the signed journal, authentication, execution or deployment. Do not label the harmless downstream application the complete production API. If a complete route contract is selected instead, obtain its actual execution closure and applicable authorization rather than mocking away the behavior being claimed. In particular, `store.py`:282–314 shows `Journal.initialize` creates signing keys and an API token; a local fixture must not silently expand this study into credential provisioning or operator-profile access.

Deliver source/environment hashes, exact locks, runnable probe, stdout/stderr, assertion-level observations, verification result and one bounded next action. A pass permits only the stated local contract decision; an observed regression supports holding the proposed bundle and retaining the verified baseline. An absent baseline, incomplete dependency closure, timeout, missing receipt or uncertain assertion yields an explicit unresolved decision. A remedy is optional until demonstrated; do not invent one to force a positive result. The evidence package itself should be complete enough for a maintainer to reproduce the judgment.

## Causal test and critic–verifier separation

1. **Produce the first job before claiming improvement.** Use the strongest available conventional method to deliver the development contract above. Record actual construction, failed attempts, environment acquisition and all resources. This becomes an exposed task, not later confirmation.
2. **Freeze the retained asset and primary criterion before fresh inputs.** Specify consumer contract, admissible environment, source closure, per-assertion oracle, decision policy, costs and maximum discovery allowance. Select fresh substantively changed dependency/source missions without inspecting outcomes; do not recycle v1's public histories as unseen. Unchanged reruns are timing/reliability checks, not new jobs.
3. **Compare equivalent outcomes.** Preserve v1's actual incumbent tools and limitations; add the new retained asset; allow a competent conventional builder to build and keep an equally useful test/decision suite. Every builder gets the same inputs and permitted execution. An incumbent's missing outcome is recorded, not falsely timed as a failed equivalent implementation. Charge new construction on both sides.
4. **Run structural ablations.** Consumer-first closure without executable probes tests whether static coverage alone changes the decision. Executable probes without the additional static lens test whether that lens contributes enough to justify cost. An otherwise identical pipeline without the retained probe asset tests construction/reuse benefit. Do not remove legitimate capabilities from the main conventional arm to manufacture a win.
5. **Verify decisions independently.** A separate verifier checks exact source/environment identity and adjudicates each requirement from recorded observations or an independent run; it does not accept the creator's status string. Missing/stale evidence and a deliberately failing bounded control must block a positive decision. Such controls are validation cases, not independent customer jobs or discovered production defects. Every critique must cite its source location, consequential discrepancy and relevance to the user's purpose; maintain disagreement until the evidence resolves it.

Primary endpoints are correct scoped decisions, complete required outcomes, reliability, turnaround, remaining customer actions, and complete attributable resource consumption. Report uncertainty and unknown inference/attention costs. An engineering gain over v1 supports a useful integration; parity with the conventional builder supports adopting good tools, not an algorithmic breakthrough. Better construction or sustained acceleration requires separate evidence.

## Discovery accounting and stop condition

Metering began before inspection in `metering/workload_review.jsonl`. This allowance screened exactly three candidates, constructed none and accessed no new confirmation input. One metadata-inspection script initially assumed a list where the preserved registry uses a dictionary; its failure and correction are charged discovery work, not suppressed. No dependency download, target-code execution, external write, financial transaction or credential creation occurred. Stop discovery here and let the independent verifier adjudicate the material criticisms before implementation choice.
