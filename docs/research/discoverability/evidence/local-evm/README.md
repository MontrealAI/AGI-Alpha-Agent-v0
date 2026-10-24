# Existing Alpha adapter: recovered local-EVM evidence

Run identity: `discoverability-20261022-v1`.

**Supplementary fresh qualification:** `qualification-02/` now preserves a new
execution of the same unchanged selection: **36 passing (12s), exit 0**, with
complete stdout/stderr, timestamps, source identities and new native receipts.
A separate disposable fixture records all five deployed runtime identities and
configuration. Its README distinguishes reused dependencies from clean bootstrap
and keeps the following original-recovery qualifications intact.

This docket preserves the existing Alpha SUCCESSOR adapter's disposable,
unforked Hardhat evidence. It does **not** establish Discoverability-specific
commissioning, a four-repository installed journey, Fleet execution, mainnet
readiness, customer revenue or an external validator's approval.

## What survived, and what did not

The original executing agent reported 43 Solidity files compiled and 36 unchanged
tests passing in 12 seconds, exit code 0: 15 lifecycle/identity, 15 marketplace,
3 settlement-conservation and 3 native-adapter tests. Its exact handoff is
preserved in `executor-handoff.json`. The original compile/test terminal stdout
and shell exit receipt were **not retained after interruption**. The pass count
is therefore an executor-reported result, not a recovered raw test transcript.

The following primary artifacts survived and are included:

- Two exact native-adapter receipt JSON files, with their signed terms,
  assignment, delivery and imported settlement data.
- Two exact npm debug logs: an EPERM setup failure (exit 1), then a successful
  unchanged `npm ci` (exit 0). The initial child-process failure and Python
  installation terminal output were not retained.
- Five ABI arrays extracted from retained compiler artifacts, plus a manifest
  distinguishing compiler template identity from observed local runtime identity.
- A source archive containing 55 original-project source/lock/license files,
  including all 11 project Solidity inputs. No `node_modules`, virtual
  environment, private keys or held PR #4863 changes are included.

`data-review.json` records 106 post-hoc consistency checks over the retained
bytes: canonical digests, Ed25519 signatures, artifact hashes, settlement
conservation, source Git blobs, compiler inputs and ABI/bytecode correspondence.
These checks did not rerun the EVM. Signatures verified against included keys
do not establish an independent validator or institutional authority.

The full retained compiler build-info has 43 inputs, Solidity
`0.8.37+commit.f401782d.Emscripten.clang`, and zero compiler diagnostics.
`compiler-build-summary.json` records its size, SHA-256, exact settings and every
input hash. The full file remains in the original local workspace and is not
redistributed here because it embeds dependency source; unchanged dependency
lockfiles reproduce those inputs. Its local path is recorded in the summary.

## Receipt results

| Receipt | Retained result | What the result means |
|---|---|---|
| `accepted-negative-evaluation.json` | Two approving reviews; a verification report is paid while its evaluated candidate has verdict `FAIL` | Acceptance of an accurate report does not admit the failed candidate. The receipt explicitly grants no institutional memory or authority. |
| `missing-review-quorum.json` | No reviews; no payouts; full bounty refund | The retained settlement is unresolved for missing quorum and refunds the simulated bounty. |

For the first receipt, simulated bounty 100 is conserved as net recipient
payouts 79.2 + burn 0.8 + employer refund 20. The second refunds all 100.
These quantities use 18-decimal **local mock** token units, not dollars or
mainnet balances. The mock token is installed at the configured canonical token
identifier inside chain 31337. Its address does not turn this into a mainnet run.

The original test source also contains assertions for duplicate settlement
import, changed-artifact rejection, worker recovery and integer rounding.
Those assertions are part of the original 36-test execution report; the two
saved receipts alone do not prove every assertion passed.

Local runtime addresses and hashes were retained for NovaSeed, AscensionJobMarket
and AscensionMark. Access and RiskOracle runtime addresses/hashes were not saved
and are `null` in `manifest.json`; deployment order and mainnet records must not
be substituted. The manifest separately records compiled pre-constructor runtime
templates, whose immutable fields are not deployed values. Receipt block times
include simulated time advances and are not wall-clock execution timestamps.

## Source identity

The executor reported Alpha revision
`61532fb82621a065e668fd11e57289dcfb65c67b`. All five suite contract Git blob
identities independently match the prior source audit. This recovered selected
closure is not a separately authenticated complete Git checkout. See
`source-inventory.json` for every archived byte count, SHA-256 and Git blob.

## Reproduction: new disposable execution

The commands below describe a fresh execution, **not a replay of the saved
receipts**. Recovery did not rerun them. Use a clean isolated directory and the
unchanged source archive. Node 24.19.0 and npm 11.9.0 are recorded in the retained
npm logs. The original Python interpreter version and installed-environment
receipt were not recovered; use a supported Python 3.11+ interpreter and retain
its version with the new run. Installation needs network access to the locked
package registries and may require execution permission in a restricted
environment. No mainnet URL, wallet, signing secret or funded account is needed.

```bash
mkdir alpha-local-evm-reproduction
cd alpha-local-evm-reproduction
unzip /absolute/path/to/source-closure.zip
python3 -m venv .venv
.venv/bin/python -m pip install --require-hashes -r requirements-agent.lock
export ALPHA_PYTHON="$PWD/.venv/bin/python"
export SUCCESSOR_EVM_EVIDENCE_DIR="$PWD/evidence/new-local-run"
mkdir -p "$SUCCESSOR_EVM_EVIDENCE_DIR"
cd tests/contracts
npm ci --no-audit --no-fund --fetch-retries 0 --fetch-timeout 15000
set -o pipefail
npm test -- test/ascension/lifecycle.test.js test/ascension/marketplace.test.js test/ascension/settlement.test.js test/ascension/successor-adapter.test.js 2>&1 | tee "$SUCCESSOR_EVM_EVIDENCE_DIR/test-terminal.log"
```

The retained npm command additionally set
`--cache /tmp/discoverability-evm/npm-cache`; this is a cache location, not an
unlocked dependency change. `ALPHA_PYTHON` selects the actual Python adapter
bridge. `SUCCESSOR_EVM_EVIDENCE_DIR` activates the unchanged test's receipt
writer. The unchanged Hardhat configuration and disposable-network guard reject
external or forked networks. Tests use deterministic local accounts with
simulated balances. Preserve fresh terminal output, exact exit status, dependency
versions and observation timestamps alongside any new receipts.

The archive is a source convenience for this focused test path; the complete
repository's unrelated scripts and test suites are intentionally absent. The
full installed Python environment and a clean archive bootstrap were not
reverified during evidence recovery.

## Integrity

`FILES.json` inventories all files in this docket except itself. It is an
integrity index, not a claim of externally anchored provenance. The source ZIP
contains the same source inventory separately as `SOURCE_INVENTORY.json`.
Existing files and failed setup evidence remain visible. No installation,
compiler run, test run, financial transfer or GitHub operation was performed
during this evidence recovery.
