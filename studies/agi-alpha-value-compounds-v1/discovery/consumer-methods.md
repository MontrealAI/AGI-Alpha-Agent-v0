# Consumer decision evidence: construction and frozen development check

Status: additive static component for the same call-compatibility capability. All material inspected here was exposed development input; no held-out source bodies were read. This file is not an economic admission or a production upgrade approval.

## Executable contribution

`src/consumer.py` exports `assess_consumers(consumer_files, before_files, after_files, producer_reports)`. Consumer records carry `path` and source text. Producer maps use repository-relative paths such as `httpx/_client.py` or `src/requests/api.py`. Reports are existing `dossier.compare_sources` outputs. The module checks every used report against both supplied source hashes before consuming its signatures.

The strict lane resolves explicit imports and reexports, direct function calls, direct class constructors, and single-base `super().__init__` calls. It verifies actual argument shapes using the existing `_constraints` binding function. Explicit positional arguments and literal closed list/tuple expansions are counted; explicit keyword names and literal closed dictionaries are resolved. Dynamic expansions, rebinding, instance dispatch, unavailable sources and unsupported declarations remain unresolved. It does not execute consumer or dependency code. A preserved binding is not a behavioral compatibility clearance.

The separately labeled candidate lane can follow wildcard reexports only if every wildcard source is captured with a closed literal `__all__`. It retains every source hash and declared export set in the trace, rejects ambiguous collisions or open export sets, and recognizes only a bounded source pattern that writes declared exports' `__module__` metadata. Import-only try blocks qualify only if all exception handlers raise. These rows remain explicitly **syntactic reexport/import-guard candidates, runtime unproved** and never replace strict unresolved rows or inflate strict findings. Independent runtime validation is required to establish behavior.

Each raw call record includes exact path, line, source snippet, call shape, targets, signatures, assumptions and a review action. Triage separates declared dependency import references, other import references and unattributed calls. A dependency reference is a review cue, not evidence that dispatch resolves or a call breaks. Calls and assertions are not customer jobs. Unvisited AST calls, if any, are counted separately.

## Frozen development result

The independent reproduction below uses complete HTTPX packages at 0.27.2 and 0.28.1, plus the exposed Starlette 0.36.3 testclient and the captured 56-file Alpha consumer slice. This is a historical/representative check, not a live requested upgrade. HTTPX 0.27.2 lies outside the current declared Alpha >=0.28 range. No paid customer or current Alpha installation of the historical Starlette pair is asserted.

| Input slice | Python files | All syntactic call sites | HTTPX import-reference sites | Strict resolved bindings | Additional runtime-unproved candidates |
| --- | ---: | ---: | ---: | ---: | --- |
| Starlette 0.36.3 testclient | 1 | 178 | 3 | 0 | 1 potential binding loss |
| Captured Alpha runtime and af_requests | 56 | 10,172 | 7 | 0 | 7 preserved bindings |

The one historical potential loss is Starlette `testclient.py:429`: `super().__init__(app=self.app, ...)` reaches the declared HTTPX `Client.__init__` signature through the complete syntactic export trace; its actual keyword shape binds before and fails afterward. This is a known historical incompatibility exposed during discovery, not an autonomous invention or unseen confirmation. The seven Alpha candidates preserve the checked call shape; that observation is not an all-clear for the codebase, its other dependencies, dynamic calls or runtime behavior.

Most of the 10,350 raw calls are not even traced to a supplied HTTPX import. They must not be presented as 10,350 likely upgrade impacts, independent defects or useful customer missions. The full raw inventory remains downloadable for audit.

## Reproduction

From the project root:

```sh
python research/value-compounds/tests/test_consumer.py
python research/value-compounds/discovery/evaluate-consumer-development.py --out /tmp/value-compounds-consumer-reproduction
```

The second command reads only the development directory, constructs source-pinned producer reports, emits both raw consumer reports and a summary, and meters report construction separately from consumer analysis. It performs no downloads or source execution. A rerun's elapsed times can differ; compare semantic rows and source identities rather than timing bytes.

The 20 focused tests cover exact aliases, local imports, qualified imports, constructor receivers, super, missing/wildcard export uncertainty, shadowing, literal/dynamic expansions, source hash mismatch, old-invalid calls, reexport relocation, wildcard collisions and missing sources, mutable export lists, import guards, class lexical scopes, source-site coverage, `src/` normalization and triage. They validate this bounded implementation; they are not paid deliverables or fresh confirmation missions.

## Construction and limits

The component was written by the assistant acting as researcher/engineer with parent-agent task guidance. It is conventional AST/source analysis built into the same tested capability. Its existence is not evidence that the operational system autonomously invented a capability. The known `app` incompatibility and public history guided development.

Construction started at 2026-10-26T13:20:01Z, before any new consumer code was written. The first test execution failed with a duplicate `node` argument in the binding helper; that attempt and repair are retained in `metering/economics.jsonl`. Discovery, construction, unsuccessful attempts, tests, source fetching, independent runtime reproduction, integration and packaging all belong in the complete asset investment. Monetary construction/inference costs and human attention are unknown, not zero. Runtime source analysis reports zero network and model calls, which does not price the assistant's construction work.

No holdout inspection occurred in this lane. The strict source mapping is deliberately incomplete for common Python dispatch. The candidate lane supplies inspectable hypotheses and scope-aware review actions, not release authority. Mainstream free tools and competent human source/grep inspection remain valid alternatives; no new commercial superiority claim follows from this component alone.

## Frozen identities and measured resources

- Consumer source SHA256: `ed74527aa013ef3c2f3aafb9ab07ee172039b09eaefebb480be89d2d0dcd82d6`.
- Test source SHA256: `156f0bc1ac364d0385a739c3c9ba31a9bec70365113d693f500667f9751c3c0b`.
- Development manifest SHA256: `1f4361cfbb584504d3e983e3fb9fd0c08372af24f15846f69d43e8b576fe35d1`.
- Exact machine-readable output: `results/consumer-development-frozen/summary.json`, with raw `starlette.json` and `alpha.json`. Earlier development outputs are retained separately.

| Operation | CPU seconds | Wall seconds | Source parses | Output bytes |
| --- | ---: | ---: | ---: | ---: |
| Producer reports | 0.175617360 | 0.175629155 | 46 | Not separately serialized |
| starlette consumer analysis, both lanes | 0.840923768 | 0.840947973 | 96 | 387073 |
| alpha consumer analysis, both lanes | 13.923584546 | 13.939380411 | 206 | 20403803 |
