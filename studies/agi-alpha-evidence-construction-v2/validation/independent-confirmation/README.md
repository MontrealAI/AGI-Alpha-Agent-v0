# Independent synthetic confirmation

The reviewer froze `plan.json` and its SHA256 before generating cases or executing the engine. Seed: `791430271`. The plan was frozen at `2026-10-27T17:27:12.997594+00:00`; generation and its hash were saved separately before execution. The tested artifact was extracted from the actual frozen capability ZIP and its source hash checked, rather than reconstructed from a prose description.

**32/32 specified checks passed; no engine correction was made.** The numerical oracle used the reviewer's independently developed exact Fraction vertex enumeration, which predates this confirmation. The instrument uses SciPy linear programming. Matching results therefore compare different implementations of the same conventional mathematics.

| Check family | Cases | Outcome |
|---|---:|---|
| Fresh four-cell means and counts; ordinary, permuted, translated and scaled numeric representations |12|All feasible count sets and interval endpoints agree with the exact oracle within the prospective tolerance.|
| Fresh contradictory source aggregates |4|All return `INCONSISTENT_HOLD`.|
| Pooled moments versus concatenated synthetic samples; SD, SE conversion, translation and permutation |4|All agree with independent sample statistics.|
| NaN, infinity, Boolean and unknown top-level field |4|All rejected.|
| Paired covariance absent, unknown dispersion, overlapping contrasts, unknown aggregate field |4|Missing covariance suppresses SE; the other three are rejected.|
| XML spans and hash, digest mismatch, entity declaration, unequal semantic units |4|Source checks behave as specified; semantic-unit case remains arithmetic only, requiring independent review.|

The last case is intentionally important: the arithmetic engine **does not establish that units or endpoint declarations are true**. It can calculate from a spec whose prose announces unequal units. It retains `semantic_acceptance=false`, `source_truth_established=false`, and `production_authority=false`. The reviewer must refuse such a mission. This boundary check is not accepted scientific delivery and must not be presented as automated semantic detection.

Every case is synthetic. These tests establish bounded execution and guards, not customer acceptance, market demand, model superiority, live identity or production authorization. The measured 15.23-second execution includes the independent exact oracle; it is not a service turnaround or complete delivery-cost estimate.

## Evidence

- Capsule SHA256: `32a9c193200f43c94b922c9b7f5460a60a57f44031f1b2c88c8a50b15766a930`.
- Frozen and received engine SHA256: `c8e40133ab0269e67afb1eb40aecd3952864b13370de0e548b638dc6726c60cb`.
- Plan SHA256: `dc24e3df18fd0192b2d5fd937195aa4fb11fccef583269ca8787f6b2bc6454b3`.
- Case file SHA256: `8e122fbde7e724fb254b4fe87f6379524c4c0804e3ade591a8d26f764caabb2c`.
- Independent oracle SHA256: `152704c8f26cf6e38e60950e1f4b77c75c73a8f7a2828ee2c8272aaef8f0d835`.

`results.json` preserves all engine responses, expected exact bounds, errors and boundary classifications. `generation-freeze.json` precedes engine execution. The original constructor code remains byte-identical. `received/` contains the exact extracted capability files.

## Reproduction

Run `python validation/independent-confirmation/run_confirmation.py` from the study directory in a **copy** of the study tree, preserving the original receipt files. The command regenerates deterministic case contents but records new generation/execution timestamps and hashes, so a rerun should not overwrite the original evidence. Numerical cases and outcomes should match; timestamps and duration will differ. Dependencies are the same NumPy/SciPy requirements as the instrument. Python's standard library supplies the exact arithmetic oracle.

The independent source diagnosis and original S4 bytes are preserved in sibling `development-review/`, with a byte-for-byte copy receipt. Its `check_development.py` can reproduce the development diagnosis without accessing any fresh source paper. Ruff formatting and lint passed for both review scripts.
