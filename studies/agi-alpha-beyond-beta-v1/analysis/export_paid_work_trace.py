# SPDX-License-Identifier: Apache-2.0
"""Export one receipt-linked modeled trajectory without fabricating a success.

This is a display-only selector. It never changes model inputs or reruns a world.
Primary scenario order and the within-scenario selection rule are fixed below.
If no primary trace qualifies, a separately labeled directed fixture may be used.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCENARIO_ORDER = ('central', 'favorable', 'conservative')
POLICY = 'optimized_network'


def load(path):
    return json.loads(path.read_text())


def canonical_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def records(path, scenario):
    with gzip.open(path / f'{scenario}_complete_records.jsonl.gz', 'rt') as stream:
        for line in stream:
            yield json.loads(line)


def qualifying_paths(record):
    jobs = record.get('job_records', {})
    for purchase in sorted((e for e in record['events'] if e.get('kind') == 'retention_purchase'),
                           key=lambda e: (e['month'], e['id'])):
        identifier = purchase['id']
        source = jobs.get(purchase.get('origin', {}).get('job_id'), {})
        if not (source.get('status') == 'validated_pass'
                and source.get('true_useful_for_analysis_only') is True
                and source.get('net_customer_receipts_after_refund_obligations', 0) > 0
                and source.get('actually_collected_by_horizon') is True):
            continue
        admitted = next((e for e in record['events'] if e.get('kind') == 'alpha_assessment'
                         and e.get('id') == identifier and e.get('admitted')), None)
        if not admitted:
            continue
        fresh = sorted((j for j in jobs.values() if identifier in j.get('used_capability_ids', [])
                        and j.get('job_id') != source['job_id']
                        and j.get('recipient') != source.get('recipient')
                        and j.get('status') == 'validated_pass'
                        and j.get('true_useful_for_analysis_only') is True),
                       key=lambda j: (j.get('delivery_month', j.get('attempt_month', 0)), j['job_id']))
        if fresh:
            yield purchase, source, admitted, fresh


def choose(path, summary, directed=False):
    scenario_names = summary.get('scenarios', {})
    for scenario in SCENARIO_ORDER:
        if scenario not in scenario_names:
            continue
        if scenario_names[scenario]['policies'][POLICY].get('probability_retention') == 0:
            continue  # Closed confirmation reports no B purchases, so no paid-retention path can qualify.
        median = scenario_names[scenario]['policies'][POLICY]['net_profit']['median']
        best = None
        qualifying_worlds = 0
        for record in records(path, scenario):
            if record['policy'] != POLICY:
                continue
            possibilities = list(qualifying_paths(record))
            if not possibilities:
                continue
            qualifying_worlds += 1
            key = (abs(record['metrics']['net_profit'] - median), record['world'])
            if best is None or key < best[0]:
                best = (key, record, possibilities[0])
        if best:
            _, record, selected_path = best
            beta = next(r for r in records(path, scenario)
                        if r['world'] == record['world'] and r['policy'] == 'optimized_beta')
            return record, beta, selected_path, {
                'basis': 'DIRECTED_QA_FIXTURE_NOT_COMMERCIAL_EVIDENCE' if directed else 'SELECTED_FROZEN_MODELED_TRAJECTORY',
                'rule': 'Scenario priority central, favorable, conservative. Within the first scenario with a qualifying path, choose the network-policy profit closest to that scenario\'s overall network median; world-number tie break. In that world choose the earliest retained/admitted candidate with a truly useful, net-collected origin and a truly useful fresh project at another recipient; earliest delivery and job-ID tie break. No positive paired-profit filter.',
                'qualifying_worlds_in_selected_scenario': qualifying_worlds,
                'scenario_worlds': scenario_names[scenario]['worlds'],
                'network_population_median_profit': median,
                'population_feedback_frequency': scenario_names[scenario].get('paired', {}).get('probability_operating_funded_paid_job_feedback'),
                'illustration_is_not_frequency_estimate': True,
                'latent_truth_used_only_for_retrospective_illustration_selection': True,
            }
    return None


def money(value):
    return 'not recorded' if value is None else f'${value:,.2f}'


def build_export(path, summary, chosen):
    record, beta, (purchase, source, admission, fresh), selection = chosen
    identifier = purchase['id']
    first = fresh[0]
    activity_by_id = {a['activity_id']: a for a in record['activities']}
    candidate = next(e for e in record['events'] if e.get('kind') == 'paid_job_candidate' and e.get('id') == identifier)
    source_ids = candidate['source_activity_ids']
    source_receipts = [activity_by_id[i] for i in source_ids]
    assert all(a['ledger'] == 'A' for a in source_receipts), 'Source exclusion includes non-A activity'
    assert abs(sum(a['cost_usd'] for a in source_receipts) - candidate['source_cost_already_charged']) < 1e-6
    assert purchase['source_job_construction_recharged'] is False
    assert len(activity_by_id) == len(record['activities']), 'Duplicate expense IDs'
    retention_receipt = activity_by_id[purchase['incremental_receipt_id']]
    assert retention_receipt['ledger'] == 'B'
    assert abs(retention_receipt['cost_usd'] - purchase['bill']) < 1e-6
    candidate_events = [e for e in record['events'] if e.get('id') == identifier or e.get('candidate_id') == identifier]
    lifecycle_events = [e for e in record.get('lifecycle', {}).get('events', []) if e.get('candidate_id') == identifier]
    linked_ids = set(source_ids + source.get('charged_activity_ids', []) + first.get('charged_activity_ids', []) + [purchase['incremental_receipt_id']])
    for event in candidate_events:
        receipt = event.get('evidence', {}).get('paid_receipt_id')
        if receipt:
            linked_ids.add(receipt)
    linked_receipts = [a for a in record['activities'] if a['activity_id'] in linked_ids]
    totals = {k: sum(a['cost_usd'] for a in record['activities'] if a['ledger'] == k) for k in 'ABC'}
    assert abs(sum(totals.values()) - record['metrics']['fully_allocated_cost_total']) < 1e-5
    ledger_keys = ('month', 'opening_cash', 'collections', 'operating_outflow', 'investment_outflow',
                   'refund_outflow', 'arrears_outflow', 'closing_cash', 'reserve',
                   'available_uncommitted_cash', 'retained_operating_cash_above_seed',
                   'unpaid_obligations', 'beta_version', 'beta_reconstruction_quantity_factor',
                   'alpha_expected_inventory_value', 'alpha_eligible_records', 'research_action')
    comparisons = {key: record['metrics'][key] - beta['metrics'][key]
                   for key in ('net_profit', 'quality_adjusted_profit', 'true_accepted_projects')}
    final_node = record.get('lifecycle', {}).get('records', {}).get(identifier)
    assessments = [{'month': e['month'], 'kind': e['kind'], 'admitted': e.get('admitted'),
                    'assessment': e.get('assessment'), 'forecast': e.get('forecast')}
                   for e in candidate_events if e.get('kind') in ('alpha_assessment', 'alpha_reassessment')]
    return {
        'schema': 'paid-work-receipt-linked-illustration/v1',
        'basis': selection['basis'], 'selection': selection,
        'source_results': str(path.relative_to(ROOT)),
        'source_record_file': str((path / f'{record["scenario"]}_complete_records.jsonl.gz').relative_to(ROOT)),
        'selected_record_sha256': canonical_hash(record),
        'matched_beta_record_sha256': canonical_hash(beta),
        'config_sha256': summary.get('config_sha256'),
        'workflow_costs_sha256': summary.get('workflow_costs_sha256'),
        'scenario': record['scenario'], 'world': record['world'], 'policy': POLICY,
        'capability_id': identifier,
        'source_job': source,
        'matched_beta_source_job': beta.get('job_records', {}).get(source['job_id']),
        'source_A_receipts': source_receipts,
        'source_A_charged_once_usd': sum(a['cost_usd'] for a in source_receipts),
        'source_candidate_event': candidate,
        'retention_purchase': purchase,
        'incremental_retention_receipt': retention_receipt,
        'admission': admission,
        'first_useful_fresh_recipient_job': first,
        'matched_beta_recipient_job': beta.get('job_records', {}).get(first['job_id']),
        'useful_fresh_recipient_projects_linked_to_capability': len(fresh),
        'first_recipient_capacity_deferred_under_beta': first['job_id'] in beta.get('project_sets', {}).get('capacity_deferred', []),
        'first_recipient_useful_completed_under_beta': first['job_id'] in beta.get('project_sets', {}).get('true', []),
        'candidate_assessments_over_time': assessments,
        'candidate_final_lifecycle_record': final_node,
        'candidate_lifecycle_events': lifecycle_events,
        'monthly_cash_reserve_and_beta': [{key: row.get(key) for key in ledger_keys} for row in record['ledger']],
        'linked_expense_receipts': linked_receipts,
        'linked_expense_totals': {k: sum(a['cost_usd'] for a in linked_receipts if a['ledger'] == k) for k in 'ABC'},
        'whole_world_expense_totals': totals,
        'whole_world_metrics': record['metrics'],
        'matched_beta_metrics': beta['metrics'],
        'paired_network_minus_beta': comparisons,
        'limitations': [
            'All jobs, prices, receipts, identities, correctness labels and commercial outcomes are simulated.',
            'This illustration is selected for the existence of a linked paid-source/retention/useful-recipient path. It is not typical-path evidence or an estimate of its frequency.',
            'Latent usefulness is used for retrospective reporting only; the controller sees approved artifacts, observed authorization and available cash.',
            'Admission project-dollar values extrapolate from synthetic component tests; no paid end-to-end frontier projects were observed.',
            'Paired whole-policy profit includes induced price, timing, capacity and other candidate decisions. It is not an isolated causal return on this one capability.',
            'Linked receipts are a subset, not a fully allocated per-capability ledger. Whole-world A/B/C totals include all activities and unallocated overhead. Refunds reverse revenue separately.',
            'A final active status is a state at the model horizon, not a promise of future usefulness. Beta epochs are assumptions.',
        ],
    }


def markdown(trace):
    s, p, f, a = trace['source_job'], trace['retention_purchase'], trace['first_useful_fresh_recipient_job'], trace['admission']['assessment']
    b = trace['matched_beta_recipient_job'] or {}
    final = trace['candidate_final_lifecycle_record'] or {}
    lines = [
        '# Receipt-linked paid-work illustration', '', f'**{trace["basis"]}**', '',
        f'Source: `{trace["source_record_file"]}`, scenario **{trace["scenario"]}**, world **{trace["world"]}**, policy `{trace["policy"]}`.', '',
        trace['selection']['rule'], '',
        f'This is a selected trajectory, not the population success rate. Qualifying worlds in this scenario: {trace["selection"]["qualifying_worlds_in_selected_scenario"]}/{trace["selection"]["scenario_worlds"]}.', '',
        '| Stage | Recorded modeled event |', '|---|---|',
        f'| Source contract | `{s["job_id"]}` at {money(s.get("offered_price"))}; approved in month {s.get("delivery_month")}; authorization {s.get("payment_authorized")}. |',
        f'| Source job cost A | {money(trace["source_A_charged_once_usd"])} across {len(trace["source_A_receipts"])} unique directly linked A receipts; charged once. This excludes unallocated operating overhead. |',
        f'| Source collections | Due month {s.get("collection_month")}; horizon status `{s.get("settlement_status")}`; net receipts after refund obligations {money(s.get("net_customer_receipts_after_refund_obligations"))}. |',
        f'| Incremental retention B | {money(p["bill"])} in month {p["month"]}; operating funds {money(p["operating_funded"])}; seed funds {money(p["seed_funded"])}. Scan and later lifecycle costs are separately charged. |',
        f'| Purchase decision | Expected incremental terminal cash {money(p.get("expected_incremental_terminal_cash"))}; cash after purchase {money(p.get("cash_after_purchase",p.get("cash_after")))}; reserve {money(p.get("reserve"))}. |',
        f'| Admission | Remaining prospective net Alpha {money(a.get("expected_prospective_net_alpha"))}; sunk-inclusive residual forecast {money(a.get("construction_inclusive_residual_forecast"))}; {a.get("raw_paired_cases")} component cases, {a.get("effective_evidence_groups")} effective groups. Forecast is not historical repayment. |',
        f'| First useful fresh recipient | `{f["job_id"]}`, `{f.get("recipient")}`, delivery month {f.get("delivery_month")}; validator pass and analyst latent usefulness true. Directly linked A cost {money(f.get("ledger_A_charged_cost"))}; separately linked B cost {money(f.get("ledger_B_charged_cost"))}; neither is a fully allocated unit cost. |',
        f'| Matched Beta recipient | Status `{b.get("status","not recorded")}`; A cost {money(b.get("ledger_A_charged_cost"))}; latent useful {b.get("true_useful_for_analysis_only","not recorded")}. Missing output does not imply inherent incapability. |',
        f'| Horizon evolution | Candidate status `{final.get("status","not recorded")}`, Beta `{final.get("beta_version","not recorded")}`; {len(trace["candidate_assessments_over_time"])} recorded assessments. |',
        f'| Whole-world result | Network−Beta profit {money(trace["paired_network_minus_beta"]["net_profit"])}; quality-adjusted difference {money(trace["paired_network_minus_beta"]["quality_adjusted_profit"])}; useful project difference {trace["paired_network_minus_beta"]["true_accepted_projects"]}. This is a whole-policy comparison. |', '',
        '## Cash and reserve chronology', '', '| Month | Collections | Closing cash | Reserve | Available cash | Beta | Expected Alpha inventory |', '|---:|---:|---:|---:|---:|---|---:|',
    ]
    if p.get('qa_forced_capital_action'):
        lines[4:4] = ['**Directed accounting QA:** the capital action and controlled test inputs were forced to exercise funded retention. This is not evidence that the optimizer selected a profitable investment under primary conditions.', '']
    for row in trace['monthly_cash_reserve_and_beta']:
        lines.append(f'| {row["month"]} | {money(row["collections"])} | {money(row["closing_cash"])} | {money(row["reserve"])} | {money(row["available_uncommitted_cash"])} | {row["beta_version"]} | {money(row["alpha_expected_inventory_value"])} |')
    lines += ['', '## Receipt allocation', '', '| Activity receipt | Class | Named cost | USD |', '|---|---|---|---:|']
    for receipt in trace['linked_expense_receipts']:
        lines.append(f'| `{receipt["activity_id"]}` | {receipt["ledger"]} | `{receipt["cost_key"]}` | {receipt["cost_usd"]:,.2f} |')
    lines += ['', 'Whole-world costs (all activities): ' + '; '.join(f'{key} {money(value)}' for key,value in trace['whole_world_expense_totals'].items()) + '.', '', '## Interpretation limits', '']
    lines += ['- ' + limitation for limitation in trace['limitations']]
    return '\n'.join(lines) + '\n'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--results', type=Path, default=ROOT / 'results/paid_work_final')
    parser.add_argument('--fixture', type=Path, default=ROOT / 'results/qa_paid_job_funded')
    parser.add_argument('--output', type=Path, default=ROOT / 'results/paid_work_trace.json')
    args = parser.parse_args()
    summary = load(args.results / 'summary.json')
    if 'confirm' not in summary.get('status','').lower():
        raise SystemExit('Trace export requires frozen primary confirmation first.')
    primary_summary = summary
    if canonical_hash(load(args.results / 'frozen_config.json')) != summary.get('config_sha256'):
        raise SystemExit('Frozen primary configuration differs from confirmation results.')
    if canonical_hash(load(args.results / 'frozen_workflow_costs.json')) != summary.get('workflow_costs_sha256'):
        raise SystemExit('Frozen primary workflow costs differ from confirmation results.')
    chosen = choose(args.results, summary)
    source_path = args.results
    primary_has_qualifying_path = bool(chosen)
    if not chosen and args.fixture.exists():
        fixture_summaries = {p.name.removesuffix('_summary.json'):load(p) for p in args.fixture.glob('*_summary.json')}
        fixture_summary = {'status':'DIRECTED QA', 'scenarios':fixture_summaries,
                           'config_sha256':canonical_hash(load(args.fixture / 'frozen_config.json')),
                           'workflow_costs_sha256':canonical_hash(load(args.fixture / 'frozen_workflow_costs.json'))}
        chosen = choose(args.fixture, fixture_summary, directed=True)
        source_path, summary = args.fixture, fixture_summary
    if not chosen:
        data = {'schema':'paid-work-receipt-linked-illustration/v1','basis':'NO_QUALIFYING_RECORDED_PATH','primary_has_qualifying_path':False,'no_positive_example_fabricated':True}
    else:
        data = build_export(source_path, summary, chosen)
        data['primary_has_qualifying_path'] = primary_has_qualifying_path
        if data['basis'] == 'DIRECTED_QA_FIXTURE_NOT_COMMERCIAL_EVIDENCE':
            data['limitations'].insert(0, 'No qualifying paid-source/retention/useful-fresh-recipient path was found in primary confirmation. This directed fixture forces a capital action and controlled inputs to exercise accounting, not to establish investment viability.')
            manifest = args.fixture / 'fixture_manifest.json'
            data['directed_fixture_manifest'] = load(manifest) if manifest.exists() else None
    data['primary_confirmation_config_sha256'] = primary_summary.get('config_sha256')
    data['primary_feedback_frequencies'] = {name: item.get('paired', {}).get('probability_operating_funded_paid_job_feedback')
                                          for name,item in primary_summary['scenarios'].items()}
    args.output.write_text(json.dumps(data,indent=2,ensure_ascii=False))
    if chosen:
        args.output.with_suffix('.md').write_text(markdown(data))
    print(json.dumps({'output':str(args.output),'basis':data['basis'],'scenario':data.get('scenario'),'world':data.get('world'),'sha256':hashlib.sha256(args.output.read_bytes()).hexdigest()}))


if __name__ == '__main__':
    main()
