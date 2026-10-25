#!/usr/bin/env python3
"""Assemble cost and intervention ledgers from existing records; run no jobs."""
import argparse
import collections
import datetime
import json
import sys
from pathlib import Path
sys.dont_write_bytecode = True
from common import DEFAULT_ROOT, read_json, sha, write_json

UNKNOWN_COSTS = ['host_compute_invoice', 'execution_service_charge', 'setup', 'human_supervision',
                 'human_review', 'human_correction', 'verification_allocation', 'maintenance_allocation',
                 'capability_construction_allocation', 'research_authoring', 'development_assistant_bill',
                 'complete_marginal_cost', 'fully_allocated_cost']

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=DEFAULT_ROOT)
    parser.add_argument('--check', action='store_true', help='Construct in memory and print counts; write no ledger files.')
    args = parser.parse_args()
    root = args.root.resolve()
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    entries, events, sources = [], [], {}
    def provenance(path, fragment=None):
        path = Path(path)
        relative = str(path.relative_to(root))
        if relative not in sources:
            sources[relative] = {'path': relative, 'sha256': sha(path), 'bytes': path.stat().st_size}
        return {'path': relative, 'fragment': fragment, 'sha256': sources[relative]['sha256']}
    def add_event(event_id, category, description, origin, outcome=None, injected=False, actor='research_or_test_operator', details=None):
        events.append({'id': event_id, 'category': category, 'description': description, 'provenance': origin,
                       'outcome': outcome, 'injected_test': injected, 'actor': actor,
                       'counts_as_primary_business_failure': category == 'measured_primary_failure',
                       'human_active_minutes': None, 'authoring_or_repair_cost': None, 'timestamp_utc': None,
                       'details': details})
    receipts = sorted((root / 'raw').rglob('receipt.json')) + sorted((root / 'development').rglob('receipt.json'))
    for path in receipts:
        r = read_json(path)
        rel = str(path.relative_to(root))
        if rel.startswith('raw/primary/'):
            scope = 'primary_confirmation'
        elif rel.startswith('raw/scale/'):
            scope = 'finite_load_repeat'
        elif rel.startswith('raw/showcase/'):
            scope = 'development_selected_public_showcase'
        elif rel.startswith('raw/successor-report/'):
            scope = 'composed_successor'
        elif 'injected_timeout' in rel:
            scope = 'development_injected_timeout_fixture'
        else:
            scope = 'development_worker'
        injected = scope == 'development_injected_timeout_fixture'
        entry = {
            'id': rel.removesuffix('/receipt.json'), 'scope': scope, 'job_id': r.get('job_id'),
            'provenance': provenance(path), 'accepted': r.get('accepted'), 'error': r.get('error'),
            'started_utc': r.get('started_utc'), 'finished_utc': r.get('finished_utc'),
            'measured_resources': {
                'worker_wall_seconds': r.get('worker_wall_seconds'),
                'process_turnaround_seconds': r.get('process_turnaround_seconds'),
                'submission_to_delivery_seconds': r.get('submission_to_acceptance_seconds'),
                'queue_wait_seconds': r.get('queue_wait_seconds'),
                'total_cpu_seconds': r.get('total_cpu_seconds'), 'cpu_scope': r.get('cpu_scope'),
                'worker_maxrss_kib': r.get('worker_maxrss_kib'), 'child_maxrss_kib': r.get('child_maxrss_kib'),
                'model_calls': r.get('model_calls'), 'model_tokens': r.get('model_tokens'),
                'human_active_minutes': r.get('human_active_minutes'), 'human_review_minutes': r.get('human_review_minutes'),
            },
            'recorded_operational_model_cost': r.get('operational_model_cost'),
            'recorded_operational_model_cost_currency': r.get('operational_model_cost_currency'),
            'actual_costs': {key: None for key in UNKNOWN_COSTS},
            'stage_observations_not_additional_cost_rows': r.get('stage_observations', []),
            'retained_tool_sha256': r.get('retained_tool_sha256'),
            'retained_tool_created_sha256': r.get('retained_tool_created_sha256'),
            'unplanned_operator_interventions_reported': r.get('unplanned_operator_interventions'),
            'intervention_count_scope': r.get('intervention_count_scope'),
            'measurement_caveat': 'Injected exception handling fixture: the tiny outer interval is a mock test interval, not an observed 35-second work attempt.' if injected else 'Worker CPU includes completed children; stage values are components, never added again. Complete delivery cost is unknown.',
        }
        entries.append(entry)
        if injected:
            add_event('development-timeout-fixture', 'injected_development_control', r['error'], provenance(path),
                      outcome='Expected failed receipt persisted; not a primary job failure.', injected=True,
                      actor='automated_test_harness', details={'recorded_outer_interval_seconds': r.get('process_turnaround_seconds'), 'actual_35_second_wait_observed': False})
        elif r.get('accepted') is False:
            category = 'measured_primary_failure' if scope == 'primary_confirmation' else 'other_recorded_job_failure'
            add_event('failure:' + entry['id'], category, r.get('error'), provenance(path), outcome='Rejected or incomplete output retained.')
    attempts_path = root / 'development/ATTEMPTS.jsonl'
    if attempts_path.is_file():
        for index, line in enumerate(attempts_path.read_text().splitlines(), 1):
            if not line.strip():
                continue
            item = json.loads(line)
            origin = provenance(attempts_path, 'line ' + str(index))
            add_event(item['id'], 'development_failure' if item.get('status') == 'FAILED' else 'development_activity', item.get('stage'), origin,
                      outcome=item.get('status'), details=item)
            # Receipt-bearing worker is already represented; other development resource observations are missing.
            if item.get('packet') != 'worker_04':
                entries.append({'id': 'development-log:' + item['id'], 'scope': 'development_activity',
                                'provenance': origin, 'status': item.get('status'), 'description': item.get('stage'),
                                'actual_costs': {key: None for key in UNKNOWN_COSTS},
                                'measured_resources': {'total_cpu_seconds': None, 'worker_wall_seconds': None,
                                                       'human_active_minutes': None, 'model_calls': None, 'model_tokens': None},
                                'note': 'Unmetered research construction; no duration inferred from shell/tool wall time.'})
    pre = root / 'development/pre_freeze_review.json'
    if pre.is_file():
        review = read_json(pre)
        for item in review['findings']:
            add_event('pre-freeze:' + item['id'], 'pre_freeze_review_correction', item['issue'], provenance(pre, item['id']),
                      outcome='Corrections documented in dev-006 before the freeze.', details=item)
    corrupt = root / 'development/development_oracle_verification.json'
    if corrupt.is_file():
        for item in read_json(corrupt).get('corruption_checks', []):
            add_event('oracle-corruption:' + item['mutation'], 'injected_development_control', item['mutation'], provenance(corrupt, item['mutation']),
                      outcome='EXPECTED_REJECTION' if item['rejected'] else 'UNEXPECTED_ACCEPTANCE', injected=True,
                      actor='independent_role_test_harness', details=item)
    controls_path = root / 'raw/controls/controls.json'
    if controls_path.is_file():
        controls = read_json(controls_path)
        for case in controls['cases']:
            origin = provenance(controls_path, case['id'])
            entries.append({'id': 'control:' + case['id'], 'scope': 'predeclared_operating_control', 'provenance': origin,
                            'status': case['status'], 'measured_resources': {'elapsed_seconds': int(case['elapsedNanoseconds']) / 1_000_000_000,
                            'total_cpu_seconds': None, 'human_active_minutes': None, 'model_calls': 0, 'model_tokens': 0},
                            'actual_costs': {key: None for key in UNKNOWN_COSTS},
                            'note': 'Finite control-case interval including its verification; not an accepted employer-job denominator.'})
            add_event('control:' + case['id'], 'predeclared_control_case', case['title'], origin, outcome=case['status'],
                      injected=True, actor='automated_control_harness', details=case['observations'])
        for path in sorted((root / 'raw/controls').glob('C*/*attempt.json')):
            attempt = read_json(path)
            if attempt.get('status') == 'rejected':
                add_event('refusal:' + str(path.relative_to(root)), 'expected_control_refusal', attempt['error']['message'], provenance(path),
                          outcome='EXPECTED_REFUSAL_SEPARATE_FROM_BUSINESS_ACCEPTANCE', injected=True, actor='automated_control_harness', details=attempt['error'])
    browser_attempts = root / 'browser/BUILD_ATTEMPTS.jsonl'
    if browser_attempts.is_file():
        for index, line in enumerate(browser_attempts.read_text().splitlines(), 1):
            if not line.strip():
                continue
            item = json.loads(line)
            add_event('browser-attempt:' + str(item['attempt']), 'browser_build_or_qa_harness_failure', item.get('error'), provenance(browser_attempts, 'line ' + str(index)),
                      outcome=item.get('outcome'), details=item)
    qa_path = root / 'browser/qa/QA_REPORT.json'
    if qa_path.is_file():
        qa = read_json(qa_path)
        add_event('browser-final-qa', 'browser_product_qa', qa['scope'], provenance(qa_path), outcome=qa['status'],
                  actor='automated_browser_test_harness', details={'checks': qa['total'], 'passed': qa['passed'], 'html_sha256': qa['htmlSha256'], 'page_errors': qa['pageErrors']})
        for item in qa['checks']:
            if not item['passed']:
                add_event('browser-failed-check:' + item['name'], 'browser_product_qa_failure', item['name'], provenance(qa_path, item['name']), outcome='FAIL', details=item)
    audit_path = root / 'verification/independent_review.json'
    if audit_path.is_file():
        audit = read_json(audit_path)
        if audit.get('audit_development_note'):
            add_event('saved-output-auditor-launcher', 'audit_harness_failure', audit['audit_development_note'], provenance(audit_path, 'audit_development_note'), outcome='Evaluator corrected; recorded results unchanged.')
        add_event('saved-output-independent-review', 'independent_role_verification', 'Saved evidence revalidated without producing-job reruns.', provenance(audit_path), outcome=audit['status'], details={'outer_checks': audit['outer_checks'], 'oracle_checks': audit['oracle_checks'], 'issues': audit['issues']})
    initial_build = root / 'paper/build-initial.log'
    if initial_build.is_file():
        lines = [(i, line) for i, line in enumerate(initial_build.read_text(errors='replace').splitlines(), 1) if line.startswith('!')]
        if lines:
            add_event('publication-tex-noalign', 'publication_build_failure', 'Initial LaTeX build failed with misplaced noalign; table macro assembly was corrected.',
                      provenance(initial_build), outcome='Failure log preserved; later build reported successful.', details={'error_lines': lines})
    if initial_build.is_file():
        add_event('publication-initial-cwd', 'publication_build_failure', 'Initial figure/publication assembly used the wrong working directory; corrected before the successful build.',
                  {'kind': 'parent_agent_report', 'origin': '/root coordination message in this research session', 'artifact_hash': None},
                  outcome='Reported corrected by publication owner; elapsed time and cost unmetered.')
        add_event('publication-layout-corrections', 'publication_visual_correction', 'Initial signature-figure and chart layouts were corrected before final visual review.',
                  {'kind': 'parent_agent_report', 'origin': '/root coordination message in this research session', 'artifact_hash': None},
                  outcome='Publication-development correction; no recorded job result changed.')
    figure_failure = root / 'verification/failed-figure-build.log'
    if figure_failure.is_file():
        add_event('publication-truncated-figure', 'publication_build_failure', 'A fresh clean compile found attention_frontier.pdf truncated, missing xref/endstream (reported size 8804 bytes).',
                  provenance(figure_failure), outcome='Publication owner changed the figure writer to buffered, validated atomic replacement and restarted fresh clean builds.',
                  details={'scope': 'Publication artifact failure, not a scientific result failure.', 'measured_repair_time_seconds': None})
    reproduction_attempts = root / 'reproduction/DEVELOPMENT_ATTEMPTS.jsonl'
    if reproduction_attempts.is_file():
        for index, line in enumerate(reproduction_attempts.read_text().splitlines(), 1):
            if line.strip():
                item = json.loads(line)
                add_event(item['id'], 'reproduction_tooling_development', item['description'], provenance(reproduction_attempts, 'line ' + str(index)), outcome=item['outcome'], details=item)
    clean_build = root / 'verification/CLEAN_BUILD.json'
    if clean_build.is_file():
        item = read_json(clean_build)
        add_event('publication-final-clean-build', 'publication_build_verification', 'Two isolated builds and render verification of every final PDF page.', provenance(clean_build),
                  outcome=item['status'], details={'byte_identical': item['byte_identical'], 'pages': item['pages'], 'all_rendered_pngs_verified': item['all_rendered_pngs_verified'], 'clean_builds': item['clean_builds']})
    visual_paths = set((root / 'verification').glob('*visual*.json')) | set((root / 'verification').glob('visual_pages*.json'))
    for path in sorted(visual_paths):
        item = read_json(path)
        add_event('publication-review:' + path.name, 'publication_visual_review', 'Preserved draft or final page-inspection record; scope and findings remain in the original file.', provenance(path),
                  outcome=item.get('status') if isinstance(item, dict) else None, details=item)
    for event in events:
        if event['category'] in {'browser_build_or_qa_harness_failure', 'browser_product_qa', 'audit_harness_failure', 'publication_build_failure', 'publication_build_verification', 'publication_visual_correction', 'publication_visual_review', 'reproduction_tooling_development'}:
            entries.append({'id': 'unmetered-event:' + event['id'], 'scope': 'publication_and_qa_development',
                            'provenance': event['provenance'], 'status': event['outcome'], 'description': event['description'],
                            'actual_costs': {key: None for key in UNKNOWN_COSTS},
                            'measured_resources': {'total_cpu_seconds': None, 'worker_wall_seconds': None, 'human_active_minutes': None, 'model_calls': None, 'model_tokens': None},
                            'accounting_note': 'Named unmetered event within shared construction/verification categories; no monetary total is inferred or double-counted.'})
    shared = [
        ('research-authoring', 'Study design, scientific writing, coordination and development-assistant usage.'),
        ('runtime-acquisition-setup', 'Source retrieval, integrity checks, dependency/environment setup and integration.'),
        ('capability-construction', 'Constructing and verifying the reusable package, wrapper, exports, independent oracle and browser companion.'),
        ('human-review-supervision', 'Employer/assessor/operator active time was not instrumented; configured review capacity is not observed review.'),
        ('maintenance', 'No production maintenance history or amortization invoice supplied.'),
        ('host-and-provider-invoices', 'Actual host allocation, host invoice and development-model bill were unavailable.'),
        ('verification-publication-qa', 'Independent software audit, original checks, figure builds, LaTeX builds, rendering and browser QA costs are not fully metered.'),
    ]
    for key, description in shared:
        entries.append({'id': 'shared:' + key, 'scope': 'shared_unmetered_investment_or_attention', 'description': description,
                        'actual_costs': {field: None for field in UNKNOWN_COSTS},
                        'measured_resources': {'total_cpu_seconds': None, 'worker_wall_seconds': None, 'human_active_minutes': None, 'model_calls': None, 'model_tokens': None},
                        'allocation_policy': 'Unknown. Do not assume zero; do not amortize until a justified denominator and investment amount are observed.'})
    study_scopes = {'primary_confirmation', 'finite_load_repeat', 'development_selected_public_showcase', 'composed_successor'}
    study_entries = [entry for entry in entries if entry['scope'] in study_scopes]
    groups = {}
    for scope in sorted({entry['scope'] for entry in entries}):
        subset = [entry for entry in entries if entry['scope'] == scope]
        values = [entry['measured_resources'].get('total_cpu_seconds') for entry in subset]
        groups[scope] = {'ledger_entries': len(subset), 'accepted_true': sum(entry.get('accepted') is True for entry in subset),
                         'not_accepted_false': sum(entry.get('accepted') is False for entry in subset),
                         'known_cpu_seconds_subtotal': sum(value for value in values if value is not None),
                         'cpu_missing_count': sum(value is None for value in values),
                         'complete_cpu_seconds': sum(values) if values and all(value is not None for value in values) else None,
                         'actual_fully_allocated_cost': None}
    measured_cpu = [entry['measured_resources']['total_cpu_seconds'] for entry in study_entries]
    costs = {'schema': 'agialpha-complete-cost-ledger/v1', 'assembled_utc': now,
             'accounting_status': 'COMPLETE_CATEGORY_LEDGER_WITH_EXPLICIT_UNMEASURED_COMPONENTS; NOT_A_COMPLETE_INVOICE',
             'scope': 'All available unique saved job receipts, development activity records, eight controls, and shared unmetered costs.',
             'counting_policy': 'One row per unique receipt. Stage observations are nested components, not extra costs. Load repeats consume resources but are not fresh independent jobs. Mock timeout and injected refusals remain separate.',
             'measured_study_receipts': len(study_entries),
             'known_study_worker_cpu_seconds': sum(value for value in measured_cpu if value is not None),
             'study_worker_cpu_missing_count': sum(value is None for value in measured_cpu),
             'total_project_cpu_seconds': None, 'total_project_wall_seconds': None,
             'actual_complete_project_cost': None, 'actual_complete_cost_per_accepted_delivery': None,
             'amortization': {'investment_amount': None, 'eligible_lifetime_accepted_outputs': None, 'allocation_per_attempt': None,
                             'rule': 'When justified, allocate construction F/N_attempts before acceptance adjustment; never present guessed amortization as observed cost.'},
             'cash_savings_observed': None, 'empirical_human_cost_ratio': None,
             'new_human_trial': 'NOT_RUN', 'market_comparison': 'MODELLED_WITH_SOURCED_BENCHMARKS',
             'modelled_economics_separate': ['economics/', 'economics_post/measured_resource_economics.json'],
             'groups': groups, 'entries': entries, 'source_files': list(sources.values()),
             'limits': ['Unknown authoring/setup/review/supervision/maintenance/invoices are null, never zero.',
                        'Zero operational model calls do not price research construction or human attention.',
                        'Reported worker CPU omits final receipt serialization, host idle allocation and uninstrumented orchestration.',
                        'Sums of concurrent per-job intervals are not user elapsed time or scale-batch makespan.']}
    operational = [entry for entry in study_entries if entry.get('unplanned_operator_interventions_reported') is not None]
    interventions = {'schema': 'agialpha-intervention-ledger/v1', 'assembled_utc': now,
                     'scope': 'All explicit development/control/QA failures and interventions found in the named logs, plus the publication-owner report.',
                     'coverage': 'The research session was not continuously instrumented for all human/operator actions; exhaustive whole-session count and attention remain unknown.',
                     'whole_session_intervention_count': None, 'whole_session_human_attention_minutes': None,
                     'operational_receipts_with_reported_intervention_field': len(operational),
                     'reported_unplanned_operational_interventions_sum': sum(entry['unplanned_operator_interventions_reported'] for entry in operational),
                     'scope_of_reported_zero': 'Batch orchestration for named receipts only; does not include setup, authoring, review or these recorded development interventions.',
                     'counts_by_category': dict(collections.Counter(event['category'] for event in events)),
                     'events': events, 'source_files': list(sources.values()),
                     'denominator_rule': 'Intentional corruption, STOP, interruption and bound tests are expected control outcomes. Browser/TeX/auditor construction failures are development evidence, not failures among the 36 frozen business jobs.'}
    if not args.check:
        write_json(root / 'COST_LEDGER.json', costs)
        write_json(root / 'INTERVENTION_LEDGER.json', interventions)
    print(json.dumps({'written': not args.check, 'cost_entries': len(entries), 'study_receipts': len(study_entries),
                      'intervention_events': len(events), 'categories': interventions['counts_by_category'],
                      'complete_cost': None, 'all_human_attention_minutes': None}, indent=2))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
