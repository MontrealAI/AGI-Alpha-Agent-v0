[Project notice](../DISCLAIMER_SNIPPET.md)

# Operate the $AGIALPHA Agent

## Install from a release

Use Python 3.11, 3.12 or 3.13. Download the wheel, `requirements-agent.lock`, `SHA256SUMS` and
`install_agent.py` from the same official GitHub release into an empty directory. Check the release's
commit and provenance before trusting its files. Then:

```sh
python3 install_agent.py --release-dir . --venv .venv-agent
.venv-agent/bin/alpha-agent --home ./agent-state init
.venv-agent/bin/alpha-agent --home ./agent-state doctor
.venv-agent/bin/alpha-agent --home ./agent-state serve
```

On Windows use `.venv-agent\Scripts\alpha-agent.exe`. Open `http://127.0.0.1:8765` and paste the token
from `agent-state/api.token`. It is held only in page memory. Keep the state directory private.
Choose a sample mission, replace its inputs with your data, execute, inspect the evidence and approve or
reject. Approval archives a result; it does not trade, send funds or operate equipment.

The installer refuses an existing virtual environment, verifies wheel/lock checksums, installs all
runtime dependencies from the hash-locked file, and runs `pip check`. A failed install may leave a partial
new environment; remove that failed environment or select another path before retrying. The complete
source ZIP preserves the original examples, documents and demos. A wheel is a Python installation,
not the full historical source archive.

For an offline installation, download dependency wheels on a matching Python/platform with
`python -m pip download --require-hashes -r requirements-agent.lock -d wheels`, then pass
`--wheelhouse wheels` to the installer. Do not mix the minimal operator environment with the much larger
legacy demo/development dependency set.

## Mission lifecycle and command line

The source archive contains `examples/missions/{research,allocation,schedule,forecast,code}.json`.

```sh
alpha-agent --home ./agent-state run examples/missions/allocation.json
alpha-agent --home ./agent-state list
alpha-agent --home ./agent-state show MISSION_UUID
alpha-agent --home ./agent-state review MISSION_UUID --revision REVISION \
  --result-hash RESULT_HASH --approve --note 'Checked budget, risk and objective against inputs.'
alpha-agent --home ./agent-state export MISSION_UUID --output approved-result.json
```

Take `REVISION` and `RESULT_HASH` from the current returned record, not an older review. Only approved
completed results export. A recipient can use `alpha-agent verify-export approved-result.json --public-key KEY`
with the agent public key obtained through an independently trusted channel. A rejected or failed record remains in the journal. Supply `--request-id UUID`
to `run` for idempotent retry; reusing that UUID with different input fails.

A mission moves through `queued → running → review → completed/rejected`. Seven recorded roles are
planning, research, strategy, market, codegen, safety and memory. Arithmetic gains use the units supplied
by the operator; the market stage leaves realized revenue empty until a separate payment is verified.

## Configure inference and code

Without a provider, research extracts relevant exact passages; it does not pretend an LLM ran.
Allocation, scheduling and forecasting use their built-in algorithms and need no provider.
Configure a local OpenAI-compatible server using a JSON file:

```json
{
  "name": "alpha-agent",
  "llm_url": "http://127.0.0.1:8080/v1",
  "llm_model": "your-installed-model-id",
  "max_output_tokens": 1200,
  "llm_timeout": 120,
  "allow_code_execution": false
}
```

```sh
alpha-agent --home ./agent-state pause
alpha-agent --home ./agent-state configure operator-config.json
alpha-agent --home ./agent-state resume
```

Restart the console after configuration changes; an old process rejects a changed configuration.
For a remote endpoint use HTTPS, set `allow_remote_llm: true`, and put its credential in the environment
variable named by `llm_key_env` (default `ALPHA_AGENT_LLM_KEY`). This explicitly permits sending mission
sources, or code goals/examples, to that provider. The model name must exist at that endpoint. Provider
errors and malformed or ungrounded results fail visibly; they do not become simulated success.

Code missions additionally require `allow_code_execution: true` and Docker. Pull the sandbox image
before execution, record its digest, and set `ALPHA_SANDBOX_IMAGE` to that digest for reproducibility:

```sh
docker pull python:3.12-slim
docker image inspect python:3.12-slim --format '{{index .RepoDigests 0}}'
export ALPHA_SANDBOX_IMAGE='python@sha256:THE_DIGEST_YOU_VERIFIED'
```

Only the candidate, test inputs and trusted runner enter the container; expected answers remain with
the evaluator. Network is disabled, root is read-only, execution is non-root, capabilities are dropped,
and CPU/memory/process/time/output limits apply. Docker is the release-tested backend. The retained
Firejail compatibility path is not covered by the Docker acceptance evidence. Use a dedicated,
maintained host for untrusted code; container isolation is not a claim of perfect containment.

A provided `candidate` bypasses generation. Otherwise generation requires the configured model.
`examples` are model-visible; `heldout` answers are not. All held-out cases must pass, and results are
rechecked at review. Passing finite cases does not prove arbitrary program correctness.

## Wallet and $AGIALPHA receipts

The runtime never requests or stores a wallet private key. Run `wallet-challenge`, sign its complete
message with your external wallet using EIP-191 personal-message signing, and pass the resulting signature
to `wallet-bind SIGNATURE`. Challenges expire after ten minutes and are single-use. Binding proves
control of that address, not an ENS name. Rebinding to a different address requires a new installation.

Add a `chain` object to operator configuration while paused:

```json
{
  "chain": {
    "rpc_url": "https://YOUR_TRUSTED_RPC",
    "chain_id": 1,
    "token_code_sha256": "64_LOWERCASE_HEX_CHARACTERS_FROM_INDEPENDENTLY_VERIFIED_DEPLOYED_BYTECODE",
    "confirmations": 12,
    "reinvest_bps": 2500
  }
}
```

This is a template: the bytecode placeholder is deliberately invalid. Independently obtain the deployed
runtime bytecode at the canonical token address, verify its provenance, then SHA-256 hash its decoded
bytes. The runtime checks chain ID, bytecode pin and 18 decimals at a confirmed block. Mainnet additionally
requires the RPC's finalized block. A trusted RPC is still part of the trust model. Test chains use a
separate chain ID and are labeled `test_chain`; only loopback test RPC can use cleartext HTTP.

The fixed token is `0xa61a3b3a130a9c20768eebf97e21515a6046a1fa`, with 18 decimals.
Amounts are **integer strings of base units**, never floating-point token amounts.

```sh
alpha-agent --home ./agent-state balance
alpha-agent --home ./agent-state invoice MISSION_UUID --payer 0xPAYER --amount-units 1000000000000000000
# The payer transfers with their own wallet, after the invoice exists.
alpha-agent --home ./agent-state settle MISSION_UUID --transaction 0xTRANSACTION_HASH --log-index 0
```

Only approved work can be invoiced. Settlement checks the exact sender, recipient, token, amount, success,
canonical block and confirmation/finality policy. Old payments and reused transfer logs are rejected.
Each invoice binds its chain settings, including the RPC, bytecode pin, confirmations and reinvestment
fraction. Keep those settings until payment settles; if changed, restore the invoice's original chain
configuration before retrying. Unrelated model or search settings do not invalidate an invoice.
Configuration changes during RPC verification reject the write and require a fresh process and retry.
The operator associates the transfer with the invoice: ERC20 itself has no mission memo. A reinvestment
fraction records an earmark only. No automatic transaction, staking deposit, burn or buyback occurs.
These mechanics have real local-EVM acceptance evidence; mainnet operation is not demonstrated.

## Stop, recover and upgrade

`pause` persists across restarts and blocks execution, review and receipt recording. Search checks pause
at bounded checkpoints; a current model request or isolated execution can finish before control returns.
A mission has a 600-second work budget; an abandoned running lease expires after 660 seconds.
Changing configuration during work invalidates its result even if the operator resumes immediately.
The mission records a failure; restart the process, then recover and execute it under the new policy.
To recover, inspect its error/stages, correct configuration if needed, then use `recover UUID` and
`execute UUID`. Recovery does not edit the original inputs. Submit a new mission for changed data.

```sh
alpha-agent --home ./agent-state pause
alpha-agent --home ./agent-state verify
alpha-agent --home ./agent-state backup ./private-backup.zip
alpha-agent --home ./restored-state restore ./private-backup.zip
alpha-agent --home ./restored-state verify
```

Restore currently accepts archives up to 256 MiB uncompressed. Check backup size and test recovery
before depending on an archive; retain the original state directory for larger journals.

Backups contain the identity key and token. Encrypt them with your normal backup system, store separately,
and retain the reported SHA-256 and journal head in an independent trusted location. Restore never
merges into or overwrites an existing directory. Stop old processes before switching to the restored
home. Review configuration and balance, then resume deliberately.

Install an upgrade into a **new** virtual environment. Pause, back up, and verify before changing the
service's executable. Keep the prior environment and backup until the new version passes your missions.
For rollback, stop the new process and restore its pre-upgrade backup into a new home with the previous
version. Do not have two versions operating on the same home. No journal migration is needed for 1.2.0.
Manual config editing, signature failure or a crash during config replacement is a fail-closed integrity
error: preserve the affected directory and restore a verified backup, rather than rewriting hashes.

A local signature detects corruption, not theft of the key, semantic truth or deletion of the newest
valid journal suffix. Independent backups/checkpoints are necessary for rollback detection.

## Container installation

The `agent-runtime` target of `alpha_factory_v1/Dockerfile` runs the connected agent as UID 10001.
Unqualified builds retain the historical orchestrator, RPC facade and Flask UI. Both targets now
use the repository root as their build context; the checked-in Compose files select that context.
The five historical demo Compose consumers use the same context. Their default and all-profile
configuration models and local build inputs are checked by `python -m scripts.validate_legacy_compose
--docker-compose`. Optional dependency profiles require Compose 2.20 or later. This parse/build-path
check does not start those research stacks or establish their optional GPU, model or service integrations.
With `--dev-ui`, the same validator also starts the isolated development dashboard with fresh Node
dependencies and loads its shared telemetry module. The hot-reload Compose override uses Node 22.17.1,
read-only source mounts and a separate dependency volume; its first start runs `npm ci`.
The legacy target requires `API_TOKEN` and the documented legacy environment settings at launch.
It installs the historical core lock; heavyweight domain integrations remain optional.
Build from the repository root and bind the published port to host loopback:

```sh
docker build --target agent-runtime -t agialpha-agent:1.2.0 -f alpha_factory_v1/Dockerfile .
docker run --name agialpha-agent -d -p 127.0.0.1:8000:8000 -v agialpha-data:/data agialpha-agent:1.2.0
docker exec agialpha-agent cat /data/agent/api.token
```

Open `http://127.0.0.1:8000`. The named volume holds the identity, configuration, token and journal;
do not delete it when upgrading. Commands inside the container use
`python -m alpha_factory_v1.core.runtime.cli --home /data/agent ...`.
An existing empty bind-mounted home is also initialized once. Make that directory writable by UID
10001 before starting the container. A nonempty or partially initialized home is never reinitialized;
preserve it and restore a verified backup if required files are missing.
Do not mount the host Docker socket into this service. Use the host installation for coding missions,
where the isolated evaluator can use a deliberately configured local Docker engine. The container's
health endpoint is public and minimal; every mission/control endpoint still requires the access token.

## Historical Insight browser build

With Node.js 22.17.1 and Python 3.11+ installed, run `npm ci` in
`alpha_factory_v1/demos/alpha_agi_insight_v1/insight_browser_v1`, then `python manual_build.py`
(or `./manual_build.ps1` in PowerShell). This uses the same checked build as `npm run build`,
including bundled service workers, sandbox hosts, CSP hashes and offline assets. For an air-gapped
build, prefetch the dependencies and browser assets before disconnecting; `FETCH_ASSETS_SKIP_LLM=1`
omits the optional historical browser model. The previous manual compiler is retained verbatim in
`build/manual_build_legacy.py.txt` as historical source, not the active build path.
