# Ubuntu Hardhat creator, separate Ledger governor

## Recommended route

1. Choose the deployer and confirm the Ledger governor address plus the deployment
   settings below. Use `conventional-eoa-direct-create.v1` with
   `qualificationEvidence: null`; no wallet-specific reports are needed.
2. Prepare the public run/config files and exact source/build as documented, then
   run the single Hardhat command below on Ubuntu. Review the transaction summary
   and enter the deployer key only in its hidden local prompt. The script performs
   its transaction checks and reconciles interrupted work automatically.
3. Check the completed deployment has the intended governor and no remaining
   creator privileges in the reported fields. On the Mac Ledger, perform only the
   separately reviewed governor configuration/activation steps you intend.

The public settings still need to be supplied; this guide does not claim an
already automated configuration wizard. The report-bearing profiles are optional
advanced routes. After the intended contracts are governed by the Ledger account
and creator privileges are absent, no ongoing deployer role is required by this
core deployment. External ENS, token/proxy and other authority remain separately
scoped; these checks do not certify every external controller.

This additive entry point implements the owner's October 16 clarification: the
owner enters a selected **creator** private key locally into the Ubuntu terminal.
The governor is explicitly `0xd76AD27a1Bcf8652e7e46BE603FA742FD1c10A99` and must be a
different account. Subsequent governor configuration is a separate Mac Studio
Ledger workflow, ordinarily through MetaMask and the verified Etherscan contract.

The older `deploy:mainnet` command remains unchanged. It is **not** the hidden-TTY
entry point. No Solidity, compiler input, artifact, original deployment, fee
wallet, treasury, ENS custody, approval, or historical report is modified here.

## One user-run creation command

Use a complete reviewed checkout with its exact new wrapper checkpoint, existing
pinned dependencies, Node **22.23.2**, and a source-bound build catalog. Compile and
verify the source/build before entering any key. Never install, compile, import
unreviewed plugins, or source shell startup helpers after key entry.

Set only the public run-file path and local HTTPS RPC endpoints in the operator
shell. An endpoint can contain a provider credential: keep it local and do not
paste it into chat, screenshots, shell traces or public reports. The launcher
never prints endpoint text or provider exceptions. Disable shell tracing before
setting those values. Do not supply a private key through any environment value,
argument, `.env` file, redirected input, command substitution, or clipboard script.
The route rejects known secret/debug/injection environment channels and deployment
`.env` files. It does not load dotenv or stored Hardhat accounts.

From the reviewed repository root, the owner executes:

```sh
MANAGER_CREATOR_RUN=/absolute/operator/run.json \
node node_modules/hardhat/dist/src/cli.js \
  --config hardhat.creator.config.mjs run \
  --no-compile hardhat/scripts/deploy-core-tty.js --network mainnet
```

`MANAGER_READ_RPC_URL` and `MANAGER_RELAY_RPC_URL` must already identify the selected
HTTPS endpoints in that shell. They are separate bounded read and once-only raw
submission transports. The isolated Hardhat network has `accounts: []`; the
creator key is read later, inside the deployment-script process. No wallet SDK,
external signing packet, companion UI, browser raw export or Mac creation step is
required by this route.

The **public** external run file has exactly these fields:

```json
{
  "schema": "manager-tty-creator-run-v1",
  "mode": "new",
  "catalog": "/absolute/operator/catalog.json",
  "catalogSha256": "REVIEWED_64_HEX_SHA256",
  "buildId": "REVIEWED_BUILD_ID",
  "config": "/absolute/operator/core-config.json",
  "session": "/absolute/operator/new-session",
  "lockDirectory": "/absolute/operator/creator-locks",
  "finalityTimeoutSeconds": 1800,
  "pollIntervalSeconds": 15
}
```

`core-config.json` uses the existing exact
`manager-core-creation-config-v1` schema. It supplies the selected checksum creator
address, explicit governor acknowledgement, current reviewed canonical block,
nonce, bounded expiry, exact constructor values, nine individual type-2 gas/fee
envelopes and maximum total fee ceiling. Constructor roots remain in this order:
`club.agi.eth`, `agent.agi.eth`, `alpha.club.agi.eth`, `alpha.agent.agi.eth`.
The script never swaps the agent and Alpha-club roots, chooses fee wallets,
changes ownership or silently fills missing authority inputs.

Both input files and the catalog must be outside the reviewed checkout. The
session must be new in `new` mode; its parent and the shared lock directory must
already exist as real, exclusively controlled directories. Run/config files are
bounded regular files with a single link. The existing session code creates
private state and identity-bound locks; stale locks are never automatically removed.

## Offline inspection

Set the public run file's mode to `inspect` and use the same command. It verifies
the actual clean Git revision, selected catalog and all constructor/envelope
inputs, then prints the public plan with `readyToBroadcast: false`. It exits before
reading endpoint values, prompting for confirmation/key, creating operator state
or signing. No provider endpoint is required for inspection. This is source/build
inspection only: current chain state still requires new/resume preflight.

## Review and execution

1. Before key input, the script validates source, compiler/artifact catalog,
   mainnet, current creator/governor state, nonce, predicted addresses, canonical
   USDC operational checks, gas bounds and fee ceilings.
2. It prints the complete public plan. Review source/build identities, creator,
   chain, d76 governor, constructor roots/wallets, nine CREATE addresses and total
   fee ceiling. Type exactly `DEPLOY <full plan SHA256>` to authorize this bounded
   sequence. Declining reaches neither a key prompt nor a transaction.
3. Enter only the selected creator's `0x`-prefixed 32-byte key at the hidden local
   TTY prompt. The derived address must match. Never send the key to the assistant.
4. The process signs each **fixed type-2, zero-value, null-destination CREATE** in
   memory. It durably records the original handoff, signed transaction capability
   and submission attempt before sending. It never changes nonce, fees, gas,
   initcode or signature to retry a failure.
5. Each next operation waits for the prior exact successful **finalized** receipt,
   canonical runtime/link checks and expected current state. Mainnet finality can
   take materially longer than a few confirmations. Timeout means stop and
   reconcile; it does not authorize a replacement.
6. After eight libraries and Manager, the existing completion check requires
   d76 owner, zero pending owner, paused creation state, no direct creator
   moderator/agent/validator exception, exact four roots and fee wallets, and zero
   new jobs/reserves. It releases only its own matching creator lock.
7. Export the existing source-bound verification package from the completed
   session, submit its exact compiler/constructor/library data to Etherscan, and
   check explorer acceptance and chain readback. Actual deployment receipts and
   explorer acceptance are post-creation acceptance steps, not prerequisites that
   could exist before creation. Governor configuration, optional ENS/metadata and
   activation remain separately authorized transactions.

## Wallet selection and account code

For the ordinary Ethereum route, set `creatorPolicy` to
`{"mode":"conventional-eoa-direct-create.v1"}` and `qualificationEvidence` to
`null` in the public config. Use any selected signing EOA, with empty code or an
existing EIP-7702 delegation marker. There is no wallet allowlist, wallet review,
consensus report, target-code hash, target-state check or extra eligibility
ceremony. Ethereum validates transaction-origin eligibility automatically.
Observed creator code is informational; the launcher does not inspect or approve
its delegate target. No delegation change is requested.

The deployment still checks that the entered key matches the selected creator
and that the exact source/build, chain, nonce, fees, balance, dependencies,
receipts, runtime and intended governor are correct. These protect the requested
transaction and resulting contracts. The creator and governor remain separate.
Changing the creator **before any handoff/signature** requires regenerating nonce,
CREATE addresses and the plan. Once a capability exists, reconcile it first;
changing the run file is not a nonce-reuse mechanism.

This conventional profile claims transaction correctness only, not formal
zero-invocation, delegate safety, exclusive key custody or production-state
qualification. Constructors can execute dependency code; no broader callback
claim follows from direct CREATE. Out-of-band nonce/balance changes, compromised
keys and other account activity remain risks.

The existing `empty-eoa-direct-create.v1`, `marker-eoa-direct-create.v1` and strict
delegated profile keep their original requirements and assurance boundaries.
The marker profile still requires its exact independently reviewed reports if
explicitly selected. The TTY route supports conventional, empty and marker
profiles; it does not select the older strict delegated profile. Every submitted
operation remains a direct type-2 CREATE: no type-4 authorization, self-call,
batching, factory creation or smart-wallet fallback.

## Interruption and limits

Run `mode: "resume"` only with the same reviewed core plan and session. Existing
handed-off/signed/attempted operations are reconciled **read-only before another
key prompt**. A known hash may wait for finality; a hashless handoff uses existing
bounded exact recovery. An unresolved capability stops the route. It never signs
again or automatically relays an old signed capability. After successful
reconciliation, only untouched `planned` operations can obtain new signatures.
Use the existing explicit journal inspection/repair workflow for a torn append;
this launcher adds no repair or stale-lock bypass.

The key is never intentionally written to a file, journal, environment, argument,
log or child input. Existing Git source observers still launch sanitized read-only
subprocesses, without the key in arguments/environment. The Wallet stays only in
the script process and references are released on success/failure. JavaScript,
V8 and ethers cannot guarantee erasure of immutable strings or memory copies.
After a typo, invalid paste or overlong input, the prompt keeps echo disabled and
discards the remaining line until Enter or explicit cancellation. Invalid input
cannot be repaired with backspace; end that line and restart the reviewed route.
A hidden prompt does not protect a compromised Ubuntu host, terminal, debugger,
clipboard, dependency or OS. It cannot restore a terminal after SIGKILL or repair
an uncooperative terminal driver. Keep operator files exclusively controlled;
identity rechecks do not guarantee safety against hostile swaps between checks.

This transport needs its own reviewed source checkpoint and disposable functional
acceptance. The retained d371/d953 hosted **96 + 30** cases qualify the earlier
contract/session source and remain unchanged; they do not retrospectively claim
this newly added TTY route was exercised. No live deployment is authorized by a
local test result.

### Public-input file identity

The process holds read-only descriptors for the original run/config files and their parent directories until the command returns or fails. It reads the bound file descriptors and checks both descriptor and named-path identities after awaits, so unlinking and recreating an identical pathname cannot pass by recycling the old inode. Descriptor cleanup never removes or modifies either the original or replacement path. Input bindings close on early validation errors as well as successful completion.

These checks require an exclusively controlled, trusted local filesystem. They are not an atomic defense against hostile changes between checks, a compromised Ubuntu process, or manipulation of the operating system. No secure-erasure guarantee is made.
