# Ubuntu Hardhat creation, then Mac Ledger governance

## Recommended route

1. Select the deployer, Ledger governor and intended settings in the public
   example. Keep the recommended conventional sender mode; no wallet reports.
2. Prepare the source-bound plan as below, run the Hardhat creator command on
   Ubuntu, review its summary and enter the key only in the hidden local prompt.
   The script checks the transactions and reconciles interrupted creations.
3. On the Mac Ledger, complete the two separately reviewed governor bindings.
   Verify the final contracts, owner/pending-owner fields and absence of creator
   roles before any separately approved funding, admission or activation.

The public settings and plan still need to be prepared; there is no automatic
configuration wizard. Once the scoped authority checks pass, the creator has no
ongoing deployment role in the fresh graph. External token/proxy/ENS controllers
remain separately scoped; this does not certify every external authority.

This additive entry point creates the five unchanged Ascension contracts from the
operator's selected creator account. Access, RiskOracle and JobMarket receive the
explicitly acknowledged governor as owner in their constructors. The creator does
not receive ownership, admission, stake, approval or another deployment privilege.
The entry point stops before both governor-only graph bindings.

## Scope and current qualification

Use a complete, clean checkout of the exact reviewed candidate, its existing pinned
Node 22/toolchain and matching compiled artifacts. The old local-fixture config,
historical manifests and v1 verification semantics remain unchanged. This path is
an additive user-run script; implementation does not authorize a Mainnet action.

No creator address is hardcoded. The recommended ordinary route uses
`sender: {"mode":"conventional-eoa-direct-create.v1"}` as in the public example.
Select any signing EOA, with empty code or an existing EIP-7702 marker. No
wallet-specific review, qualification report, target code hash or storage checks
are required. Ethereum validates transaction-origin eligibility automatically.
The script does not inspect or approve the delegate target or change delegation.
It still checks the key matches the creator and the requested transactions and
resulting contracts are correct. No formal zero-invocation, delegate safety,
exclusive custody or real-state qualification is claimed. Constructor dependencies
can execute code, so direct CREATE alone is not a universal callback proof.

The existing empty, strict-delegated and marker-qualified modes retain their
original checks for operators explicitly choosing those advanced profiles. No
fallback uses a smart-contract wallet, factory, batch, self-call or type-4
authorization. A last-minute creator change requires a new nonce/address/constructor
plan before any signature; existing signed/submitted work must be reconciled first.

All five transactions are exact type-2, zero-value, null-destination CREATEs. Their
chain, sender, nonce, gas, fee caps, access list and full initcode are fixed by the
plan. Governor and creator must differ. No existing deployment is a write target.

## Operator preparation

1. Compile and run the qualified contract checks. Obtain an independent clean-source
   revision and generate the v2 plan with mainnet:authority-plan. Pin fresh canonical
   account, dependency and namespace evidence, current nonce and explicit economic
   parameters. Reconcile cross-project allocations first. The plan must pass the
   bounded read-only preflight; old observations are not current permission.
2. Keep the plan, command file, journal, checkpoint and shared lock directory outside
   the checkout, under real existing directories. The command JSON has exactly three
   public fields: plan, journal and output, each containing its corresponding path.
   Choose a new output path on each invocation. Never edit a partial journal or head.
3. In the owner's Ubuntu terminal, set ALPHA_CREATOR_COMMAND to that public command
   path, DEPLOYMENT_LOCK_DIRECTORY to the common actual-sender lock directory, and
   ALPHA_READ_ONLY_RPC_URL plus ALPHA_RAW_RELAY_RPC_URL to the intended HTTPS endpoints.
   Provider URLs, access credentials and errors are not printed by the script.
   Creator private keys must not appear in environment variables, command arguments,
   .env files, shell history, logs, command JSON, clipboard automation or assistant
   conversations. Do not run the prompt through an assistant-controlled terminal.
4. From tests/contracts, the user-run command is:

       npm run mainnet:creator

   It invokes Hardhat with hardhat.creator.config.js, --network mainnet and
   --no-compile. The config has no accounts or private keys. The script shows the
   public source, chain, creator, governor, dependencies, parameters, addresses,
   complete five transaction envelopes and aggregate maximum fee. The owner must
   type DEPLOY followed by the full displayed plan SHA256 before session writes or
   signing. A genuine unused terminal then accepts a hidden 0x-prefixed 32-byte key.
   This step is performed by the owner; no assistant receives or enters the key.

The reader rejects redirected input, competing readers, malformed scalars, extra
input and control sequences. It restores terminal mode on handled cancellation.
The signer checks the derived address and exposes only an exact-creation signing
capability. The key is kept in this process during the bounded creation/finality
sequence. Input buffers are cleared where possible and references are dropped at
exit; JavaScript, dependencies, terminal software and the host cannot provide a
secure-erasure guarantee. A compromised Ubuntu host can steal an entered key.

## Execution and interruption

The durable intent precedes signing. The journal records the exact signed hash,
never the private key or serialized signed transaction. The durable submission
attempt precedes the one-shot relay. Exact canonical finalized receipts, deployment
addresses, runtime, ownership and partial graph state are checked before advancing.
The script never replaces fees, skips a nonce or retries an ambiguous send.

The operator normally confirms and enters the key once. Each creation allows at
most 120 read-only recovery observations, 15 seconds apart; the run has an overall
three-hour budget. Per-read and cumulative request/byte caps remain enforced.
Finality delays can therefore keep the ephemeral key in process memory for a long
time. A timeout or interrupt stops the campaign. Resume first reconciles the exact
outstanding transaction without prompting for a key. If unresolved, it stops and
retains uncertainty and locks. No observed transaction does not prove no broadcast.
An already finalized prefix is never replayed. A fresh key prompt occurs only when
the next creation is eligible; a lost pre-submission signature/handoff can require
explicit operator investigation rather than an automatic reset.

## Creation checkpoint and Ledger continuation

After five finalized creations, the output says awaiting-governor-bindings. It
contains public addresses, exact creation receipts and the verified unbound graph.
It does not claim final authority, campaign completion, explorer acceptance or
activation. Alpha has no global pause switch; an uncommissioned graph is not paused.

The existing seven-operation session retains both actor locks. With one shared
creator, the minimal cross-project order is Manager's creation and closeout, Jobs'
creation and closeout, then Alpha's five creations last. Other project-specific
requirements must also be satisfied; this order is not a cross-machine nonce lock.

On Mac, independently revalidate the reviewed source/build and this public
checkpoint. Only the Ledger governor may approve Oracle.bindMarketplace and
JobMarket.bindMark for these newly receipt-bound addresses. Do not copy the Ubuntu
absolute-path session as a portable authority. The original coordinator can prepare
and reconcile those exact externally authorized calls; final verification/export
requires all five creations and both governor receipts before lock cleanup.
Filesystem locks protect cooperating processes on the same shared filesystem only.
Serialize all Mac and out-of-band governor activity separately.

External independent audit and Sepolia rehearsal remain owner-accepted omissions,
not passes or new blanket prerequisites. Fresh actual-account/dependency evidence,
the physical Ledger route, actual explorer acceptance and participant/capital
commissioning retain their distinct operational status. No automatic binding,
admission, approval, funding or activation is performed by this creator script.

## Process-scoped extra CA policy

Default operation uses normal Node TLS roots and no extra CA declaration. If the
operator's reviewed environment genuinely needs NODE_EXTRA_CA_CERTS, it must name
one canonical regular PEM CA file outside the checkout. ALPHA_CREATOR_CA_POLICY
must name a public JSON file with exactly schema = agialpha.creator-ca-policy.v1,
certificate = that exact absolute path, and sha256 = its reviewed lowercase SHA256.
The script checks the file, digest and CA material before RPC or key entry and
rechecks them at operational boundaries. Unknown, changed or undeclared extra
trust is refused. NODE_TLS_REJECT_UNAUTHORIZED and loader/debug settings remain
refused. No OS or browser trust is changed, and certificate validation stays on.

The policy is an operator-reviewed local trust decision, not authenticity proved
by a self-declared hash. Node loads extra roots at process startup; these repeated
observations assume a trusted local filesystem/runtime and do not prove immunity
to hostile changes between startup or checks. Never approve a CA supplied by an
untrusted deployment proposal. Native CI uses only a disposable child-process CA
for its numeric-loopback HTTPS fixture.

## Additive native acceptance

The read-only native workflow retains all previous serial contract and three
sender-profile campaigns. It adds hidden-TTY unit tests, real Linux PTY checks,
the five-creation interruption/resume fixture, and an actual clean-checkout Hardhat
entry campaign. The latter observes HEAD independently, rejects dirty/forged source
and unknown CA trust, checks wrong-key refusal, creates exactly five with the fixed
public fixture key, then regenerates the pending-governor checkpoint without a key
or resend. Public artifacts contain receipts and safe summaries, never private
transcripts, raw signatures, fixture TLS keys or session directories. Local partial
source-overlay tests are not reported as hosted clean-checkout passes.
