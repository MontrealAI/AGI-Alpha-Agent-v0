# SPDX-License-Identifier: Apache-2.0
"""Preserved assembly of the first manual development work package.

This is a retained incumbent asset. It is not an untouched confirmation result.
"""
from __future__ import annotations

import datetime
import difflib
import hashlib
import json
from pathlib import Path
import shutil
import time

ROOT = Path(__file__).resolve().parent.parent


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    started, cpu = time.perf_counter(), time.process_time()
    destination = ROOT / 'results/development/first-delivery'
    destination.mkdir(parents=True, exist_ok=False)
    (destination / 'evidence').mkdir()
    before = ROOT / 'results/development/baseline-bridge-verification.json'
    after = ROOT / 'results/development/target-verification.json'
    verifications = [json.loads(path.read_text()) for path in (before, after)]
    if any(item['status'] != 'PRESERVED_WITHIN_COMPONENT_CONTRACT' for item in verifications):
        raise ValueError('FIRST_DELIVERY_REQUIRES_BOTH_INDEPENDENT_RESULTS')
    bindings = []
    for label, environment in [('baseline-bridge', 'development-baseline-bridge-environment'),
                               ('target', 'development-target-environment')]:
        for suffix in ('observations.json', 'execution.json', 'verification.json', 'verification-execution.json'):
            path = ROOT / 'results/development' / f'{label}-{suffix}'
            target = destination / 'evidence' / path.name
            shutil.copyfile(path, target)
            bindings.append({'source': str(path.relative_to(ROOT)), 'package_path': str(target.relative_to(destination)),
                             'sha256': digest(path), 'bytes': path.stat().st_size})
        for source_name, target_name in [('requirements.lock', f'{label}.lock'),
                                          ('preparation.json', f'{label}-environment.json')]:
            path = ROOT / 'data' / environment / source_name
            target = destination / 'evidence' / target_name
            shutil.copyfile(path, target)
            bindings.append({'source': str(path.relative_to(ROOT)), 'package_path': str(target.relative_to(destination)),
                             'sha256': digest(path), 'bytes': path.stat().st_size})
    for rel in ['protocol/component-contract.json', 'protocol/component-projections.json',
                'protocol/intent-charter.json', 'src/manual_probe.py', 'src/verify_component.py',
                'src/measured_run.py', 'data/consumer/api.py', 'data/consumer/models.py',
                'discovery/test_api_boundary.py']:
        path = ROOT / rel
        target = destination / 'evidence' / path.name
        shutil.copyfile(path, target)
        bindings.append({'source': rel, 'package_path': str(target.relative_to(destination)),
                         'sha256': digest(path), 'bytes': path.stat().st_size})
    old_lock = (destination / 'evidence/baseline-bridge.lock').read_text()
    new_lock = (destination / 'evidence/target.lock').read_text()
    patch = ''.join(difflib.unified_diff(old_lock.splitlines(keepends=True), new_lock.splitlines(keepends=True),
                                        fromfile='baseline-component.lock', tofile='proposed-component.lock'))
    (destination / 'proposed-component-lock.patch').write_text(patch)
    contract = json.loads((ROOT / 'protocol/component-contract.json').read_text())
    result = {
        'schema': 'alpha-component-decision/v1', 'mission_id': 'native-component-refresh-development',
        'phase': 'exposed-development', 'decision': 'SCOPED_COMPONENT_PRESERVED',
        'acceptance': 'Internally verified component work package; customer acceptance not observed.',
        'buyer': 'Maintainer of the AGI ALPHA native Python agent',
        'trigger': 'Proposed refresh of the actual native component tuple to stable versions selected at the declared cutoff.',
        'before_versions': verifications[0]['environment_versions'],
        'after_versions': verifications[1]['environment_versions'],
        'useful_action': 'Accept the listed component-compatibility evidence for further qualification; keep the current native lock until remaining application and release checks are completed.',
        'accepted_properties': [
            'Required request length, framing, byte limit, origin, disconnect and actual 15-second timeout behavior.',
            'Required security headers and exact forwarded request bytes.',
            'Enumerated strict Mission, Review and Control validation and complete accepted model serialization.'
        ],
        'coverage': {'requirements': len(contract['cases']), 'before_pass': 61, 'after_pass': 61,
                     'consumer_source_revision': 'eb07086ac42799ff45f7b1c946a2f7c514bd3bbc',
                     'current_equal_source_revision': '804e1afeb78ea48fb4807d76b336803aa0906a20'},
        'remaining_customer_work': [
            'Decide whether this bounded refresh is needed for the maintained release.',
            'Resolve and qualify the full native application lock and supported platform matrix.',
            'Run authorized whole-application authentication, journal persistence and mission execution checks.',
            'Obtain existing owner review and required exact-source release gates before adoption.'
        ],
        'limits': contract['coverage_limits'] + [
            'The component lock patch is an exact executable research profile, not a replacement for requirements-agent.lock.',
            'No vulnerability audit, production deployment, paid demand or guarantee outside this finite contract.',
            'Neither component passing nor package integrity supplies operator authority.'
        ],
        'corrections_charged': [
            'Preserved provisional eight-package Starlette-direct baseline; corrected original FastAPI import bridge.',
            'Preserved failed environment logger attempt, two failed prelaunch input bindings and verifier schema correction.'
        ],
        'cost': {'marginal_money_usd': None, 'recurring_money_usd': None, 'fully_loaded_money_usd': None,
                 'actual_customer_receipts_usd': 0, 'customer_price_usd': None,
                 'customer_minutes': None, 'operator_minutes': None,
                 'basis': 'Known process, setup, request and storage quantities are retained; inference, billing, maintenance and customer attention are unpriced.'},
        'evidence': bindings,
        'source_urls': [
            'https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/804e1afeb78ea48fb4807d76b336803aa0906a20/alpha_factory_v1/core/runtime/api.py',
            'https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/804e1afeb78ea48fb4807d76b336803aa0906a20/alpha_factory_v1/core/runtime/models.py',
            'https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/804e1afeb78ea48fb4807d76b336803aa0906a20/tests/runtime/test_api_boundary.py'
        ],
        'created_at': datetime.datetime.now(datetime.timezone.utc).isoformat()
    }
    (destination / 'decision.json').write_text(json.dumps(result, indent=2) + '\n')
    report = '''# Dependency refresh: the component evidence is ready

**Decision: preserve the current production lock; accept this component evidence for the next application qualification.**

The proposed Starlette 1.7.0 → 1.10.0 and Pydantic 2.13.5 → 2.14.1 refresh,
with pydantic-core 2.46.5 → 2.50.1, preserved the declared request-boundary
and mission-input behavior. FastAPI stayed at 0.141.1. Both before and after
environments passed all 61 source-grounded cases and independent verification.
The original FastAPI import bridge and actual 15-second timeout were exercised.

## What this enables

A maintainer can reuse the exact component lock, observations and independent
verification in the broader upgrade review, without reconstructing these specific
checks. The component patch is reviewable and replayable; it is not a qualified
replacement for the complete native application lock.

## Remaining work

Qualify the complete application dependency closure and supported platforms.
Run the authorized authentication, persistence and mission-execution checks.
Use the existing owner review and release acceptance process before adoption.
No application, credentials, Journal, settlement or operator action was created.

## Cost and demand

This was an internal project assessment, not a paid order. Actual collections are
zero. Complete delivery money, price, customer time and operator time remain
unknown. Setup, failed attempts, correction, execution, verification and package
assembly records are preserved. Runtime process quantities are not a bill or wage.

## Résultat utile

**Décision : conserver le verrou de production actuel et accepter ces preuves
de compatibilité des composants pour la qualification suivante.** Le changement
proposé conserve les comportements déclarés de la frontière des requêtes et de
la validation des entrées. Les 61 cas ont réussi avant et après le changement,
avec une vérification indépendante. Le chemin d'importation FastAPI d'origine
et le délai réel de 15 secondes ont été conservés.

Ce dossier permet au responsable de réutiliser les preuves exactes dans la revue
de mise à jour. La qualification complète de l'application, les contrôles
d'authentification et de persistance, ainsi que l'autorisation de publication
restent à effectuer. Le coût monétaire complet et le prix sont inconnus;
aucun paiement client n'a été reçu.

See decision.json for source links, exact versions, required actions and evidence
hashes. The full companion preserves environments, wheels, helper source and
primitive cost records; this folder is the readable decision packet.
'''
    (destination / 'READ-ME.md').write_text(report)
    replay = '''From the complete companion root (Python 3.12 / Linux x86_64):

1. Recreate the declared ten-package environments from their exact wheel locks,
   using curation/prepare_environment.py --offline and the saved plans. Paths in
   saved command receipts identify the original execution; relocate only through
   an explicit regenerated plan, retaining original source/wheel/contract hashes.
2. Run src/manual_probe.py with each environment's venv/bin/python -I -B,
   --consumer data/consumer --contract protocol/component-contract.json and a new --out.
3. Run src/verify_component.py with --projection native-fastapi-bridge-v2,
   the same consumer/contract, the matching environment preparation.json,
   --observations from step2 and a new --out.

The complete before/after argv and pre/post input hashes are in evidence/*execution.json.
Do not overwrite historical observations. Passing this finite component contract
does not authorize application deployment or replacement of the full native lock.
'''
    (destination / 'reproduce.txt').write_text(replay)
    files = [{'path': str(p.relative_to(destination)), 'sha256': digest(p), 'bytes': p.stat().st_size}
             for p in sorted(destination.rglob('*')) if p.is_file()]
    (destination / 'artifact-manifest.json').write_text(json.dumps({'files': files}, indent=2) + '\n')
    for row in files:
        if digest(destination / row['path']) != row['sha256']:
            raise ValueError('FINAL_PACKAGE_INTEGRITY')
    (destination / 'assembly-receipt.json').write_text(json.dumps({
        'schema': 'first-manual-delivery-assembly/v1', 'assembler_sha256': digest(Path(__file__)),
        'wall_seconds': time.perf_counter() - started, 'cpu_seconds': time.process_time() - cpu,
        'files_verified': len(files), 'money_usd': None, 'customer_acceptance': None,
        'retained_for_incumbent_reuse': True}, indent=2) + '\n')
    print(json.dumps({'out': str(destination), 'decision': result['decision'], 'files_verified': len(files)}))


if __name__ == '__main__':
    main()
