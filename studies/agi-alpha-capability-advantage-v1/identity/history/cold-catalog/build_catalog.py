from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = 'evidence/discovery-qualified'


def file_record(path: str) -> dict[str, str]:
    return {'path': path, 'sha256': hashlib.sha256((ROOT / path).read_bytes()).hexdigest()}


def case(family: str) -> dict[str, str]:
    output = f'{SOURCE}/DISC-01/{family}/B'
    task = f'workloads/discovery/tasks/DISC-01-{family.upper()}.json'
    value = {'task': task, 'result': output + '/result.json', 'oracle': f'workloads/discovery/oracles/DISC-01-{family.upper()}.json'}
    if family == 'design':
        value.update(task=f'{SOURCE}/materialized/DISC-01/B-DESIGN.json', parent_task='workloads/discovery/tasks/DISC-01-INVERSE.json',
                     parent_result=f'{SOURCE}/DISC-01/inverse/B/result.json')
    return value


def evidence(cases: list[dict[str, str]]) -> dict[str, object]:
    paths = sorted({p for c in cases for p in c.values()})
    return {'files': [file_record(p) for p in paths], 'cases': cases,
            'scope': 'Independent replay of connected discovery evidence; primary answers excluded'}


skills = []
for generation, family in enumerate(['forward', 'inverse', 'design']):
    sources = ['skills/core.py', f'skills/{family}.py']
    skills.append({'id': family, 'version': '1', 'creator': 'constructor.agent.agi.eth (FIXTURE ATTRIBUTION; root model session)',
                   'motivatingJob': f'DEV-{family.upper()} then connected DISC-01-{family.upper()}', 'outputs': [family + '-result'],
                   'dependencies': [] if generation == 0 else [(['forward', 'inverse'][generation - 1]) + '@1'],
                   'implementation': {'entrypoint': f'skills/{family}.py', 'files': [file_record(p) for p in sources]},
                   'evidence': evidence([case(family)]),
                   'scope': {'family': family, 'schema': 'agi-alpha-conductance-job/v1', 'maximumNodes': 4096,
                             'currentEvidence': '49-node development and 225/400-node connected discovery', 'largerScopeStatus': 'FRESH_CONFIRMATION_PENDING'},
                   'environment': {'python': '3.12.14', 'numpy': '2.3.5', 'scipy': '1.17.0', 'execution': 'fixed-local-research'},
                   'rights': {'license': 'Apache-2.0', 'dataClass': 'synthetic'}, 'expiresAt': 9000,
                   'costStatus': 'ACTUAL_COMPLETE_COST_UNKNOWN', 'liveAuthentication': 'NOT RUN'})
compositions = []
for family, members in [('inverse', ['forward@1', 'inverse@1']), ('design', ['forward@1', 'inverse@1', 'design@1'])]:
    families = ['forward', 'inverse'] if family == 'inverse' else ['forward', 'inverse', 'design']
    compositions.append({'id': family + '-validated-composition', 'target': family + '@1', 'members': members,
                         'evidence': evidence([case(f) for f in families]), 'scope': 'Actual independently accepted connected chain; no live grants'})
(ROOT / 'identity/catalog.json').write_text(json.dumps({'skills': skills, 'compositions': compositions}, indent=2) + '\n')
