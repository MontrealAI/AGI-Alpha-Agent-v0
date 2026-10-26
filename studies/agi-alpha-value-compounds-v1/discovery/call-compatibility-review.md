# Complementary call-shape compatibility capability: independent assessment

26 October 2026. Follow-up to the opportunity screen. Inspected Alpha checkout `eb07086ac42799ff45f7b1c946a2f7c514bd3bbc`; no root-reserved live workflow or confirmation history was inspected.

## The proposed outcome is new relative to the inspected incumbent

`alpha_factory_v1/core/runtime/successor/transformation_source_audit.py`, `_facts` (approximately lines 765-791), records license, syntactic imports, top-level non-underscore function/async-function/class names and dynamic-import count. `reference_report` emits these facts with captured direct/transitive dependencies and exact file identities. It does not emit parameter lists, requiredness, binding modes or a relation between before/after call acceptance. Its public-scope report is intentionally a static inventory, not full API compatibility certification. The source audit README corroborates that bounded inventory scope.

Thus a **source-pinned report of call shapes accepted before a change and rejected afterward** is a real new output relative to that inventory. A release maintainer could use the report to review a dependency upgrade, repair downstream calls, add a deprecation bridge or revise release notes. This remains a representative use case until actual project recurrence and acceptance are recorded. It is not itself evidence of willingness to pay or of avoided incidents.

The strongest narrow contribution would be a retained callable-compatibility lens integrated as an additive Workbench adapter, preserving the TI catalogue/native checks. The existing reports and `git diff` remain available to every arm. Describe assembly of this lens as researcher-assisted engineering, not autonomous invention.

## Recommended finite primary contract

Analyze only an explicitly declared scope of **top-level directly defined callables**, with every claimed result tied to before/after repository, exact commit, path, content hash, function name and source span. Calling all non-underscore names a guaranteed public API would overstate static evidence; prefer 'public-looking direct definitions' or a user-supplied declared callable scope.

Preserve all syntactic binding features: positional-only parameters, positional-or-keyword parameters, keyword-only parameters, required/default presence, variadic positional and variadic keyword. Default expressions and annotations must remain inert text; only default presence is needed for argument binding. `async` versus ordinary functions can share argument-binding shape but not runtime result semantics.

For each claimed contraction, output a finite witness:

- Number of positional arguments.
- Ordered keyword names and inert placeholder values.
- Before signature and proof that binding succeeds.
- After signature and binding rejection reason, or explicit disappeared-definition status.
- Scope qualifications and an actionable explanation.

Validate witnesses by building a fresh `inspect.Signature` from the independent AST extraction and calling `Signature.bind`, never `inspect.signature` on imported inspected code. The official Python 3.12 docs specify that `bind` returns a binding when the shape matches and raises `TypeError` otherwise. Do not use `bind_partial`, which deliberately permits missing required arguments.

A useful precision contract is zero invalid or source-unbound witnesses. Coverage should be measured against the declared supported subset and should count unresolved callables explicitly. A report with unresolved cases cannot turn zero observed witnesses into a complete compatibility pass.

## Soundness boundaries

Treat the following as unresolved or outside the primary static call-shape guarantee unless separately implemented and independently checked:

- Decorators that can replace wrappers/signatures.
- Duplicate, conditional, rebound or deleted definitions; alias/re-export resolution and module-level dynamic export machinery.
- Methods, descriptors, class constructors, generated callables and inherited members.
- Dynamic `__getattr__`, monkey patches, runtime dispatch and import-time/default-expression failures.
- Type/annotation contracts, return values, side effects, exceptions, synchronization, iterator/async semantics and argument-value validation.
- Positional reordering that silently changes meaning while preserving binding acceptance.
- Changes to default values that preserve optionality but change behavior.

A removal from a file's direct definitions is not automatically proof of a package-level API removal: an alias, re-export or dynamic replacement can preserve it. Keep the claim local to the declared definition model.

## Complete finite binding-domain option

For two supported signatures, a brute-force conventional comparator can enumerate positional counts from zero through `max(before_fixed_positionals, after_fixed_positionals) + 1`, and keyword subsets drawn from the union of parameter names plus one fresh name not used by either signature. Arbitrary values are represented by inert distinct objects. Check every shape with before/after `Signature.bind`.

This finite abstraction addresses positional-capacity differences, required parameters, positional/keyword collisions, keyword-name/kind changes and acceptance of otherwise unknown keywords. The extra positional count represents the unbounded varargs case; a fresh keyword represents the otherwise unrestricted keyword class. If presenting this as exhaustive beyond the finite enumerated domain, include the argument explaining equivalence of larger counts and additional fresh names. It does not address behavioral semantics.

The keyword power set grows exponentially. Freeze explicit source-byte, AST-node, callable, parameter and total-shape limits. Exceeding a limit must produce `unresolved/bound exceeded`, not a zero-break pass. If the primary implementation instead emits targeted witnesses, describe them as witnessed breakages and evaluate coverage without claiming exhaustive compatibility.

## Strong practical comparator: Griffe

Griffe is an established static Python API comparison tool, with `griffe check` and `find_breaking_changes`. Its official documentation covers removed objects/parameters, parameter kind changes, required additions, changed defaults and positional movement. It also emits human-readable Markdown/verbose reports. A standard-library-only comparator should not be presented as the strongest existing option without considering Griffe.

Use its static `griffe.visit(module_name, filepath, code)` entry point, or a loader explicitly configured to forbid dynamic inspection. No extensions that execute inspected source should be enabled. Pin and record the installed version and package hashes. Griffe was not installed in the current Python environment when checked; installing it in an isolated environment would be comparator setup, charged to acquisition/integration. Existing library development is a legitimate pre-existing conventional asset, not new construction that must be invented or repriced.

Griffe's semantic scope is broader than the witness lens: default-value or positional-order warnings can be valuable even when argument binding still succeeds. Report those extra alerts separately; they are not automatically false positives. Conversely, a concrete binding witness can add precision or explainability to a conventional alert without establishing a better discovery algorithm. Give the equally resourced conventional builder the right to retain a simple witness-enrichment adapter too.

### Primary sources checked

- Python 3.12 `inspect` reference: https://docs.python.org/3.12/library/inspect.html
- Griffe checking guide: https://mkdocstrings.github.io/griffe/guide/users/checking/
- Griffe static visitor API: https://mkdocstrings.github.io/griffe/reference/api/agents/
- Griffe official repository: https://github.com/mkdocstrings/griffe

These are technical source descriptions, not evidence of task-duration savings or economic payback.

## Three-arm interpretation and no-op handling

The incumbent source inventory plus ordinary Git diff should be judged honestly for what it already exposes. The new capability adds specific callable evidence; it does not prove an incumbent maintainer with ordinary tools could not identify a change. For a claim about the automated deliverable, compare automation coverage and complete report resource use. For a human-work comparison, unknown review duration requires break-even thresholds.

If the full scoped source pair is unchanged, return the prior report or a no-op receipt. A changed project revision with unchanged scoped callable signatures may still justify one substantive release assessment, but its finding is no detected binding contraction; repeatedly re-running it is not new demand. Multiple witnesses, functions and negative controls are not multiple customer jobs.

The stronger conventional arm may match or exceed the new lens. Such a result supports adopting conventional analysis inside AGI ALPHA where useful, while denying a stronger algorithmic or economic Flywheel claim. No source of observed revenue, independently measured human saving or complete inference charge was established by this assessment.
