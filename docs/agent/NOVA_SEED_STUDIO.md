[Project notice](../DISCLAIMER_SNIPPET.md)

# Nova-Seed Studio

[Open the Studio](../ascension/mainnet/index.html) · [Ascension Lab](../ascension/index.html) ·
[MARK wallet](../ascension-protocol/mainnet/index.html)

Nova-Seed Studio brings project preparation and the Ascension contract lifecycle into one browser journey.
A capsule is an encrypted project file. Minting records that file's commitments in a Nova-Seed NFT.
Independent review, funding, campaign activation and job execution are separate steps with separate actors.

**Deployment status:** the public build retains the October 11, 2026 deployment's restrictions on new exposure.
That deployment is immutable and predates later settlement safeguards. Preparing a project does not require
a wallet. A local exact-source rehearsal does not spend mainnet funds. No new mainnet deployment or public
funding approval is supplied by installing this frontend.

The [acceptance record](NOVA_SEED_STUDIO_ACCEPTANCE.md) identifies tested behavior and remaining gates.
The [commissioning guide](NOVA_SEED_STUDIO_COMMISSIONING.md) explains who can clear deployment prerequisites.

Actual interface captures are retained with the
[acceptance run artifacts](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/actions/workflows/nova-studio.yml).
`studio-protected.png` shows local preparation with synthetic project data and no connected wallet. It is
evidence of the implemented interface, not a live-mainnet mint, receipt or funding record.

## Prepare a project

1. Describe the project and define its jobs. Give each job a concrete goal, objective acceptance criteria,
   maximum bounty, work duration and price/time preference. Values use **$AGIALPHA**, with 18 decimals.
   Ethereum transaction fees use **ETH**. This is the Ascension protocol, not the USDC-based AGIJobManager.
2. Compile the plan. The browser creates indexed commitments and Merkle proofs from the exact specifications.
   Changes to a specification change the commitment. Review the total budget before freezing the package.
3. Choose a private capsule passphrase and seal the project. This is **not your wallet recovery phrase**.
   The exact compiled plan is inside the encrypted capsule. Keep the generated file; resealing creates a
   different capsule and therefore a different mint commitment even when the project text is unchanged.
4. Test recovery by opening the same sealed capsule. Export the recovery kit and keep the passphrase separately.
   A checksum helps detect changed files; it is not a signature, independent review or backup service.
5. Review the public artifacts before publication. Job specifications, plan/proofs, evidence, metadata and
   blockchain actions can expose project information. The capsule encrypts its contents; it does not make
   public evidence, routed job text, wallet addresses or transactions private.

Opening the page does not connect a wallet or request a signature. Capsule passphrases and decrypted project
text belong in the current session, not URLs, transaction journals or published metadata. An exported recovery
kit contains public plan information as well as the encrypted capsule; store it according to that disclosure.

## Before minting

Publication must return usable references and the app must retrieve and verify the actual bytes. Saving a file
locally is not publication. A content-addressed reference identifies content; it does not guarantee that someone
will keep hosting it. Retain an independent copy and the storage provider's retention information.

Choose a wallet explicitly, connect its account and check the displayed network and deployment. A business
uses an owned, registered `<label>.alpha.agi.eth` name and a current admission decision. Registration records
an existing name; it does not buy or create the name. Holding tokens, owning an unrelated ENS name or owning
an NFT does not grant business eligibility. The namespace owner and admission authority remain distinct actors.

The deployment selector lists only profiles registered in the reviewed build. A recovery file identifies its
deployment; importing it cannot authorize another deployment or enable mainnet spending. Qualification renewal
does not change an existing capsule's deployment identity, but a different address or code identity does.

The app must report an unavailable action with its reason. The archived profile's blocked new minting cannot
be cleared by a checkbox, imported file or wallet connection. A separately reviewed profile, exact-source
evidence and the appropriate operator authorization are required for a new mainnet offering.

For an authorized profile, the mint transaction calls `NovaSeed.seal` with the verified capsule hash, plan root,
job count, metadata URI, optional parent and evidence hash. **There is no $AGIALPHA mint fee or token approval
in this function.** The transaction sends zero ETH value; the wallet separately quotes network gas.
Review the exact account, contract, action and artifacts before confirming in the wallet.

The seed ID comes from the matching `SeedSealed` event and checked on-chain state, never a predicted counter.
A returned transaction hash means the transaction needs reconciliation. It does not prove that the NFT exists.

## Continue from the verified seed

| Step | Responsible participant | What completion means |
| --- | --- | --- |
| Independent risk review | Owner and separate eligible validators | Green, unexpired on-chain review |
| Open campaign | Eligible business and seed owner | Recorded campaign with reviewed funding parameters |
| Fund campaign | Admitted funding participant | Explicit allowance, purchase receipt and recorded lots/reserve agree |
| Activate (`bloom`) | Campaign business and seed owner | Execution phase; curve trading/redemption ended |
| Launch planned job | Authorized campaign business | Exact specification/proof and verified escrowed job |
| Execute and deliver | Awarded worker and authorized runtime | Actual submitted result commitment |
| Review and settle | Selected eligible reviewers | Verified outcome and reconciled balances |

Risk review has a deadline and a real quorum. Different addresses alone do not prove that reviewers are
independent people or organizations. The interface cannot manufacture admission, votes, stakes or availability.
Funding-only participants need the admission that the contract requires; they do not need an unnecessary
business-role registration.

Campaign lots are internal accounting units. They are not company shares, an ERC-20 or a promise of profit.
Use the explicit approval and purchase actions; **never transfer tokens directly to MARK**. A direct transfer
does not create lots or credit campaign reserve. If an approval succeeds but a purchase fails, inspect the
remaining allowance and current quote before deciding whether to purchase or revoke it.

The full plan budget and campaign target can differ. Reaching a partial target does not fund every job.
Activation ends curve redemption immediately. Once activated, job routing still requires the exact plan proof,
available reserve, a sufficient execution horizon and three real reviewers with suitable capacity and opt-in.
A preview does not reserve reviewers or prevent another transaction from changing the state.

An NFT, activated campaign or posted job is not a running AI agent. Runtime credentials, model access, computer
use and spending limits are configured separately. A work handoff carries a job's identity and requirements;
it neither gives the runtime wallet custody nor proves that work has started or been accepted.

## Resume after an interruption

Keep your recovery kit and transaction journal. Restore them, choose a provider and refresh the chain state
before continuing. Import is a read/validation operation and must not open a wallet signing request.
An existing NFT requires matching artifacts; a new plan cannot be attached to an old immutable commitment.

If the wallet response is lost, **do not send the action again**. The journal records the intent before the
wallet opens. Obtain the actual transaction hash from the wallet and reconcile it. The app checks the sender,
nonce, destination, arguments, value, receipt and canonical block. An unknown response remains unresolved.
A same-nonce cancellation or different replacement is not completion of the original action.

Two Studio/MARK tabs share a lock and journal within one browser profile. This does not coordinate a second
device, other wallet software or another browser profile. Finish and reconcile the action on one device before
moving to another. Export before clearing site data; a lost local journal cannot be reconstructed from a
passphrase alone. A browser without working durable storage and Web Locks can inspect but cannot safely sign.

Ownership also needs a fresh check. Transferring an NFT does not transfer its passphrase, all legal/IP rights,
or the original campaign's business authority. A successor is a new seed with its own commitments and review;
it does not mutate the parent or inherit green approval.

## Exit and recover funds

Use the [MARK wallet](MARK_WALLET.md) for the selected deployment's permitted completion and recovery actions.
Before activation, funding-phase redemption can remain possible after admission or review expiry when the
contract allows it. A competing activation or closure can change that right before your transaction lands.

For a MARK-funded job, collect its refund into MARK before eligible campaign closure. Then unused remaining
capital can be reclaimed proportionally. Spent funds are not refundable principal. Withdraw only unlocked
stake and revoke unnecessary allowances. Award, negative review and timeout can affect another participant's
funds; read the exact consequences. No administrator can pause the immutable suite or rescue arbitrary funds.

## En français

Préparez le projet et ses tâches, compilez le plan, chiffrez la capsule puis vérifiez sa récupération.
Conservez le kit et la phrase secrète séparément. La phrase de la capsule n'est jamais celle du portefeuille.
Les montants du protocole sont en **$AGIALPHA**; les frais réseau sont en **ETH**.

La création du NFT, l'examen indépendant, le financement, l'activation et le lancement d'une tâche sont des
étapes distinctes. L'activation termine immédiatement les échanges et le rachat sur la courbe. Une tâche
publiée ne signifie pas qu'un agent est connecté ou que le résultat a été accepté.

Les nouveaux engagements demeurent bloqués pour le déploiement archivé du 11 octobre. Une nouvelle version
du site ne modifie pas ses contrats. Si le résultat d'une signature est incertain, conservez le journal et
vérifiez la transaction réelle avant toute autre action. Le kit contient aussi des informations publiques du
plan; le chiffrement de la capsule ne rend pas les transactions et les descriptions de tâches privées.

Le fichier `studio-fr-320.png`, conservé dans les artefacts de validation ci-dessus, montre l'interface réelle
en français à 320 pixels, avec des données fictives et sans portefeuille. Ce contrôle de mise en page ne
constitue pas un essai sur téléphone physique ni une transaction mainnet.

Voir aussi : [formats et modèle de sécurité](NOVA_SEED_STUDIO_TECHNICAL.md),
[récupération et mise en service](NOVA_SEED_STUDIO_COMMISSIONING.md).
