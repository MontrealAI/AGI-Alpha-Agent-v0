# Bounded runtime qualification pilot

**Observed result, 27 October 2026:** the reported ZipStore failure reproduces in the historical dependency closure, while the same path passes in the authoritative current closure. **Stop using this specific failure as an unresolved current flagship need.** Preserve it as historical development evidence. No general instrument or speculative repair was built.

## Results

| Environment | Zarr | Dask | Public existing-array path | LocalStore control | Published direct-create control |
|---|---|---|---|---|---|
| Reported dependencies | 3.1.3 | 2025.9.1 | Write returns; ZIP integrity fails; fresh reader raises `BadZipFile`; rejected | Accepted | Accepted |
| Current releases | 3.4.2 | 2026.8.0 | Write returns; ZIP integrity passes; fresh reader recovers expected array; accepted | Accepted | Accepted |

Historical NumPy/Numcodecs were 2.3.3/0.16.1. Current resolution installed 2.5.4/0.17.1. Both environments used Python 3.12.14 on this Linux host, rather than the original Python 3.11 report. This reproduces the reported array/write path and named package versions, not the entire original machine environment.

The historical failed ZIP is preserved with SHA-256 `116d8f44693ab4e71ff58e1fdb57b2b004e0cb390835baa8055ee7d5355065f4`. The accepted current ZIP has SHA-256 `a3d6ee8609187a77b716723eac14ae0e9ee36d9bdf2da0f992165f2407817fd8`. Result JSON files include all artifact lengths/hashes, exact installed versions, wrapper-source hashes, warnings, timings and fresh-reader output.

### What was executed

The primary case follows [Zarr issue #3516](https://github.com/zarr-developers/zarr-python/issues/3516): create an existing Zarr array within a writable ZipStore, call `dask.array.to_zarr` with that array, close the writer, and reopen in a fresh Python process. The verifier independently applies the standard-library ZIP integrity checker and then reads shape, dtype and values through Zarr.

The LocalStore control keeps the group/data organization. The direct-create control implements the already published alternative using `zarr.create_array(data=...)`; it creates a root array of twenty consecutive integers. Its different layout and input are explicit: it is an available conventional alternative, not a matched-layout cure invented here. All known remedies belong in E.

Exactly one completed primary case and two completed controls ran per environment. These are finite qualification observations, not reliability estimates. The single-element zero-valued primary fixture tests the public failure path, not scientific workload coverage. No distributed cluster, cancellation campaign, large dataset, unfamiliar recipient or model-comparison experiment was run.

### Preserved interruption and protocol correction

The initial default-sandbox attempt in each environment stalled before creating an artifact. Both were interrupted with exit code 130 and retained as the first attempt. No stack was recorded before interruption, so neither the exact blocking operation nor its cause is established. A subsequent standalone default-sandbox background-thread probe successfully created a socket pair and asyncio loop; attributing the initial stalls to network restrictions would be unjustified.

`protocol_amendment.json` was written before any scientific outcome. It counted those attempts against the four-attempt cap, dropped the synchronous-scheduler case, and specified three remaining cases per environment. Each ran in the normal approved execution context with a 30-second outer deadline, ten-second stack diagnostics, and `OMP_NUM_THREADS=1` / `OPENBLAS_NUM_THREADS=1`. No application network requests or external writes were made by those cases. They completed in approximately 0.67–0.97 seconds wall time each, including interpreter startup. Thus **four total attempts per environment** were used, including the interrupted attempt. The pilot does not establish synchronous-scheduler behavior locally.

The old wrapper is preserved under `sources/run_case-before-timeout-observation.py`. Initial protocol, amendment, interrupted receipts and completed receipts remain separate. Original results are not overwritten by the corrected execution procedure.

## Current release and prior-work status

Official [PyPI Zarr](https://pypi.org/project/zarr/) and [PyPI Dask](https://pypi.org/project/dask/) metadata were fetched and saved at 2026-10-27 16:18 UTC. Zarr 3.4.2 was uploaded that day; Dask 2026.8.0 was uploaded on 24 August. `sources/release_selection.json` records the exact metadata hashes, selected versions, upload times and distribution hashes. Pip installation reports retain package URLs and hashes, and complete installed freezes are saved. July's 3.2.1/2026.7.1 pair is not called current.

[PR #4168](https://github.com/zarr-developers/zarr-python/pull/4168) was open when read. Its proposal is to reject writable ZipStore pickling rather than promise successful concurrent ZIP writes. No proposed PR code was installed or applied. The observed current success does not identify which dependency change caused it, establish that every related path is fixed, or prove the proposal unnecessary. The pilot deliberately stops rather than searching for another failing variant to rescue the selection.

## Temporal outside option: documented, not executed

The current [Temporal Python README](https://github.com/temporalio/sdk-python/blob/main/README.md) documents that multiprocess/other activities do not receive the same raised cancellation as threaded activities and exposes cancellation/context primitives. The current [sync/async guidance](https://docs.temporal.io/develop/python/best-practices/python-sdk-sync-vs-async) explains activity execution choices and warns against blocking an async event loop.

In [issue #1048](https://github.com/temporalio/sdk-python/issues/1048), a maintainer explicitly suggests using an async **activity** that delegates to the chosen executor and handles cancellation according to that executor's semantics. This is an established E option. It is not permission to perform nondeterministic executor work in a Temporal **workflow**. An async wrapper alone does not establish native-process quiescence or correct artifact publication; the application-specific mechanism still needs testing.

**No Temporal SDK/server execution, process-pool cancellation test, heartbeat test, or side-effect test occurred in this pilot.** The cancellation need therefore remains sourced rather than locally reproduced. It cannot be combined with the historical ZIP failure into an observed joint failure.

## Evidence and commercial limits

Observed: package installation, six completed local cases, two interrupted attempts, files, readback outcomes and local timing. Sourced: public report, known alternatives, release metadata and Temporal guidance. Unmeasured: broad failure rates, expert labor savings, customer acceptance, actual total research cost, willingness to pay, profit, and fresh transfer value. No customer revenue or admitted Alpha resulted.

Complete costs remain unknown: installation, aborted attempts, preparation, analysis and evaluation all consumed resources without a complete billing/time ledger. The subsecond successful case durations are not complete delivery costs or a claim of economic advantage.

## Files and reproduction

- `prepare_envs.py`: creates isolated scratch environments using official PyPI; it refuses an existing environment. The recorded freezes and install reports identify the actual experiment more precisely than a later rerun of "current" selection.
- `protocol.json`, `protocol_amendment.json`: original cap and prospective execution correction.
- `run_case.py`, `verify_store.py`: qualification wrapper and independent-process readback, with source hashes in receipts.
- `run_remaining.py`: completed three-case sequence with outer deadlines; existing result directories prevent accidental reuse.
- `results/`, `logs/`, `sources/`: preserved output bytes, observations, failures, installation evidence and exact dependency freezes.

To replay one frozen case into a **new** directory, use the corresponding existing environment's interpreter with `run_case.py --mode reported_default --out /absolute/new/path`. Apply the recorded thread limits and an outer 30-second deadline. Recreate environments from the recorded exact freezes and distribution hashes when necessary. The environment directories are local installation products; exclude them from the compact research package and retain their reproducible manifests.
