[Project notice](../DISCLAIMER_SNIPPET.md)

# Release acceptance and reproducibility

Version 1.2.1 separates direct evidence from mocks, simulations and unavailable integrations.
The release workflow (`agent-release.yml`) must complete its gates before publishing assets.
Its run URL and tested commit are recorded in the published release manifest; JUnit reports, browser
screenshots and integration evidence are retained as workflow artifacts and release evidence.

The 1.2.0 release remains available unchanged. Patch 1.2.1 adds a required complete gallery rebuild:
legacy documentation repair must retain the exact sandbox-host script hashes, every generated demo
must load, and the rebuilt site must advance its simulation online and offline under normal browser
security. Workflow-only repairs also retain distinct evidence from both Python matrix jobs.

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

The workspace kernel prevents Chromium and ZMQ notebook sockets. Their local failures are **not passes**.
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

Both browser projects have production-dependency audit gates, with JSON reports retained in release
evidence. The repaired dashboard audit reports zero production advisories. Some optional legacy
development tools still have advisories; this is not a claim that every historical dependency is clear.

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
its exact SHA and invocation are in the evidence JSON. No model weights are included in the release.

`check_agent_preservation.py` checks all 2,125 original paths, the entire original README byte sequence,
and equality of shipped Solidity sources with the copies compiled by the contract tests.
Packaging verifies wheel metadata, installs outside the repository in a clean virtual environment,
checks dependency consistency, and exercises the installed CLI and packaged web assets.

This evidence supports the bounded capabilities in [CAPABILITIES.md](CAPABILITIES.md).
It is not a security audit, regulatory approval, investment-performance result or proof of AGI/ASI.
