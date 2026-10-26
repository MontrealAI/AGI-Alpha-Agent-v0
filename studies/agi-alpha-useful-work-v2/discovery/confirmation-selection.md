# Confirmation selection before package execution

The primary selection uses release and distribution metadata only. No selected
wheel, package source body, or execution outcome was downloaded or inspected by
this curation lane. The selection cutoff is **2026-10-26 14:33:37 UTC**. The
selection manifest is `confirmation-metadata-v1.json`, SHA256
`db83024274acf14b05b21e39cd35af4d52c3d71869e21d15bde4c0610956b55a`.

## The concrete internal decision

The native `requirements-agent.lock` at consumer revision
`eb07086ac42799ff45f7b1c946a2f7c514bd3bbc` pins Starlette 1.7.0 and Pydantic
2.13.5. The file has the same Git blob
`d450350998018b691f04fa99093d2fef68b929f0` at current main
`804e1afeb78ea48fb4807d76b336803aa0906a20`. PyPI release metadata identifies
Starlette 1.10.0 and Pydantic 2.14.1 as the latest stable development tuple at
the cutoff. These versions meet the incoming native-profile constraints recorded
in the manifest. That observation does not establish successful installation,
consumer behavior, application qualification, or approval to upgrade the lock.

Development therefore asks whether the actual RequestBoundary and explicit
Mission-input model contract can support a useful, bounded decision about the
native profile refresh. This is an observed internal maintenance question. No
pending customer request, paid order, or maintainer commitment to adopt the
upgrade was found or asserted.

## Outcome-independent primary selection

For each primary package major (Starlette 1 and Pydantic 2), the curator selected
the latest four stable PEP 440 versions with non-yanked Python 3.12 wheel
metadata before the cutoff, satisfying current incoming dependency constraints,
after removing every known source/runtime exposure and both development
versions. The resulting adjacent eligible versions define three transitions per
package. Intervening excluded versions are skipped transparently.

| Mission | Primary dependency transition | Other component held fixed |
|---|---|---|
| starlette-1 | 1.5.1 → 1.6.0 | Pydantic 2.13.5 |
| starlette-2 | 1.6.0 → 1.8.0 | Pydantic 2.13.5 |
| starlette-3 | 1.8.0 → 1.9.0 | Pydantic 2.13.5 |
| pydantic-1 | 2.13.2 → 2.13.3 | Starlette 1.7.0 |
| pydantic-2 | 2.13.3 → 2.13.4 | Starlette 1.7.0 |
| pydantic-3 | 2.13.4 → 2.14.0 | Starlette 1.7.0 |

The changed package versions and wheel identities are substantive mission
triggers. These are **six representative historical compatibility assessments**
against the same source-pinned current consumer, not evidence of six actual
historical Alpha adoptions, six independent defect families, six customer
orders, or prospective releases. Multiple cases, repetitions and comparator
evaluations inside a transition are not extra missions. The unchanged other
component and common support packages are deliberately reused exposed inputs.

## Exclusions and coupled dependencies

Known v1 Starlette exposure consists of 0.36.3 (source and executed integration)
and 0.37.2 (executed known remedy). Both are outside the selected primary major
as well. Pydantic 2.14.1 was imported in v1 and included as an offline wheel.
Development additionally excludes Starlette 1.7.0 and 1.10.0, and Pydantic
2.13.5 and 2.14.1. Every release considered, its eligibility, and its rejection
reasons are retained in the machine-readable manifest. Metadata-only exposure
of historical tags in v1 is not treated as package-body inspection.

Pydantic's exact core dependency is part of each declared environment, not a
hidden independent intervention:

| Pydantic | Required pydantic-core |
|---|---|
| 2.13.2 | 2.46.2 |
| 2.13.3 | 2.46.3 |
| 2.13.4 | 2.46.4 |
| 2.13.5 (development incumbent) | 2.46.5 |
| 2.14.0 | 2.50.0 |
| 2.14.1 (development proposed) | 2.50.1 |

Native support versions anyio 4.15.1, annotated-types 0.8.0,
typing-extensions 4.16.0, and typing-inspection 0.4.4 satisfy the active direct
component requirements on Python 3.12/Linux in the metadata. Core wheel
availability and complete installation closure have not yet been established
by this selection. They must be verified after the protocol freeze. A missing
wheel or failed installation is evidence to retain, not permission to replace
a selected mission based on its outcome.

## Provenance, reproduction and limits

The normalized release metadata is under `release-metadata/`. Each record
preserves its PyPI URL, retrieved JSON hash, file metadata and exact wheel
digest supplied by PyPI. `requests.jsonl` records fourteen successful bounded
JSON reads, request time, CPU time and bytes; inference tokens and monetary
charges are unknown. Wheel URLs were recorded but not followed.

`curation/fetch_release_metadata.py` retrieves bounded metadata.
`curation/select_confirmation_metadata.py` deterministically derives the
selection from the preserved metadata and refuses to overwrite a recorded
selection. To reproduce selection, copy the retained metadata to a fresh
study directory and run the selector before creating its output file.

Public historical releases may have appeared in model pretraining. Held out
means no package-body/runtime/outcome inspection by this study's builders
before freeze; it does not mean the releases were secret or prospectively
sampled. Metadata compatibility cannot replace the frozen behavioral contract,
independent validation, or the repository's qualification and adoption gates.

No candidate package body will be acquired until the lead supplies the final
protocol freeze and explicitly authorizes retrieval.
