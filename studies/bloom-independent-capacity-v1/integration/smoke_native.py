# SPDX-License-Identifier: Apache-2.0
"""Small executable check of native dispatch, custody and inactive restoration."""

import argparse
import json
from pathlib import Path

from .native_workflow import FAMILY_MAP, execute_stages, fixture_registry
from .source_loader import native_modules


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    stages = []
    for index, ident in enumerate(FAMILY_MAP):
        def handler(inputs, index=index):
            return {'scope': 'integration smoke only; not scientific evidence', 'counter': index,
                    'parent_count': len(inputs), 'qualified': True}
        stages.append({'id': ident, 'handler': handler})
    result = execute_stages(args.output, stages, mission_id='bloom-native-integration-smoke',
        objective='Exercise the actual pinned native dispatcher and retain inactive recovery.',
        source_paths=[Path(__file__), Path(__file__).with_name('native_workflow.py')],
        bindings={'execution_mode': 'synthetic-local', 'authority': 'none'})
    assert result['receipt']['status'] == 'completed'
    assert result['receipt']['resource_ledger']['spent'] == {'stage_calls': 7}
    root, modules = Path(result['directory']), native_modules()
    p, t = modules['successor.protocol'], modules['successor.trust']
    registry, keys, _ = fixture_registry(t)
    journal = modules['store'].Journal(root / 'restored-journal')
    store = modules['successor.state'].SuccessorStore(journal, registry)
    dispatcher = modules['successor.jobs'].JobDispatcher(store, 'bloom-local-study')
    first = p.JobContract.model_validate(json.loads((root / 'native_graph.json').read_text())['jobs'][0])
    authorization = p.ExecutionAuthorization(authorization_id='forbidden-restored-attempt',
        acting_identity=first.worker, job_terms_digest=p.digest('job-terms', first),
        release_digest=first.release_digest, environment_digest=first.environment_digest,
        capabilities=['installed-study-stage'], reservation_id='forbidden-restored-reservation', expires_at=first.valid_until)
    rejected = None
    try:
        dispatcher.dispatch(first.job_id, t.sign_record(keys['bloom-fixture-controller'],
                            'bloom-fixture-controller', 'execution', authorization))
    except modules['store'].Conflict as exc:
        rejected = str(exc)
    assert rejected == 'institution or agent is stopped', rejected
    check = {'scope': 'Native adapter smoke only; not a scientific experiment', 'stages_completed': 7,
             'native_journal_valid': journal.verify()['valid'], 'restored_dispatch': 'REJECTED',
             'reason': rejected, 'active_proofs': [], 'active_grants': []}
    (root / 'smoke_checks.json').write_text(json.dumps(check, indent=2) + '\n')
    print(json.dumps(check, indent=2))


if __name__ == '__main__':
    main()
