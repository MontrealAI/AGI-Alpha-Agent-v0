[Project notice](../DISCLAIMER_SNIPPET.md)

# Alpha-Factory — from first mission to Ascension evidence

**Version 1.12.2.** Start with a useful result, inspect the evidence, and extend the workflow from there.
The `alpha_factory_v1` package retains the original domain agents, demos, blueprints and flowcharts.
Its maintained runtime provides five bounded mission types, a signed persistent journal, explicit review,
recovery and an authenticated local console. Ascension adds a tested, undeployed enterprise protocol.

## Choose your starting point

| Goal | Path | Requirements |
|---|---|---|
| Try editable decision cases | [Decision Studio](../studio/index.html) | Browser; built-in cases need no key or wallet |
| Work with your own supplied records | Native operator below | Python 3.11–3.13; private state directory |
| Explore all original experiments | [Demo walkthrough](DEMOS.md); `alpha-factory demos list`, `show NAME` and `check NAME` | Installed wheel or source checkout; optional dependencies listed per entry |
| Connect reviewed native work to a venture plan | FusionPlan and delivery commands below | Hash-locked operator environment, or the installed `chain` extra |
| Reproduce actual funding and settlement | [Ascension local-EVM run](ASCENSION_PROTOCOL.md#reproduce-the-end-to-end-run) | Source checkout, Python and Node 22.17.1 |
| Extend models, SDKs, memory or industry agents | [Preserved backend](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/tree/main/alpha_factory_v1/backend) | Separate research environment and integration-specific qualification |

## Install and obtain a first result

For release assets, follow the checksum-verifying [installer instructions](OPERATIONS.md#install-from-a-release).
For a source checkout, run from the repository root:

```bash
python3 -m venv .venv-agent
source .venv-agent/bin/activate
python -m pip install --require-hashes -r requirements-agent.lock
python -m pip install --no-deps -e .
python -m alpha_factory_v1.scripts.preflight --profile agent --offline
alpha-factory mission examples --output my-missions
alpha-factory mission --home ./agent-state init
alpha-factory mission --home ./agent-state run my-missions/allocation.json
alpha-factory mission --home ./agent-state serve
```

On Windows use `python -m venv .venv-agent`, then `.venv-agent\Scripts\Activate.ps1`.
The remaining commands are the same. An installed wheel includes the five mission examples; copying
examples works outside the repository and refuses an existing destination. For a second experiment,
choose another directory. Example inputs are constructed scenarios, not observed business outcomes.

Open **http://127.0.0.1:8765** and enter the token in `agent-state/api.token`. Select the returned mission,
inspect its selected items, budget, risk and totals, and approve or reject the exact result. Approval
archives evidence. It does not make a payment, execute a trade, or cast a validator vote. Stop the
console with **Ctrl+C**. `alpha-factory mission` and `alpha-agent` expose the same native commands.

| Example | Useful question | What is checked |
|---|---|---|
| `research.json` | Does a support-automation pilot justify rollout? | Quotations and source IDs; interpretation still needs review |
| `allocation.json` | Which operations improvements fit the capital and risk budget? | Selected IDs, integer totals and feasibility; benefits are assumptions |
| `schedule.json` | How should seven orders use constrained production resources? | Every operation, precedence, duration, machine exclusivity and lateness |
| `forecast.json` | Which forecast performs best on an untouched time holdout? | Temporal split, predictions and reproduced error metrics |
| `code.json` | Does a generated or supplied function pass held-out cases? | Isolated Docker replay and host-owned expected outputs; explicit opt-in required |

Research uses extractive passages until a provider is explicitly configured. Missing inference or
sandbox prerequisites fail visibly where required. No model download or paid provider request occurs
just because a key is present in the shell. Follow [model and code configuration](OPERATIONS.md#configure-inference-and-code).

## Prepare a FusionPlan

`examples` also creates `ascension-jobs.json`, containing a job for the allocation example. Edit its
goal, success metric, bounty, delivery duration and price/time weight before committing a plan.
The goal must exactly match the native mission you intend to deliver. A metric must describe what
reviewers can actually establish from the evidence; the compiler cannot supply that judgment.

```bash
alpha-agent ascension-compile my-missions/ascension-jobs.json --output fusion-plan.json
alpha-agent ascension-check fusion-plan.json
```

The compiler supports 1–128 ordered jobs. It uses Ethereum Keccak, double-hashed ABI leaves and sorted
Merkle pairs, including odd-node promotion. Its output matches the JavaScript compiler and shipped
Solidity `hashSpec`. It rejects ambiguous JSON, extra fields, fractional integers, bool-as-integer
values, invalid UTF-8 byte lengths and out-of-range token amounts. No RPC or wallet is contacted.

| Field | Exact meaning |
|---|---|
| `goal` | 1–512 UTF-8 bytes; identical to the delivered native mission goal |
| `successMetric` | 1–512 UTF-8 bytes; evidence reviewers must assess |
| `bounty` | Integer **string**, 100 through `2^96-1` base units; canonical $AGIALPHA has 18 decimals |
| `duration` | Integer 1–7,776,000 seconds (90 days) |
| `priceWeight` | Integer 0–10,000 basis points; remaining weight applies to delivery time |

`"100000000000000000000"` represents 100 tokens. The compiler prints `planRoot`, job count and exact
`totalBounty`; the output includes each indexed job, leaf and proof. Changing a job or its order changes
the commitment. `ascension-check` recomputes the whole plan and rejects modified metadata or proofs.
Existing output files are never overwritten.

## Deliver reviewed native evidence

After running a mission, use the console or the returned ID, revision and result hash to review it:

```bash
alpha-agent --home ./agent-state show MISSION_UUID
alpha-agent --home ./agent-state review MISSION_UUID --revision REVISION \
  --result-hash RESULT_HASH --approve --note 'Verified the selected items, budget, risk and integer totals.'
alpha-agent --home ./agent-state ascension-deliver fusion-plan.json \
  --index 0 --mission MISSION_UUID --output reviewed-delivery.json
```

The handoff refuses pending, rejected or mismatched work. It signs the entire association between the
plan, job index and existing approved journal receipt, then independently rechecks the native result.
The printed `resultHash` is Ethereum Keccak of the **exact delivery-file bytes**. Do not reformat that
file: even an added newline changes the bytes and is rejected by verification.

A reviewer obtains the agent public key through an independently trusted channel and the plan root
from the intended Nova-Seed on the intended chain/contract. Then:

```bash
alpha-agent ascension-verify-delivery reviewed-delivery.json \
  --public-key TRUSTED_ED25519_PUBLIC_KEY --plan-root TRUSTED_ONCHAIN_PLAN_ROOT
```

Never trust the key or root solely because the same delivery file supplies them. Verification binds
identity, plan, exact goal, signature, result and arithmetic. For code deliveries, the external reviewer
must explicitly add `--replay-code` and have the isolated Docker runtime available. Verification never
silently executes a supplied program. Provider access is not needed to verify a research quotation.

The Ed25519 signer is a native journal identity, **not proof of ENS ownership**. Match it to the assigned
worker using your independently verified operating records. Verify the correct chain, deployed modules,
seed, job, worker, deadlines, evidence availability and current validator eligibility separately.
The same FusionPlan may be used in several seeds: a plan root alone is not a unique on-chain job ID.
The delivery format deliberately does not assert an unobserved chain binding or transaction.

The CLI does not upload the file, submit a transaction or approve work on behalf of validators. The
agent or operator must make the exact file available at the submitted result URI. The three selected
validators assess the success metric and exact artifact; two matching approvals trigger settlement.
A successful local check cannot decide the semantic truth, economic value or independence of a review.
See the [contract rules and deployment boundary](ASCENSION_PROTOCOL.md).

## Trace the full vision to executable components

| Vision stage | Implementation | Evidence / remaining boundary |
|---|---|---|
| Insight sees opportunities | Insight Atlas, research, allocation, schedule and forecast engines | Reproducible supplied-input analysis; beyond-human foresight is unmeasured |
| Nova-Seed preserves foresight | Encrypted browser genome, `NovaSeed.sol` ERC-721, immutable plan root and lineage | Local-EVM mint/transfer; durable external storage and key custody remain operator responsibilities |
| MARK prices and funds a plan | `AscensionMark.sol` bonding curve, admitted lots and plan-restricted treasury | Real local-EVM arithmetic and recovery; no live market deployment |
| Risk validators gate the seed | `AscensionRiskOracle.sol`, staked ENS roles, expiring evidence-bound reviews | Distinct fixture signers; independent real organizations must be recruited separately |
| Sovereign decomposes and routes work | Indexed Merkle plan → once-only committed jobs | Budget, horizon and reviewer-capacity checks; external runtime must drive a live campaign |
| Agents execute with reputation | Native five-kind engine plus `AscensionJobMarket.sol` auctions | Price/time/reputation rule, locked collateral, result-bound handoff; broad domain agents remain separate research integrations |
| Validators approve or fail work | Two of three exact-result approvals/rejections; deadline paths | Local checks and on-chain reviews are distinct; missing quorum refunds instead of inventing failure |
| Value settles in $AGIALPHA | Fixed canonical token, 1% payout burn, explicit refunds and slashing | Actual local-EVM conservation; real token compatibility and mainnet commissioning are separate gates |
| Experience compounds | Transfer experiment, Proof Bloom, native memory and successor NFTs | Held-out/control evidence; successors start unapproved and do not inherit scientific validity |

The original domain/flow diagrams remain the architecture vision. Finance, biotech, drug design,
cybersecurity and the other industry modules must be validated for their own data, model, actuation and
operating environment. Research fallback outputs are not equivalent to live integrations. This release
does not label every historical experiment production-ready or certify global autonomous enterprises.

## Launchers, offline use and recovery

Both Bash entry points delegate to the same Python launcher. Their historical default remains `legacy`.
Use explicit `--profile agent` for the maintained runtime:

```bash
python alpha_factory_v1/quickstart.py --profile agent --preflight --offline
python alpha_factory_v1/quickstart.py --profile agent --venv .venv-operator -- --home ./operator-state init
python alpha_factory_v1/quickstart.py --profile agent --venv .venv-operator -- --home ./operator-state serve
```

`--preflight` performs checks only. The agent profile needs neither Docker nor Node for its four
non-code mission kinds. A new environment installs its chosen hash-locked requirements and runs
`pip check`; an incomplete bootstrap or changed lock digest is rejected on retry. Choose a new path or inspect and remove
only that failed environment yourself. Existing unmarked environments are retained and checked.
`--skip-preflight` is an explicit operator choice; a failed check never silently starts a service.
Relative mission, home and output paths resolve from the invoking directory. No `.env` is overwritten.

Use `--wheelhouse /path/to/wheels --offline` for a new network-free installation. Build that wheelhouse
on a matching Python/platform beforehand. The [release installer](OPERATIONS.md#install-from-a-release)
also supports offline wheels and checksum verification. Keep the operator environment separate from
the much larger historical SDK/training environment.

Before upgrade, pause, verify and back up the journal. Keep its identity, head and checksum separately.
Restore into a **new** home, verify it, then resume deliberately. Never run two processes against the
same home or manually edit signed records. No journal migration is needed for 1.12.2.
[Recovery commands and troubleshooting](OPERATIONS.md) cover Windows, containers and rollback.

## Verification and preservation

The release pipeline checks the installed wheel outside the checkout, packaged examples, native
missions, tamper/recovery behavior, the Python/JavaScript/Solidity commitment boundary, contract
settlement, browser flows, all catalog entries, full Python regression, strict types and documentation.
`scripts/check_factory_readiness.py` additionally preserves every pre-update package path and every
original Mermaid block, plus the original media bytes. The canonical examples and installed copies
must agree. The 198-page manuscript and earlier releases remain intact.

[Release readiness](RELEASE_READINESS.md) defines what the gates establish. Successful finite tests do
not replace operational commissioning, independent review, security assessment or measured usefulness
with real buyers and data.
