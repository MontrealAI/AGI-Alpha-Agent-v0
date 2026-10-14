[Project notice](../DISCLAIMER_SNIPPET.md)

# Nova-Seed Studio: commissioning, recovery and support

This runbook separates the implementation release, contract deployment, operator canary and public launch.
Use the [deployment record](MAINNET_DEPLOYMENT.md) for the immutable October 11 suite, and the
[new-deployment guide](MAINNET_READINESS.md) for separately authorized current-source preparation.

## Deployment capability matrix

| Profile/stage | Preparation/inspection | New exposure |
| --- | --- | --- |
| No wallet | Local compile, seal and recover | None |
| October 11 archive | Exact archive identity required | Blocked; permitted recovery/obligations remain |
| Exact-source local | Pinned local chain and profile | Local test assets only |
| Operator canary | Independently reviewed qualified build | Explicit bounded scope; no profile supplied here |
| Public launch | Verified state and completed gates | Separate launch decision after real canary |

Do not edit the archive, present predicted addresses as deployed, point MARK at a different marketplace,
or replace a negative capability flag in the browser. Qualification is a reviewed release/configuration action
bound to evidence, not a user checkbox. Interface limits do not prevent direct contract calls.

The source-registered qualification adapter is implemented, including dependency/authority checks, exact
canary intent scope and recovery after authorization expiry. The production registry contains no qualified
mainnet entry. Deployment evidence and the operational approval are still required to populate that registry.

## Commission an exact deployment

1. Freeze the reviewed source commit, lockfiles, compiler settings, ABI bundle and frontend artifact. Retain
   digests and run the full required CI on the exact merge candidate. Record findings and reviewers explicitly.
2. Qualify the token, ENS and governance dependencies, including proxy implementation and authority where
   applicable. A proxy shell hash does not establish which implementation executes. Verify governance control,
   parameters, admission authority and the three role namespaces with current independent RPC observations.
3. Rehearse the browser workflow on the exact local source, then on an isolated pinned mainnet fork using real
   dependencies. Preserve balances, receipts, source/profile identities and failure-path evidence. Never point
   fixture reset, account impersonation or mock-installation helpers at a funded network.
4. For a new suite, obtain separate deployment/signing authorization, use the existing unsigned preparation
   tools, verify the actual deployed bytes/bindings and explorer sources, and preserve its own deployment record.
   The old suite remains immutable and users' old obligations remain attributable to that suite.
5. Define the operator canary **before** general launch: exact profile, participating consenting wallets,
   responsible approvers, token and ETH limits, bounded plan/jobs, reviewers, stop criteria and refund handling.
   Add only the reviewed profile/stage through the normal code/configuration review. Public mode stays closed.
   Keep the stable deployment descriptor, mutable qualification and exact run authorization distinct. Publish
   verified artifacts before approving the final mint calldata. Bind each canary action's sender, nonce and
   gas-unit ceiling; separately authorize its ETH fee budget, which the gas-unit ceiling does not bound.
6. Execute the bounded lifecycle with real authorized actors. Reconcile mint, review, purchases, activation,
   routing, delivery, validation/settlement and exits against receipts and token balances. Label it a canary.
   Local fixtures, simulated votes and an outer smart-wallet success are not substitutes for these observations.
7. After resolving findings, obtain the public-launch decision and publish a separate evidence-bound activation.
   Verify the actual hosted route/version and profile after deployment. Assign operators and exercise recovery.

No deployment, spending, admission, governance, canary or public-funding authorization is inferred from a
request to implement, merge or release frontend code. Until these gates are cleared, documentation must say
which step is blocked and who owns the decision.

## Recovery procedures

| Situation | Safe continuation and evidence |
| --- | --- |
| Refresh/device change | Restore exact kit/journal; inspect live state; never auto-sign |
| Wallet rejection | Retain project; retry intentionally only after definite rejection and no unresolved action |
| Lost response | Preserve unknown status; reconcile exact sender/nonce/call and canonical finalized receipt |
| Pending transaction | Wait or manage wallet replacement; never assume it was dropped |
| Same-nonce cancellation | Confirm cancellation; refresh before a new intentional action |
| Different replacement | Verify replacement; never report original intent completed |
| Reorg/no finality | Remain unresolved until receipt is canonical and finalized |
| Missing semantic effect | Keep resend barrier; verify exact emitter, arguments and contract state |
| Canary gas mismatch | Export receipt for operator review; never resend to repair the mismatch |
| Approval then rejected buy | Re-read allowance, quote, lots and reserve; never invent funding |
| Artifact unavailable | Restore exact retained bytes/references; never silently reseal |
| Review/admission expired | Obtain genuine renewal from the responsible actor where required |
| Existing job refund | Collect terminal MARK job refund, then eligible closure/reclaim |
| Lost capsule passphrase | Use separate passphrase backup; wallet keys/administrators cannot decrypt it |

A new device cannot safely infer that no action is pending elsewhere. Stop using the original device until
its journal and wallet outcome are reconciled. Never import an unrelated person's journal to clear your state.
Journals and kit checksums are editable local evidence aids; on-chain observations establish actual execution.

Keep the original sealed capsule and complete plan/proofs, profile identity, public evidence/metadata, known
seed/job IDs and verified receipt records. Keep the capsule passphrase separately. Never include private keys,
wallet recovery phrases, storage credentials or RPC credentials. Before deleting local data, export and open
the backup. Clearing the page cannot revoke the wallet extension's account permission or on-chain allowance.

## Monitor and respond

Assign a named operator for artifact availability and local backup retention; review/admission/ENS expiry;
pending wallet requests and replacements; active-job and campaign deadlines; reviewer capacity; token and
dependency changes; and refunds, stake unlocks and remaining allowances. A static page does not run these
checks after it is closed and cannot automatically expire a job on-chain.

An incident response can disable new frontend entry points or roll back a bad static build while retaining
old-profile inspection and permitted recovery routes. It cannot reverse confirmed transactions, pause these
immutable contracts, delete obligations or upgrade deployed bytes. Confirm the replacement frontend's version,
profile identity and cache behavior before reopening access.

## Browser and wallet support evidence

| Combination/capability | Support and evidence boundary |
| --- | --- |
| Web Crypto/modules/secure context | Preparation exercised in Chromium; see exact acceptance reports |
| EIP-1193 injected EOA wallet | Explicit selection/direct requests; fixture coverage is not an extension trial |
| Multiple EIP-6963 providers | Explicit choice, untrusted provider text; real provider trials still required |
| Durable storage and Web Locks | Required for signing; inspect-only fallback if unavailable |
| Mobile injected browser | Compatibility candidate; no physical device trial claimed |
| Hardware through injected wallet | Wallet handles hardware; no physical trial or USB/Bluetooth integration |
| WalletConnect QR | Not supplied; do not advertise support |
| Smart accounts/batches/type 4 | Unsupported; direct supported EOA transaction verification only |
| Accessibility | EN/FR, keyboard/layout and axe exercised; manual screen-reader trial still required |

The recorded Chromium run exercised the generated site: no-wallet creation, encryption/recovery, wrong
passphrase, kit import, EN/FR, keyboard navigation, desktop and 320/390-pixel viewports, and 42 panel/viewport
axe checks. The shared MARK browser run passed its 15 checks, including explicit/rejected requests, reload,
journal import, same-browser locks, replacement/finality and reorganization. These are browser automation
results with synthetic data/provider fixtures. They do not establish a real extension, phone, hardware wallet
or screen-reader user's experience. The [acceptance record](NOVA_SEED_STUDIO_ACCEPTANCE.md) identifies the
exact reports and the separate current-source EVM lifecycle evidence.

Record device, OS/browser, wallet version, account type, date, exact build/profile, steps and observed results
for every claimed supported combination. Keep addresses/public receipts only with the participants' consent.
Do not claim universal mobile, hardware-wallet or accessibility coverage from mock-provider tests.

## Release and preservation

Preserve the Ascension Lab, old capsule readers, Protocol Desk demo, MARK recovery workspace, native/runtime
handoffs, SUCCESSOR Ω, historical deployment files, existing URLs and all flowcharts. Restrict old-file edits
to integration links, build/cache packaging, shared compatible wallet additions and tests/release registration.
The exact preservation diff and validation belong in the release evidence record.

Normal branch protection, independent review and required CI remain in force. A merged PR does not prove
Pages has deployed. Record the actual merge commit, release tag, built artifact digest and observed hosted
frontend identity. A passing software release is neither an audit nor operational-mainnet completion.
