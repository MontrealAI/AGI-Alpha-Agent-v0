# Strong conventional design: reusable component-contract assessment

**Status:** design only. No implementation or fresh confirmation access. Construction starts only after the first current-profile development output is available. The comparator will be independently implemented by the workload reviewer; the independent verifier is a separate role.

## Outcome and comparison boundary

The conventional method must deliver the same scoped maintainer outcome as the intent charter: an exact before/after environment assessment of Alpha's real `RequestBoundary`, mission models, `Review` and `Control`, including executable evidence, a justified component decision, a reviewable lock change and remaining full-application gates. It may use all ordinary tools, original source, common requirements, published dependency metadata, reusable test assets and legitimate caches available to the proposed method. It is not restricted to source diffs or signature checking.

Use a normal **stdlib `unittest` suite plus an isolated environment matrix and evidence collector**. This is a standard reusable engineering approach, without a gratuitous pytest dependency; pytest remains permitted if it provides a concrete benefit. A successful conventional result is useful enterprise capability and may be selected over the proposed method. A tie cannot support a stronger improvement-method claim.

The native tests in [test_api_boundary.py](test_api_boundary.py) are requirement evidence, not an executable script for this study: they instantiate `Journal`, create credentials and exercise `create_app`, all excluded by the charter. Transfer their framing expectations into the common component contract while making the narrower execution boundary explicit. No assertion that a journal is unchanged can be inferred from a harmless downstream fixture.

## Proposed minimal interface

An existing controller prepares hash-locked environments under identical permission and accounting rules. Each conventional worker runs with one chosen interpreter:

```sh
/absolute/profile/bin/python -I -B src/conventional_worker.py \
  --job /absolute/job.json --out /absolute/new-observation-directory
```

This is a proposed interface, not an already working command. The output destination must be new. The worker never downloads packages, initializes an operator profile, reads credentials or contacts a server.

The common input schema should contain:

| Field | Required meaning |
|---|---|
| `schema`, `mission_id`, `role` | Versioned contract; development or confirmation is explicit |
| `trigger` | Substantive source, dependency-lock or requirement change; not an unchanged rerun |
| `intent` | Charter identity and exact bounded maintainer question |
| `sources` | Original API/models paths, hashes, repository and revision |
| `contract` | Case-manifest identity, required case IDs and assertion/oracle identities |
| `profile` | Environment ID, complete component-lock identity, expected distribution inventory and source-lock provenance |
| `limits` | Identical wall-time, process, output and fixture-data envelopes across arms |

A pairing command, proposed as `src/conventional_assess.py --before BEFORE --after AFTER --job JOB --out NEW_DIR`, consumes the two independently executed records, runs the common independent verifier, and builds the bounded decision package. It does not import the proposed method's decision algorithm or accept its statuses. If root prefers one parent CLI, this logic can be exposed as `assess(job, before_record, after_record, output_dir)` instead. Freeze the agreed schema before confirmation.

## Independent ordinary implementation

1. **Source custody and isolation.** Verify full original file hashes. Parse exact API definitions/constants required by the component (`RequestBoundary`, `MAX_REQUEST_BYTES`, `BODY_TIMEOUT_SECONDS`, `SECURITY_HEADERS`, `Review`, `Control`) and execute those original AST nodes with the actual pinned framework imports and the real captured model definitions. Preserve a node/line/hash manifest and explicit imported globals. Do not rewrite the component, replace framework classes, execute `create_app`, or use `Journal`. The separate verifier checks isolation against original source. Any source not meeting the declared extraction rules is incomplete, not silently adapted.
2. **Conventional test cases.** Each required case becomes an ordinary unittest case, with expected outcomes fixed in the shared requirement manifest. A recording ASGI downstream app supplies deterministic messages and records whether it was called, which body it received and how often. Actual `Request`, `JSONResponse`, Pydantic validation and serialization execute under the pinned environment. Observations are captured before assertions, including failed cases.
3. **Evidence collection.** Retain raw ordered ASGI headers/messages and downstream observations, model input/acceptance/error locations/serialization, return codes, tracebacks, start/finish receipts and resource counters. Encode raw bytes losslessly, rather than collapsing duplicate headers into a dictionary. Standard unittest success/failure/error/skipped counts are retained alongside complete per-case records; no skip yields positive acceptance.
4. **Decision and package.** Pair complete records with exact source, environment, case and implementation identities. All required assertions passing in both environments supports only the named component-preservation conclusion. An observed proposed-profile regression supports rejecting/holding that proposed bundle. Missing evidence, setup failure, timeout or an unresolved requirement yields incomplete/HOLD. The package includes the proposed lock diff, rerun command, complete raw artifacts, a digest manifest and release gates. No status derived solely from an exit code or test count is sufficient.

## Common semantic acceptance to agree before implementation

The shared case manifest, not either implementation, owns expected outcomes and required IDs. Both builders may inspect it and keep reusable assets. The independent verifier owns admission.

- **Request framing:** preserve source/native-test expectations for missing/invalid/non-ASCII length, duplicate length, transfer encoding, excessive declared/actual length, length mismatch, and cross-origin mutations. Rejection must include its specified status, required security headers and zero downstream calls.
- **Accepted transport:** fragmented valid input reaches the downstream app exactly once with unchanged body bytes; success responses receive the required security headers. Source limits and constants are checked explicitly. Additional cases such as GET passthrough should be either required for both arms or outside both primary endpoints.
- **Timeout/disconnect:** retain no downstream work on incomplete uploads. The agreed design runs the actual original 15-second timeout with **no override**, under the same worker budget of at least 45 seconds. The native unit test's 0.01-second monkeypatch is requirement context only and is not carried into this experiment. Unexpected hangs yield incomplete evidence, never silent skips.
- **Models:** use the actual captured `StrictModel` hierarchy and explicit validation entry points. State separately whether a case invokes `model_validate` or `model_validate_json`; these are not interchangeable assumptions. Require accepted mission serialization against fixed independent values, forbidden extra fields, implicit type-coercion rejection, declared bounds and duplicate IDs. Include declared `Review` and `Control` cases. Prefer semantic error locations/types to version-specific prose/error URLs.

The number of cases must be fixed before confirmation and reported as assertions/cases, not missions. A case expected to reject invalid input passes when the required rejection occurs. It is not an observed broken dependency. Whole-application authentication, journal integrity, mission execution, browser behavior and deployment remain untested by this component suite.

## Reuse, cache fairness and metering

The conventional builder retains its suite, fixtures, collector, standard runner, source extraction, lock preparation and package generator. It may cache downloaded wheels, verified environments, parsed sources and immutable definition slices, keyed by all relevant source, dependency, interpreter, platform and implementation identities. Warm caches are not removed to manufacture a construction or speed advantage. Charge both cold acquisition and later maintenance; show utilization assumptions separately.

Every fresh substantive mission executes its required behavioral probes. A cached prior pass cannot stand in for execution under a changed lock/source/requirement. Repeated unchanged requests may return a declared no-op or evidence lookup and do not add jobs. A rerun for timing or verification retains its original mission identity.

Record construction before coding, including this design, unsuccessful attempts, shared case/spec work, test construction, environment preparation, execution, independent scrutiny, corrections, packaging and residual user action. Record exact CPU/wall/output/cache facts where available; preserve unknown model tokens, inference dollars and attention costs. The timeout case has intentional waiting, so elapsed time alone cannot establish improved productive efficiency.

## What can falsify the improvement claim

The same independent verifier must accept or reject both methods' complete outputs. Missing/stale case evidence and a deliberately failing bounded control must prevent a positive decision in both. Controls are validation fixtures, not new customer jobs. Source-isolation differences, failed environment closure and unsupported assumptions remain explicit.

Compare the retained method against this reusable conventional builder on equivalent complete outcomes, construction cost, resource use, reliability and remaining customer effort. Also preserve the actual v1 incumbent for the narrower question of added useful coverage. A targeted ablation of static closure versus executable contract can determine whether the additional static layer earns its cost. Do not deny the conventional arm tests, source closure, automation, retries, caches or evidence packaging that the candidate receives.

This design offers no predetermined result. If ordinary tests and a collector provide the same outcome at lower complete cost, use them and retain the negative comparison honestly.

## Design handoff

Root will first produce the manual development result on the correctly pinned native-agent dependency tuple and freeze the common case/oracle matrix, exact AST-slice/import/constant identities and resource envelope. Conventional implementation is explicitly deferred until that result is available. The actual incumbent remains v1's strong conventional static assessment plus any honestly recorded normal manual completion work; no fictional free reviewer hours or removed legitimate tools are introduced.
