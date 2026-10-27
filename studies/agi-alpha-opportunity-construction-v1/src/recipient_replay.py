"""Six-case local recipient portability check, separate from access authority.

Run `freeze`, then `run`. Policy and original evidence are never overwritten.
Recipients get only the two public modules, then receive freshly generated case
inputs by CLI path. Neither copied answers nor a model-agent runtime is supplied.
"""
from __future__ import annotations
import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import sys
import time
from collections import Counter

BASE = Path(__file__).resolve().parents[1]
OUT = BASE / 'technical/recipient_transfer'
PINS = {
    'e1_instrument_v2.py': '4a57ec8f74c72c85c6209b4123692af5c95ac63ca15e856a3626bfdf5c3d1406',
    'e1_verify_v2.py': 'aa673747ebca69ea44d5ce70c251216705d103f39c4ae85c7e120d1be226cd51',
}
ROUTES = {
    'authenticated_access_copy': 'technical/research_access_fixture_v2/authenticated_recipient/src',
    'ordinary_library_copy': 'technical/research_access_fixture_v2/ordinary_library/src',
}


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def canonical_sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def normalized(value):
    # This is the only field excluded. Entire decisions, refusals, searches,
    # cost ledgers, witnesses and input snapshots remain in the comparison.
    if isinstance(value, dict):
        return {key: normalized(item) for key, item in value.items() if key != 'elapsed_seconds'}
    if isinstance(value, list):
        return [normalized(item) for item in value]
    return value


def authority():
    return {
        'local_subprocess_execution_basis': 'Explicit user-authorized local research execution conveyed by the parent task: execute copied public instrument bytes on six fresh synthetic inputs in local subprocesses.',
        'access_fixture_basis': 'H fixture previously retrieved the public code for local assessment. Its signed action is local-code-assessment and execution_authorized is false.',
        'execution_authority_inferred_from_access_fixture': False,
        'native_or_ens_execution_grant_used': False,
        'live_ens_resolution_or_live_agent_execution': False,
        'native_roles_or_trust_modified': False,
        'scope': 'Local Python processes in the authorized research workspace; no external service, actual care, funds, customer data or operational deployment.',
    }


def freeze():
    if OUT.exists():
        raise RuntimeError('Recipient-transfer directory already exists; preserve prior evidence')
    OUT.mkdir(parents=True)
    existing = json.loads((BASE / 'technical/independent_audit/FRESH_V2_POLICY.json').read_text())
    excluded = {row['seed'] for row in existing['cases']} | {784103 + i * 7919 for i in range(48)} | {910271}
    seeds = []
    while len(seeds) < 6:
        candidate = secrets.randbits(64)
        if candidate not in excluded and candidate not in seeds:
            seeds.append(candidate)
    for route, source in ROUTES.items():
        for name, pin in PINS.items():
            assert sha(BASE / source / name) == pin, (route, name, 'source pin mismatch')
    policy = {
        'schema': 'agi-alpha.recipient-portability-policy.v1',
        'frozen_at_utc': now(),
        'runner_sha256': sha(__file__),
        'source_pins': PINS,
        'routes': ROUTES,
        'case_count': 6,
        'seeds': seeds,
        'generation_family': 'independent_audit_v2.fresh_case(seed, index), index 0..5; same bounded two-employer, four-worker, two-child family, with new identities, times, commutes, permissions, prices and budgets. Index 0 is the existing family\'s declared positive anchor.',
        'generator_sha256': sha(BASE / 'src/independent_audit_v2.py'),
        'base_generator_sha256': sha(BASE / 'src/independent_audit_cases.py'),
        'input_creation_order': 'Freeze this policy; hand off only the pinned public constructor and checker to both clean recipient directories; then generate all six new inputs. No reference answers or previous offers are handed off.',
        'process_protocol': 'Run each route once on each new input in a separate local Python process, using the public CLI compare command. Twelve processes total. Retain raw results, commands, exit codes, stdout/stderr, input hashes and all refusals.',
        'recipient_directory_contents': ['e1_instrument_v2.py', 'e1_verify_v2.py'],
        'normalization': 'Recursively remove only elapsed_seconds, then compare the entire JSON decision/result document including all four controls and full offers.',
        'success_criterion': 'Every process exits successfully and writes a comparison result; both routes produce exactly equal normalized outputs for each of the six inputs. No case selection after outcomes or replacement seeds.',
        'scope_limit': 'Execution portability through local subprocesses; not independent LLM competence, OS isolation, live .eth authorization, external acceptance or economic superiority.',
        'authority': authority(),
        'cost_accounting': {'model_and_tool_costs': 'unmetered', 'execution_monetary_cost': 'unmetered', 'priced_amount': None, 'timing_not_converted_to_money': True},
        'economic_retention': 'HOLD',
        'no_additional_tests_planned': True,
    }
    write(OUT / 'POLICY_FREEZE.json', policy)
    print(json.dumps({'policy':str(OUT/'POLICY_FREEZE.json'), 'sha256':sha(OUT/'POLICY_FREEZE.json'), 'frozen_at_utc':policy['frozen_at_utc'], 'case_count':6}))


def run():
    policy = json.loads((OUT / 'POLICY_FREEZE.json').read_text())
    assert sha(__file__) == policy['runner_sha256'], 'Runner changed after freeze'
    assert sha(BASE / 'src/independent_audit_v2.py') == policy['generator_sha256']
    assert sha(BASE / 'src/independent_audit_cases.py') == policy['base_generator_sha256']
    if (OUT / 'SOURCE_HANDOFF.json').exists():
        raise RuntimeError('Handoff already performed; no silent rerun or overwrite')
    started = now()
    handoff = {'started_at_utc':started, 'routes':{}, 'no_answers_or_case_inputs_copied':True, 'authority':authority()}
    for route, source in ROUTES.items():
        destination = OUT / 'recipients' / route
        destination.mkdir(parents=True, exist_ok=False)
        files = []
        for name, pin in PINS.items():
            original = BASE / source / name
            assert sha(original) == pin
            shutil.copyfile(original, destination / name)
            assert sha(destination / name) == pin
            files.append({'source':str(original.relative_to(BASE)), 'recipient_path':str((destination/name).relative_to(BASE)), 'sha256':pin})
        assert sorted(x.name for x in destination.iterdir()) == sorted(PINS)
        handoff['routes'][route] = {'directory':str(destination.relative_to(BASE)), 'files':files, 'only_two_public_modules':True}
    handoff['completed_at_utc'] = now()
    write(OUT / 'SOURCE_HANDOFF.json', handoff)

    # This generator runs only in the coordinator, after code handoff. It is not
    # copied into, imported by, or used to supply answers to either recipient.
    from independent_audit_v2 import fresh_case
    (OUT / 'inputs').mkdir()
    generated = []
    for index, seed in enumerate(policy['seeds']):
        case, metadata = fresh_case(seed, index)
        case['case_id'] = f'recipient_fresh_{index}_{seed:016x}'
        case['disclosures'].append('New local recipient portability input; generated after public-code handoff; no answer supplied.')
        path = OUT / 'inputs' / f'case_{index:02d}.json'
        write(path, case)
        generated.append({'case_id':case['case_id'], 'created_at_utc':now(), 'input_path':str(path.relative_to(BASE)), 'input_file_sha256':sha(path), 'input_canonical_sha256':canonical_sha(case), 'generation':metadata})
    inputs_record = {'created_after_source_handoff':all(row['created_at_utc']>handoff['completed_at_utc'] for row in generated), 'inputs':generated, 'answers_supplied':False}
    assert inputs_record['created_after_source_handoff']
    write(OUT / 'INPUT_MANIFEST.json', inputs_record)

    results = []
    processes = []
    env = dict(os.environ)
    env.pop('PYTHONPATH', None)
    for route in ROUTES:
        (OUT / 'outputs' / route).mkdir(parents=True)
    for index, entry in enumerate(generated):
        route_results = {}
        for route in ROUTES:
            recipient = OUT / 'recipients' / route
            output = OUT / 'outputs' / route / f'case_{index:02d}.json'
            command = [sys.executable, '-B', '-s', '-E', str(recipient/'e1_instrument_v2.py'), 'compare', '--input', str(BASE/entry['input_path']), '--output', str(output)]
            wall_start = time.perf_counter()
            process_start = now()
            proc = subprocess.Popen(command, cwd=recipient, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            stdout, stderr = proc.communicate(timeout=30)
            observed = {'case_id':entry['case_id'], 'route':route, 'command_argv':command, 'cwd':str(recipient), 'pid':proc.pid, 'started_at_utc':process_start, 'finished_at_utc':now(), 'exit_code':proc.returncode, 'elapsed_wall_seconds':time.perf_counter()-wall_start, 'stdout':stdout, 'stderr':stderr, 'input_file_sha256_before':entry['input_file_sha256'], 'input_file_sha256_after':sha(BASE/entry['input_path']), 'source_sha256_after':{name:sha(recipient/name) for name in PINS}}
            observed['output_path'] = str(output.relative_to(BASE)) if output.exists() else None
            observed['output_sha256'] = sha(output) if output.exists() else None
            processes.append(observed)
            if proc.returncode == 0 and output.exists():
                value = json.loads(output.read_text())
                clean = normalized(value)
                normalized_path = output.with_name(output.stem+'.normalized.json')
                write(normalized_path, clean)
                route_results[route] = value
                observed['normalized_output_path'] = str(normalized_path.relative_to(BASE))
                observed['normalized_output_sha256'] = canonical_sha(clean)
        matching = len(route_results)==2 and normalized(route_results['authenticated_access_copy']) == normalized(route_results['ordinary_library_copy'])
        outcomes = {}
        for route, value in route_results.items():
            outcomes[route] = {
                'schema':value.get('schema'),
                'statuses':{mode:row['status'] for mode,row in value.get('results',{}).items()},
                'refusals':{mode:{'status':row['status'],'rejection_reasons':row.get('rejection_reasons'), 'minimum_funding_shortfall_cents':row.get('minimum_funding_shortfall_cents'), 'exhaustive_within_declared_bounds':row.get('exhaustive_within_declared_bounds')} for mode,row in value.get('results',{}).items() if row['status']!='offered'},
                'combined_package_cents':value.get('results',{}).get('combined',{}).get('offer',{}).get('maximum_funded_package_cents') if value.get('results',{}).get('combined',{}).get('offer') else None,
                'within_route_same_formulation_parity':value.get('same_formulation_exact_control',{}).get('identical_selected_result'),
            }
        results.append({'case_id':entry['case_id'], 'input_file_sha256':entry['input_file_sha256'], 'complete_normalized_result_equality':matching, 'outcomes':outcomes})
    recipient_only_public = all(sorted(x.name for x in (OUT/'recipients'/route).iterdir())==sorted(PINS) for route in ROUTES)
    sources_intact = all(sha(OUT/'recipients'/route/name)==pin and sha(BASE/ROUTES[route]/name)==pin for route in ROUTES for name,pin in PINS.items())
    all_processes_ok = all(p['exit_code']==0 and p['output_path'] is not None and p['input_file_sha256_before']==p['input_file_sha256_after'] for p in processes)
    statuses = {route:dict(Counter(row['outcomes'].get(route,{}).get('statuses',{}).get('combined','missing_result') for row in results)) for route in ROUTES}
    summary = {
        'schema':'agi-alpha.recipient-portability-result.v1',
        'policy_sha256':sha(OUT/'POLICY_FREEZE.json'),
        'runner_sha256':sha(__file__),
        'started_at_utc':started, 'finished_at_utc':now(),
        'authority':authority(),
        'source_pins':PINS,
        'case_count':len(results), 'process_count':len(processes),
        'processes_successful':sum(p['exit_code']==0 and p['output_path'] is not None for p in processes),
        'full_normalized_equal_cases':sum(row['complete_normalized_result_equality'] for row in results),
        'combined_status_counts_by_route':statuses,
        'fresh_inputs_created_after_source_handoff':inputs_record['created_after_source_handoff'],
        'recipient_directories_contain_only_public_modules_after_execution':recipient_only_public,
        'source_pins_unchanged':sources_intact,
        'all_refusals_retained':True,
        'normalization_removed_only':['elapsed_seconds'],
        'success':len(results)==6 and len(processes)==12 and all_processes_ok and recipient_only_public and sources_intact and all(row['complete_normalized_result_equality'] for row in results),
        'cases':results,
        'cost_accounting':policy['cost_accounting'],
        'economic_retention':'HOLD',
        'interpretation':'Public V2 code copied through two access routes executed on six newly generated inputs in distinct local processes. Equality establishes this bounded portability/control check, not independent LLM competence, live .eth authority, a security sandbox, economic advantage or real childcare delivery.',
        'evidence':{'policy':'technical/recipient_transfer/POLICY_FREEZE.json','handoff':'technical/recipient_transfer/SOURCE_HANDOFF.json','inputs':'technical/recipient_transfer/INPUT_MANIFEST.json','process_commands_and_logs':'technical/recipient_transfer/PROCESS_LOG.json','raw_and_normalized_results':'technical/recipient_transfer/outputs/'},
        'existing_frozen_evidence_modified':False,
    }
    write(OUT/'PROCESS_LOG.json', processes)
    write(OUT/'SUMMARY.json', summary)
    print(json.dumps({key:summary[key] for key in ['success','case_count','process_count','processes_successful','full_normalized_equal_cases','combined_status_counts_by_route','fresh_inputs_created_after_source_handoff','recipient_directories_contain_only_public_modules_after_execution','source_pins_unchanged','economic_retention']},indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['freeze','run'])
    args = parser.parse_args()
    freeze() if args.command=='freeze' else run()
