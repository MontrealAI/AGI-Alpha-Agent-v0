[Project notice](../DISCLAIMER_SNIPPET.md)

# Release acceptance and reproducibility

Version 1.3.0 separates direct evidence from mocks, simulations and unavailable integrations.
The release workflow (`agent-release.yml`) must complete its gates before publishing assets.
Its run URL and tested commit are recorded in the published release manifest; JUnit reports, browser
screenshots and integration evidence are retained as workflow artifacts and release evidence.

The 1.2.0 release remains available unchanged. Patch 1.2.1 adds a required complete gallery rebuild:
legacy documentation repair must retain the exact sandbox-host script hashes, every generated demo
must load, and the rebuilt site must advance its simulation online and offline under normal browser
security. Both minimal and full-asset gallery builds must pass. The generated site receives the
complete browser distribution so documentation source exclusions cannot break its precache.
Workflow-only repairs also retain distinct evidence from both Python matrix jobs.

Before main-branch packaging, a separate gate requires the historical integration and PR CI workflows
to succeed on that exact main commit. A failure, cancellation, timeout or skipped workflow blocks
publication. Their final run snapshots are included in the validation archive.

Full-repository and changed-file pre-commit hooks are required gates, including the locked browser
ESLint environment. Their complete report, exit status and any proposed formatting are retained.
The PostgreSQL ledger is exercised against a real temporary Docker database after TCP readiness;
TypeScript meme mining uses the locked compiler. Both integration checks must run without skips.

## Runtime and integration evidence

- The runtime/control suite runs on every supported Python version, covering mission execution, signatures, corruption, review
  races, pause, idempotency, provider failure, coding opt-in, wallet control, confirmation/finality,
  invalid transfer receipts, exact integer accounting and replay rejection. RPC attack cases use fixtures.
- [Real local inference](release-evidence/local-inference.json): pinned Qwen3 4B GGUF via llama.cpp,
  six exact quotes verified, operator review/export and backup/restore. This is actual inference,
  not the repository's legacy SDK stub. It is a public sample task, not a general intelligence benchmark.
- [Real local EVM](release-evidence/local-evm.json): deployed ERC20 mock at the canonical address on an
  ephemeral Hardhat chain 31337; actual signed wallet proof, transaction, confirmation delay, receipt,
  integer balance, duplicate rejection after restart and verified backup/restore. No public-chain funds.
- Solidity suite: 36 tests passed against shipped sources, including two new real identity rejection tests.
  The initial 34-test baseline used an always-true identity stub; it was not evidence of identity enforcement. The initial local Insight browser suite reported 6 passed, 1 skipped;
  hosted execution reported 5 passed, 1 skipped before the additional source-host test;
  TypeScript compilation passed; ESLint had zero errors and 9 existing warnings.
- Initial broad Python regression: 893 passed, 12 failed, 100 skipped, 5 expected failures.
  Configuration precedence, loopback guard, compiler discovery and missing preview-asset causes were fixed;
  focused recheck passed 44 with only two notebook-kernel environment failures remaining.

## Required hosted gates

The initial workspace kernel prevented Chromium and ZMQ notebook sockets. Those local failures were **not passes**.
Hosted CI runs the full offline Python regression, real Chromium console interactions, the legacy web
client tests, sandboxed Insight simulation online/offline from both npm and manual builds, the legacy container
services, and real Docker isolation plus persistent
operator-container restart. Each must succeed before publication. Optional test skips and
expected failures remain visible in JUnit; they do not establish unavailable hardware, cloud credentials,
optional integrations, live trading or deployed mainnet behavior.

The Insight cache-update check rebuilds after separate host-only and worker-only changes, requires
new page precache revisions and matching CSP/worker integrity, then restores and reproduces the
original build. The page revision covers its policy-complete template, the bundled worker template
and all precached assets before filling the worker hash; hashing the final page and a worker that
embeds that page's hash would create a circular dependency.

Both browser projects have dependency audit gates, with JSON reports retained in release evidence.
The Insight audit includes its entire npm graph, including build tools and bundled browser libraries;
its prior production-only audit omitted those development-labelled dependencies. The repaired dashboard
audit covers production dependencies. Other legacy development environments can still have advisories;
this is not a claim that every historical dependency is clear. The [local full-graph audit](release-evidence/browser-dependencies.json)
records the exact lockfile hash, Node/npm versions and zero advisories; release CI independently reruns it.

The Python coverage gate retains the repository's existing scope: demos, legacy backend agents/memory
and temporary test copies are excluded in both collection and reporting. The earlier expanded report
measured 74.97%; applying the already configured scope measured 81.72%. The release retains its XML
and raw coverage data so this distinction remains inspectable.

The runtime matrix covers Python 3.11, 3.12 and 3.13 using the hash-locked minimal environment.
The larger historical suite runs in its original locked Python 3.12 development environment, without
service credentials, external Python sockets or model downloads. Run locally with:

```sh
python scripts/check_python_deps.py
python -m scripts.run_local_tests --junitxml=regression.xml
python -m scripts.check_agent_preservation
python -m scripts.validate_agent_ui --output ui-evidence
python -m scripts.validate_agent_sandbox --output sandbox-evidence.json
python -m scripts.validate_agent_chain --output chain-evidence.json
```

Prefetch Insight browser assets with `FETCH_ASSETS_SKIP_LLM=1 npm run build` in its browser directory
before the offline regression; its network guard intentionally blocks downloads during tests.

The last three require installed Playwright Chromium, Docker, and compiled Hardhat dependencies,
respectively. They fail if their required capability is missing; they do not silently skip.
The model validator additionally requires the independently downloaded server binary and pinned GGUF;
its exact SHA and invocation are in the evidence JSON. The Qwen GGUF is downloaded independently;
the full browser release ZIP includes the separately pinned quantized GPT-2 ONNX weights.

`check_agent_preservation.py` checks all 2,125 original paths, the entire original README text and flywheels (only CI badge URL queries may change),
and equality of shipped Solidity sources with the copies compiled by the contract tests.
Packaging verifies wheel metadata, installs outside the repository in a clean virtual environment,
checks dependency consistency, and exercises the installed CLI and packaged web assets.

This evidence supports the bounded capabilities in [CAPABILITIES.md](CAPABILITIES.md).
It is not a security audit, regulatory approval, investment-performance result or proof of AGI/ASI.

## Additional 1.3.0 acceptance

The full-gallery job now requires real local ONNX text generation before and after a network-disabled
reload, with matching deterministic continuations, the actual WASM backend and no page errors. The
minimal-gallery job continues to require working offline simulation. Browser API-response fixtures
are reported separately from actual ONNX inference. Model provenance is in `scripts/browser_model_manifest.json`.

The standalone Smoke Test matrix covers all nine OS/Python combinations; exact-main smoke success is
included in the historical-CI publication gate. AIGA's direct-file startup test can no longer turn a
service failure into a skip. README preservation permits only query changes to the four historical CI
badge URLs and still rejects any removed flywheel or other historical text.
