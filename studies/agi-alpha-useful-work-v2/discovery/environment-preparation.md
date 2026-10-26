# Development environments and reusable preparation utility

Both corrected development environments are ready. Exact hash installation,
declared dependency closure, `pip check`, installed version inventory, and the
original FastAPI import bridge passed. No Alpha `api.py`, `create_app`, Engine,
Journal, credentials, application route, or component behavioral case was
executed during preparation. This is environment setup evidence; the behavioral
contract is evaluated separately.

## Corrected scope and preserved attempts

The earlier eight-package baseline at `data/development-environment` is
preserved. Review established that the original source imports `Request` via
`fastapi` and `JSONResponse` via `fastapi.responses`; the initial direct
Starlette projection omitted that import bridge. The corrected environment
includes native FastAPI 0.141.1 and annotated-doc 0.0.5. The correction is
recorded in `environment-scope-correction.json`. The eight-package target draft
was never installed or executed; its pre-correction hash is retained.

The first corrected baseline attempt failed because the utility's event logger
used the same `kind` argument name as a network event field. That attempt remains
under `data/development-baseline-bridge-environment-attempt-1-failed`. It consumed
one 131,954-byte official wheel response before installation; the log collision
prevented writing the individual request event and saving that response. Its
aggregate request/byte/time costs remain in the failed report and meter. The
narrow parameter-name repair was completed before confirmation. The successful
attempt charged the repeated acquisition rather than hiding it as a free retry.

## Exact environments

| Package | Native development baseline | Proposed development target |
|---|---:|---:|
| Starlette | 1.7.0 | 1.10.0 |
| Pydantic | 2.13.5 | 2.14.1 |
| pydantic-core | 2.46.5 | 2.50.1 |
| FastAPI | 0.141.1 | 0.141.1 |
| annotated-doc | 0.0.5 | 0.0.5 |
| anyio | 4.15.1 | 4.15.1 |
| annotated-types | 0.8.0 | 0.8.0 |
| typing-extensions | 4.16.0 | 4.16.0 |
| typing-inspection | 0.4.4 | 0.4.4 |
| idna | 3.20 | 3.20 |

The environments use Python 3.12.14 on Linux x86-64. Their setup tool is pip
25.0.1, provisioned by the existing interpreter's venv module. FastAPI's active
base requirements are satisfied. The current pydantic-settings 2.15.0 metadata
constraint on Pydantic is checked without adding pydantic-settings or its other
dependencies to this component environment. FastAPI optional extras are not
enabled. The Alpha constraints FastAPI >=0.116,<1 and Pydantic >=2.11,<3 are
checked explicitly.

The two usable interpreters are:

- `data/development-baseline-bridge-environment/venv/bin/python`
- `data/development-target-environment/venv/bin/python`

Both setup logs show `Request is starlette.requests.Request` and
`JSONResponse is starlette.responses.JSONResponse` through the original FastAPI
imports. Those imports initialize package code, not the Alpha application.

| Preparation record | SHA256 |
|---|---|
| Baseline `preparation.json` | `90a2c60e589e00fe126db94f58cc1b5817ca406e4601d00dd26ea8e7eeae50e7` |
| Target `preparation.json` | `64a7e770c036aea9ef1cc4387f71a4b29f6ffe9dd6ee86765490ab1fd335c77b` |
| Executed builder | `ca6741e4ad22de14f2dc270cc18b80154f3b40a5b5b1f612c6ca0dba08afe026` |

## Resources and attribution

| Successful preparation | New requests | Response bytes | Reused wheel bytes | Wall seconds | Child CPU seconds |
|---|---:|---:|---:|---:|---:|
| Corrected baseline | 2 | 137,256 | 2,893,263 | 3.472 | 3.294 |
| Target | 2 | 208,837 | 3,060,929 | 3.437 | 3.240 |

These totals cover the executed utility, hash checks, installation, dependency
checks, and import bridge. They exclude earlier discovery, researcher/model
construction, the preserved failed attempt, original eight-package baseline,
Ruff provisioning, and later consumer execution. Those activities have their
own records and must be included when deriving a full cost. Reused wheels are
checked against preserved official PyPI metadata; their earlier acquisition
is not silently reclassified as free construction. The preparation reports
also retain self CPU, peak RSS, storage bytes, installed identities, command
logs, and every successful network request. Monetary compute/storage rates and
inference charges are unknown. Elapsed research time is not an inferred bill.

## Reproduce and reuse

`curation/prepare_environment.py` processes a supplied exact plan. It does not
select missions or resolve unpinned additions. It preserves official metadata,
chooses compatible wheels deterministically, verifies byte size and SHA256,
checks the complete declared closure, writes a hash lock, and installs using
`--no-index --require-hashes`. It refuses an existing output directory and
preserves failed attempts. Network bounds are 20 requests, 20 MB per response,
64 MB total, 30 seconds per request, with no automatic request retries or
redirects. Setup commands have a 180-second timeout. A confirmation plan must
identify a separately supplied frozen manifest by hash.

Run from the workspace/repository parent that contains `research/`. For an
offline target replay into a fresh output directory:

```sh
python research/useful-work-v2/curation/prepare_environment.py \
  --plan research/useful-work-v2/data/development-target-plan.json \
  --out research/useful-work-v2/results/target-environment-offline-replay \
  --metadata-reuse research/useful-work-v2/data/development-target-environment/metadata \
  --wheel-reuse research/useful-work-v2/data/development-target-environment/wheels \
  --offline
```

The recorded setup uses exact local plan paths relative to that working
directory. A relocated standalone package must retain this layout or provide
an explicitly adjusted plan; a plan change creates a new identity. Venv paths
are disposable execution products. Hash locks, wheels, metadata and preparation
logs are the portable evidence.

The repository CI log pins Ruff 0.12.5. Its official wheel and license are
retained in `support/ruff-0.12.5`; provisioning is charged separately. All four
curation files passed that version with the current repository configuration
and no added rule waiver. Exact command, source hashes and output are in
`environment-builder-lint.json`.

## Source rights and retirement conditions

Every acquired component wheel retains its original bytes and extracted
distribution license notice. Each environment's `licenses/index.json` maps
wheel identity, official provenance, metadata license expression and notice
hashes. Starlette and idna declare BSD-3-Clause; typing-extensions declares
PSF-2.0; the remaining seven components declare MIT. The extracted notices are
the operative preserved text. The Alpha consumer source and original project
license remain source-pinned; this utility's new source carries Apache-2.0.
Redistributed companions must preserve these notices and provenance.

An environment or retained result must be requalified for a new mission when
the consumer source, behavioral contract, package version/hash, active extras,
incoming constraint, Python ABI/platform, or import bridge changes. A hash
mismatch, missing required case, unresolved dependency, unsupported platform,
failed setup or failed bridge check cannot produce a positive compatibility
decision. An upstream withdrawal or security change warrants a new maintainer
assessment before new use; it does not justify rewriting historical evidence.
Retire the capability from active use if its maintenance and required checking
costs cease to justify measured value, or if the corresponding contract is no
longer a useful offering. Preserve its original records after retirement.

No primary historical package wheel or source body has been acquired. The
selected primary missions remain held until the lead's explicit freeze and
retrieval authorization.
