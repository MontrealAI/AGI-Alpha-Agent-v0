# Scoped capability admission for numerical research

This additive module reuses the previous study's authority and commitment sources unchanged. It adds new numerical dossiers and actual independent callback validation; it does not inherit metadata-workflow admission. It creates no live identity, credential, runtime policy, operator grant or blockchain operation. Live identity enforcement is **NOT RUN**.

`inherited-source-manifest.json` identifies every unchanged copied file. `native/SOURCE.json` identifies the seven-module original SUCCESSOR Workbench closure. The research Merkle profile remains `SHA256_RESEARCH_V1`; it is not compatible with the paper's `JCS_KECCAK256_V2` byte format.

## Installed interface

```js
import {createCapabilityStore} from './capability-store.mjs';
const store = createCapabilityStore({
  rootDirectory: studyRoot,
  fixture,
  verifier: independentSkillVerifier,
  compositionVerifier: independentCombinedVerifier,
  verifierSource: [{path:'workloads/verifier.py', sha256: verifierHash}],
  compositionVerifierSource: [{path:'workloads/verifier.py', sha256: verifierHash}],
  executionPolicy: null
});
const admitted = await store.admit(dossier);
await store.admitComposition(compositionDossier);
const epoch = store.publish();
const result = store.select('inverse-result', {
  strategy:'registry',
  scopeDigest: admitted.binding.scopeDigest,
  environmentDigest: admitted.binding.environmentDigest,
  rightsDigest: admitted.binding.rightsDigest,
  expectedRoot: epoch.root.graphRoot
});
```

A dossier supplies `id`, string `version`, `creator`, `motivatingJob`, `outputs`, exact versioned `dependencies`, `implementation: {entrypoint, files:[{path,sha256}]}`, `evidence: {files:[{path,sha256}], ...}`, `scope`, `environment`, `rights` and integer fixture-time `expiresAt`. It can additionally record candidate history and cost/provenance references. Records contain safe integer values or strings; numerical floats belong in exact hashed file bytes, not rounded record fields. Source/evidence paths must remain within the study root and may not traverse symlinks.

The installed skill verifier receives frozen `{dossier, binding, implementationFiles, evidenceFiles}`. File entries include their verified UTF-8 `text`, byte count and hash. It must **actually independently evaluate** the supplied scoped evidence and return `{accepted, checks, implementationDigest, evidenceDigest, scopeDigest}`, copying the last three values from the received binding only after its independent computation succeeds. The store invokes it before admission or revalidation; record-level `claimedPass` flags are irrelevant. Source identities name the installed verifier, and a later source change refuses reuse. This is a trusted installed callback boundary, not a sandbox for imported validator code. Returning a dishonest true value from trusted verifier code cannot be cured by hashing it.

A composition dossier supplies `id`, `target` (e.g. `inverse@1`), exact topological `members`, and `evidence.files`. The installed composition verifier receives frozen `{dossier, bindings, bindingDigest, evidenceFiles}` and must execute independent combined-workflow checks before returning `{accepted, checks, compositionValidated:true, bindingDigest}`. Components alone never qualify a composition. Changed component bindings or evidence require new validation.

Registry and graph arms use the same indexed output search, exact versioned dependencies, source/evidence identities, authority policy, composition validation, lifecycle rules and cost observations. The registry performs competent dependency closure directly from record fields; the graph follows its adjacency index. No performance advantage is built into either branch.

`revoke(id, reason)` and `supersede(oldId, newId, reason)` append lifecycle events, invalidate the current root and preserve old roots/evidence. Republishing binds the new lifecycle state. `admit(sameDossier, {revalidation:true})` reruns the actual verifier and issues a fresh fixture attestation without rewriting the version. Retired versions require a newly validated version. `inspect()` returns a copy of records, composition evidence, events, roots and successful validation receipts. Callers must record failed exceptions and the complete outer resource cost; the module does not invent missing authoring, attention or cash costs.

The creator string is attribution only. Skill attestation defaults to an eligible direct agent under `ISSUE_SKILL_ATTESTATION`; root publication uses a separate `COMMIT_GRAPH_ROOT` signer. Names, signatures and registry data are expressly noncryptographic fixtures. A matching Merkle root is never execution permission.

Optional `executionPolicy` is an independently installed local research limit with `{mode:'LOCAL_RESEARCH_ONLY', nativeAuthority:[], allowedSkills:[...], maxRuns, expiresAt}`. `authorizeLocalExecution(selection,{missionId,now})` accepts only an original successful selection object issued by this store, checks current source/lifecycle again and consumes one local run. Serialized or reconstructed copies cannot confer permission. It launches nothing and never grants Harness/Fleet, signing or settlement authority.

## Native Workbench binding

Use `native/examples/successor-workbench/engine.mjs` via its documented `createWorkbench([adapter])` interface. The installed adapter supplies `manifest`, `validate`, and `execute`. It can invoke a fixed reviewed local research solver and fixed independent verifier; the importing job must never supply code, command or host-path authority. Bind `sourceHash` to the adapter and unchanged source closure. `inspectPack` verifies native plan/artifact/history integrity.

The native canonical format permits safe integers, strings, booleans and null. Preserve full-precision numerical output as exact artifact JSON text or file hashes; do not round it to fit the native record. Each artifact is bounded to 200,000 characters; at most twelve are allowed. Native evaluation remains `PUBLIC_LOCAL_EXECUTION`, `admission:HOLD`, empty authority and `settlement:NOT_CONNECTED`. A fixture graph admission cannot upgrade those original fields. Importing a pack remains unauthenticated historical evidence.

## Current source admission and cached reuse

The study freezes numerical admission separately from later reuse. `validate_evidence.py` executes the exact declared entrypoints for `forward@1`, `inverse@1`, retained historical `design@1`, and the contributed `design@2` on the two registered 225- and 400-node discovery chains. It independently verifies every new output. Both design versions receive networks materialized from the newly accepted inverse output. A further six executions use the actual production worker and current dispatcher, with independently accepted results and current linked design inputs. It hashes the complete local implementation closure before and after each execution, including the dispatcher, core, independent contribution and worker. An archived accepted answer cannot admit changed source.

`build_catalog.py` constructs version-specific dossiers from this bound evidence. `study_catalog.mjs` admits all four versions, independently admits the three dependency compositions, publishes their state, supersedes `design@1` with the selected contribution `design@2`, and publishes again. The predecessor remains inspectable history. The contributor's method is ordinary, reproducible numerical engineering; the retained versions are not counted as two independent market capabilities.

The resulting `evidence/admission-cached/catalog-admission.json` contains the validated state and an exact manifest of source, configuration, fixture, verifier and evidence files. `protocol/admission-pin.json` pins that receipt, the catalog and fixture bytes, the state digest and the graph root. The production freeze must additionally bind both files and the catalog and fixture JSON. Receipt creation uses exclusive writes and refuses replacement. Any intentional later revision requires a separately retained receipt and a new protocol freeze, with source changes first executing and passing new validation.

Later B and C invocations load the same receipt, verify its production pin and complete input identities, and restore the validated state with admission callbacks disabled. They check current source, evidence, policy, authority, lifecycle, dependency bindings and inclusion proofs; they do not rebuild the Merkle forest or rerun all numerical admission. This equal treatment prevents cold validation overhead from being charged to every shared-registry or graph job. Charge the original execution, validation and publication once, allocate it transparently, and charge each actual cached lookup and integration to its recipient.

Before retrieval, `runtime_context.py` validates the actual job's schema, family, finite numerical arrays, permitted synthetic provenance, grounded network, node/load/parameter/design bounds and measured Python/NumPy/SciPy versions. `production/run_one.mjs` derives the requested scope and environment from those checks, binds the exact job hash to a separate one-run local execution receipt, and checks the executed job still has those bytes. Every arm receives the same domain/runtime check. The permission is a **prospective bounded research trial**, up to 4,096 nodes, 16 loads, 32 inverse parameter groups and 80 design variables. The empirical admission evidence covers **225 and 400 nodes only**. Larger jobs require their own fresh independent outcome acceptance. No record or inclusion proof changes that distinction.

Reproduction order for the current immutable admission was:

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 python identity/validate_evidence.py --output evidence/admission-current-v2
python identity/build_catalog.py --evidence-root evidence/admission-current-v2
node identity/study_catalog.mjs
python production/freeze_runtime.py
```

The published output directories already exist, so these commands must not be used to overwrite them. Old cold diagnostics and the first direct-entrypoint prototype remain preserved. Final source changes invalidate their admission identity and require new execution, evidence and receipt paths before another protocol freeze.

## Software controls

Run `node identity/capability-store.test.mjs` from the study root. Twenty explicit controls cover actual verification, false self-certified evidence, agent-only namespace, independent grants, registry/graph parity, independent composition, source/evidence drift, expiry, authority transfer, revocation, supersession, revalidation, dependency binding, trusted-root mismatch, Merkle tampering, finite separate execution permission and unsafe paths. The tiny arithmetic used in these controls tests admission behavior; it is **not** part of the demanding numerical study or evidence of capability scarcity.

`node identity/admission-cache.test.mjs` adds fourteen focused controls for restoration without admission callbacks, registry/graph selection of the same contributed composition, tampered state, changed policy or source, finite execution permission, and actual job hash/runtime/schema/domain checks. The saved outputs are `audit/identity-controls-cached.txt` and `audit/admission-cache-controls.txt`.
