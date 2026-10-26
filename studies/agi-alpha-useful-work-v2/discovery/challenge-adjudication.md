# Independent adjudication of C1, C2 and the intent charter

**Decision:** C1 is verified as an evidence-construction limitation. C2 is verified as a gap against the larger consumer decision, with an important qualification: v1 did not falsely claim that its scoped source report was a completed production upgrade. The new intent charter describes a useful **bounded component-compatibility work package**, subject to the concrete conditions below before confirmation freeze.

This verifier did not author `critic-opportunities.md` or the charter. The verifier previously authored v1's consumer mapper, so this is a disclosed same-session source/evidence cross-check, not blind external review. No candidate was built, no target source was executed and no v1 artifact was changed. Exact identities and findings are in [challenge-adjudication.json](challenge-adjudication.json).

## C1: verified, with the claimed counts reproduced

`value-compounds/src/pipeline.py:75–101` derives `changed` from source differences and constructs reports only inside the loop beginning at line 88. `consumer.py:507–516` subsequently requires a signature in those supplied reports before checking an actual mapped call shape.

The preserved first conventional FastAPI packet has SHA256 `898723b41ecec47a305ea104c7be21ca695491a27c8d72efa126582e7f38e848`, independently recalculated. Its only reported modules are `fastapi`, `fastapi.dependencies.models`, `fastapi.dependencies.utils` and `fastapi.routing`.

Of its **57 dependency-import references**, these **38** have successful target resolution in both versions but no supplied signature:

| Target | Calls | Exact declaration position | Parameters |
| --- | ---: | --- | ---: |
| `FastAPI.__init__` | 1 | `fastapi/applications.py:68–1030` | 38 |
| `Header` | 6 | `fastapi/param_functions.py:734–1063` | 32 |
| `Depends` | 23 | `fastapi/param_functions.py:2391–2477` | 3 |
| `HTTPException.__init__` | 8 | `fastapi/exceptions.py:45–83` | 4 |

Those three modules have identical before/after bytes, consistent with the packet manifest. The named declarations are direct and undecorated. The remaining **19** references stop at uncaptured Starlette exports: `FileResponse` 14, `JSONResponse` 4 and `Request` 1. The example at consumer `api.py:131` correctly resolves to `fastapi.applications.FastAPI.__init__`, then receives `source-pinned-supported-signature-unavailable`.

This verifies C1's specific omission. It does **not** establish that all 38 calls would pass the complete supported-scope checker, that all 57 could be resolved, or that fixing the omission establishes application behavior. Signature demand closure is justified supporting work; a general dispatch analyzer is not implied.

## C2: verified as an acceptance-purpose gap

`pipeline.py:109–111` computes readiness from upstream report validation. Consumer observations do not enter that condition. The same raw packet is `ASSESSMENT_READY` with **10,172 unresolved calls, zero preserved bindings and zero established consumer losses**.

That status cannot answer an application's behavioral acceptance question. However, lines 118–121 explicitly retain `production_approved=False`, zero paid jobs and local/source-only limitations. Accordingly, the supported criticism is that the v1 acceptance contract was insufficient for the broader requested outcome. It is not evidence that the v1 report violated its declared narrower contract or falsely approved a release. This qualification should accompany the change rationale.

## Charter: useful scope, with explicit requirements needed before freeze

The charter's API/model hashes match both the preserved v1 source and the native `alpha/` copies. The native test file is also exact: 5,089 bytes, SHA256 `afa41ae0e428e9be048544e03daaf7a4e2c3e45a0b83d889d6883e8121fdcd45`, Git blob `ce8df8ce4157b4f0dba2f45dfc5c9935f000ccaf`. The captured lock is unchanged between the two reported repository commits; its newer retrieval URL does not represent a new experimental consumer revision.

`api.py:37–110` supplies a real, consequential component contract: request framing and byte bounds, origin rejection, timeout/disconnect handling, body replay and response security headers. `models.py:12–143` supplies strict mission inputs, discriminated work variants, bounds and validators. These are useful compatibility prerequisites. A dependency change that violates them should not proceed unquestioned.

The charter correctly excludes `create_app`, journal initialization, credentials, full authentication and operator/release authority. Those exclusions matter: native `test_api_boundary.py:93–109` initializes a journal and tests real mission persistence/status 201; lines 124–130 test authentication and trusted-host rejection through the full application. `store.py:282–311` generates the signing key and API token. A recording downstream component cannot stand in for those behaviors.

Before freezing confirmation, resolve six conditions:

1. **Freeze a finite case/oracle matrix.** Give every required case an independent expected observation, source location and decision consequence. Missing, unexecuted or stale evidence must block positive component acceptance.
2. **Bind the extracted execution closure.** Preserve exact definitions, constants and imported-symbol identities for `RequestBoundary`; use actual pinned framework/Pydantic objects. Do not rewrite the tested implementation in the harness.
3. **Specify disconnect and timeout precisely.** Disconnect returns no response and does not enter downstream (`api.py:80–82`; native test line 120). Rejections return the source-defined status plus security headers. Native tests shorten the timeout to 0.01 seconds at line 115; if reused, label that override as a timeout-path check, not a measurement of the production 15-second deadline.
4. **List excluded full-application assertions.** Downstream call count and byte preservation do not prove signed-journal immutability, authenticated mission creation, trusted-host enforcement or the complete middleware stack. Preserve those as subsequent qualification gates.
5. **Enumerate model coverage.** Name the tested `Mission`/`Work` variants, strict types, boundaries, duplicate-ID cases and serialization expectations. `Forecast` has relational and finite-value checks at lines 86–95; untested variants must not be implied covered. `ChainConfig` and `RuntimeConfig` are outside a Mission-only claim.
6. **Keep the decision at its stated level.** A pass supports advancing this exact component package to further application qualification. It does not validate the entire production lock, all FastAPI routes, authentication, release readiness, paid demand or operator authorization.

These are protocol-completeness conditions, not a request to broaden the job into a full release or to create credentials. The work can proceed within the useful bounded scope. No measured v2 outcome, commercial advantage or deployment claim follows from this adjudication alone.
