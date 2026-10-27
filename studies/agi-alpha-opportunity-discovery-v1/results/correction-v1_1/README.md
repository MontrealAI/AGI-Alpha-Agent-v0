# Prospective strict snapshot revision, v1.1 candidate

This is a new candidate, not a change to the frozen v1 experiment or its transferred archive. The original 64 events, recipient assay and capability archive remain unchanged. The freeze manifest checks 54 preserved source/v1/recipient files.

## What changed

`instrument/continuity_v1_1.py` is a standalone revision of the existing bounded REML snapshot adapter. It has explicit field allowlists for every supported event kind. Unsupported fields now produce a hold with no numerical result. In particular, a scoped correction cannot silently carry an unknown `source_id`, covariance, clustering or sequential-history field. These inputs need upstream qualification and an explicitly supported representation.

The legacy optional `source_id` on a no-change/background event is restricted to sources already declared background-only. This preserves the original valid fixtures without treating arbitrary new identities as qualified.

The batch wrapper and CLI explicitly state that every event is applied independently to the same original packet. Declared sequential, cumulative or other unsupported batch modes are held without executing their events. No source monitor, cumulative ledger, event order, idempotency store or live authority system has been added.

## Prospective sequence and results

- Code, conformance requirements and generator frozen: **2026-10-27 16:23:08.556843 UTC**.
- New instances generated, expected states saved and hashes recorded without executing the candidate: **16:23:13.061059 UTC**.
- Candidate execution completed: **16:23:16.830237 UTC**.
- Seed: **91824067**, distinct from the original confirmation seeds 77319 and 77320.
- Candidate SHA-256: `27c40889c0b11bd3d837034f21cf9a93f11d4b002628e253ff2e8f2d84a66921`.

All **46 fresh generated conformance instances** met their prespecified dispositions: 35 holds, 1 rejection, 8 numerical recomputations, 1 unchanged result and 1 explicitly independent two-event batch. The eight fresh numerical updates and unchanged result matched an independently applied update and REML score-equation reference within `2e-6`. The independent batch deliberately reports 18 rows and then 19 rows, with the same original packet digest and `cumulative_history=false`; it does not claim sequential state maintenance.

All **64 separate v1 regression cases** retained their earlier expected disposition and numerical result. These are replayed regression evidence, not fresh cases. All 54 preserved file hashes remained unchanged. The CLI's actual sequential-mode refusal is saved separately in `cli-sequential-refusal.json`; `cli-help.txt` records its stated scope.

Every output denies production admission and commercial acceptance. Holds and rejects are controls, not accepted paid analyses. The candidate has not been transferred to a fresh recipient, admitted to production, deployed or used to earn revenue. These bounded cases do not establish population reliability, autonomous semantic interpretation, scientific validity, market feasibility or recovered historical profit.

## Reproduce without overwriting this evidence

From the repository root, choose a new output directory:

```bash
python studies/agi-alpha-opportunity-discovery-v1/protocol/check_correction_v1_1.py generate --out /tmp/snapshot-correction-reproduction
python studies/agi-alpha-opportunity-discovery-v1/protocol/check_correction_v1_1.py execute --out /tmp/snapshot-correction-reproduction
```

Generation refuses an existing destination and verifies frozen bytes before writing cases. Execution verifies the freeze and generated case hashes before and after processing. Preserved v1/recipient files are inputs only.

## Remaining limits

The caller still supplies a qualified packet and an already adjudicated event kind and scope. The strict schema prevents undeclared fields from being ignored, but cannot prove that an allowed value is truthful, that no notice was missed, or that the original studies are independent. Local purpose and authority flags remain research fixtures; current native protected-network controls must be evaluated separately. Conservative holds can increase customer effort and cost; neither benefit nor profitability is guaranteed.

Ruff formatting and lint passed for the candidate and checker. Black could not import because the installed `pathspec` dependency lacks `pathspec.patterns.gitignore`. Strict mypy on the candidate was blocked by missing `scipy.optimize` type stubs. The repository-wide environment scripts named in `AGENTS.md` are absent from this local source snapshot; direct imports of NumPy and SciPy were available. No complete repository test campaign or hosted release gate is claimed.
