# MARK Mainnet Wallet

[Open the wallet workspace](../ascension-protocol/mainnet/index.html) · [Original local demonstration](../ascension-protocol/index.html) · [Recorded deployment](MAINNET_DEPLOYMENT.md)

The Protocol Desk now has an additive **Ethereum Mainnet wallet workspace**, separate from its unchanged local-EVM demonstration. It reads the five recorded October 11, 2026 contracts and can request real transactions through an injected EIP-1193 wallet. The wallet keeps custody and signing. No key, seed phrase, transaction broadcast or account permission request occurs merely by opening the page.

## What this version permits

The interface implements inputs and ABI encoding for MARK's `open`, `buy`, `sell`, `transferLots`, `bloom`, `route`, `collect`, `close` and `reclaim`; bounded token approval; existing ENS-role registration; seed sealing; risk review; staking; reviewer availability; job bidding, award, delivery, validation, timeout and refunds.

**New exposure is intentionally blocked for the archived deployment.** This includes buying lots, nonzero token approvals, deposits, new seeds/campaigns, new risk approval, bids and new job routing. The recorded contracts lack newer settlement safeguards and have not been commissioned for public funding. The checked deployment profile always carries `newExposureEnabled: false`; the browser rejects an enabled or unknown profile. There is no URL parameter, localStorage flag, imported approval file, wallet signature or checkbox that bypasses this boundary. Enabling a separately reviewed deployment requires a subsequent reviewed implementation/configuration change and its evidence—not altering this archive or pretending a release upgraded it.

This is **not a read-only mock**: recovery actions and actions needed to complete existing obligations can prepare and send real transactions when the exact deployed contract permits them. They include redeeming funding-phase lots, collecting terminal-job refunds, closing eligible campaigns, reclaiming remaining capital, withdrawing unlocked stake, setting a protocol allowance to zero, revoking future review availability, and processing existing jobs. Job award, validation and timeout can have financial consequences, including worker slashing; they are not harmless housekeeping.

## First use

1. Open the wallet workspace in a compatible wallet browser or a browser with an injected wallet. WalletConnect QR pairing and direct USB/Bluetooth hardware-wallet drivers are not implemented. A hardware wallet can sign through a compatible injected wallet; physical-device compatibility is not established by automated tests.
2. Choose the wallet. Use **Verify deployment and inspect** without requesting account permission, or **Connect account** to expose an account deliberately. The wallet must be on Ethereum Mainnet, chain ID 1. Network switching is a separate explicit button.
3. Enter an existing Nova-Seed ID and/or job ID, then inspect. No counter is assumed to be zero. Contract bytecode and immutable/one-time bindings are checked at a named block; failed RPC reads remain failures, not empty campaigns.
4. Select an action. Human token fields accept exact decimal $AGIALPHA amounts. Durations and Unix timestamps are seconds. The advanced route form takes the exact five-field FusionPlan specification, a JSON Merkle-proof array and three reviewer addresses; its bounty is in 18-decimal integer base units. Use the existing FusionPlan compiler rather than hand-authoring a root or proof.
5. Choose **Prepare and simulate**, inspect sender, destination, calldata, arguments and consequences, then acknowledge **this exact action**. Choose **Confirm in my wallet**, and review the wallet's own final transaction/fee display. The page rechecks account, chain, bytecode, bindings, simulation and gas before requesting a signature. A preview expires after 60 seconds.
6. Refresh the receipt. Submitted, mined, reverted and finalized are distinct states. A returned hash is not successful payment. Export the observation and transaction journal before leaving. Journals contain public transaction data and are kept in memory, not silently persisted or uploaded.

The ENS namespaces remain distinct: businesses use `*.alpha.agi.eth`, agents use `*.alpha.agent.agi.eth`, and validators use `*.alpha.club.agi.eth`. Registering an existing label neither creates a name nor grants admission. Funding-only participation requires admission but does not acquire an unnecessary role-name requirement. This wallet does not impersonate an owner, set admission policy or fabricate independent review.

## Funding and recovery semantics

Before bloom, `sell` can remain available despite admission revocation or risk-review expiry. Do not apply the new-funding gate to this exit path. After the funding deadline, an unclosed Funding campaign can still permit selling; a concurrent `close` changes the claim to a proportional Closed-campaign claim. A competing `bloom` also ends redemption. Simulation does not eliminate transaction-ordering risk.

Bloom ends trading and curve redemption immediately, not only when the funding deadline arrives. Campaign lots are internal funding-accounting units, not an ERC-20, company equity, dividends or a promise of profit. Unused capital is reclaimed proportionally after closure. Spent funding is not refundable principal. MARK-originated job refunds must be collected into MARK before closure; the business wallet is not the recorded escrow client. There is no administrative withdrawal, global pause, proxy upgrade, arbitrary rescue, or automatic migration.

Never transfer $AGIALPHA directly to MARK. Purchases require a bounded token approval followed by the contract's `buy` action. A direct ERC-20 transfer does not credit campaign lots or reserve accounting. This deployment uses the canonical $AGIALPHA token, not USDC, and its fixed AscensionJobMarket—not AGIJobsv0 or AGIJobManager.

## Verification and signing boundaries

The build derives SHA-256 bytecode digests from the unchanged archived runtimes. In the browser, Web Crypto compares the exact bytes returned at the observed block against those digests; this is byte-identity verification, not a replacement Ethereum hash algorithm. Conformance tests also cross-check those archived runtimes against the manifest's Ethereum Keccak-256 digests. Bindings and token decimals are read back. Observation records explicitly say that external token/ENS dependencies have not been independently reviewed. The provider may be wrong or malicious; use the repository's read-only record verifier and a second independent provider for operational qualification.

RPC requests are restricted to documented reads plus a separately requested wallet connection, explicit network switch and a single confirmed transaction. No generic transaction editor, arbitrary destination, permit, unlimited-approval shortcut, automatic signing, hidden retry, external dependency CDN, external metadata fetch, private-key import or AI wallet control is included. Provider names are untrusted text; supplied SVG/icons are not rendered. Chain/account/provider changes invalidate pending previews. A disconnected page does not revoke the extension's account permission.

The interface exposes advanced fields rather than claiming to be a complete nontechnical campaign-creation service. It does not generate a Nova-Seed capsule, recruit reviewers, run an AI agent, host deliverables, provision ENS names, or settle a separate marketplace. Existing tools perform those jobs and remain available.

If a signing request's outcome is unknown, check the wallet and explorer before doing anything else. The app never retries automatically and blocks additional actions in that session. A replacement or cancellation must be reconciled outside this first-version journal; it is not falsely reported as a successful original transaction. Export evidence before closing the page. No background keeper or automatic deadline processing is provided.

## Build and test

From a checkout of this change:

```sh
python -m scripts.build_mark_wallet
node --test tests/mark-wallet/core.test.mjs
npm ci --prefix tests/contracts
node --test tests/mark-wallet/abi.test.mjs
python -m unittest discover -s tests/mark-wallet -p test_build.py -v
python -m http.server 8000 --directory docs
```

The new page is at `/ascension-protocol/mainnet/` on the local server. Normal MkDocs builds generate the profile through the existing `scripts/mkdocs_assets.py` hook. Building never changes the deployment archive, current Solidity, compiler settings, existing local-EVM receipt or wallet state. Serve the generated files; opening the HTML directly with `file://` is not supported. Without a valid profile the page fails closed.

Automated codec/provider tests are not a real hardware-wallet trial, independent audit, observed mainnet settlement, or approval to open public funding. The targeted workflow retains test reports; existing release acceptance remains in force. A code review/merge and the normal Pages deployment are still necessary before the new route exists on the public website.

## En français

Le Protocol Desk conserve sa démonstration locale et ajoute un **espace portefeuille Mainnet réel**. Choisissez un portefeuille, vérifiez les contrats, préparez une action, examinez-la puis signez uniquement dans votre portefeuille. Les montants sont en $AGIALPHA avec 18 décimales; les frais réseau sont en ETH.

Les nouveaux engagements restent bloqués pour le déploiement archivé. Les récupérations admissibles et le traitement des obligations existantes peuvent envoyer de vraies transactions. La validation ou un dépassement de délai peut provoquer un paiement ou une confiscation de mise. Vérifiez les effets exacts avant de signer. Une empreinte de transaction envoyée n’est pas une preuve de réussite. Exportez votre journal avant de quitter et réconciliez toute transaction incertaine avant de réessayer.

La documentation et les avertissements du déploiement du 11 octobre restent applicables. Une publication GitHub n’installe aucune correction sur les contrats immuables. Aucun portefeuille, mécanisme de test ou case de confirmation ne remplace l’examen indépendant et la mise en service.

## Primary technical references

- EIP-1193, Ethereum Provider JavaScript API: https://eips.ethereum.org/EIPS/eip-1193
- EIP-6963, multi-injected wallet discovery: https://eips.ethereum.org/EIPS/eip-6963
- Solidity ABI specification: https://docs.soliditylang.org/en/latest/abi-spec.html
- The repository's archived deployment sources and compiler artifacts under `deployments/ethereum-mainnet/2026-10-11/`.
