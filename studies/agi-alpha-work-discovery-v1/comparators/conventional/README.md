# Independent conventional API assurance constructor

This source was written without reading the retained producer implementation. It demonstrates that a competent agent
with ordinary tools can reconstruct the scoped structural-response workflow within the registered twenty-minute
allowance. The observed construction interval was 390.812334 seconds, including search, installation, correction,
verification and waiting. This is not a human task duration, inference bill or priced construction cost.

`SOURCE_FREEZE.json` binds the exact constructor, independent BFS verifier, tests, tool lock and original cost record.
`conventional.py` performs recursive response traversal with cached JSON-pointer lookup. `verify_dossier.py` independently
enumerates the same declared structural scope using a breadth-first queue. The verifier does not call the constructor.
Neither implementation claims a novel algorithm or general runtime compatibility proof.

## Run from this directory

```sh
python conventional.py OLD.json NEW.json dossier.json
python verify_dossier.py OLD.json NEW.json dossier.json
python -m unittest -v test_baseline.py
```

Use identical normalized JSON inputs for algorithm comparisons. YAML input is supported with PyYAML, but YAML decoding
must be charged to all arms consistently. The development YAML run took about 1.22 CPU seconds; the same final source
using normalized JSON took 0.11360 internal CPU seconds including writing the complete dossier. Process startup and
independent acceptance add further cost. These are one development observation each, not primary effect estimates.

## Scope

Every inline GET path operation and its 2xx successful response is inventoried. JSON schema properties, arrays,
additional-property schemas, local schema and response references, and indexed allOf branches are traversed.
Reference cycles and unsupported features stay unassessed. Swagger `x-nullable` is interpreted as `nullable` when an
explicit nullable keyword is absent. Non-JSON responses are recorded and excluded from schema traversal.

Schema source pointers and reference chains are reported separately from semantic fact identity. Thus moving an
unchanged referenced schema does not create a false fact change. allOf branch ordering remains structural: equivalent
reordered conjunctions may appear different. Path-item and operation-reference discovery, arbitrary external reference
retrieval, whole JSON Schema semantics, live server behavior and consumer application acceptance are outside this scope.

The complete development dossier contains 2,408 old and 2,413 new schema nodes, with six changed surfaces. Five are
added `VolumeOptions.Subpath` contexts; one changes `ImageInspect.Created` format and nullability. Default values,
reference siblings and other unsupported constructs remain explicit. The exact Docker specifications still retain
`ContainerConfig`, despite documented runtime removals: a static specification cannot certify real-server compatibility.

## Strong public alternative

The checksum-verified public comparator was oasdiff 1.34.1. Its direct input of the Swagger 2 documents produced an
empty change list, but validation exposed invalid format use; this failed attempt is retained. The established
swagger2openapi 7.0.8 converter then produced valid OpenAPI documents. Converted baseline validation reported zero
errors, three warnings and eleven informational findings. oasdiff reported the changed `Created` nullability and a
broader changelog. All original command outputs and conversion timing remain in `evidence/`.

The converter dependency lock is retained in `tools/`; install locally with `npm ci --prefix tools --ignore-scripts`.
Generated node_modules and local quality tools are deliberately outside this source capsule.

## Preservation and evidence

The original discovery variant traversed six non-JSON schema roots. It was corrected before confirmation, and its exact
source and result summary remain in `evidence/original-development-v1.zip`. A verifier numeric-normalization control
also failed during development and was corrected before freeze; original failing test output remains. Seventeen final
controls, repository Ruff checks, strict mypy and single-file Black checks pass. A batch Black process did not exit
normally; sequential single-file checks subsequently passed. No failed or unrun check is represented as passing.

The added study-level `tests/accept_dossier.py` adapts this frozen independent enumerator to compact Workbench dossiers
and fragmented output. Its own source freeze and twenty negative controls are separate. It validates exact changes,
provenance, source digests, counts, unsupported-scope coverage and output-file binding to the retained Workbench pack.

Actual customer collections are zero. Actual full monetary authoring cost, inference-token count and human attention
remain unknown. This accepted reconstruction limits claims of scarce or unavailable capability: missing prior files
did not imply that the competent recipient could not construct the method.
