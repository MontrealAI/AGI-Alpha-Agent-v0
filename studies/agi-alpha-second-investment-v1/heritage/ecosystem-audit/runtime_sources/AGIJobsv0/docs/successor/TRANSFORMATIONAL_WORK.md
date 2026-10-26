# Native transformation campaigns and the AGIALPHA boundary

`integrations/alpha-agent/transformational-work-request.mjs` preserves Alpha's
`transformational-intelligence/v1` campaign as inert data. Alpha owns discovery,
the charter, formulation, transformation witness, evaluator and campaign history;
Fleet owns isolated execution and review. Jobs retains its separate **18-decimal
AGIALPHA** lifecycle. Manager's USDC route remains separate.

The current native version supports a free bounded source-understanding
comparison. Both currency allowances are zero. Jobs can inspect that campaign;
it refuses a positive AGIALPHA proposal. Positive-budget policy-double tests
exercise future market-boundary behavior only. They do not establish native paid
campaign support, authorize spending, or complete the paper's wider research
program.

## First steps — source preview

1. Open the [free Alpha TI workspace](https://montrealai.github.io/AGI-Alpha-Agent-v0/transformational-intelligence/).
   Start with public, non-personal material, compare the proposed methods and save your project.
   Follow the workspace’s separate local instructions when you need a native result.
2. Continue **the same saved project** with the [Fleet project guide](https://github.com/MontrealAI/AGI-Fleet-Linux/blob/main/docs/transformational-project.md).
   Preserve its identifier, original files and complete request, result and review history.
3. Jobs can inspect that native campaign as inert evidence. Both native currency caps are zero.
   Jobs refuses positive AGIALPHA proposals; Manager’s USDC route stays separate. The free comparison needs no payment;
   importing a project does not commission work or authorize execution.

This remains a source preview until the final compatible release set is qualified.
Check the guides and evidence supplied with the versions you actually use.

## Premiers pas — aperçu des sources

1. Ouvrez l’[espace Alpha TI gratuit](https://montrealai.github.io/AGI-Alpha-Agent-v0/transformational-intelligence/).
   Choisissez des données publiques non personnelles, comparez les méthodes proposées et enregistrez votre projet.
   Pour un résultat natif, suivez les instructions locales distinctes présentées dans cet espace.
2. Poursuivez **le même projet enregistré** avec le [guide Fleet](https://github.com/MontrealAI/AGI-Fleet-Linux/blob/main/docs/transformational-project.md).
   Conservez son identifiant, les fichiers d’origine et tout l’historique des demandes, résultats et revues.
3. Jobs peut inspecter cette campagne native comme preuve inerte. Les deux plafonds monétaires natifs sont zéro.
   Jobs refuse les propositions AGIALPHA positives; le parcours USDC de Manager reste distinct.
   La comparaison gratuite n’exige aucun paiement.
   Importer un projet ne commande aucun travail et ne donne aucune permission d’exécution.

Il s’agit d’un aperçu des sources, en attendant la qualification des versions compatibles.
Consultez les guides et les preuves fournis avec les versions réellement utilisées.

The specification is the owner's attached manuscript, with exact SHA-256 inputs:

| Input                                  | SHA-256                                                            |
| -------------------------------------- | ------------------------------------------------------------------ |
| `Transformational_Intelligence(2).pdf` | `d7170e8217e3bf6aa1b84868c1c76c5994c6995c5297ed092d7e72a6430c664f` |
| `Transformational_Intelligence(2).tex` | `9d4a664d951d6b97f5136bf0b44f1ca458e90d585434a6a27a542694bb2ece5f` |

## Installed interfaces

```js
const campaign = await inspectTransformationWorkRequest(campaignRaw, {
  expectedBindingsDigest,
  inspectWorkRequest,
});
```

`inspectWorkRequest` must be the installed, reviewed native Alpha
`inspectTransformationEnvelope` function from the compatible source set. It must
return the complete validated campaign, not an `accepted: true` verdict. Imported
data cannot select or install an inspector. Native object commitments use Alpha's
existing canonical encoding and domain separation, preserving its Unicode and
integer semantics. `expectedBindingsDigest` comes from the consuming runtime's
independently frozen code, model, configuration and evidence context. Copying it
from an untrusted import would defeat the freshness check. Native object digests
are plain 64-digit hex; Jobs byte identities have the explicit `sha256:` prefix.

The adapter requires public-only charter data and refuses recognized credentials,
decoded credential-bearing JSON fields, private-address patterns and duplicate
keys before native inspection. Quoted or Unicode-escaped configuration keys
cannot bypass the credential-field screen. These
checks supplement operator source-rights review; they do not certify arbitrary
content as public, truthful or non-personal.

This bounded intake admits credential-free HTTPS references on default port 443
to DNS names; literal IPv4/IPv6 addresses, alternate numeric IP encodings, local
pseudo-domains, fragments, credential query fields and other ports are refused before the
native callback. Public IP literals are also outside this profile. DNS names are
not resolved or fetched here; source rights and network admission remain separate
runtime checks. Native inert authorization metadata and the draft's fixed public
AGIALPHA token address and exact public authorization-commitment digest have
explicit structural exceptions; a generic token or
authorization string is not admitted as public campaign data.
Credential families are conservatively matched within normalized field names,
including header/provider prefixes and token suffixes; public computational
`tokens` budgets remain distinct from credential-shaped `token` fields.

A future separately reviewed native charter with a positive AGIALPHA allowance
can be presented to the conditional proposal interface:

```js
const draftRaw = await createTransformationWorkDraft(campaignRaw, {
  amountBaseUnits: '1000000000000000000',
  createdAt: '2026-10-19T15:00:00.000Z',
  expectedBindingsDigest,
  inspectWorkRequest,
});
const draft = await inspectTransformationWorkDraft(draftRaw, {
  expectedBindingsDigest,
  inspectWorkRequest,
});
```

One AGIALPHA is `1000000000000000000` base units. The positive proposal must fit
the explicit `charter.budgets.AGIALPHABaseUnits` cap and the existing 96-bit reward
bound. Both charter and settlement routes must say `AGIALPHA`. No USDC, dollar
quote, generic money unit or observed expense is converted. Material changes
require a newly authorized native charter and comparison basis; this adapter
makes no such amendment.

The draft binds the exact original UTF-8 campaign bytes, charter, formulation,
witness, instrument, measurement epoch, runtime and local authorization binding,
plus the actual adapter and canonical-data-policy source bytes. Its specification
commitment fits the registry's `createJob(uint256,uint64,bytes32,string)` interface.
Deployment, deadline, URI and transaction remain unset. This is a specification
proposal, not a compiled job graph or dispatched work.

Every output has zero reserved funds, no execution or settlement authority,
independent review required, no authenticated computer execution and no production
approval. Reinspection reconstructs the entire draft. Recomputing an outer hash
cannot authorize changed budgets, source identities, authority or measurement
fields. Hashes bind bytes; they do not establish truth, independence or trustworthy
freeze timing.

## Reproduction and scope

Use the repository's pinned Node **22.23.3**:

```bash
node --test test/pages/transformational-work-request.test.mjs
node test/pages/transformational-native.mjs /absolute/reviewed/alpha-checkout /absolute/reviewed/free-campaign.json
```

The regular `npm run site:test` runs the policy regressions. Their simplified
native-inspector double is explicitly labeled. The second command uses Alpha's
real inspector and a complete free campaign. It checks inert inspection, refusal
of positive AGIALPHA work, stale-context rejection and authority-expansion
rejection. Its expected context comes from a reviewed test artifact; this is not
presented as a production freshness mechanism or pinned mixed-version evidence.

| Paper requirement                                    | Implementation and test                                                        | Supported scope / limitation                                                |
| ---------------------------------------------------- | ------------------------------------------------------------------------------ | --------------------------------------------------------------------------- |
| Distinct charter, formulation, evaluator and package | Native inspection, object commitments and epoch binding; altered-object tests  | Full semantic validation remains with the installed native inspector        |
| Permission before execution                          | Inert proposal, zero reservation, no deployment or transaction; mutation tests | No campaign execution or paid commissioning occurs                          |
| Whole-life resource accounting                       | Separate AGIALPHA cap and proposed payout; integer and exhaustion tests        | Model, verification, maintenance, gas and human costs are not measured here |
| Frozen comparisons and revised measurement           | Runtime binding and measurement epoch; stale-context and epoch-tamper tests    | Independent process and calibration evidence remain necessary in Alpha      |
| Reusable successor history                           | Complete original retained; deterministic reinspection                         | No automatic promotion, restoration of authority or archive-routing claim   |

For recovery, retain the original campaign and proposal unchanged. Reinspect
against the installed native validator and current frozen context. Create a newly
authorized campaign revision when material terms change. The adapter performs no
persistence, network request, reservation or external action; interruption leaves
no partial commissioned job.

Existing deployments, flowcharts, historical records, ENS and governance remain
unchanged. Initial creation remains Hardhat on Ubuntu with local hidden ephemeral
deployer-key entry; governance remains the owner's Ledger on Mac Studio. Never
store or print keys in arguments, `.env`, history, logs or artifacts. No Mainnet
deployment, signing, funding, approval, activation or authority change is included.

## Français

Cet adaptateur conserve la campagne Alpha complète comme donnée inerte. Le
parcours natif actuel est gratuit : ses deux plafonds monétaires sont zéro et
une proposition AGIALPHA positive est refusée. Une future charte explicitement
autorisée devra préciser son propre plafond **AGIALPHA à 18 décimales**; aucun
montant USDC ne sera converti. L'importation revérifie les objets, le contexte
figé et l'époque de mesure. Elle ne donne aucune permission d'exécution, de
dépense, de signature ou de règlement et ne crée aucune revue indépendante.
