# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def file_record(path: str) -> dict[str, str]:
    return {'path': path, 'sha256': hashlib.sha256((ROOT / path).read_bytes()).hexdigest()}


def build(evidence_root: Path, output: Path) -> None:
    summary_path = evidence_root / 'execution-summary.json'
    summary = json.loads(summary_path.read_text())
    if summary['schema'] != 'capability-current-implementation-validation/v1' or not summary['accepted']:
        raise ValueError('EXECUTED_CURRENT_ADMISSION_REQUIRED')
    for record in summary['source_files']:
        if file_record(record['path'])['sha256'] != record['sha256']:
            raise ValueError('SOURCE_DRIFT_SINCE_EXECUTED_ADMISSION:' + record['path'])
    entries = summary['entries']
    if set(x['skill'] for x in entries) != {'forward@1', 'inverse@1', 'design@1', 'design@2'} or len(entries) != 8:
        raise ValueError('COMPLETE_FOUR_VERSION_TWO_CHAIN_ADMISSION_REQUIRED')
    dispatch_entries = summary['dispatch_entries']
    if len(dispatch_entries) != 6 or not all(x['accepted'] for x in dispatch_entries):
        raise ValueError('CURRENT_PRODUCTION_DISPATCH_EXECUTION_REQUIRED')
    closure = [file_record(x['path']) for x in summary['source_files']
               if x['path'].startswith(('skills/', 'independent/')) or x['path'] == 'production/worker.py']
    receipt_record = file_record(summary_path.relative_to(ROOT).as_posix())

    def evidence(selected, dispatch):
        cases = [x['case'] for x in selected]
        dispatch_cases = [x['case'] for x in dispatch]
        paths = {value for case in cases + dispatch_cases for value in case.values()}
        paths.add(summary_path.relative_to(ROOT).as_posix())
        return {'files': [file_record(p) for p in sorted(paths)], 'cases': cases, 'dispatchCases': dispatch_cases,
                'executionReceipt': receipt_record,
                'scope': 'Actual current-version execution on two discovery chains; no primary answers in skill index'}

    skills = []
    for skill in ['forward@1', 'inverse@1', 'design@1', 'design@2']:
        family, version = skill.split('@')
        selected = [item for item in entries if item['skill'] == skill]
        skills.append({'id': family, 'version': version,
                       'creator': ('independent-recipient.agent.agi.eth (FIXTURE ATTRIBUTION; actual same-session independent contributor)'
                                   if skill == 'design@2' else 'constructor.agent.agi.eth (FIXTURE ATTRIBUTION; root model session)'),
                       'motivatingJob': 'Connected DISC-01/DISC-02 ' + family + ' work and identified repeated-solve bottleneck',
                       'outputs': [family + '-result'],
                       'dependencies': [] if family == 'forward' else ['forward@1' if family == 'inverse' else 'inverse@1'],
                       'implementation': {'entrypoint': selected[0]['entrypoint'], 'callable': selected[0]['callable'],
                                          'files': closure, 'dispatch': 'skills/network_capability.py'},
                       'evidence': evidence(selected, [x for x in dispatch_entries if x['skill'] == skill]),
                       'scope': {'family': family, 'schema': 'agi-alpha-conductance-job/v1',
                                 'empiricalNodeCounts': [225, 400], 'maximumNodes': 4096, 'maximumLoads': 16,
                                 'maximumInverseParameters': 32, 'maximumDesignVariables': 80,
                                 'permission': 'PROSPECTIVE_BOUNDED_RESEARCH_TRIAL',
                                 'largerScopeStatus': 'FRESH_CONFIRMATION_PENDING'},
                       'environment': {**summary['runtime'], 'execution': 'fixed-local-research',
                                       'threadPolicy': 'OPENBLAS_OMP_MKL_1'},
                       'rights': {'license': 'Apache-2.0', 'dataClass': 'synthetic'}, 'expiresAt': 9000,
                       'costStatus': 'ACTUAL_COMPLETE_COST_UNKNOWN', 'liveAuthentication': 'NOT RUN'})
    compositions = []
    for target, members in [('inverse@1', ['forward@1', 'inverse@1']),
                            ('design@1', ['forward@1', 'inverse@1', 'design@1']),
                            ('design@2', ['forward@1', 'inverse@1', 'design@2'])]:
        compositions.append({'id': target.replace('@', '-v') + '-validated-composition', 'target': target,
                             'members': members, 'evidence': evidence([x for x in entries if x['skill'] in members],
                                 [] if target == 'design@1' else [x for x in dispatch_entries if x['skill'] in members]),
                             'scope': 'Both actual freshly executed connected chains, version-specific design and accepted inherited calibration'})
    value = {'schema': 'capability-advantage-catalog/v2', 'skills': skills, 'compositions': compositions,
             'supersessions': [{'old': 'design@1', 'new': 'design@2',
                               'reason': 'Actual independently authored contribution selected before primary; original version/evidence retained'}],
             'executionReceipt': receipt_record, 'runtime': summary['runtime']}
    output.write_text(json.dumps(value, indent=2) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--evidence-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, default=ROOT / 'identity/catalog.json')
    args = parser.parse_args()
    build(args.evidence_root.resolve(), args.output.resolve())
