# Confirmation failure analysis: constructor scope disagreement

**Status:** postconfirmation diagnosis of preserved first-repeat results. No frozen implementation, validator, protocol or primary result was modified. The retained candidate's recorded rejection remains in force. This diagnosis is not a repaired confirmation run.

## Finding

The three rejected callable rows across `urllib3-2` and `urllib3-3` arise from **one scope-screen disagreement about assignments to class attributes**. The retained implementation reports `no_call_loss`. The independent validator refuses to decide the constructor relation because it treats any module-level assignment through the class object as another binding of the parent class. The strong conventional comparator uses the same conservative scope policy and reports `unresolved`.

These failures are **not observed before-valid/after-invalid calls missed by the candidate**. No rejected row has a loss witness, and the primary validator executes zero binding stubs for the disputed rows because scope exclusion happens first. A separately recorded signature-only diagnostic confirms that all three declared constructor signature pairs preserve the binding language. That diagnostic does not change the frozen acceptance result or prove runtime compatibility.

The appropriate primary classification is **unsupported resolved statement relative to the frozen scope checker**, or **inventory/scope-policy mismatch**. It would be misleading to call the three rows three false compatibility predictions, three newly discovered dependency defects, or three independent failure families.

## Exact affected rows

| Primary mission | Transition | Callable | Frozen retained report | Frozen conventional and validator |
| --- | --- | --- | --- | --- |
| `urllib3-2` | urllib3 2.6.2 → 2.6.3 | `Retry.__init__` | `no_call_loss`; module `complete` | Constructor `unresolved`; parent-class assignment policy |
| `urllib3-3` | urllib3 2.6.3 → 2.7.0 | `Retry.__init__` | `no_call_loss`; module `complete` | Constructor `unresolved`; same parent-class assignment policy |
| `urllib3-3` | urllib3 2.6.3 → 2.7.0 | `WrappedSocket.__init__` | `no_call_loss`; module `complete` | Constructor `unresolved`; same parent-class assignment policy |

The candidate evidence files are:

- `results/confirmation/repeat-1/evidence/0029-urllib3-2-retained.json`, SHA-256 `b5e026d8be1b99a2e0277b5cfdf8d3e2e37c9df6f26496a81141e27723314f5b`.
- `results/confirmation/repeat-1/evidence/0031-urllib3-3-retained.json`, SHA-256 `0fa673de8eb8b228edfbfaf7493d4a79a74542d5a57fb9be40a97417ac43da03`.

Both hashes were verified during diagnosis. The corresponding unchanged conventional evidence is `0030-urllib3-2-conventional.json` and `0032-urllib3-3-conventional.json` in the same directory. Those reports agree with the validator by abstaining on these constructors. Their relevant module validations are accepted but explicitly have `scope_complete: false`. Acceptance therefore does not mean the conventional arm proved these constructor relations or completed all application coverage.

## Source evidence

All source bodies below are captured and hash-checked in `data/confirmation/source-custody.json` and its referenced snapshots. Inspection occurred only after the parent authorized failure diagnosis.

| Source revision | Source path and line | Actual assignment |
| --- | --- | --- |
| 2.6.2, `83f8643ffb5b7f197457379148e2fa118ab0fcdc` | `src/urllib3/util/retry.py:533` | `Retry.DEFAULT = Retry(3)` |
| 2.6.3, `0248277dd7ac0239204889ca991353ad3e3a1ddc` | `src/urllib3/util/retry.py:549` | `Retry.DEFAULT = Retry(3)` |
| 2.7.0, `9a950b92d999f906b6020bb2d1076ee56cddd5d2` | `src/urllib3/util/retry.py:557` | `Retry.DEFAULT = Retry(3)` |
| 2.6.3, `0248277dd7ac0239204889ca991353ad3e3a1ddc` | `src/urllib3/contrib/pyopenssl.py:410` | `WrappedSocket.makefile = socket_cls.makefile` |
| 2.7.0, `9a950b92d999f906b6020bb2d1076ee56cddd5d2` | `src/urllib3/contrib/pyopenssl.py:409` | `WrappedSocket.makefile = socket_cls.makefile` |

Captured source hashes are:

- `retry.py`, 2.6.2: `6e3fb6614a9b9712e5bfc4c78397f1c30f83339e1709b8e0657210ef55e2a026`.
- `retry.py`, 2.6.3: `58e7081d56b129ff9d55bf3d9546e9bdca5e33bacd605fefb0ab0238ac35d19f`.
- `retry.py`, 2.7.0: `d989d25fefc579c312843eb5331e6cebc274fdbb541d9aeb73f064155452d4fe`.
- `pyopenssl.py`, 2.6.3: `e1ac138dae28ddb7931931a6996a3fdeb068120ce37bde50e1b816cf88a24b1f`.
- `pyopenssl.py`, 2.7.0: `5d963e433c93eecf1de37aa2b00e28f9e49960178890fc8131986d8f69242d9b`.

These are assignments to `DEFAULT` and `makefile`, respectively. Neither source statement directly replaces `__init__` or rebinds the class name. The `Retry` right-hand side instantiates a class, so these lines are still runtime activity; the source-only tools do not execute or certify that activity.

## Mechanism in frozen code

`src/dossier.py` builds `_bound_names` from `ast.Name` nodes in `Store` or `Del` context, with explicit function/class/import and pattern handling. For an assignment such as `Retry.DEFAULT = ...`, the assignment target is an `ast.Attribute` with `Store` context, but its base `Retry` is a `Name` with `Load` context. The candidate therefore does not add another `Retry` binding. Its constructor extraction sees one direct class declaration and one direct constructor, and evaluates the declared signatures.

`src/conventional.py::_targets` instead recursively follows `Attribute` and `Subscript` targets to their base names. The class is recorded as `['class', 'assignment-or-deletion']`; `parent_blocks` consequently excludes its constructor.

`src/validate_dossier.py::DeclarationInventory._bind_target` independently follows the same kinds of targets to the base name. The parent's binding count becomes two, and `_read_declarations` places the class in `parent_excluded`. `validate_dossier` then expects `unresolved`, rather than evaluating a finite binding domain. This explains both the explicit `status differs from independent source relation` error and the absence of stub-call work in the rejected checks.

The conventional/validator policy conservatively treats **any** mutation through the class object as constructor uncertainty. The candidate's screen ignores that entire target class, including potentially material constructor replacement. These are different limitations. The observed `DEFAULT` and `makefile` mutations do not demonstrate a constructor replacement; the candidate's broader omission should not be excused simply because these particular mutations leave the declared signature relation unchanged.

## Signature-only isolation, kept outside primary results

The diagnostic script `publication/diagnose-confirmation-failures.py` checks frozen method identities and source/evidence hashes, extracts the exact direct constructor AST nodes, and invokes the frozen independent safe-stub relation **without applying the disputed parent-class scope screen**. It never imports or executes the captured urllib3 source. Its output is separately stored at `results/postconfirmation-diagnostics/constructor-scope-v1.json`.

| Pair | Diagnostic result | Independent method |
| --- | --- | --- |
| Retry 2.6.2 → 2.6.3 | `no_call_loss` | Complete safe-stub frontier; 361 examined shapes, 531 stub calls; full finite domain size 10,485,760 |
| Retry 2.6.3 → 2.7.0 | `no_call_loss` | Identical generated binding signatures |
| WrappedSocket 2.6.3 → 2.7.0 | `no_call_loss` | Identical generated binding signatures |

The first transition appends optional `retry_after_max`; the other two generated binding signatures are identical. This is a mechanistic explanation, not a post hoc replacement of primary acceptance. The diagnosis used approximately 0.770 process CPU seconds and 0.770 wall seconds inside the script, excluding interpreter startup, review and unknown inference charges. The work is attributable postconfirmation analysis, not another productive customer mission.

## What the frozen protocol does and does not justify

`protocol.json` excludes decorated or rebound definitions and requires supported no-loss statements to agree with the independent finite-domain checker. The frozen checker includes its conservative scope inventory. The candidate failed that agreement condition, so the recorded research-admission rejection is retained.

However, the prose protocol does not separately enumerate unrelated class-attribute mutation as a rebinding exclusion. The study should disclose this granularity difference rather than pretending the checker exposed a mathematical error in containment. The direct signature guarantee and the runtime/class-mutation screen are distinct parts of the implementation. A verifier agreement failure is not automatically evidence that a real customer call would break.

The strong conventional arm remains an appropriate available component if its complete frozen evaluation qualifies, but this local agreement is partly achieved through conservative abstention. Its benefit cannot be described as discovering a break that the retained method missed in these three rows. Further outcome and completeness review belongs to the complete primary record, not to this limited failure diagnosis.

## Failure grouping and follow-up boundary

Count **one shared mechanism**, seen in two source patterns and three rejected callable-transition rows across two substantive source transitions. The persistent `Retry.DEFAULT` assignment is the same mechanism across revisions, not a second independent family. `WrappedSocket.makefile` illustrates another class attribute routed through the same coarse target rule; it is not a separate algorithmic defect family.

A future scope policy could distinguish class-name rebinding, replacement of `__init__`, other material dispatch mutation and unrelated attributes. That distinction would need explicit specification, controls and a new untouched confirmation set. No such correction was made here. The original candidate, comparator, evaluator, failure outputs, rejection and source identities remain preserved.
