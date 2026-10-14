[Project notice](../DISCLAIMER_SNIPPET.md)

# Nova-Seed Studio: architecture, evidence and commissioning

Implementation baseline: main `7436a02cc4619d4f636bd02390888b9bb47a7eb3`; MARK PR #4778 originally inspected at
`1bb348b9f87920f38e565cfa43f0ffe4249e52c9`. The change is stacked on the current MARK foundation and must retain
its latest recovery/cache corrections, integrated at `5ad36fdc5870b9667e681eb81f41e3c923b8375b`.
The complete user handoff dated October 13, 2026 is the acceptance scope.

## Implementation map and initial gaps

| Surface | Baseline | Addition |
|---|---|---|
| Ascension Lab / crypto | Offline genome, compatible encryption, recovery | Preserved; Studio embeds the executable plan before encryption |
| MARK wallet | Explicit provider/action/preview, archive policy, journal, lock, finality/replacements | Reused client and journal; fixed build-time qualification registry and session coordinator |
| Compiler | Native Python, JavaScript and Solidity implementations | Browser compiler using the already-locked ethers 6.17.0 distribution; parity across all four |
| Artifacts | Offline capsule exports | Versioned package, privacy review, Pinata multipart upload, strict retrieval, portable checksummed kit |
| Browser orchestration | Advanced isolated action forms | Guided editor, identity/mint/review/funding/bloom/route, verified receipts and coherent resume |
| Execution | Native Ascension and SUCCESSOR workflows | Context-bound work export and existing on-chain job controls; no invented runtime connection |
| Production activation | Archived immutable profile with new exposure blocked | Same restriction; no approved replacement registry entries |

All new UI code lives under `docs/assets/nova-studio/`, with an additive `docs/ascension/mainnet/index.html`.
Existing changes are limited to shared profile/client/session integration, contextual MARK links, navigation,
cache exclusion, evidence inventories and existing CI integration. Solidity, compiler locks, historical
archives, original local receipts and existing flowcharts are unchanged. No framework migration is involved.

## Hash and schema contracts

| Value | Exact meaning |
|---|---|
| Inner capsule `commitment` | SHA-256 of established canonical `{blind,payload}`; not the mint capsule hash |
| `capsuleHash` | `0x` + existing `hashObject(finalSealedCapsule)`, covering the whole sealed object |
| `capsuleByteHash` | SHA-256 of canonical capsule JSON plus one LF; matches uploaded/exported file bytes |
| FusionPlan leaf | Double Ethereum Keccak of ABI-encoded index, goal hash, metric hash, uint96 bounty, uint32 duration, uint16 weight |
| Merkle root/proof | Sorted pairs; unpaired node promoted unchanged; indexed leaves |
| Evidence/metadata hash | SHA-256 of the established canonical public object |
| CID | Immutable storage identifier; never substituted for a protocol hash or availability evidence |
| Recovery checksum | SHA-256 of the serialized body; body is copied at export so later journal mutations cannot alter it |

The package is `agialpha.nova-studio.package.v1`; the outer recovery kit is
`agialpha.nova-studio.recovery.v1`; publication, public evidence, metadata, operator request, review reference
and work handoff have their own v1 schemas. Existing capsule and FusionPlan formats are unchanged. Imports
reject duplicate decoded keys, prototype keys, unsafe numbers, excessive depth and size. No archives are
decompressed. The compatible capsule remains below 250 KB; plaintext is capped early to account for base64,
complete proofs and authenticated header overhead. The kit limit is 2 MB.

The same project can be prepared without account permission. Only encrypted capsules and public references
are uploaded. Passphrases and storage tokens never enter URLs, journal, exports or unencrypted persistent
project storage. Clearing a JavaScript input is best effort, not secure erasure. The recovery kit intentionally
contains readable job specifications and public associations; disclose this before exporting it.

## Wallet and deployment boundaries

`MarkClient` remains the only transaction engine. `WalletSession` uses `RecoveryStore`, its original journal
key and atomic Web Lock. Existing MARK journals remain readable. New qualified profiles require an exact
match to the source-controlled `qualified-profiles.mjs` registry, a different schema and identity, runtime
digests, external dependency/proxy-slot identities, authority observations, permitted operations and
commissioning evidence. Canary entries additionally restrict actors/actions/amounts and may expire. Expiry
blocks new exposure while preserving explicitly permitted recovery. Runtime toggles, imported approvals,
JSON and wallet signatures cannot register a profile. The production registry is empty.

The test harness copies production modules to a temporary directory, builds a registry there for the
newly created unforked Hardhat chain 31337, and leaves production registry/assets unchanged. Fixture mutation
requires the existing `requireDisposableLocalNetwork` check, not merely a chain ID. The fixture RPC bridge
and wallet injector exist only in tests. Synthetic actors, mock ENS/token and local artifact HTTP service
are labelled throughout. This is neither an Ethereum fork nor a real participant commissioning trial.

Wallet writes bind the selected profile, provider epoch, sender, nonce, destination, calldata, zero ETH value,
simulation, bounded gas and expiring preview. Studio refreshes artifact/actor/phase/reviewer preconditions
before `MarkClient.confirm`. The receipt engine verifies submitted intent and canonical finality. Studio then
checks matching mint/route events and on-chain records. Smart-account envelopes are unsupported rather than
treated as direct calls. A same-nonce cancellation or replacement is distinct from original success.

| Deployment | Inspect | Existing recovery/obligations | New mint/funding/route |
|---|---|---|---|
| October 11 archive, Mainnet | Exact archived code/bindings | Allowed only when its actual contract conditions permit | Blocked |
| Unknown/imported/mixed profile | No trusted write context | Not accepted as a qualified profile | Blocked |
| Test-generated exact-source local profile | Tested local state | Tested with fixture actors | Tested; never shipped to production |
| Future canary/public Mainnet profile | Requires new reviewed registry entry | Explicit operation policy | Separately approved commissioning scope only |

Executable assets are local. Ethers 6.17.0 is copied byte-for-byte from the existing contract lock and retains
its license; a test checks identity. CSP permits scripts only from this origin and connects only to this
origin and the three specified storage endpoints. Wallet RPC stays in the selected injected provider. The
site's service worker excludes wallet and Studio routes/assets from its demo cache. A path is not an origin
security boundary: other same-origin scripts, extensions and compromised hosting remain relevant threats.
GitHub Pages meta CSP does not enforce header-only directives such as `frame-ancestors`.

## Executable checks and artifacts

Run from the repository root with the repository's pinned environments:

```sh
python -m scripts.build_mark_wallet
npm ci --prefix tests/contracts
npm ci --prefix tests/browser --ignore-scripts
python -m pip install --require-hashes -r requirements-agent.lock
node --test tests/mark-wallet/core.test.mjs tests/mark-wallet/recovery.test.mjs tests/mark-wallet/abi.test.mjs
node --test tests/nova-studio/core.test.mjs
python -m unittest discover -s tests/mark-wallet -p 'test_*.py' -v
npm test --prefix tests/contracts
python -m scripts.validate_mark_wallet --output evidence/mark-wallet
cd tests/contracts
NOVA_BROWSER=1 npx --no-install hardhat run scripts/nova-studio.js
```

The existing MARK workflow now also gates Nova's parity, package/storage and exact-source lifecycle/browser
checks. The parent Agent release acceptance already depends on that workflow; no release gate is removed.
The `nova-studio-acceptance` Actions artifact contains the exact-source report, source digests, explicitly local
transaction hashes, browser report, actual screenshots, sample recovery/work packages and result bytes.
Its `evidence-index.json` records the tested commit, exact local profile, source and artifact SHA-256 digests,
reproduction command and trials not performed. Existing generated/public MARK acceptance also fetches and
hashes the Studio route and every executable asset, binding publication to these exact tested bytes.
`studio-desktop.png` and `studio-mobile-fr.png` are captured from the real page, not design illustrations.
The commit/run identity comes from the Actions run; local reports alone do not prove a merged or published site.

## Handoff acceptance matrix

“Local” means tested against the actual current-source EVM or production browser code with the clearly
labelled test infrastructure above. It does not mean a mainnet fork, real validators or physical wallets.

| Cases | Evidence or remaining gate |
|---|---|
| 01 Preservation | Existing MARK/browser/contract tests; archive and Solidity unchanged; strict site build and normal release gates remain |
| 02 Shared foundation | Same client, journal key and Web Lock; existing MARK concurrency/recovery suite |
| 03 No-wallet start | Chromium creation/compilation/encryption/export with zero provider calls |
| 04 Wallet/network changes | Preserved MARK provider/epoch tests and real-browser injected-provider checks |
| 05 Profile policy | Empty production registry, archive denial, mixed qualified profile rejection, code/binding checks |
| 06–07 Identity/operators | Live-reader implementation, local ENS/admission, explicit operator handoff; real namespace/admission decisions external |
| 08–09 Compiler/bounds | Browser/JS/Python parity at 1,2,3,7,127,128; every corresponding leaf cross-checked with deployed Solidity; malformed bounds reject |
| 10–11 Encryption/commitments | Round trip, wrong passphrase, altered plan, randomized sealing, distinct hashes, complete-plan/base64 size tests |
| 12 Publication | Actual adapter and real local multipart/retrieval; live Pinata account and public-IPFS propagation trial **not performed** |
| 13–15 Mint/receipt/resume | Zero-value direct seal, exact event/readback, open existing receipt, kit recovery and lost-response reconciliation on local contracts |
| 16 Risk lifecycle | Local distinct signer review plus existing risk-contract tests; beneficial independence is an external prerequisite |
| 17–18 Funding | Exact curve quotes, separate approval/purchase, insufficient allowance and preserved interrupted-transaction tests |
| 19 Bloom | Explicit irreversible acknowledgement, real local phase transition and updated state |
| 20–21 Routing | Actual indexed proof/escrow/committee reads; duplicate index and duplicate reviewers rejected; current-source contract boundary suite |
| 22 Runtime truth | Versioned bound work package, no runtime-connected claim; actual native execution remains separately authorized |
| 23–24 Settlement/exits | Real local paid result, review, collection, closure, reclaim and approval revocation; existing contract rejection/timeout/accounting tests |
| 25–27 Uncertainty/concurrency/finality | Real local mint broadcast with deliberately lost response, reload and no resend; preserved MARK lock/replacement/reorg suite |
| 28 Ownership/successor | Current-owner reader, bounded Transfer discovery, explicit transfer and new-parent draft; larger-history/provider-limit field trials pending |
| 29 Recovery portability | Fresh-session import, frozen export snapshots, revalidation of latest transaction, initial pre-publication kit receipt recovery |
| 30 Hostile inputs | Duplicate/prototype/depth/size checks, unsafe storage refs, byte mismatch, malicious wallet metadata; no untrusted HTML |
| 31 Browsers/accessibility | Chromium EN/FR, keyboard, 1440/390/320 px and axe WCAG A/AA on all steps; human screen-reader and other browser trials **not performed** |
| 32 Physical wallets | Real injected-wallet extension, mobile wallet app and hardware-wallet trials **not performed** |
| 33 Complete vertical slice | Production state machine on actual local contracts; browser creation through settlement and recovery, separately labelled fixtures |
| 34 Authorized canary | **Not performed; no authorization to spend, deploy, admit or obtain genuine review was supplied** |
| 35 Launch/rollback | Archive restrictions remain; no public new-profile registry entry; normal independent review and release acceptance required |

## Commissioning and release gates

Independent reviewers must assess wallet/ABI boundaries, crypto/hash parity, deployment policy, recovery and
lifecycle accounting before merge/release. Passing tests is not that review. No independent audit or physical
wallet compatibility is claimed. Do not publish this as an operational mainnet launch merely because the page
builds or old contracts exist.

1. **Maintainer/reviewers:** review the exact PR head and run all existing/additional CI. Record findings and
   approve the smallest necessary shared-source edits. Verify the generated page and exact production assets.
2. **Storage operator:** exercise real public uploads/retrieval, two gateways and retention with a bounded,
   explicitly authorized account. Retain sanitized status/byte-hash evidence without API tokens.
3. **Wallet/accessibility testers:** test the actual declared injected-wallet extension, mobile-wallet route
   and hardware-wallet combination. Record versions, chain/account changes, rejection/backgrounding and
   device signing. Perform human keyboard/screen-reader/larger-text testing; axe alone is not WCAG certification.
4. **Deployment governance:** use the existing exact-build preparation/verifier for a separately authorized
   deployment. Bind verified source/runtime, dependencies and proxy authorities, genuine ENS/admission,
   reviewed token behaviour, pinned real-dependency fork evidence, responsible operators and allowed actions.
5. **Canary approvers and participants:** approve named wallets, time window, asset/amount limits and lifecycle
   before a canary registry entry is reviewed. Record actual consenting participants, receipts, settlement,
   token burn/refunds and balances. No UI checkbox can enable this stage.
6. **Public launch approvers:** review canary evidence separately before public activation. Preserve the old
   deployment records and eligible exits. Never redirect its immutable MARK binding to another job market.

The operator must monitor artifact availability, ENS/admission/review expiry, participant capacity,
job/auction/review deadlines, dependency/proxy/governance changes, uncertain broadcasts and refund obligations.
The static page is not a background keeper. Removing an entry point cannot pause contracts or reverse
transactions. Roll back the frontend through the existing release process while retaining recovery routes;
an unsafe new profile must lose new-exposure permission through reviewed policy, without erasing obligations.

Primary references: [EIP-1193](https://eips.ethereum.org/EIPS/eip-1193),
[EIP-6963](https://eips.ethereum.org/EIPS/eip-6963), [ethers v6](https://docs.ethers.org/v6/single-page/),
[Pinata API](https://github.com/PinataCloud/pinata/blob/main/ai-instructions),
[WCAG 2.2](https://www.w3.org/TR/WCAG22/). The locked repository artifacts remain authoritative for contract semantics.
