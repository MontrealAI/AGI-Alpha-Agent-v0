[Project notice](../DISCLAIMER_SNIPPET.md)

# Nova-Seed Mainnet Studio

[Open Studio](../ascension/mainnet/index.html) · [MARK wallet](MARK_WALLET.md) · [Engineering and acceptance](NOVA_SEED_STUDIO_ENGINEERING.md) · [Complete-cycle guide](ASCENSION_CYCLE.md)

Studio adds a guided browser journey to the existing Ascension Lab. It compiles the exact executable plan,
encrypts it, proves local recovery, publishes artifacts, prepares minting and carries the same seed into review,
MARK funding, activation, routing and settlement. Signing remains in your selected wallet. Opening Studio
does not connect a wallet, contact Ethereum, upload a project or request a signature.

**Deployment availability:** the recorded October 11 Mainnet profile permits inspection and eligible recovery;
new exposure remains blocked. No replacement Mainnet profile is approved in this build. The complete workflow
is exercised on a disposable exact-source local deployment with mock ENS/token dependencies and synthetic
participants. This implementation does not upgrade the immutable contracts or authorize public funding.
See the [deployment record](MAINNET_DEPLOYMENT.md) and [qualification checklist](MAINNET_READINESS.md).

## Create and recover

1. Describe your project privately. Add 1–128 jobs with a precise goal, objective acceptance criteria, maximum
   gross bounty, delivery duration in seconds and a price preference in basis points. Prices use exact
   18-decimal $AGIALPHA arithmetic. Job specifications become public when routed on-chain.
2. Compile the plan. Studio creates every indexed leaf and Merkle proof. It preserves your exact strings;
   changing a job changes the commitment. The committed budget is the sum of maximum gross bounties, including
   the contract-defined reviewer allocation. Ethereum gas is separate.
3. Choose a **capsule passphrase**, never a wallet recovery phrase. Studio includes the complete plan before
   encryption, then decrypts and verifies the result locally. Keep the passphrase separately. Once encrypted,
   that package stays frozen; make an explicit new version for edits.
4. Download the **Nova-Seed Recovery Kit**. It contains the encrypted capsule, readable exact plan/proofs,
   deployment identity, public evidence, references and available transaction records. It never includes your
   passphrase or wallet keys. The readable plan and address associations make the kit a private file.
5. To continue on another device, import the kit and enter its capsule passphrase in **Resume & recover**.
   Restore checks the checksum, commitments and encrypted plan. Imported transaction outcomes remain
   untrusted until reconciled against the chain. Nothing signs or uploads automatically.

Existing compatible encrypted capsules remain readable. Conversion of an old unminted capsule produces a
new package while preserving the original. A capsule without a committed on-chain plan cannot be relabelled
as ready to mint or attached to an already-minted NFT.

## Publish the exact package

Review the public fields before publication. The implemented adapter uploads three JSON files through
Pinata's public-IPFS API: the encrypted capsule, public verification evidence and immutable metadata. The
private project title/description and plaintext plan are not uploaded by this adapter. Metadata discloses
deployment identity, parent, plan root/count/budget, evidence and capsule references/hashes.

Use your own Pinata account and a token restricted to upload permissions. The token is held in the current
page, sent only to `https://uploads.pinata.cloud/v3/files`, then cleared from the input. It is not stored,
logged or exported. Check the provider's current prices, pinning limits and retention yourself. The software
does not purchase storage. Public-IPFS availability is not guaranteed by a CID; retain the exact files and
continue pinning them. Unpinning cannot recall copies others retained.

Studio retrieves and byte-checks every artifact through `gateway.pinata.cloud`; an explicit second-gateway
check also uses `ipfs.io`. Redirects, credentials in references, paths, query parameters, placeholders and
oversized responses are rejected. Advanced users can import existing immutable `ipfs://CID` references, but
the bytes must match the generated files including their final newline. Successful upload is retained through
an interrupted retry; retry does not re-encrypt the capsule. Export an updated kit after publication.

The adapter's production HTTP/multipart and integrity logic is tested against a real local HTTP artifact
service. **A live paid Pinata account/upload and independent public-IPFS propagation trial were not performed.**
This is a remaining operational acceptance item, not a claim that a local fixture is public publication.

## Wallet, identity and mint

Choose an injected wallet explicitly, then connect the account. Network switching is a separate action.
The deployment selector lists only the archived recovery profile and entries reviewed into this build.
Changing a selection never authorizes new funding or imports a deployment policy from a file.
Studio and MARK use the same wallet client, policy, recovery journal and Web Lock. Account, network or provider
changes cancel previews. No WalletConnect QR pairing, native USB/Bluetooth driver, smart-account batch or
account-abstraction receipt support is claimed.

For a business, Studio checks the registered `*.alpha.agi.eth` name, ENS ownership (including wrapped expiry),
admission evidence/expiry and `eligible(account, 0)`. The namespace administrator and current admission governor
are different roles; the operator export records the observed authorities. **Register name** records a name
already owned by the wallet. It neither purchases a name nor grants admission. An operator must perform any
genuine provisioning/admission separately. Funding-only participants follow the contract's admission rules
and do not need an unnecessary business name.

Mint preparation fills `seal(capsuleHash, planRoot, jobs, metadataURI, parent, evidenceHash)` from the verified
package. It rechecks publication, eligibility, parent ownership, profile and wallet context before signing.
There is **no $AGIALPHA mint fee or ERC-20 mint allowance** in this call; ETH value is zero and wallet gas is separate.
Studio accepts the new ID only from the matching finalized `SeedSealed` receipt and verifies the NFT's URI,
genome, plan and current owner. A returned hash is not confirmation. Existing seeds can be opened by ID or
verified mint receipt, without minting again.

## Review, fund and activate

The owner opens a review round. Separately connected eligible, staked validators recover and inspect the exact
artifacts through an authorized disclosure channel before attesting. The UI records findings and commits
their evidence hash; retain and share the actual findings with the participants. It cannot prove different
addresses have independent beneficial owners. Approval is read from current `green(seedId)` and explanatory
round/quorum/expiry reads, never a saved approval badge. Seven days runs from opening the round.

Open the same seed's MARK campaign with an exactly reachable target and bounded funding/execution windows.
A partial funding target does not fund the entire plan. An existing campaign is resumed, not reopened. Lots
are internal accounting units, not company shares, dividends or guaranteed returns.

Purchasing lots is **two explicit transactions**: bounded token approval and purchase. Recheck the current
quote and maximum cost after approval. Never transfer tokens directly to MARK. **Activate campaign (bloom)**
is another explicit action: it immediately ends curve trading/redemption and commits the reserve to the plan.
The UI explains this irreversible phase transition before opening the wallet.

Launch a job from the frozen plan. Studio supplies its specification, index and proof, checks the unposted
index, reserve and execution horizon, and checks three distinct reviewers' eligibility, stake, opt-in
availability and spare capacity. Capacity is reserved only by successful execution, not by the preview.
The matching `MissionRouted` receipt is checked against the resulting job, committee, business, escrow client
and specification. The escrow client is MARK, not the business wallet.

## Execute and settle

Export the versioned work package, exact `plan.json` and recovery kit. Follow the existing
[native Ascension guide](ASCENSION_PROTOCOL.md), [SUCCESSOR work guide](SUCCESSOR_WORK.md) and
[Computer Use authorization](SUCCESSOR_COMPUTER_USE.md). The work package carries chain/profile, seed/job,
specification/proof, acceptance, references and delivery requirements. It grants no runtime, network, spending
or signing authority. There is no authenticated browser-to-runtime connection in this version, and Studio
therefore says **No runtime connected**. Do not infer execution from a minted NFT, bloom or job posting.

The job controls support bids, award, exact result-file hashing, delivery, distinct reviewer votes and timeout.
Promise a delivery duration shorter than the committed job limit, leaving time for the award transaction.
An award processed too late can make otherwise valid bids ineligible and refund the job. Refresh the job
after processing the auction; only the actually awarded worker can deliver before its on-chain deadline.
Before delivery, Studio retrieves the immutable result URI and compares its actual bytes with the file
selected locally. Reviewers select that exact delivered file, record their findings and explicitly confirm
their independent review. Studio computes a deployment/seed/job/result-bound evidence hash and exports the
findings; reviewers do not need to calculate or paste a hash.
Keep the result bytes and evidence and publish them through the supported runtime/artifact process. Choose
**Native signed delivery** for an `ascension-deliver` envelope and supply its independently trusted Ed25519
public key. Studio verifies the signature over the original bytes, the plan root and committed job index,
then fills the native protocol's Keccak result hash. Its signature check does not replay the work or connect
a runtime; use `ascension-verify-delivery` for independent replay. Ordinary result files use the separately
labelled SHA-256 mode. Do not convert or reserialize signed native files before publication.
Match the observed job and result hash before voting. A terminal state observed in the latest block remains
unconfirmed until Studio verifies the same settlement at a canonical finalized block. The exact deployed
contract decides payout, burn, slashing or refund outcomes.

After a job terminates, collect its refund into MARK. Close the campaign only when allowed and reclaim unused
capital proportionally. Spent funding is not refundable principal. Funding-phase redemption remains possible
when the contract permits it despite expired admission/review. Concurrent bloom/close transactions can change
the available exit. Withdraw only unlocked stake and revoke unnecessary allowances. No administrator rescue
or automatic deadline keeper is implied.

Transferring a seed transfers its NFT, not its passphrase, legal/IP rights or existing campaign's business
authority. It may interrupt review, activation and routing. **Create successor** first exports the parent,
then makes a distinct draft referencing that parent; a new encrypted package and review are required.

## Interrupted transactions

Enable the disclosed public recovery journal before preparing a write. The exact public intent is stored
before opening the wallet. Working persistent storage and Web Locks are required to sign. A lock coordinates
the two workspaces on this origin/browser profile, not other devices or wallets.

If the request loses its response, reloads or backgrounds, the action remains unresolved. Obtain the original
or replacement hash from the wallet and reconcile. Studio checks sender, nonce, chain, exact input/value,
canonical receipt and finality. Cancellation and different replacement never count as execution of the
original intent. Missing or reorganized receipts remain unresolved. There is no blind retry/reset button.
Mint and route receipts also remain unresolved until their exact events and resulting records are verified.
An unsupported transaction envelope remains unresolved for investigation. An older transaction becoming
uncertain blocks further signing even if a newer transaction was previously confirmed.
After each confirmed transition, export an updated kit. Its checksum detects accidental alteration; it is
neither a signature nor independent evidence.

## En français

Créez le projet sans portefeuille, compilez les travaux, chiffrez le plan exact puis téléchargez le kit.
Gardez la phrase secrète séparément. Examinez les champs publics avant publication. Le jeton Pinata reste
limité à la session; les fichiers doivent être récupérés et leurs octets vérifiés avant la création du NFT.

Connectez ensuite le portefeuille approprié. L’identité ENS et l’admission sont distinctes. La création du NFT,
la revue indépendante, le financement, l’activation et la publication du premier travail sont des transitions
séparées. Chaque signature reste explicite. Un travail publié n’est pas un agent en marche, et une livraison
n’est pas encore un paiement accepté. Pour une transaction incertaine, réconciliez son empreinte; ne renvoyez
jamais automatiquement la même intention.

Les nouveaux engagements restent bloqués sur l’archive Mainnet du 11 octobre. L’interface fonctionne contre
un déploiement local des sources exactes; la qualification indépendante, les essais de portefeuilles physiques,
le stockage public et une mise en service Mainnet autorisée restent des étapes distinctes.
