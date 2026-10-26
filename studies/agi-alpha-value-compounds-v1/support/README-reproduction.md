# Reproduce the useful result offline

This companion includes the exact source, inputs, frozen methods, wheels and licenses required for the bounded source-assessment workflow. The command below installs its existing dependencies offline, verifies the original source identities, runs the recorded checks, and produces a new English/French dependency-upgrade packet. It writes everything to a new directory outside this package.

From the companion root:

```sh
python3.12 support/replay_offline.py \
  --out /tmp/agi-alpha-offline-replay-001 \
  --mission httpx-development \
  --arm conventional
```

Choose a new output name for each run. Existing destinations are refused. Open `/tmp/agi-alpha-offline-replay-001/mission/report-en.html` or `report-fr.html` for the useful result. The same folder contains `upgrade-packet.json`, exact source identities, a resource receipt, `pack.json`, independent inspection and the full evidence report. `summary.json`, `environment.json`, `operations.json` and the `logs/` folder describe the clean replay environment and its costs.

## Supported environment and actual verification

The bundled wheels support **CPython 3.12 on Linux x86-64 with glibc 2.34 or newer**. Python must include `venv` and its bundled `ensurepip`. Node.js is an external prerequisite. The verified environment was CPython **3.12.14**, glibc **2.39**, and Node **24.22.1**. The script records a different Node version as a different environment; equivalence is not established merely by starting the command. The repository's independently pinned Node 22.17.1 release qualification remains a separate process.

Python, Node, the operating system and a LaTeX distribution are not bundled. No compiler, model credentials, model inference service, npm installation, package index, customer account or blockchain transaction is required for this replay. A different CPU architecture, Python ABI or operating system needs a separately verified wheel set. The supplied historical HTTPX/Starlette demonstration is an exposed development case; its old versions are not a current deployment recommendation.

The clean replay on 26 October 2026 completed:

- An offline installation of all **12** exact runtime wheel distributions using `--no-index`, `--require-hashes` and binary wheels only; `pip check` reported no missing or incompatible required dependency.
- Import-origin checks proving that Griffe, Pydantic, cryptography and the other named third-party modules came from the new virtual environment. The existing `deps/site` unpacked cache was absent from the staged copy.
- The **75** frozen shared tests and **47** candidate cross-checks. One cross-check contains 150 synthetic signature pairs; those are development checks, not additional missions.
- The existing Node economics test program.
- The unchanged native SUCCESSOR Workbench extension executing the conventional HTTPX development assessment: 31 source-binding losses, no strict consumer finding and one separately labelled syntactic caller candidate.

That replay took **18.6339 seconds wall time** and **18.5899 seconds observed child-process CPU**, including virtual-environment creation, installation, tests and the selected Workbench mission. It is packaging/reproduction work and adds **zero new customer jobs**. Monetary inference charges remain unknown. It does not replace the primary experiment's timing measurements.

One earlier support-only attempt failed before environment installation because the staged copy omitted `discovery/confirmation-metadata-v3.json`. Its failure record is preserved in `verification/failed-run-01/FAILED.json`. The support staging code was corrected; no frozen method, source or primary result changed. Successful evidence, complete subprocess logs and the resulting packet are preserved under `verification/successful-run-02/`, with a file inventory in `verification/manifest.json`.

## What the replay preserves

The script verifies the final freeze manifest SHA256:

```text
25ee20b1cd68710a5eea65fc08e2eba2f47a521bfde2d9ebbf37731280bc6d64
```

It checks all 20 frozen files and all 19 native source files before and after replay. Native code remains pinned to Alpha commit `eb07086ac42799ff45f7b1c946a2f7c514bd3bbc`. Original primary outputs are never the replay destination.

The Workbench's own inspection result remains `UNAUTHENTICATED_HISTORICAL_IMPORT`, with empty active proof and authority. Integrity validation is not operator approval, release qualification, production adoption or financial authority. This package demonstrates the local research adapter on the existing extension API.

The offline installer requests no index access. The selected static local workflow makes no runtime model or network calls; the support script does not claim a kernel-enforced network sandbox. It never imports the source snapshots being assessed. Those Python files are data for the static analyzers.

## Exact dependency closure

`dependency-manifest.json` records the wheel byte counts, SHA256 values, package metadata and dependency declarations. `requirements-replay.lock` pins every required runtime package and its actual local wheel hash. The 12 runtime wheels total **7,962,779 bytes**:

| Role | Exact distributions |
| --- | --- |
| Conventional analyzer | griffe 2.4.1; griffecli 2.4.1; griffelib 2.4.1; colorama 0.4.6 |
| Native typed models | pydantic 2.14.1; pydantic_core 2.50.1; annotated-types 0.8.0; typing-inspection 0.4.4; typing_extensions 4.16.0 |
| Native cryptographic imports | cryptography 50.0.2; cffi 2.1.1; pycparser 3.11 |

Optional Griffe `faster`/`pypi`, Pydantic `email`/`timezone`, and cryptography `ssh` extras are not part of the selected workflow and are not claimed to be bundled. FastAPI, Requests and urllib3 confirmation snapshots are analyzed as inert source; importing those target packages is not part of this static service.

The older ASGI runtime illustration has its own 11 wheel files under `data/development/integration-example/wheels/` and its own previously recorded replay. They are separate from this analyzer environment, especially the old typing_extensions version. Their license/notice files are indexed in `licenses/integration-wheel-index.json`.

## Other registered assessments

The registry preserves `httpx-development` plus the 12 historical confirmation transitions: `fastapi-1` through `fastapi-4`, `requests-1` through `requests-4`, and `urllib3-1` through `urllib3-4`. Supply another existing ID and a fresh output directory to reproduce that assessment with `--arm incumbent`, `retained`, or `conventional`.

Running an already recorded mission again is a replay, not a new customer job or fresh confirmation. The held-out claim describes the original study chronology: exact metadata and methods were frozen before those primary source bodies were retrieved. Public historical source may have been present in model pretraining; it was not a prospective secret release. The raw release snapshots, source-custody record and licenses remain inspectable under `data/confirmation/` and `data/confirmation-licenses/`.

## Replay the original twelve-transition campaign

After the successful support command above, its `study/` directory contains a separate copy of the frozen
methods and registered source inputs, and its `venv/` contains the verified runtime dependencies. Use that
copy and an unused destination to repeat the original campaign:

```sh
cd /tmp/agi-alpha-offline-replay-001/study
PYTHON_EXECUTABLE=/tmp/agi-alpha-offline-replay-001/venv/bin/python \
  node src/campaign.mjs /tmp/agi-alpha-campaign-replay-001
```

The final path must not exist. This command repeats the twelve missions whose registry role is
`held-out-historical-confirmation`, using all three arms and three timing repetitions. It does not turn
the replay into fresh confirmation or automatically evaluate other newly registered mission IDs. Run a
separately registered assessment through `src/workbench.mjs` with its explicit ID and a new output directory.

Inspect the **new destination's** `runs.json`, `COMPLETED.json`, `repeat-1/` through `repeat-3/`, packets and
full evidence for the replay's actual decisions and timings. Failed executions retain their new failure
record. Keep the original companion's `results/confirmation/` and published tables unchanged. The campaign
driver records per-run resources; it does not by itself reproduce the original external process-metering
record or complete construction costs.

### The supplied summarizer is fixed to the original study

`analysis/summarize.py` has no command-line option for a campaign path or an output path. Its paths are
hardcoded relative to its companion root:

| Operation | Fixed original-study path |
| --- | --- |
| Read completed campaign | `results/confirmation/runs.json` and `results/confirmation/COMPLETED.json` |
| Read mission identities and process costs | `data/missions.json` and `metering/campaign-process.json` |
| Write aggregate tables | `results/summary.json` and `results/outcomes.csv` |

It also requires the original 108 timing evaluations and three repetitions per registered study
mission/arm. Passing a replay directory as an extra argument does not change these paths. Running it
beside the original evidence would reconstruct and overwrite the original aggregate tables, not analyze
the new campaign. Moving a replay into `results/confirmation/` or reusing the original process-cost
record would erase that distinction.

The staged support copy intentionally does not include this aggregator or the original campaign outputs.
For a new campaign, its own `runs.json`, completion marker and source-bound evidence are the delivered
records. A new aggregate must use a separately identified analysis with explicit new input/output paths
and appropriate timing provenance; that configurable aggregator is not supplied here. If the original
published tables need to be reconstructed, use a disposable complete copy of the original companion with
its original registry, campaign and process-metering record. Such a reconstruction remains analysis of
the original study, irrespective of any other replay that was run.

## Inspect or rebuild supporting indexes

In a separate working copy of the companion, the following local command regenerates the runtime dependency inventory and extracts the license files already embedded in the existing runtime wheels. It makes no network request and does not change frozen methods, but it rewrites supporting indexes; preserve the original sealed package:

```sh
python3.12 support/build_dependency_manifest.py
```

See `licenses/README.md` for attribution and the exact source/license indexes. No dependency, model bill, staffing assumption or deployment qualification is silently supplied by this installer. A failed installation or validation retains its logs and a `FAILED.json`; address the concrete missing input in a new support edition instead of changing a frozen result.
