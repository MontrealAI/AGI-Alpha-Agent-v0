# Attribution and retained licenses

The study's new support code uses Apache-2.0 SPDX headers. `AGI-Alpha-Agent-v0-LICENSE.txt` preserves the exact Alpha license already captured with the source-pinned development inputs. Native Alpha source remains at commit `eb07086ac42799ff45f7b1c946a2f7c514bd3bbc`; canonical economic-ledger files retain their original source identities and headers.

## Runtime wheel distributions

`distribution-index.json` records the exact originating wheel, member path, copied license path, SHA256 and byte count for **14** supplied license files from **12** runtime wheel distributions. These are the distributions used by `support/requirements-replay.lock`.

| Distribution | Version | License identified by distribution metadata or supplied text |
| --- | --- | --- |
| annotated-types | 0.8.0 | MIT |
| cffi | 2.1.1 | MIT-0, as declared in wheel metadata; preserve supplied detailed license text |
| colorama | 0.4.6 | BSD-style three-clause text; no SPDX expression supplied by this wheel |
| cryptography | 50.0.2 | Apache-2.0 OR BSD-3-Clause; both license texts preserved |
| griffe | 2.4.1 | ISC |
| griffecli | 2.4.1 | ISC |
| griffelib | 2.4.1 | ISC |
| pycparser | 3.11 | BSD-3-Clause |
| pydantic | 2.14.1 | MIT |
| pydantic_core | 2.50.1 | MIT |
| typing_extensions | 4.16.0 | PSF-2.0 |
| typing-inspection | 0.4.4 | MIT |

The exact files are in `distributions/`. `support/dependency-manifest.json` retains the complete declared license-expression and dependency metadata. This index describes the wheel-supplied licensing material; it is not a separate legal certification of every statically linked or transitive native component.

## Historical integration illustration

`integration-wheel-index.json` preserves **13** supplied license/notice files from the **11** existing historical HTTPX/Starlette runtime-example wheels. Exact wheel and copied-text identities are recorded. The files are in `integration-distributions/`. These old development-example dependencies are separate from the static analyzer's runtime environment and are not current deployment recommendations.

## Source snapshots and consumer inputs

`source-license-index.json` indexes the **24** exact license/NOTICE files already retained with the development and confirmation source inputs. Their source repositories, exact commits, Git-blob identities and retrieval provenance are in `data/development/manifest.json` and `data/confirmation-licenses/manifest.json`.

| Source | Retained attribution |
| --- | --- |
| AGI-Alpha-Agent-v0 consumer scope | Apache 2.0; original license preserved |
| HTTPX 0.27.2 and 0.28.1 | Original BSD-style license files at both exact commits |
| Starlette 0.36.3 TestClient development example | Original BSD-style license file at its exact commit |
| FastAPI, five selected releases | MIT license at every selected exact commit |
| Requests, five selected releases | Apache 2.0 LICENSE and NOTICE at every selected exact commit |
| urllib3, five selected releases | MIT license at every selected exact commit |

No inspected upstream Python source was rewritten to add this project's header. Original notices, historical versions and negative research results remain preserved. External Python/Node/operating-system distributions are user-supplied prerequisites; their executable distributions are not included in the companion.
