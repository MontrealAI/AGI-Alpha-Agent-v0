# Independent component contract: scope and oracle rationale

This contract was constructed from exact, previously exposed project source before the first development observation was inspected. It is an evaluation asset with attributable construction and scrutiny costs. The 61 cases are requirements checks within one component work package, not 61 customer missions. The contract's SHA256 is `89d9c776a7c9f32444b1e14479b9403e8beaaef81c0832f0237af027ddf41735`.

## Useful decision and authority

The work package asks whether an exact proposed dependency environment preserves the enumerated input-validation and request-boundary behavior of an unchanged consumer. An accepted package provides a source-pinned decision, raw observations, independently checked results, and a command that a maintainer can reproduce before proceeding to broader integration qualification. A component pass does not approve a whole dependency lock or release. Authentication, Host policy, persistence, credentials, actual mission execution, operator controls, and production deployment remain outside this package.

The native boundary test uses `create_app` and a Journal, and combines component behavior with routing and persistence (`discovery/test_api_boundary.py`, lines 20–72, 90–130). That route is not exercised here. The exact unchanged `RequestBoundary`, its three constants, and the inert `Review` and `Control` model declarations are extracted without their surrounding application construction. `Mission` and its model definitions are loaded from the pinned model source. The observation records extracted source slices, hashes, declared imports, and the original constants.

An independently confirmed pre-freeze criticism identified an import-route qualification: original `api.py` lines 11–12 import Request and JSONResponse through FastAPI, while the first provisional probe imported their defining Starlette classes directly. `component-projections.json` preserves both explicit profiles and AST hashes. `provisional-starlette-direct-v1` can produce only a provisional projection match, not native-route acceptance. `native-fastapi-bridge-v2` preserves the actual used FastAPI import statements and requires its ten-package environment, including FastAPI and annotated-doc. The behavior contract remains unchanged; this correction expands execution fidelity before candidate selection. The first record and original verifier edition are retained; reacquisition, setup, rerun, and scrutiny costs are chargeable. Neither profile claims that the whole FastAPI application was tested.

## Source basis and meaningful coverage

| Area | Cases | Source basis and reason |
|---|---:|---|
| Mutation framing, declared/actual byte limits, origin, stream integrity, pass-through, disconnect, real timeout | 21 | `data/consumer/api.py`, lines 24–110. These cover consequential framing branches, genuine body-byte preservation, all three mutation methods, and the read-only bypass. They preserve the native test's material malformed-framing examples while distinguishing no-response disconnect from rejection. |
| Mission variants and engine bounds | 19 | `data/consumer/models.py`, lines 12–124. Five valid Work variants include complete default serialization, both integer bounds are represented, and strictness, forbidden extras, goal limits, and the discriminator have rejection checks. |
| Variant-specific validation | 14 | `data/consumer/models.py`, lines 27–143. Empty research, nonpositive or noninteger resource fields, duplicate identifiers across all three relevant variants, forecast fit/finite/magnitude requirements, and required held-out code cases have consequential rejection examples. |
| Review and Control input models | 7 | `data/consumer/api.py`, lines 113–125. These test inert input acceptance, complete output, revision/hash/approval/note restrictions and the finite control-state vocabulary. No approval or state change is performed. |

Every case carries its own source path and line range. The exact source identities and consumer commit are in `component-contract.json`; native requirement source SHA256 is `afa41ae0e428e9be048544e03daaf7a4e2c3e45a0b83d889d6883e8121fdcd45`. Case counts describe finite coverage, not completeness over all possible values or all model constraints. In particular, this is not a full proof of nested collection maxima, all text patterns, every numeric combination, non-HTTP ASGI behavior, or the excluded runtime/configuration models.

## Independent expected results

Expected statuses, error text, downstream invocation counts, complete model dumps, and required header literals were transcribed from the pinned declarations and control flow without executing target code. The four security-header values are fixed in the contract; the verifier does not read its expected values from the target's runtime constant. The downstream fixture deliberately emits `cache-control: public, max-age=3600`, requiring the boundary to replace it with exactly one `no-store` header. Other required security headers must also appear exactly once with their exact values.

The valid fragmented body includes a two-byte UTF-8 character, and the expected length and SHA256 are derived independently from the literal input. Successful downstream calls must preserve the entire joined byte sequence. Rejected or disconnected calls require zero downstream invocations and null downstream body evidence. The disconnect case expects no response at all. The 512 KiB boundary is tested exactly, and the actual-body overflow case checks the source's precedence of byte-limit rejection over declared-length mismatch.

The timeout case runs the original 15-second timeout with a delayed receive of 15.2 seconds. No clock or timeout substitution is authorized. The verifier rejects an apparent timeout whose recorded wall time is below 14.999 seconds (one millisecond of measurement tolerance), checks that the recorded original constant is exactly the float `15.0`, and retains the actual elapsed observation. This is deliberately more expensive than the native test's 0.01-second monkeypatch; that verification expense belongs in delivery cost.

The forecast nonfinite cases begin as valid JSON fixtures and materialize an actual Python IEEE NaN or positive/negative infinity at an explicitly listed path before `model_validate`. The recorder must report that path, token, type and representation. Rejecting a string or marker object is not evidence for nonfinite handling. Accepted outputs are compared as complete JSON trees while preserving bool, integer and float types; Python's `True == 1` does not establish output equality.

## Separate verification and refusal conditions

`src/verify_component.py` reads raw observation JSON and expected source/contract/environment records without importing or executing consumer code. It rejects missing, duplicate and unexpected case IDs; wrong recorded or on-disk source hashes; a changed frozen contract; wrong projected slices, imports or constants; unaccounted runtime model/network activity; missing measurements; and mismatched dependency versions. Its verdict is incomplete when required evidence is absent. An observed behavior mismatch is not automatically attributed to a dependency change without baseline evidence and exact reproduction.

The verifier checks recorded identities and pinned wheel records. The native profile specifically requires `component-environment-preparation/v1`, a boolean `complete: true`, no preparation error, the successful original import bridge, and normalized installed distribution versions matching the ten declared wheels (the installer pip is separately permitted). The older `component-development-environment/v1` acquisition/status format is accepted only for the provisional eight-package profile. This explicit schema correction was made before the corrected development executions, after discovering that the builder's actual output was `preparation.json`. The verifier does not independently attest installed binary bytes, prove a hostile recorder truthful, or replace installation provenance checks. These limits must remain visible in the final work package. Its own execution, corrections, construction and negative controls are attributable evaluation costs. Financial amounts unavailable from billing remain unknown; no check converts those unknowns into zero, savings, receipts, repayment, or affordable expansion.

## Reproduce verification

From the workspace root, after the separately operated observer has produced a raw record:

```sh
python research/useful-work-v2/src/verify_component.py \
  --contract research/useful-work-v2/protocol/component-contract.json \
  --consumer research/useful-work-v2/data/consumer \
  --environment /path/to/native-fastapi-environment/preparation.json \
  --projection native-fastapi-bridge-v2 \
  --observations /path/to/raw-observations.json \
  --out /path/to/new-independent-verification.json
```

Supply the matching independently pinned acquisition manifest for the selected profile and dependency environment; the original eight-package acquisition manifest is valid only for the provisional profile. The script refuses to overwrite an existing result. A complete match exits 0; a mismatch or incomplete record exits 2. A provisional profile returns the explicit `PROVISIONAL_PROJECTION_MATCH` status, which must never be counted as native-route acceptance. Existing editions and observation records remain intact.
