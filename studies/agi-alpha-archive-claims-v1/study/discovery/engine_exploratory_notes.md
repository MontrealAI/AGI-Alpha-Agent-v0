# Post-search construction — exact claim engine

This is separate from the frozen six-query independent E arm. The original discovery report, finite prototype, and result JSON were not changed. No additional web search was performed. No held-out confirmation cases or result files were generated or inspected, and no confirmation seed was used.

## Source-access correction received after the arm froze

The root agent reports that the authorized Zenodo API metadata for record 12784802 has `access_right: restricted` and no downloadable files, despite a license field and the paper's data citation. The real ten-page benchmark was **not run**. This supersedes the raw discovery report's characterization of the payload as open. No alternative endpoints were attempted. The construction remains confined to research-authored finite models.

## Deliverable and freeze

- File: `/workspace/scratch/8285c42b25e1/src/claim_engine.py`
- Python 3.12 standard library only; tested on Python 3.12.14.
- Length: 225 lines.
- Frozen SHA-256: `0cea250d7ad8299edcfea7c37432e7b7dbc7f2c8f597b50b926d5ecfe0326c69`.
- Public function: `solve(payload, source_input_sha256=None)`.
- CLI: `python src/claim_engine.py --input INPUT.json --output OUTPUT.json`.
- Successful CLI evaluation exits 0; refusal exits 2 and emits a refusal JSON when the destination is safe and writable. A destination identifying the input itself is refused on stderr and never overwritten.

The CLI's `source_input_sha256` hashes exact input bytes. Direct `solve` without an externally supplied digest hashes UTF-8 canonical JSON with sorted keys, compact separators, and unescaped Unicode. A supplied digest must be lowercase SHA-256 hex. The digest records input identity; it does not authenticate source evidence.

## Contract

The engine accepts exactly the root-specified `agialpha.archive-claim.v1` schema. The sole supported source model is `research-authored`. Rows require nonempty source IDs; a common explicit unit is required. Calibration is additive and shared by the declared group. No unit conversion or unsupported coupling is silently introduced.

Numeric values are strings containing a signed integer, ordinary finite base-10 decimal, or numerator/positive-denominator fraction. JSON floats, exponent syntax, surrounding whitespace, and nonfinite values are refused. Each numeric string is at most 40 characters. There are 1–64 rows, 1–64 calibration groups, 1–8 distinct numeric alternatives per row/group, and an integer error budget between zero and the row count. Use a singleton calibration alternative `"0"` for a fixed zero offset. Duplicate numeric alternatives are refused even if their spellings differ, so state counts remain unambiguous. Unknown keys are refused to avoid accidentally ignoring extra constraints.

Output provides exact rational strings for lower and upper bounds, the threshold decision, sparse signed error maps, all glyph and calibration choices, resulting row values and query values, and the latent-assignment count. Declared unused calibration groups count as latent choices. Different latent choices can yield the same numerical observations; `world_count` is not the count of distinct observation vectors.

## Standard mathematical argument

Write the query as the sum of independent glyph terms, calibration-group terms whose coefficients are the sum of member weights, and row-error terms. The first two parts achieve their extrema by choosing each finite alternative independently. For errors with magnitudes b_i, row i contributes at most |w_i| b_i to the support. At most k rows can have nonzero errors, so the exact radius is the sum of the largest k such contributions. Selecting their signs produces actual extremal histories. Zero-weight rows need no witness error even when their positive error bounds contribute to the count of possible latent error assignments.

This is conventional separable support arithmetic plus a top-k sparse-error radius. It is not a new algorithm, a claim of physical source completeness, or evidence that prior certain-answer methods cannot provide the same contract.

## Hand-authored exploratory checks actually run

One three-row example used weights 1/2, -2, and 3/2; two shared-calibration groups; two glyph alternatives per row; error bounds 1/5, 3/10, and 2/5; and an error budget of 2. Exact exhaustive enumeration covered 608 latent assignments. It agreed with the engine's interval `[-137/10, 139/20]`. Both emitted witness queries equaled the corresponding endpoint and obeyed the error budget.

Additional exploratory variations checked strict-threshold TRUE/FALSE/UNRESOLVED behavior including endpoint equality, budget zero, all-zero weights, and one zero error bound. Ten hand-authored invalid inputs were refused: unsupported coupling; missing unit; missing source ID; unsupported source model; a JSON floating-point weight; an unknown calibration group; duplicate numerical alternatives; a negative error bound; a Boolean error budget; and division by zero.

CLI checks confirmed exact byte hashing, duplicate-JSON-key refusal, and refusal to overwrite the input through an identical output path. Temporary exploratory input/output files were removed with their temporary directory. No actual archived measurement was analyzed.

## Independence and audit boundary

The construction protocol was read to align the implementation contract. Its listed held-out seeds were not used. The test above was manually authored and is not part of confirmation. An independent reviewer should generate/check fresh cases only after the code hash above is recorded. Any later code correction should receive a new hash and retain the initial failure record rather than silently replacing the frozen version.

The three raw-arm file hashes were rechecked and remained unchanged:

- `expert_discovery.md`: `8b21c116ce20ad424d7e0475aa33cda4d308e5dbd0d2ff75c3b163ded218cc49`
- `expert_discovery_verify.py`: `7d360d267fdbd5babe98ee4c2cc8f12a8a648ef57d9b5d784d93d0432d0d6f1f`
- `expert_discovery_exact_result.json`: `8024c53310f5098c454b7d935bbd6f9a0ed23be2251e85abde96234830ad2e4f`

## Final packaging correction before confirmation

At the root agent's request, the implementation was copied to the required final location, `/workspace/scratch/8285c42b25e1/study/src/claim_engine.py`, and the comment `# SPDX-License-Identifier: Apache-2.0` was inserted immediately after the Python shebang. The original `src/claim_engine.py` remains unchanged. No executable expression, validation policy, or algorithm was changed; parsed Python ASTs match exactly.

The initial exploratory source hash above remains part of the record. The final implementation has 226 lines and SHA-256:

`ae357866f167cf61eacb86681f48dcf99f783641699ff3a46cf6fa3912da2336`

Requested checks were attempted on that final file:

- Ruff ran and reported one existing style issue, E731, for the local `encode` lambda assignment. It reported no other issue under the invoked configuration. The expression was retained to keep the packaging change limited to path and license metadata.
- Black could not start because its installed environment lacks `pathspec.patterns.gitignore`. No dependency changes were made.
- Strict mypy ran and reported 40 diagnostics concerning missing function annotations and calls to untyped functions. The implementation is deliberately disclosed as untyped; it does not pass strict mypy.

These results are not clean lint/format/type-check passes. The exact-arithmetic exploratory verification remains as recorded above. No confirmation cases were generated or inspected during this packaging step.

## Final annotation cleanup before confirmation

The root agent subsequently requested a narrow annotation and Ruff cleanup before generating primary cases. The final `study/src/claim_engine.py` now annotates all public, private, and nested functions, uses a `TypedDict` for parsed internal rows, and replaces the local encoding lambda assignment with a named function. JSON boundaries permit `Any`. No algorithm, numeric syntax, validation condition, output field, or input contract changed. The original root `src/claim_engine.py` remains at its initial exploratory hash.

This final pre-confirmation implementation has 239 lines and SHA-256:

`dce5ac65b3c1cdaf625a2f9a0ee554df88d5d2853454ebad5d2cfc00265794db`

Ruff now reports **all checks passed**. Strict mypy now reports **success, no issues found in one source file**. The earlier findings and intermediate hashes above remain in the audit record. Black's previously recorded external dependency failure remains unresolved; no dependency installation was attempted.

The same hand-authored exploratory suite was rerun without generating additional test cases: all 608 histories matched the exact bounds; threshold and zero-budget/weight/bound variations passed; all ten invalid models were refused with messages identical to the original implementation; and CLI byte hashing, duplicate-key refusal, and no-overwrite behavior passed. All valid exploratory outputs also matched the original implementation exactly. No held-out confirmation case or result was inspected or generated, and no confirmation seed was used.
