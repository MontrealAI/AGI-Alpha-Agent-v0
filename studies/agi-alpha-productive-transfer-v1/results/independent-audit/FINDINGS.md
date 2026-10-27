# Independent audit of the sealed primary experiment

The curator arm A and model intake arm B identify the same fifteen relevant calls across six consumer/transition jobs. They produce the same six conditional binding-preserved results, one conditional binding conflict and eight unresolved results. The frozen oracle finds no omitted, duplicated or spurious calls and no wrong declared targets in either arm. The conventional arm C also inventories all fifteen calls, but returns unresolved for every call. This difference does **not** establish an advantage over a strong conventional implementation: the comparator demands export resolution that the other arms need not prove before proposing a conditional target.

The complete customer handoff remains incomplete in every primary arm. This is distinct from the successful source-inventory endpoint. All primary outputs, the candidate and the oracle remain unchanged.

## What was verified

The independent task/oracle freeze `348dc36931d02792bfae75316e0d5dcf73491aaad775e0bd6abe3d3adec27ea5` contains eighty immutable files. Every file still matches. The thirty-one candidate files, twenty-two execution-freeze files and 162 sealed campaign payloads also match. All fifty-six original source/license bodies still match their recorded Git blob identities and SHA-256 digests. Six raw inputs equal the previously sealed oracle copies, including all embedded source bodies.

The primary campaign is `8bf1219d32de201c5adacecb94b66c281886c6664505a9ec8166d11946fc7323`. It contains exactly eighteen successful, non-retried executions. Each recorded meter command invokes the actual Workbench adapter; each resulting pack binds the exact input, proposal, result and unchanged source closure. All eighteen retain HOLD admission, no active authority, no active proof, disconnected settlement, zero collections and no production approval. The source closure is `9299882e85b1887fdd8c16071c4a2b314f8cf4f7a95136ce04e39ba5e7f214bd`. Local evidence is not a signed external attestation or an installed-operator trial. See `identities.json`, `workbench-audit.json` and `acceptance-release.json`.

The unchanged pre-outcome evaluator was run on B/C's sealed extraction responses. A's native request was losslessly projected into the same evaluator: identical call coordinates, targets and mapping explanations, after checking exact original source equality. This audit did not add or repair any call. The projection files and the eighteen evaluator reviews are retained. No candidate mission was rerun, and no upstream package was installed or executed.

## Per-job results

“Accepted inventory” means the complete scoped call inventory passes the fixed extraction oracle. “Preserved” and “conflict” refer to the named declarations, conditional on correct runtime dispatch and successful argument evaluation. They do not approve an upgrade.

| Job | Arms | Accepted inventory | Required calls | Preserved | Conflict | Unresolved | Output next action |
|---|---|---:|---:|---:|---:|---:|---|
| T01, Alpha HTTPX evaluator | A / B | Yes / Yes | 6 | 0 | 0 | 6 | Review unresolved receiver/dispatch scope |
| T01 | C | Yes | 6 | 0 | 0 | 6 | Review unresolved scope |
| T02, OpenAI HTTPX initializers | A / B | Yes / Yes | 2 | 0 | 0 | 2 | Review expanded arguments |
| T02 | C | Yes | 2 | 0 | 0 | 2 | Review expanded arguments |
| T03, KernelPCA earlier transition | A / B | Yes / Yes | 2 | 2 | 0 | 0 | Review unproved imports/dispatch |
| T03 | C | Yes | 2 | 0 | 0 | 2 | Review unresolved target |
| T04, KernelPCA later transition | A / B | Yes / Yes | 2 | 1 | 1 | 0 | Hold dependency-only update and test |
| T04 | C | Yes | 2 | 0 | 0 | 2 | Review unresolved target |
| T05, locally linear embedding | A / B | Yes / Yes | 2 | 2 | 0 | 0 | Review unproved imports/dispatch |
| T05 | C | Yes | 2 | 0 | 0 | 2 | Review unresolved target |
| T06, statsmodels spline integration | A / B | Yes / Yes | 1 | 1 | 0 | 0 | Review local import/dispatch |
| T06 | C | Yes | 1 | 0 | 0 | 1 | Review control-flow-dependent binding |

No arm omitted a required call, invented a call, selected a wrong target or emitted a source-binding result that disagrees with the independent oracle. No runtime mapping is established for the seven conditional bindings. T03 and T04 share a consumer and are two transition questions, not independent defect families. Fifteen calls are not fifteen jobs or customers. The full machine-readable per-job/per-arm data are in `summary.json`.

## Substantiated consequential defect

The actual scikit-learn 1.1.3 consumer at commit `ffc0f66676b4835eb1bdd3f3ecab025e9c1be9fe`, `sklearn/decomposition/_kernel_pca.py`, lines 330–332, calls `linalg.eigh(K, eigvals=(...))` on the dense branch. The captured SciPy 1.10.1 declaration at `c1ed5ece8ffbf05356a22a8106affcd11bd3aee0`, `scipy/linalg/_decomp.py`, line 270, accepts the `eigvals` keyword. The captured SciPy 1.14.1 declaration at `92d2a8592782ee19a1161d0bf3fc2241ba78bb63`, line 283, does not accept that keyword and has no arbitrary keyword collector. The independent inert Python signature binder rejects the latter with an unexpected-keyword error.

This substantiates a source-contract conflict under the recorded nominal target. A/B correctly instruct the maintainer to hold a dependency-only update, reproduce that dense path, review the supported upstream migration and test the complete dependency set. It does not establish an observed runtime crash: the packages and application were not executed, and the original core continues to mark the re-exported target as unproved runtime identity. The separate preserved `eigsh` path does not erase the dense-branch conflict. The frozen evidence is `../../acceptance/oracle/T04.json`; original full bodies and source licenses are retained beside it.

## Why C is not a sufficient strong comparator

`src/conventional.py`, `Provider.resolve`, treats each wildcard import as an unknown binding. It does not inspect the captured imported module's `__all__` and follow an eligible wildcard export chain. These are normal public export patterns in the supplied HTTPX and SciPy sources. The failure is visible in the code's `bindings.append(("unknown", None))` path followed by its single-binding requirement. A/B, in contrast, are explicitly allowed by the frozen prompt and unchanged core to name source-supported **conditional declaration candidates** without claiming runtime identity.

For T03–T05, C therefore emits “target is absent or ambiguous in captured provider declarations” even though the captured export modules and unique declaration candidates support the same conditional review performed by A/B. The wording records the extractor's unresolved state; it does not independently demonstrate that the underlying source lacks a candidate. For T06, C merges the local `simpson` import with the compatibility fallback after `ImportError`; it does not use the captured availability of `simpson` to offer the same standard-import conditional candidate. The conservative alternative remains safe, but it provides less useful evidence for reasons an ordinary reusable export resolver could address.

For T01/T02, genuine runtime limitations remain even with correct target extraction: constructor/descriptor/context-manager dispatch and expanded `**kwargs`. C's refusal is appropriate in outcome, although its missing-target language for the two HTTPX constructors is less precise than the evidence permits. Neither arm may turn these into compatibility approval.

The primary shows B's ability to propose useful targets that this C does not propose. It does not identify a model-specific advantage over competently implemented conditional symbol resolution. A and B have no quality difference here. Unknown model costs and unknown curator attention prevent a supported labor/cost advantage. Preserve C and the original results. Any C2 correction must have its own construction cost, freeze and independent fresh corpus; it cannot replace these primary values.

## Complete-delivery failures preserved

All six C executions have `coreRecord: null`. The shared `run_mission.py` renders customer reports only when a core record exists, so C produces neither `report-en.md` nor `report-fr.md`. This is a packaging defect for an all-unresolved outcome, not evidence that C's call inventory is wrong. B would face the same shared rendering defect if it produced only unresolved intake rows.

All twelve A/B report pairs refer to files absent from the delivery directory: `decision-record.json`, `automated-costs.json`, `cost-analysis.json`, `ledger.json` and `ledger-analysis.json`. The adapter used the existing report renderer without creating its expected companion artifacts. T01/T02 also show empty code blocks and no source links in their unresolved-call sections. Their JSON requests retain the underlying coordinates and original bodies, but the reader-facing report loses that navigation and does not name a concrete integration check.

Accordingly, **6/6 inventory acceptance per arm is preserved, while 0/6 complete bilingual handoffs per arm pass this additional artifact audit**. The latter is a post-outcome audit against the already specified complete deliverable; it is not a replacement frozen extraction endpoint. The files were not repaired. No customer acceptance was observed. A new common packager may produce a clearly labeled supplementary handoff or be tested in a fresh experiment, but must not rewrite the original artifact history.

## Useful actions that remain

T01 needs a named integration test for the actual Alpha `evaluate_agent` HTTPX download/stream path and the runtime receiver identities. T02 needs the concrete keyword dictionary and MRO at each OpenAI client initializer before a dependency decision. T03/T05/T06 have conditional preserved argument bindings and still need the relevant imported callable identity plus numerical regression tests. T04 warrants holding the dense KernelPCA path's dependency-only update pending a supported upstream change and a regression check. These are reviewer recommendations drawn from the source evidence; they are not claimed to be extra text generated by the primary arms.

## Reproduction and interpretation

Run `python results/independent-audit/audit_primary.py --out /new/audit/directory` from the study directory after obtaining the source bundle. The copied `acceptance` directory contains the unchanged independent protocol, six tasks, oracle, controls, complete original source/license bodies and original freeze. The driver's new output directory must not already contain its output files. `--copy-corpus` was used once for the first audit release and should not be supplied again.

The resource supplement records this audit separately from per-mission work. Model authoring, active attention and money remain unknown; elapsed session or process time is not a wage bill. This audit neither discovers new sales nor justifies a lower trust, integration or human-effort input in the economic model.
