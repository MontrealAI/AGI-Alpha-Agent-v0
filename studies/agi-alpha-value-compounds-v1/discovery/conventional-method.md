# Conventional comparator and independent evaluator

Implemented before confirmation exposure. These files were authored by a research assistant in this session; they are not claimed as autonomous discovery. Their complete construction cost includes unknown model/inference charges. See `metering/workload_review.jsonl` for observed work records and `discovery/conventional-development-tests*.log` for development checks. Neither tests, signature pairs nor function witnesses are customer missions.

## Comparable retained conventional assets

`src/conventional.py` uses the installed, pinned Griffe/griffelib 2.4.1 static visitor to retain before/after API snapshots and every broader breaking-change alert. The source under inspection is parsed, never imported. Griffe's static metadata field `runtime: true` describes its member model; it is not evidence that the inspected code ran.

A reusable independently written witness enrichment layer constructs safe argument-binding stubs from AST parameter names, kinds and optionality. It discards original bodies, defaults' expressions, annotations, decorators and type parameters. The constructed body only returns `None`; optional defaults are constant `None`. The implementation compiles and invokes those generated stubs, not the source functions. This accurately exercises CPython's call binder without relying on `inspect.Signature.bind` behavior for positional-only names captured by `**kwargs`.

The conventional comparator retains parsed source facts and Griffe snapshots in a bounded in-memory cache. Keys include source SHA-256, module, comparator source SHA-256, Python runtime identity and Griffe version. The cache is limited to 64 entries and 16,000,000 captured source bytes, evicting least-recently-used entries. This byte cap measures retained source size; it is not an RSS limit. Returned snapshots and exclusions are copied so consumer mutation cannot poison a later hit. `clear_cache()` supports declared cold/warm experiments; `compare_sources(..., use_cache=False)` disables reuse for the ablation. Existing source caches and reusable conventional analysis are legitimate comparison assets, not handicaps removed from a baseline.

## Declared source model

The primary objects are top-level non-underscore direct function declarations and direct, undecorated synchronous `PublicClass.__init__` declarations. Constructor comparison is unbound and includes the declared `self` parameter. Consumer code may be mapped by adding an implicit receiver only as a conditional static relation: `__new__`, metaclasses, inheritance resolution and actual runtime export behavior remain outside the claim.

Decorated, duplicate, rebound, conditional or aliased definitions are unresolved. Constructors are additionally unresolved for decorated classes, multiple bases, class keyword/metaclass arguments, dynamic class bodies or non-unique/direct constructor definitions. A class remaining without a direct constructor is unresolved because inheritance may supply it; it is not treated as a proved removal. Module-level star imports, `__getattr__`, or explicit `exec/eval/globals/locals` calls outside function/class bodies trigger unresolved module scope. This conservative syntactic screen does not prove general runtime namespace stability.

Source bounds are 1,000,000 UTF-8 bytes and 100,000 AST nodes per source, and 64 declared parameters per callable. The comparator additionally bounds its total stub-call budget at 100,000,000. Existing tighter native intake bounds remain intact in the surrounding project; this comparator does not relax them. A bound refusal is reported explicitly.

## Complete binding frontier

Let the before/after signatures have maximum fixed positional length `P`. Test positional counts `0,...,P+1`. Let `U` contain every parameter name in either signature and one fresh keyword name outside both. For each positional count:

1. Construct the smallest keyword set `R` needed by the before signature: unfilled required positional-or-keyword names plus required keyword-only names.
2. Invoke the before stub with `R`. If it rejects, no larger keyword set can repair too-few positional-only or too-many positional arguments, so this positional count has no valid before shape.
3. Test `R`, then `R` with each additional name in `U` individually. Retain a shape only when the before stub accepts. A failed after call supplies a concrete counterexample.

Why this frontier suffices in the declared model: at a fixed positional count, Python binding acceptance is a conjunction of required-key inclusion, permitted-key membership and absence of positional/keyword duplicates. If the after stub accepts the minimum before set, all its required keys are already supplied. If it accepts each permitted one-key extension, no allowed extra key is individually forbidden or duplicates a positional binding. Combining such keys introduces no new cross-key constraint, because keyword names in the shape are unique. Larger positional counts beyond `P+1` have the same variadic/nonvariadic behavior; one fresh keyword represents every name outside the finite parameter-name union. The theorem concerns binding shapes only.

The conventional method therefore avoids an intentionally weak exponential search. It can match a constraint-based implementation while offering a strong established API-analysis library and reusable snapshots. Any match must be reported as a match, not a discovery-method advantage.

## Independent validation

`src/validate_dossier.py` does not import comparator or candidate extraction code. It separately inventories module declarations with an AST visitor and renders a new, safe function declaration from validated identifier spellings, kind markers and constant defaults. It checks report hashes, exact callable inventory, status, coverage counters, findings consistency and each reported witness using real calls to these independent stubs. Only generated code runs.

For the finite containment relation, the evaluator enumerates the complete positional-count/keyword-subset domain when it fits the remaining declared budget. Identical generated binding signatures are admitted directly because their accepted call languages are identical. In default `auto` mode, larger domains use a separately implemented complete safe-stub frontier, deriving required keys from the generated stub's signature metadata and exercising actual Python binding. Every method is recorded in the validation output. Explicit `validation_mode="exhaustive"` forces literal powerset enumeration; an exhausted budget reports unresolved, never a fabricated no-break verdict. A validated concrete counterexample still proves a loss without enumerating all other calls. The evaluator distinguishes report correctness from complete supported-scope coverage.

Development checks include 150 deterministically seeded pairs of generated signatures checked against independent exhaustive binding, explicit positional-only/variadic keyword cases, actual source/body non-execution, changed-source cache invalidation, returned-object mutation isolation, constructor scope exclusions and deliberately corrupted reports. These are validation controls, not historical workload recurrence or confirmed customer output.

## Broader conventional findings

Griffe's parameter-order, default-value and other API alerts are retained alongside the call-shape relation. Such changes can be important even when every before shape still binds afterward. They are not scored as false positives merely for lying outside the narrow relation. The witness lens does not certify behavior, argument meaning, types, return values, runtime exports, customer compatibility or production readiness.

## Entry points

```python
from conventional import compare_sources, clear_cache, cache_info
from validate_dossier import validate_dossier
report = compare_sources(before_text, after_text, "package.module")
validation = validate_dossier(before_text, after_text, "package.module", report)
```

`functions` contains `{name,status,witness,reason}` records. Status is `call_loss`, `no_call_loss`, `added` or `unresolved`. A witness has exactly `{positional_count,keyword_names}`. The source-bound report retains `findings`, `coverage`, broader Griffe alerts/snapshots, scope limitations and execution counters. Monetary values are not inferred from these counters.

## Preconfirmation consumer-adapter amendment

Development integration revealed that the shared consumer mapper required `source_ids` and per-row signature metadata. The conventional report already bound source hashes and produced valid witnesses, but its missing adapter fields caused all conventional consumer mappings to be refused. Before any confirmation body was opened, the report was amended to export `source_ids=[before_sha256,after_sha256]` and independently parsed `before_signature`/`after_signature` records with parameter name, kind, requiredness, inert default-expression text and async flag. No candidate comparison algorithm was imported or reused. The independent validator now checks these metadata fields against its own source parse so that forged metadata cannot silently alter consumer conclusions.

The original frozen implementation, evaluator, tests and method note are preserved under `discovery/frozen-conventional-v1/`. The amended `conventional-freeze-v2.json` records the new identities. Fifty development tests passed after this correction, including metadata interoperability and tamper rejection. This corrects comparator integration fairness; it is not a confirmation-driven performance change.
