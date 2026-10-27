# SPDX-License-Identifier: Apache-2.0
"""Read every frozen v3 stress result without selecting or rerunning cases."""
import csv
import json
from pathlib import Path

LABELS = {
 'lower_reference_4900': ('Human reference $4,900', 'Référence humaine de 4 900 $', 'Central condition; assumed complete-package reference reduced to $4,900.', 'Condition centrale; référence supposée du produit complet réduite à 4 900 $.'),
 'demand_downturn_one_arrival': ('One monthly opportunity', 'Une occasion mensuelle', 'Favorable condition; one new project opportunity per month, no arrival growth.', 'Condition favorable; une nouvelle occasion par mois, sans croissance.'),
 'zero_job_candidate_emergence': ('No emergent candidates', 'Aucun candidat émergent', 'Scans still cost resources; the probability of a candidate after a scan is zero.', 'Les examens consomment toujours des ressources; probabilité de candidat nulle après examen.'),
 'optional_research_disabled': ('Optional campaigns disabled', 'Campagnes facultatives désactivées', 'Additional paid-job retention remains available. Startup discovery remains charged.', 'La rétention issue des projets reste possible. La découverte initiale reste payante.'),
 'zero_alpha_mapping': ('No activity or quality benefit', 'Aucun gain d’activité ou de qualité', 'The assumed retained-Alpha activity and quality effect mappings are both zero.', 'Les effets supposés d’Alpha retenu sur l’activité et la qualité sont nuls.'),
 'cost_only_alpha': ('Activity savings test (confounded)', 'Test d’activité (effets confondus)', 'Realized quality effect is set to zero, but the recipient valuation omits that setting and retains a quality term. This frozen ablation is confounded and does not cleanly isolate activity savings. Activity savings can also affect throughput.', 'L’effet qualité réalisé est nul, mais la valeur du destinataire ignore ce réglage et garde un terme de qualité. Ce test figé comporte des effets confondus et n’isole pas proprement les économies d’activité. Ces économies peuvent aussi modifier le débit.'),
 'all_recipients_already_equivalent': ('All recipients have equivalents', 'Tous possèdent des équivalents', 'Every recipient initially has equivalent R and V capabilities.', 'Chaque destinataire possède initialement des capacités équivalentes R et V.'),
 'free_ordinary_reuse_across_agents': ('Free ordinary sharing baseline', 'Partage ordinaire gratuit sous Beta', 'Beta may share ordinary local artifacts across agents without the additional retained network package.', 'Beta peut partager les artefacts locaux ordinaires entre agents sans paquet de rétention supplémentaire.'),
 'static_beta': ('Fixed declared Beta epoch', 'Époque Beta déclarée fixe', 'The first Beta epoch persists; other maintenance, overlap and lifecycle assumptions remain.', 'La première époque Beta persiste; entretien, équivalence et autres hypothèses restent actifs.'),
 'rapid_beta_erosion': ('Faster Beta erosion', 'Érosion Beta accélérée', 'Assumed updates in months 1, 5, 9, 13, 17 and 21; reconstruction factor falls by 25% per epoch and monthly public-equivalent probability is 8%.', 'Mises à jour supposées aux mois 1, 5, 9, 13, 17 et 21; reconstruction diminuée de 25 % par époque et probabilité mensuelle d’équivalent public de 8 %.'),
 'fortyeight_recipients_same_compute': ('48 recipients, same compute', '48 destinataires, même calcul', 'Recipient diversity increases to 48 without increasing aggregate resource allowances.', 'Le nombre de destinataires atteint 48 sans hausse des ressources globales.'),
 'specialized_routing_same_compute': ('Specialized routing', 'Routage spécialisé', 'All routing uses the declared specialist rule; aggregate resource allowances are unchanged.', 'Tout le routage suit la règle spécialisée déclarée; ressources globales inchangées.'),
 'concentrated_compatible_scope': ('80% in one compatible domain', '80 % dans un domaine compatible', 'Domain weights become 80%, 5%, 5%, 5%, 5%.', 'Poids des domaines : 80 %, 5 %, 5 %, 5 %, 5 %.'),
 'validation_activity_double': ('Validation activity ×2', 'Activité de validation ×2', 'Declared validation, component evaluation and version-recheck quantities and resources double; official tariffs do not change.', 'Volumes et ressources de validation, évaluation et réévaluation de version doublés; tarifs officiels inchangés.'),
 'retention_activity_double': ('Retention activity ×2', 'Activité de rétention ×2', 'All incremental retention-option activity counts double.', 'Tous les volumes d’activité des options de rétention supplémentaire doublent.'),
 'strong_shared_errors': ('Stronger shared errors', 'Erreurs communes renforcées', 'Central condition; shared-fault probability 20%, conditional shared-fault miss probability 60%.', 'Condition centrale; défaut commun 20 %, non-détection conditionnelle du défaut commun 60 %.'),
 'authorization80_lag2': ('80% authorization, two-month lag', 'Autorisation de 80 %, délai de deux mois', 'Compound central stress: payment authorization probability 80% and collection lag two months.', 'Stress central composé : autorisation de paiement 80 % et encaissement après deux mois.'),
 'loose_capacity_cost_only': ('Looser capacity; quality effects retained', 'Capacité accrue; effets qualité conservés', 'Workbench and token allowances ×20. Quality effects remain active; this is not the activity-savings-only ablation.', 'Allocations de temps et de jetons ×20. Les effets qualité restent actifs; ce n’est pas le test des seules économies d’activité.'),
 'compound_static_beta_large_pool_recurrence': ('Joint capacity, diversity and demand condition', 'Condition conjointe capacité, diversité et demande', 'Exploratory compound condition: first Beta epoch, 48 recipients, 32 monthly opportunities without growth, resource allowances and control cost ×4.', 'Condition composée exploratoire : première époque Beta, 48 destinataires, 32 occasions mensuelles sans croissance, allocations de ressources et coût de contrôle ×4.'),
}


def normalize_stress(root: Path, primary_config_hash, primary_workflow_hash):
    path = root / 'results/paid_work_sensitivity'
    if not (path / 'run_manifest.json').exists():
        return {'complete':False, 'status':'Internal build: sensitivity execution is not complete.', 'cases':[]}
    manifest = json.loads((path / 'run_manifest.json').read_text())
    if manifest['base_config_sha256'] != primary_config_hash or manifest['base_workflow_costs_sha256'] != primary_workflow_hash:
        raise ValueError('Sensitivity base hashes differ from primary confirmation.')
    if not manifest.get('completed_at_utc'):
        raise ValueError('Sensitivity run manifest has no completion timestamp.')
    with (path / 'results.csv').open() as stream:
        csv_rows = list(csv.DictReader(stream))
    indexed = {row['name']:row for row in csv_rows}
    declared = [case['name'] for case in manifest['cases']]
    if len(csv_rows) != len(indexed) or set(indexed) != set(declared):
        raise ValueError('Sensitivity table must preserve every declared case exactly once.')
    output = []
    for frozen in manifest['cases']:
        name = frozen['name']
        result = json.loads((path / f'{name}_summary.json').read_text())
        if result['config_sha256'] != frozen['configuration_sha256'] or result['workflow_costs_sha256'] != frozen['workflow_costs_sha256']:
            raise ValueError(f'Sensitivity result identity mismatch: {name}')
        case = result['case']
        if case['name'] != name or case['scenario'] != frozen['scenario'] or case['compound'] != frozen['compound']:
            raise ValueError(f'Sensitivity case identity mismatch: {name}')
        for key,value in case.items():
            raw = indexed[name][key]
            if isinstance(value,bool):
                matches = raw.lower() == str(value).lower()
            elif isinstance(value,(float,int)):
                matches = abs(float(raw)-value) <= 1e-8 * max(1,abs(value))
            elif value is None:
                matches = raw in ('','None','null')
            else:
                matches = raw == value
            if not matches:
                raise ValueError(f'Sensitivity CSV/summary disagreement: {name}/{key}')
        if result['summary']['worlds'] != manifest['worlds_per_case']:
            raise ValueError(f'Incomplete sensitivity worlds: {name}')
        en,fr,en_description,fr_description = LABELS.get(name,(name,name,name,name))
        output.append({**case,'label_en':en,'label_fr':fr,'description_en':en_description,'description_fr':fr_description,
                       'paired':result['summary']['paired'],'config_sha256':result['config_sha256'],
                       'workflow_costs_sha256':result['workflow_costs_sha256'],
                       'source_summary':str((path / f'{name}_summary.json').relative_to(root))})
    return {'complete':True,'status':manifest['status'],'worlds_per_case':manifest['worlds_per_case'],
            'source_run':str(path.relative_to(root)),'manifest':manifest,'cases':output,
            'interpretation':'All declared cases retained. Compound conditions are exploratory. Frequencies are conditional model frequencies, not empirically calibrated commercial probabilities. Each network result is paired with competent Beta and private retention under that case.'}
