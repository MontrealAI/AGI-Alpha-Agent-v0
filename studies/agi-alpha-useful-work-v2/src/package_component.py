# SPDX-License-Identifier: Apache-2.0
"""Candidate: produce the decision, source links and evidence inventory together."""
from __future__ import annotations

import argparse
import difflib
import hashlib
import html
import json
from pathlib import Path
import shutil
import time

# Adopt the stronger conventional validator discovered during independent review.
# Its construction is part of this capability's lifecycle cost, not a free asset.
from conventional_package import receipt_check, VERIFIER_SHA256

ROOT = Path(__file__).resolve().parent.parent


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def assemble(job_path, pair_root, out):
    wall, cpu = time.perf_counter(), time.process_time()
    out.mkdir(parents=True, exist_ok=False)
    evidence = out / 'evidence'
    evidence.mkdir()
    job, pair = read(job_path), read(pair_root / 'pair.json')
    failures, verification = [], {}
    worker = ROOT / 'src/manual_probe.py'
    verifier = ROOT / 'src/verify_component.py'
    contract_path = (ROOT / job['contract']['path']).resolve()
    consumer = (ROOT / job['consumer']['directory']).resolve()
    if not contract_path.is_relative_to(ROOT) or not consumer.is_relative_to(ROOT):
        raise ValueError('REGISTERED_INPUT_PATH_REQUIRED')
    if digest(verifier) != VERIFIER_SHA256:
        failures.append('INDEPENDENT_VERIFIER_IDENTITY')
    if pair.get('schema') != 'alpha-component-pair/v1' or pair.get('arm') != 'retained':
        failures.append('PAIR_SCHEMA_OR_ARM')
    if pair.get('worker_path') != 'src/manual_probe.py' or pair.get('worker_sha256') != digest(worker):
        failures.append('WORKER_IDENTITY')
    for name in ('api', 'models'):
        if digest(consumer / (name + '.py')) != job['consumer'][name + '_sha256']:
            failures.append('JOB_CONSUMER_IDENTITY:' + name)
    if digest(job_path) != pair.get('job_sha256') or digest(pair_root / 'job.json') != digest(job_path):
        failures.append('JOB_BINDING')
    if pair.get('custody_complete') is not True:
        failures.append('PAIR_CUSTODY')
    for row in pair.get('artifacts', []):
        path = pair_root / row['path']
        if (not path.resolve().is_relative_to(pair_root.resolve()) or not path.is_file()
                or digest(path) != row['sha256'] or path.stat().st_size != row['bytes']):
            failures.append('PAIR_ARTIFACT:' + row['path'])
    required_names = {'job.json'} | {f'{side}-{name}.json' for side in ('before', 'after')
                                   for name in ('observations', 'execution', 'verification', 'verification-execution')}
    if not required_names.issubset({row['path'] for row in pair.get('artifacts', [])}):
        failures.append('PAIR_MANIFEST_INCOMPLETE')
    environment_paths = {}
    for side in ('before', 'after'):
        environment = (ROOT / job[side]['environment']).resolve()
        if not environment.is_relative_to(ROOT):
            raise ValueError('ENVIRONMENT_PATH')
        environment_paths[side] = environment
        observed = pair_root / f'{side}-observations.json'
        verified = pair_root / f'{side}-verification.json'
        if not observed.is_file() or not verified.is_file():
            failures.append('MISSING_OBSERVATION_OR_VERIFICATION:' + side)
            continue
        item = read(verified)
        verification[side] = item
        if item.get('observations_sha256') != digest(observed):
            failures.append('OBSERVATION_BINDING:' + side)
        if item.get('environment_manifest_sha256') != digest(environment / 'preparation.json'):
            failures.append('ENVIRONMENT_BINDING:' + side)
        if item.get('contract_sha256') != job['contract']['sha256']:
            failures.append('CONTRACT_BINDING:' + side)
        if item.get('environment_versions') != job[side]['expected_versions']:
            failures.append('VERSION_BINDING:' + side)
        if item.get('projection_id') != 'native-fastapi-bridge-v2' or item.get('native_import_route') is not True:
            failures.append('PROJECTION_BINDING:' + side)
        for name in ('execution', 'verification-execution'):
            receipt_path = pair_root / f'{side}-{name}.json'
            if not receipt_path.is_file():
                failures.append('MISSING_EXECUTION_RECEIPT:' + side + name)
                continue
            receipt = read(receipt_path)
            required = observed if name == 'execution' else verified
            if name == 'execution':
                bound = [job_path, worker, ROOT / 'src/measured_run.py', contract_path,
                         ROOT / 'protocol/component-projections.json', consumer / 'api.py', consumer / 'models.py',
                         environment / 'requirements.lock', environment / 'preparation.json', environment / 'venv/bin/python']
                allowed_exits = {0, 1}
            else:
                bound = [job_path, verifier, contract_path, ROOT / 'protocol/component-projections.json', observed,
                         consumer / 'api.py', consumer / 'models.py', ROOT / 'discovery/test_api_boundary.py',
                         environment / 'preparation.json']
                allowed_exits = {0, 2}
            failures.extend(receipt_check(receipt, bound, required, allowed_exits, side + ':' + name))
    before_status = verification.get('before', {}).get('status')
    after_status = verification.get('after', {}).get('status')
    if failures or before_status != 'PRESERVED_WITHIN_COMPONENT_CONTRACT' or after_status not in (
            'PRESERVED_WITHIN_COMPONENT_CONTRACT', 'BEHAVIOR_MISMATCH'):
        decision = 'INCOMPLETE_HOLD'
    elif after_status == 'BEHAVIOR_MISMATCH':
        decision = 'COMPONENT_REGRESSION'
    else:
        decision = 'SCOPED_COMPONENT_PRESERVED'
    changed = [{'package': name, 'before': version, 'after': job['after']['expected_versions'][name]}
               for name, version in sorted(job['before']['expected_versions'].items())
               if version != job['after']['expected_versions'][name]]
    if not changed:
        decision = 'NO_SUBSTANTIVE_CHANGE'
        failures.append('IDENTICAL_INPUT_IS_NOT_NEW_MISSION')
    contract = read(contract_path)
    if digest(contract_path) != job['contract']['sha256']:
        raise ValueError('CURRENT_CONTRACT_IDENTITY')
    status_rows = {side: {r['id']: r for r in verification.get(side, {}).get('cases', [])}
                   for side in ('before', 'after')}
    coverage = []
    for case in contract['cases']:
        requirement = case['requirement']
        original = 'alpha_factory_v1/core/runtime/' + Path(requirement['path']).name
        if requirement['path'].startswith('discovery/'):
            original = 'tests/runtime/test_api_boundary.py'
        start, end = requirement['lines']
        coverage.append({'id': case['id'], 'before': status_rows['before'].get(case['id'], {}).get('status', 'MISSING'),
                         'after': status_rows['after'].get(case['id'], {}).get('status', 'MISSING'),
                         'source_url': 'https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/'
                         '804e1afeb78ea48fb4807d76b336803aa0906a20/' + original + f'#L{start}-L{end}',
                         'requirement': requirement,
                         'after_errors': status_rows['after'].get(case['id'], {}).get('errors', [])})
    for path in sorted(pair_root.iterdir()):
        if path.is_file():
            shutil.copyfile(path, evidence / path.name)
    for side, environment in environment_paths.items():
        for source, name in [('requirements.lock', f'{side}.lock'), ('preparation.json', f'{side}-environment.json')]:
            shutil.copyfile(environment / source, evidence / name)
    for path in [contract_path, ROOT / 'protocol/component-projections.json', ROOT / 'src/verify_component.py']:
        shutil.copyfile(path, evidence / path.name)
    old, new = [(environment_paths[side] / 'requirements.lock').read_text() for side in ('before', 'after')]
    patch = ''.join(difflib.unified_diff(old.splitlines(keepends=True), new.splitlines(keepends=True),
                                        fromfile='before-component.lock', tofile='proposed-component.lock'))
    (out / 'proposed-component-lock.patch').write_text(patch)
    (out / 'requirement-results.json').write_text(json.dumps(coverage, indent=2) + '\n')
    actions = {
        'SCOPED_COMPONENT_PRESERVED': 'Accept this component evidence for further application qualification. Keep the existing native lock until the remaining release checks are complete.',
        'COMPONENT_REGRESSION': 'Do not adopt this tuple for the declared component contract. Reproduce the listed failing consumer cases, preserve the working tuple, and review the attributable change.',
        'INCOMPLETE_HOLD': 'Do not decide compatibility from this packet. Resolve the named missing evidence or execution failure and rerun the same contract.',
        'NO_SUBSTANTIVE_CHANGE': 'Reuse the existing decision; the unchanged request is not another mission.'
    }
    packet = {'schema': 'alpha-component-decision/v1', 'mission_id': job['mission_id'], 'phase': job['phase'],
              'arm': 'retained', 'decision': decision, 'useful_outcome_accepted': decision in (
                  'SCOPED_COMPONENT_PRESERVED', 'COMPONENT_REGRESSION'),
              'customer_acceptance_observed': False, 'trigger': job['trigger'], 'action': actions[decision],
              'changes': changed, 'contract_sha256': job['contract']['sha256'], 'job_sha256': digest(job_path),
              'source_identity': job['consumer'], 'before_versions': job['before']['expected_versions'],
              'after_versions': job['after']['expected_versions'], 'cases': len(coverage),
              'verification': {side: {key: verification.get(side, {}).get(key) for key in ('status', 'counts')}
                               for side in ('before', 'after')},
              'failed_requirements': [r for r in coverage if r['after'] != 'PASS'], 'custody_failures': failures,
              'remaining_customer_work': ['Decide whether the refresh is needed.',
                  'Qualify the full native application lock and supported platforms.',
                  'Complete authorized authentication, persistence and mission execution checks.',
                  'Follow existing owner review and exact-source release gates.'],
              'limits': contract['coverage_limits'] + [
                  'The component lock is not a replacement for the complete native application lock.',
                  'This packet grants no authentication, execution, settlement or publication authority.',
                  'Historical confirmation inputs are representative maintenance assessments, not paid orders.'],
              'cost': {'marginal_money_usd': None, 'recurring_money_usd': None, 'fully_loaded_money_usd': None,
                       'customer_price_usd': None, 'actual_customer_receipts_usd': 0,
                       'customer_minutes': None, 'operator_minutes': None,
                       'pair_wall_seconds': pair['wall_seconds'],
                       'pair_process_cpu_seconds': pair['process_cpu_seconds'],
                       'pair_child_cpu_seconds': pair['child_cpu_seconds'],
                       'setup_reference': [job[side]['environment'] + '/preparation.json' for side in ('before', 'after')],
                       'aggregation': 'Pair totals include execution and independent verification; do not add their nested receipts again. Setup, discovery, construction, correction, packaging and upkeep are separate recorded costs.'}}
    (out / 'decision.json').write_text(json.dumps(packet, indent=2) + '\n')
    replay = ('Replay from the complete companion root, using new output paths:\n\n'
              f'python src/run_pair.py --job {job_path.relative_to(ROOT)} --out results/replay/{job["mission_id"]}/pair --arm retained\n'
              f'python src/package_component.py --job {job_path.relative_to(ROOT)} --pair-root results/replay/{job["mission_id"]}/pair --out results/replay/{job["mission_id"]}/package\n\n'
              'Recreate missing pinned environments with the saved wheels and an explicit relocated offline plan.\n'
              'The component patch is a research environment change; full application qualification remains required.\n')
    (out / 'reproduce.txt').write_text(replay)
    for language in ('en', 'fr'):
        fr = language == 'fr'
        title = 'Une décision, avec ses preuves' if fr else 'A decision with its evidence'
        action = ('Accepter ces preuves de compatibilité des composants pour la qualification suivante; conserver le verrou natif actuel.'
                  if fr and decision == 'SCOPED_COMPONENT_PRESERVED' else
                  'Ne pas adopter ce changement avant de résoudre les échecs ou les preuves manquantes.' if fr else packet['action'])
        rows = ''.join(f'<tr><td>{html.escape(r["package"])}</td><td>{html.escape(r["before"])}</td><td>{html.escape(r["after"])}</td></tr>' for r in changed)
        heading = 'Prochaine action' if fr else 'Next action'
        cost = ('Coût monétaire complet, prix et temps client inconnus. Aucun paiement client reçu.' if fr else
                'Complete monetary cost, price and customer time are unknown. No customer payment was collected.')
        limitation = ('La vérification porte sur les composants déclarés. La qualification complète de l’application reste à effectuer.' if fr else
                      'The evidence covers the declared components. Full application qualification remains required.')
        document = f'''<!doctype html><html lang="{language}"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>{title}</title>
<style>body{{margin:0;background:#f7f4fc;color:#231236;font:17px/1.6 system-ui}}main{{max-width:960px;margin:auto;padding:36px 24px}}header{{background:#271043;color:white;padding:36px;border-radius:18px}}h1{{font-size:clamp(32px,5vw,54px);line-height:1.1}}small{{letter-spacing:.13em}}h2{{color:#602c91;margin-top:2em}}table{{width:100%;border-collapse:collapse}}th,td{{text-align:left;padding:12px;border-bottom:1px solid #d8cbe7}}.note{{padding:20px;background:#ece4f6;border-left:4px solid #9b62c8}}a{{color:#6b2c9d}}code{{overflow-wrap:anywhere}}</style>
<main><header><small>AGI ALPHA · SUCCESSOR Ω · TRANSFORMATIONAL INTELLIGENCE ∞</small><h1>{title}</h1><p>{html.escape(job['mission_id'])}</p></header>
<h2>{heading}</h2><p>{html.escape(action)}</p><div class="note">{limitation}</div>
<h2>{'Changement évalué' if fr else 'Assessed change'}</h2><table><thead><tr><th>Package</th><th>{'Avant' if fr else 'Before'}</th><th>{'Après' if fr else 'After'}</th></tr></thead><tbody>{rows}</tbody></table>
<h2>{'Résultat vérifié' if fr else 'Verified result'}</h2><p><code>{decision}</code> · {len(coverage)} {'cas déclarés par environnement' if fr else 'declared cases per environment'}.</p>
<p>{'Les assertions ne sont pas des commandes clients.' if fr else 'Assertions are not customer orders.'}</p><h2>{'Coût et responsabilité' if fr else 'Cost and responsibility'}</h2><p>{cost}</p>
<p>{'Les journaux conservent les coûts de préparation, exécution et vérification. Les coûts non mesurés restent inconnus.' if fr else 'The records retain preparation, execution and verification resources. Unmeasured costs remain unknown.'}</p>
<h2>{'Téléchargements' if fr else 'Downloads'}</h2><p><a href="decision.json">decision.json</a> · <a href="requirement-results.json">requirement-results.json</a> · <a href="proposed-component-lock.patch">proposed-component-lock.patch</a> · <a href="reproduce.txt">reproduce.txt</a></p>
<p><a href="report-{'en' if fr else 'fr'}.html">{'English' if fr else 'Français'}</a></p></main></html>'''
        (out / f'report-{language}.html').write_text(document)
    manifest = [{'path': str(path.relative_to(out)), 'sha256': digest(path), 'bytes': path.stat().st_size}
                for path in sorted(out.rglob('*')) if path.is_file()]
    (out / 'artifact-manifest.json').write_text(json.dumps({'files': manifest}, indent=2) + '\n')
    for row in manifest:
        if digest(out / row['path']) != row['sha256']:
            raise ValueError('PACKAGE_INTEGRITY')
    receipt = {'schema': 'component-package-assembly/v1', 'wall_seconds': time.perf_counter() - wall,
               'cpu_seconds': time.process_time() - cpu, 'files_verified': len(manifest), 'money_usd': None,
               'assembler_sha256': digest(Path(__file__)), 'manifest_sha256': digest(out / 'artifact-manifest.json')}
    (out / 'assembly-receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    return packet


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--job', type=Path, required=True)
    parser.add_argument('--pair-root', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    result = assemble(args.job.resolve(), args.pair_root.resolve(), args.out.resolve())
    print(json.dumps({'decision': result['decision'], 'accepted': result['useful_outcome_accepted']}))


if __name__ == '__main__':
    main()
