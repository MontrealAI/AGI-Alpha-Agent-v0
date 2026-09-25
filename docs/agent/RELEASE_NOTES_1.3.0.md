[Project notice](../DISCLAIMER_SNIPPET.md)

# $AGIALPHA Agent 1.3.0

This release completes concrete legacy integration gaps while retaining the bounded operator runtime,
all original paths, the README text and every flywheel. CI badge URL queries explicitly track main.
The preceding state is recoverable from `checkpoint-2026-09-25-v1.2.1`, including its verified Git bundle.

## Changes

- Full Insight builds run actual quantized GPT-2 inference through pinned Transformers.js and ONNX Runtime.
  Every model file is pinned to a Hugging Face revision and checked against SHA-256 before packaging.
  Generation uses the local assets, disables remote model fetching and is bounded to 32 new tokens.
  After the first successful generation, cached inference works after an offline reload.
  Missing model assets produce a clear error; echoed prompts are no longer reported as inference.
- Browser API credentials live in memory. Earlier persisted credentials are read once and removed from
  local storage. API errors and empty responses fail explicitly, with a one-minute request timeout.
- WebGL plotting uses fixed shader programs without JavaScript code generation, preserving the strict
  content-security policy and avoiding accumulating animation loops on every plot update.
- Evolutionary selection now respects the configured population bound even when the entire candidate
  set is Pareto-optimal; retained elites cannot grow the population without limit.
- The AIGA service starts both as a module and as a direct file. Its optional dashboard can be disabled
  with `ENABLE_GRADIO=false`; the service acceptance test requires actual startup and graceful shutdown.
- Windows initialization, restoration and private writes now apply owner-only ACLs; permission
  failures stop before secret bytes are written. POSIX private modes remain unchanged.
- Smoke Test runs automatically on Linux, macOS and Windows, across Python 3.11, 3.12 and 3.13.
  It checks the operator runtime, legacy imports, an offline simulation and SQLite integrity.
  Artifacts include the OS and Python version. Main-commit smoke success is required before publication.
- Existing workflow badges remain and explicitly track main; release and acceptance badges are added.
  The release badge follows the latest stable version rather than a hard-coded passing label.

## Installation and recovery

Use `OPERATIONS.md`, `install_agent.py`, the hash-locked runtime and the release wheel.
Existing 1.2.x operator homes need no journal migration. Back up first; restore to a new directory
and verify the signed journal before resuming. Never overwrite an operator's existing data during restore.
For browser inference, the release includes a ready-to-serve full browser ZIP whose model hashes are
checked again during packaging. To build from source, build without `FETCH_ASSETS_SKIP_LLM=1`; see the full-browser instructions.

## Validation and limits

The publication workflow requires runtime checks, real-model and code-sandbox acceptance, real local
EVM payments, Solidity tests, full Python regression and coverage, all-file quality checks, both gallery
builds, real online/offline browser generation, clean installation, source preservation and exact-main CI.
The attached validation archive records results for the release commit; skipped optional tests remain
reported as skipped. Browser provider-response tests use fixtures, while offline ONNX generation is real.
GPT-2 is a small completion baseline, not an instruction-following assistant or general intelligence.
No mainnet transaction, automatic treasury spending, independent security audit or guaranteed return
is claimed. Original research ambitions and demonstrations remain present with their documented boundaries.
