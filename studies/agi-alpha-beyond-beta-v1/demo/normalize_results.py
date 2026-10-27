# SPDX-License-Identifier: Apache-2.0
"""Display-only normalization of the paid-work, retained-Alpha simulation.

This adapter neither reruns worlds nor optimizes prices. It preserves paired worlds,
all-world pooled cost/error denominators, and explicitly selected illustrations.
"""
import argparse
import csv
import gzip
import hashlib
import json
import pathlib
import statistics
from stress_view import normalize_stress

ROOT = pathlib.Path(__file__).resolve().parents[1]
POLICIES = ('optimized_beta', 'optimized_private', 'optimized_network', 'fixed_network')
BASELINE = 'optimized_beta'
FOCUS = 'optimized_network'


def sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def number(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def qstats(values):
    values = sorted(v for v in values if v is not None)
    if not values:
        return dict.fromkeys(('mean', 'median', 'p05', 'p95'))
    def quantile(q):
        position = (len(values) - 1) * q
        low = int(position)
        high = min(low + 1, len(values) - 1)
        return values[low] + (values[high] - values[low]) * (position - low)
    return {'mean': statistics.mean(values), 'median': quantile(.5), 'p05': quantile(.05), 'p95': quantile(.95)}


def series(rows, key):
    return [number(row.get(key)) for row in rows]


def average(rows, key):
    values = [v for v in series(rows, key) if v is not None]
    return statistics.mean(values) if values else None


def paired_stats(rows, reference, key):
    return qstats([number(row[key]) - number(reference[int(row['world'])][key]) for row in rows])


def enrich_ledger(record, policy, config, scenario):
    ledger = []
    for row in record['ledger']:
        action = row.get('research_action', 'retain')
        if action.startswith('retain_'):
            action = action.removeprefix('retain_')
        elif action.startswith('research_'):
            action = action.removeprefix('research_')
        decision = ('invest_' + action if action in ('R', 'V', 'bundle') else
                    'wait' if row.get('research_progress_fraction') is not None else 'retain')
        reason_en = 'The recorded forecast and reserve constraint justify this candidate under the assumed model.'
        reason_fr = 'La prévision enregistrée et les réserves justifient ce candidat selon le modèle supposé.'
        if decision == 'wait':
            reason_en = 'A paid research campaign consumes finite resources before evidence assessment and admission.'
            reason_fr = 'Une campagne payante consomme des ressources finies avant évaluation des preuves et admission.'
        elif decision == 'retain':
            reason_en = 'No further eligible affordable candidate is selected by the declared policy; retain cash.'
            reason_fr = 'Aucun autre candidat admissible et finançable n’est choisi par la politique; conserver la trésorerie.'
        if policy == BASELINE:
            reason_en = 'Competent Beta can reconstruct and use existing equivalents; new retained research is disabled in this paired comparison.'
            reason_fr = 'Beta compétent peut reconstruire et utiliser les équivalents existants; la nouvelle recherche retenue est désactivée dans cette comparaison.'
        if row.get('unpaid_obligations', 0) > 0:
            reason_en = 'Unpaid obligations halt new operating activity.'
            reason_fr = 'Les obligations impayées arrêtent les nouvelles opérations.'
        if row['month'] > config['months']:
            reason_en = 'The operating horizon has ended; collections and obligations run off.'
            reason_fr = 'L’horizon d’exploitation est terminé; encaissements et obligations restants sont réglés.'
        grid = [{'fraction': point['fraction'], 'price': scenario['human_reference'] * point['fraction'],
                 'objective': point['expected_monthly_net'], 'adoption': point['expected_adoption'],
                 'expected_started_projects': point['expected_started_projects']} for point in row['price_curve']]
        ledger.append({**row, 'available': row['available_uncommitted_cash'],
                       'operating_cash': row['retained_operating_cash_above_seed'], 'decision': decision,
                       'reason_en': reason_en, 'reason_fr': reason_fr, 'price_grid': grid})
    return ledger


def investments(record):
    events = []
    for event in record['events']:
        if event.get('kind') not in ('research_purchase', 'retention_purchase'):
            continue
        completion = next((x for x in record['events'] if x.get('kind') == 'research_complete'
                           and x.get('action') == event.get('action') and (not event.get('id') or x.get('id') == event['id']) and x['month'] >= event['month']), None)
        events.append({'asset': event['action'], 'ledger_class': event.get('ledger', 'C' if event['kind'] == 'research_purchase' else 'B'), 'origin_job_id': event.get('origin', {}).get('job_id'), 'month': event['month'], 'cost': event['bill'],
                       'seed_funded': event['seed_funded'], 'operating_funded': event['operating_funded'],
                       'expected_gain': event['expected_incremental_terminal_cash'],
                       'cash_after': event.get('cash_after_purchase', event.get('cash_after')), 'reserve': event['reserve'],
                       'estimated_build_months': event['estimated_build_months'],
                       'actual_build_months': completion['actual_build_months'] if completion else None,
                       'status_en': f"Completed in month {completion['month']}" if completion else 'Unfinished at horizon',
                       'status_fr': f"Terminé au mois {completion['month']}" if completion else 'Inachevé à la fin',
                       'raw_event': event})
    return events


def illustrate(record, baseline, policy, config, scenario, selected=False):
    world = record['world']
    metrics = record['metrics']
    seed = config['seed_cash']
    note_en = (f'SELECTED FUNDED-RETENTION ILLUSTRATION, world {world}: closest network-policy profit to the overall network-policy median among worlds that funded additional retention. No success filter. This does not represent retention frequency.' if selected else
               f'World {world}, chosen near the overall network-policy median profit; the same world is used for every policy. This is not an average forecast.')
    note_fr = (f'ILLUSTRATION SÉLECTIONNÉE DE RÉTENTION FINANCÉE, monde {world}: profit du réseau le plus proche de sa médiane globale parmi les mondes ayant financé la rétention. Aucun filtre de réussite. Ne représente pas la fréquence de rétention.' if selected else
               f'Monde {world}, proche du profit médian global du réseau; même monde pour chaque politique. Ce n’est pas une prévision moyenne.')
    note_en += f" Seed ${seed:,.0f}; discovery ${metrics['discovery_cost']:,.2f}; {metrics['setup_months']} setup months before operation."
    note_fr += f" Capital {seed:,.0f} $; découverte {metrics['discovery_cost']:,.2f} $; {metrics['setup_months']} mois de préparation."
    return {'illustration_kind': 'selected_funded' if selected else 'median', 'illustrative_world': world,
            'ledger': enrich_ledger(record, policy, config, scenario), 'counterfactual_ledger': baseline['ledger'],
            'investments': investments(record), 'events': record['events'], 'lifecycle': record.get('lifecycle', {}),
            'graph_records': record.get('graph_records', {}), 'illustrative_metrics': metrics,
            'paid_work_cases': paid_work_cases(record, baseline, config),
            'allocation_totals': q_allocation(record),
            'illustration_en': note_en, 'illustration_fr': note_fr}


def q_allocation(record):
    """Sum actual expense records, keeping source IDs and cash/resource execution distinct."""
    activities = record.get('activities', [])
    totals = {}
    for entry in activities:
        group = entry.get('ledger', 'unclassified')
        totals[group] = totals.get(group, 0) + float(entry['cost_usd'])
    ids = [entry['activity_id'] for entry in activities]
    return {'basis': 'ACTUAL_SIMULATED_EXPENSE_RECORDS', 'totals_usd': totals,
            'activity_count': len(ids), 'unique_activity_ids': len(set(ids)),
            'duplicate_ids': len(ids) - len(set(ids)),
            'scope': 'All recorded world expenses; resource budgets and zero-cash prepaid execution records are not summed as duplicate spending.',
            'reported_audit': record.get('metrics', {}).get('allocation_audit', record.get('accounting_audit'))}


def paid_work_cases(record, baseline, config):
    """Normalize actual paid-job/candidate traces without inventing missing use or collection evidence."""
    jobs = record.get('job_records', {})
    beta_jobs = baseline.get('job_records', {})
    events = record.get('events', [])
    candidates = [e for e in events if e.get('kind') == 'paid_job_candidate']
    scans = [e for e in events if e.get('kind') == 'paid_job_scan']
    selected_events = candidates + scans
    if not selected_events:
        selected_events = [{'kind': 'job_record_only', 'origin_job_id': job['job_id'], 'month': job.get('delivery_month', job.get('attempt_month'))}
                           for job in jobs.values() if job.get('status') == 'validated_pass'][:12]
    # Sorting selects a recorded chronology, not the best or most profitable outcome.
    selected_events.sort(key=lambda e: (e.get('month', 0), e.get('origin_job_id', ''), e.get('id', '')))
    cases = []
    activity_by_id = {a['activity_id']: a for a in record.get('activities', [])}
    lifecycle_events = record.get('lifecycle', {}).get('events', [])
    for index, event in enumerate(selected_events):
        job_id = event['origin_job_id']
        job = jobs.get(job_id, {})
        beta = beta_jobs.get(job_id)
        identifier = event.get('id')
        related = [e for e in events if identifier and (e.get('id') == identifier or e.get('candidate_id') == identifier)]
        purchase = next((e for e in related if e.get('kind') == 'retention_purchase'), None)
        assessment = next((e for e in related if e.get('kind') == 'alpha_assessment'), None)
        related_lifecycle = [e for e in lifecycle_events if identifier and e.get('candidate_id') == identifier]
        source_ids = set(event.get('source_activity_ids', []))
        scan_id = event.get('charged_activity_id') or event.get('scan_activity_id')
        receipts = [a for a in record.get('activities', []) if a['activity_id'] in source_ids
                    or a['activity_id'] == scan_id or a.get('origin_job_id') == job_id
                    or a.get('job_id') == job_id or (identifier and a.get('capability_id') == identifier)]
        ids = [a['activity_id'] for a in receipts]
        observed_collection = job.get('settlement_status', job.get('actually_collected_by_horizon', job.get('collection_status')))
        true_useful = job.get('true_useful_for_analysis_only')
        payment = job.get('payment_authorized')
        outcome_en = f"{job.get('status', 'not recorded')}; payment authorized: {payment}; collection by horizon: {observed_collection if observed_collection is not None else 'not separately recorded'}; latent useful: {true_useful} (analyst only)."
        outcome_fr = f"{job.get('status', 'non enregistré')}; paiement autorisé: {payment}; encaissement à l’horizon: {observed_collection if observed_collection is not None else 'non enregistré séparément'}; utile latent: {true_useful} (analyse seulement)."
        if beta:
            outcome_en += f" Matched Beta job: {beta.get('status', 'not recorded')}; latent useful {beta.get('true_useful_for_analysis_only')}."
            outcome_fr += f" Projet Beta apparié: {beta.get('status', 'non enregistré')}; utile latent {beta.get('true_useful_for_analysis_only')}."
        else:
            outcome_en += ' No job-level completion is recorded under paired Beta; no reason is inferred.'
            outcome_fr += ' Aucun achèvement de ce projet n’est enregistré sous Beta; aucun motif n’est déduit.'
        candidate_label = '+'.join(event.get('components', [])) or event.get('result', 'No additional candidate')
        candidate_en = f"{identifier or 'No candidate ID'}; scope domain {event.get('domain', job.get('domain'))}. Source rights available: {event.get('rights_available', 'not assessed')}."
        candidate_fr = f"{identifier or 'Aucun identifiant candidat'}; domaine {event.get('domain', job.get('domain'))}. Droits disponibles: {event.get('rights_available', 'non évalués')}."
        retention_en = (f"Recorded class B purchase ${purchase['bill']:,.2f}; seed ${purchase['seed_funded']:,.2f}; operating ${purchase['operating_funded']:,.2f}. Admission: {assessment.get('admitted') if assessment else 'not yet recorded'}." if purchase else 'No additional retention purchase is recorded for this candidate.')
        retention_fr = (f"Dépense B enregistrée {purchase['bill']:,.2f} $; capital {purchase['seed_funded']:,.2f} $; fonds opérationnels {purchase['operating_funded']:,.2f} $. Admission: {assessment.get('admitted') if assessment else 'non enregistrée'}." if purchase else 'Aucune dépense supplémentaire de rétention enregistrée pour ce candidat.')
        recipients = [j for j in jobs.values() if identifier and identifier in j.get('used_capability_ids', []) and j.get('job_id') != job_id]
        access_only = [e for e in related_lifecycle if e.get('event') == 'member_execute' and e.get('allowed')]
        if recipients:
            useful = sum(j.get('true_useful_for_analysis_only') is True for j in recipients)
            unblocked = [j['job_id'] for j in recipients if j.get('true_useful_for_analysis_only') and j['job_id'] in baseline.get('project_sets', {}).get('capacity_deferred', []) and j['job_id'] not in baseline.get('project_sets', {}).get('true', [])]
            recipient_en = f"{len(recipients)} fresh job records using this capability; {useful} latent useful (analyst labels). {len(unblocked)} were capacity-deferred and not useful-completed under paired Beta. This is model-conditional feasibility, not an inherent Beta inability."
            recipient_fr = f"{len(recipients)} nouveaux projets utilisant cette capacité; {useful} utiles latents (analyse). {len(unblocked)} différés par capacité et non achevés utilement sous Beta. Faisabilité conditionnelle au modèle, pas incapacité intrinsèque de Beta."
            recipient_label = f'{useful} / {len(recipients)}'
        else:
            recipient_en = f"{len(access_only)} allowed execution events; no linked fresh job outcome is recorded. Access permission is not proof of useful delivery."
            recipient_fr = f"{len(access_only)} exécutions autorisées; aucun résultat de nouveau projet lié enregistré. L’accès autorisé ne prouve pas une livraison utile."
            recipient_label = '—'
        cases.append({'id': identifier or f'{event["kind"]}:{job_id}:{index}',
                      'label': f"{job_id} · {candidate_label}",
                      'note_en': 'Recorded selected-world trajectory. Analyst truth labels do not enter controller decisions. Source job, retention and actual payment status remain separate.',
                      'note_fr': 'Trajectoire du monde choisi. La vérité latente d’analyse n’entre pas dans les décisions. Projet, rétention et paiement effectif restent distincts.',
                      'outcome': {'label': job_id, 'description_en': outcome_en, 'description_fr': outcome_fr},
                      'candidate': {'label': candidate_label, 'description_en': candidate_en, 'description_fr': candidate_fr},
                      'retention': {'label': f"${purchase['bill']:,.2f}" if purchase else '—', 'description_en': retention_en, 'description_fr': retention_fr},
                      'recipient': {'label': recipient_label, 'description_en': recipient_en, 'description_fr': recipient_fr},
                      'receipts': [{'receipt_id': a['activity_id'], 'activity_id': a['cost_key'], 'allocation_class': a['ledger'],
                                    'charged_cost_usd': a['cost_usd'], 'activity_components': a.get('activity_components', []),
                                    'original_record': a} for a in receipts],
                      'receipt_audit': {'scope': 'Related source/candidate activities only; original activity IDs preserved.', 'rows': len(ids),
                                        'unique_ids': len(set(ids)), 'duplicate_ids': len(ids)-len(set(ids)),
                                        'class_totals_usd': {key: sum(a['cost_usd'] for a in receipts if a['ledger'] == key) for key in sorted({a['ledger'] for a in receipts})},
                                        'source_A_recharged': purchase.get('source_job_construction_recharged') if purchase else None},
                      'raw_trace': {'originating_job': job, 'matched_beta_job': beta, 'candidate_event': event, 'events': related,
                                    'lifecycle_events': related_lifecycle, 'fresh_recipient_jobs': recipients, 'activities': receipts}})
    return cases


def records_for_worlds(path, scenario, worlds):
    found = {world: {} for world in worlds}
    with gzip.open(path / f'{scenario}_complete_records.jsonl.gz', 'rt') as stream:
        for line in stream:
            record = json.loads(line)
            if record['world'] in found:
                found[record['world']][record['policy']] = record
    for world, records in found.items():
        if set(records) != set(POLICIES):
            raise ValueError(f'Missing paired v2 records for world {world}: {set(records)}')
    return found


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--results', default=str(ROOT / 'results/paid_work_final'))
    parser.add_argument('--output', default=str(ROOT / 'results/paid_work_demo_view.json'))
    parser.add_argument('--allow-pilot', action='store_true')
    parser.add_argument('--refresh-sensitivity', action='store_true', help='Attach completed frozen stress records to an already validated primary display, without rereading full histories.')
    args = parser.parse_args()
    path = pathlib.Path(args.results)
    if not path.is_absolute():
        path = ROOT / path
    summary = json.loads((path / 'summary.json').read_text())
    config_path = path / 'frozen_config.json'
    workflow_path = path / 'frozen_workflow_costs.json'
    if not config_path.exists():
        if not args.allow_pilot:
            raise ValueError('Final display requires frozen_config.json')
        config_path = ROOT / 'sim/config_v3.json'
        workflow_path = ROOT / 'evidence/workflow_costs_v3.json'
    config = json.loads(config_path.read_text())
    workflow = json.loads(workflow_path.read_text())
    if 'paid' not in config['study_id'].lower() or workflow.get('schema_version') != 3:
        raise ValueError('The active companion requires paid-work data; prior findings remain archived.')
    if not args.allow_pilot:
        if summary['config_sha256'] != sha(config) or summary['workflow_costs_sha256'] != sha(workflow):
            raise ValueError('Frozen result/configuration/workflow identity mismatch')
        if 'confirm' not in summary['status'].lower():
            raise ValueError('Final demo requires independent confirmation results')
    cash_path = path / 'commercial_cash_summary.json'
    commercial_cash = json.loads(cash_path.read_text()) if cash_path.exists() else None
    if not args.allow_pilot:
        if not commercial_cash or commercial_cash.get('audit', {}).get('status') != 'PASS':
            raise ValueError('Final display requires the audited all-world commercial cash export.')
        # This exporter binds the literal frozen JSON file, while the simulator also records a canonical JSON hash.
        if commercial_cash['frozen_config_sha256'] != hashlib.sha256(config_path.read_bytes()).hexdigest():
            raise ValueError('Commercial cash export belongs to a different frozen configuration file.')
    if args.refresh_sensitivity:
        output = pathlib.Path(args.output)
        view = json.loads(output.read_text())
        if (view['config_sha256'] != summary['config_sha256']
                or view['workflow_costs_sha256'] != summary['workflow_costs_sha256']
                or view['source_run'] != str(path.relative_to(ROOT))):
            raise ValueError('Cannot refresh a display from another primary confirmation.')
        sensitivity = normalize_stress(ROOT, view['config_sha256'], view['workflow_costs_sha256'])
        if not sensitivity['complete']:
            raise ValueError('Sensitivity execution has not completed; existing display was not changed.')
        view['sensitivity'] = sensitivity
        output.write_text(json.dumps(view, indent=2, ensure_ascii=False))
        print(json.dumps({'output': str(output), 'sensitivity_cases': len(sensitivity['cases']), 'primary_data_unchanged': True}))
        return
    foundation = json.loads((ROOT / 'evidence/foundation_source_register.json').read_text())
    source = next(item for item in foundation['sources'] if item['id'] == 'GSA-4S-2026')
    effort = next(item for item in foundation['assumptions'] if item['id'] == 'HUMAN-EFFORT-01')
    role_map = [('or', 'operations_research_analyst', 'Operations research', 'Recherche opérationnelle'),
                ('software', 'software_engineer', 'Software engineering', 'Génie logiciel'),
                ('independent_qa', 'software_engineer', 'Independent engineering QA', 'Assurance qualité indépendante'),
                ('systems', 'systems_engineer', 'Systems integration', 'Intégration des systèmes'),
                ('pm', 'journeyman_project_manager', 'Project coordination', 'Coordination de projet')]
    labels = {'conservative': ('Conservative', 'Prudent'), 'central': ('Central', 'Central'),
              'favorable': ('Favorable', 'Favorable'), 'capacity_loose': ('Capacity-loose condition', 'Capacité abondante')}
    view = {'study_id': config['study_id'], 'status': summary['status'],
            'config_sha256': summary['config_sha256'], 'workflow_costs_sha256': summary['workflow_costs_sha256'],
            'workflow_source': str(workflow_path.relative_to(ROOT)), 'source_run': str(path.relative_to(ROOT)),
            'commercial_cash_source': str(cash_path.relative_to(ROOT)) if commercial_cash else None,
            'commercial_cash_audit': commercial_cash.get('audit') if commercial_cash else None,
            'commercial_cash_definitions': commercial_cash.get('definitions') if commercial_cash else None,
            'sampling_unit': summary['sampling_unit'], 'policies': list(POLICIES),
            'beta_epochs': config['network']['beta_epochs'], 'scenarios': [],
            'interpretation': 'Display-only normalization of executed model results; no independent simulation, price tuning, or decision revision.',
            'metric_unit_notes': {'retention_useful_fresh_projects': 'Useful capability-project pairs summed over retained nodes; one project can count for multiple nodes.', 'source_true_collected_useful_recipient_projects': 'Useful capability-project pairs with a true net-collected origin; not a distinct project count.', 'operating_funded_true_paid_source_useful_projects': 'Useful capability-project pairs from operating-funded retention and true net-collected origins.', 'R_uses_and_V_uses': 'Compatible component-use attempts, not guaranteed useful recipient outcomes.'}}
    for name, case in summary['scenarios'].items():
        if set(case['policies']) != set(POLICIES):
            raise ValueError(f'{name} is not a complete four-policy v2 result.')
        sc = config['scenarios'][name]
        human = sc['human_reference']
        band = min(('low', 'central', 'high'), key=lambda key: abs(effort['derived_cost_usd'][key] - human))
        hours = effort['hours_' + band]
        roles = [{'role': key, 'label_en': en, 'label_fr': fr, 'hours': hours[key], 'rate': source['rates'][rate]}
                 for key, rate, en, fr in role_map]
        with (path / f'{name}_worlds.csv').open() as stream:
            all_rows = list(csv.DictReader(stream))
        by_policy = {policy: [row for row in all_rows if row['policy'] == policy] for policy in POLICIES}
        if len(all_rows) != case['worlds'] * len(POLICIES):
            raise ValueError(f'{name}: incomplete or duplicate scalar world records.')
        for policy, rows in by_policy.items():
            if len(rows) != case['worlds'] or len({row['world'] for row in rows}) != case['worlds']:
                raise ValueError(f'{name}/{policy}: world records are not unique and complete.')
            if any(row['scenario'] != name for row in rows):
                raise ValueError(f'{name}/{policy}: scalar records mix scenarios.')
        baseline_rows = {int(row['world']): row for row in by_policy[BASELINE]}
        private_rows = {int(row['world']): row for row in by_policy['optimized_private']}
        world = case['illustrative_world']
        funded = [row for row in by_policy[FOCUS] if float(row.get('retention_cost', 0)) > 0]
        funded_world = (int(min(funded, key=lambda row: (abs(float(row['net_profit']) - case['policies'][FOCUS]['net_profit']['median']), int(row['world'])))['world']) if funded else None)
        requested = {world}
        if funded_world is not None:
            requested.add(funded_world)
        records = records_for_worlds(path, name, requested)
        scenario = {'id': name, 'label_en': labels.get(name, (name.replace('_', ' ').title(), name))[0],
                    'label_fr': labels.get(name, (name, name.replace('_', ' ')))[1], 'worlds': case['worlds'],
                    'horizon': config['months'], 'seed_cash': config['seed_cash'], 'human_reference': human,
                    'human_low': config['human_reference']['low'], 'human_high': config['human_reference']['high'],
                    'human_roles': roles, 'human_total_assumed_hours': sum(hours.values()), 'policies': {},
                    'illustrative_world': world, 'scenario_assumptions': sc, 'paired_results': case.get('paired', {})}
        scenario['human_note_en'] = f"{sum(hours.values())} assumed team hours for the complete package, including up to two revisions. Published US GSA schedule effective May 2024; rates apply May 2026–April 2027. QA uses the software-engineer rate as an assumption. No matched quote, observed effort or verified human-only delivery. Routine installed-engine replanning is included."
        scenario['human_note_fr'] = f"{sum(hours.values())} heures d’équipe supposées pour le produit complet, avec jusqu’à deux révisions. Barème GSA américain publié en mai 2024; tarifs applicables de mai 2026 à avril 2027. Le tarif logiciel sert de référence supposée pour l’AQ. Aucun devis comparable, effort observé ou travail exclusivement humain vérifié. La replanification ordinaire est incluse."
        for policy in POLICIES:
            stat = case['policies'][policy]
            rows = by_policy[policy]
            totals = {label: sum(float(row[key]) for row in rows) for label, key in
                      [('our', 'orders'), ('human', 'human_choices'), ('postpone', 'retain_choices'), ('decline', 'decline_choices')]}
            offered = sum(totals.values())
            delivered = sum(float(row['validated_deliveries']) for row in rows)
            false = sum(float(row['false_passes']) for row in rows)
            increment = paired_stats(rows, baseline_rows, 'net_profit')
            fresh = paired_stats(rows, baseline_rows, 'true_accepted_projects')
            network_increment = paired_stats(rows, private_rows, 'net_profit')
            price_fraction = stat['mean_price_fraction']['mean']
            cash_data = commercial_cash['scenarios'][name]['policies'][policy] if commercial_cash else None
            if cash_data and cash_data['worlds'] != case['worlds']:
                raise ValueError(f'{name}/{policy}: commercial cash world count mismatch.')
            node = {'policy': policy, 'price': human * price_fraction, 'price_fraction': price_fraction,
                    'commercial_cash': cash_data,
                    'matched_collected_prices': cash_data['true_useful_collected_price_reference'] if cash_data else None,
                    'price_fraction_stats': stat['mean_price_fraction'],
                    'stats': {'profit': stat['net_profit'], 'quality_adjusted_profit': stat['quality_adjusted_profit'],
                              'full_cost': stat['pooled_fully_allocated_cost_per_true_project'],
                              'collections': average(rows, 'collections'),
                              'delivered_invoice_mean_across_nonzero_worlds': stat['delivered_price_mean']['mean'] if stat.get('delivered_price_mean') else None,
                              'useful': stat['true_accepted_projects'], 'material_error': false / delivered if delivered else None,
                              'aggregate_false_passes': false, 'aggregate_delivered': delivered,
                              'capabilities': average(rows, 'research_admissions'),
                              'research_probability': sum(float(row.get('retention_cost', 0)) > 0 for row in rows) / len(rows),
                              'retention_probability': sum(float(row.get('retention_cost', 0)) > 0 for row in rows) / len(rows),
                              'optional_research_probability': stat['probability_research'], 'incremental_profit': increment['mean'],
                              'incremental_profit_stats': increment, 'incremental_projects': fresh,
                              'network_incremental_profit_stats': network_increment,
                              'R_uses': average(rows, 'R_uses'), 'V_uses': average(rows, 'V_uses'),
                              'seed_funded': average(rows, 'research_seed_funded'),
                              'operating_funded': average(rows, 'research_operating_funded'),
                              'zero_output_worlds': stat['zero_output_worlds'],
                              'retention_spend': average(rows, 'retention_cost'),
                              'optional_research_spend': average(rows, 'investment_cost'),
                              'emergence_scan_spend': average(rows, 'emergence_scan_cost'),
                              'emergence_scans': average(rows, 'emergence_scans'),
                              'empty_scans': average(rows, 'empty_scans'),
                              'emergent_candidates': average(rows, 'emergent_candidates'),
                              'retention_seed_funded': average(rows, 'retention_seed_funded'),
                              'retention_operating_funded': average(rows, 'retention_operating_funded'),
                              'ledger_A': average(rows, 'ledger_A_delivery_total'),
                              'ledger_A_direct': average(rows, 'direct_job_cost_in_A'),
                              'ledger_A_other': average(rows, 'baseline_overhead_in_A'),
                              'ledger_B': average(rows, 'ledger_B_retention_total'),
                              'ledger_C': average(rows, 'ledger_C_optional_research_total'),
                              'startup_discovery_in_C': average(rows, 'startup_discovery_in_C'),
                              'separate_optional_campaign_cost': average(rows, 'separate_optional_campaign_cost'),
                              'retention_admissions': average(rows, 'retention_admissions'),
                              'retention_uses': average(rows, 'retention_uses'),
                              'operating_funded_true_paid_source_uses': average(rows, 'operating_funded_true_paid_source_uses'),
                              'retention_useful_fresh_projects': average(rows, 'retention_useful_fresh_projects'),
                              'source_true_collected_useful_recipient_projects': average(rows, 'source_true_collected_useful_recipient_projects'),
                              'operating_funded_true_paid_source_useful_projects': average(rows, 'operating_funded_true_paid_source_useful_projects')},
                    'buyer_shares': {key: value / offered if offered else None for key, value in totals.items()},
                    'buyer_choice_denominator': offered, 'raw_population_stats': stat,
                    'pricing_rule_en': 'Each month, the declared controller selects the best grid price under its current posterior, quality, collections and finite resources. This is an approximate receding-horizon capital policy, not a global optimum or an empirically calibrated market equilibrium.',
                    'pricing_rule_fr': 'Chaque mois, le contrôleur choisit le meilleur prix de la grille selon ses croyances, qualité, encaissements et ressources finies. Il s’agit d’une politique approximative à horizon glissant, pas d’un optimum global ou d’un équilibre de marché étalonné empiriquement.'}
            if policy == 'fixed_network':
                node['pricing_rule_en'] = f"This diagnostic policy holds price at {config['fixed_price_ablation']:.0%} of the human-team reference. The recorded grid shows the controller's comparison values; the fixed policy does not choose its maximizing point. Its optional retention and cash decisions still operate."
                node['pricing_rule_fr'] = f"Cette politique diagnostique maintient le prix à {config['fixed_price_ablation']:.0%} de la référence humaine. La grille montre les valeurs comparatives; la politique fixe ne choisit pas son maximum. Rétention et trésorerie restent actives."
            for key in ('network_access_cost', 'network_distribution_cost', 'network_composition_cost', 'beta_reevaluation_cost',
                        'revocation_cost', 'alpha_candidates', 'alpha_admissions', 'alpha_rejections', 'alpha_reassessments',
                        'alpha_retirements', 'alpha_inventory_erosion', 'new_admitted_expected_alpha', 'recipient_adoptions',
                        'rich_true_projects', 'alpha_expected_inventory_value', 'alpha_eligible_records',
                        'distinct_recipient_users', 'distinct_completed_domains', 'unique_true_projects',
                        'graph_overhead_total', 'research_full_cycle_recovered'):
                node['stats'][key] = average(rows, key)
            node['stats']['alpha_inventory_final'] = average(rows, 'alpha_expected_inventory_value')
            node.update(illustrate(records[world][policy], records[world][BASELINE], policy, config, sc))
            if funded_world is not None and funded_world != world:
                node['funded_illustration'] = illustrate(records[funded_world][policy], records[funded_world][BASELINE], policy, config, sc, True)
            scenario['policies'][policy] = node
        if funded_world is not None and funded_world != world:
            scenario['funded_selection'] = {'world': funded_world, 'criterion': 'Positive incremental retention spending, closest network-policy profit to whole-ensemble network median; no success filter; world-number tie break.'}
        view['scenarios'].append(scenario)
    view['sensitivity'] = normalize_stress(ROOT, view['config_sha256'], view['workflow_costs_sha256'])
    output = pathlib.Path(args.output)
    output.write_text(json.dumps(view, indent=2, ensure_ascii=False))
    print(json.dumps({'output': str(output), 'scenarios': len(view['scenarios']), 'status': view['status'], 'config_sha256': view['config_sha256']}))


if __name__ == '__main__':
    main()
