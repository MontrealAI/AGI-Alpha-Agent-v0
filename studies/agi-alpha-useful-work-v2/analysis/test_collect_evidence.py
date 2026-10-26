# SPDX-License-Identifier: Apache-2.0
"""Synthetic accounting-scope controls; no primary worker or evaluator changes."""
import importlib.util
from pathlib import Path
import tempfile
import unittest


SPEC = importlib.util.spec_from_file_location('collector', Path(__file__).with_name('collect_evidence.py'))
COLLECT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(COLLECT)


class CollectionScopeControls(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='postfreeze-analysis-control-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.out = self.root / 'analysis-output'
        self.out.mkdir()

    def write(self, relative, value):
        path = self.root / relative
        COLLECT.write(path, value)
        return path

    def test_unknown_and_bool_are_not_numeric_zero(self):
        self.assertIsNone(COLLECT.number(None))
        self.assertIsNone(COLLECT.number(True))
        self.assertEqual(COLLECT.number(0), 0)
        self.assertIsNone(COLLECT.complete_sum([1, None]))

    def test_manual_finalization_alone_does_not_end_a_run(self):
        self.write('results/confirmation/m/manual/manual-finalization.json', {'decision': 'SCOPED_COMPONENT_PRESERVED'})
        self.write('results/confirmation/m/manual/finalization-execution.json', {'exit_code': 0})
        run = COLLECT.discover_run(self.root, 'm', 'manual', {})
        self.assertFalse(run['terminal'])

    def test_manual_inclusive_span_and_cpu_not_nested_sums(self):
        base = 'results/confirmation/m/manual/'
        terminal_path = self.write(base + 'terminal.json', {
            'schema': 'useful-work-campaign-terminal/v1', 'mission_id': 'm', 'arm': 'manual',
            'started_at': '2026-10-26T00:00:00+00:00', 'ended_at': '2026-10-26T00:01:40+00:00',
            'service_span_seconds': 100, 'inclusive_child_cpu_seconds': 4, 'driver_process_cpu_seconds': 1,
            'mechanical_pair': base + 'pair/pair.json', 'manual_finalizations': 1})
        self.write(base + 'pair/pair.json', {'wall_seconds': 15, 'child_cpu_seconds': 3, 'process_cpu_seconds': 0.1})
        self.write(base + 'finalization-execution.json', {'wall_seconds': 2, 'child_cpu_seconds': 0.5, 'meter_cpu_seconds': 0.1})
        run = COLLECT.discover_run(self.root, 'm', 'manual', {})
        resources, envelopes = [], []
        quality = {'accepted': True, 'decision': 'SCOPED_COMPONENT_PRESERVED', 'independently_verified': True,
                   'evidence_path': None, 'errors': []}
        row = COLLECT.materialize_run(self.root, self.out, run, quality, resources, envelopes)
        self.assertEqual(row['request_to_package_wall_seconds'], 100)
        self.assertEqual(row['mechanical_wall_seconds'], 17)
        self.assertEqual(row['measured_local_cpu_seconds'], 5)
        self.assertIsNone(row['runtime_model_calls'])
        self.assertEqual(sum(r['accounting_role'] == 'additive' for r in resources), 1)
        self.assertEqual(resources[1]['evidence_path'], str(terminal_path.relative_to(self.root)))

    def test_failed_terminal_keeps_measured_resources_without_credit(self):
        base = 'results/confirmation/m/retained/'
        self.write(base + 'terminal.json', {'schema': 'useful-work-campaign-terminal/v1',
            'mission_id': 'm', 'arm': 'retained', 'ended_at': '2026-10-26T00:00:10+00:00',
            'service_span_seconds': 10, 'inclusive_child_cpu_seconds': 2, 'driver_process_cpu_seconds': 0.1,
            'accepted': False, 'error': 'Synthetic failure'})
        run = COLLECT.discover_run(self.root, 'm', 'retained', {})
        resources, envelopes = [], []
        row = COLLECT.materialize_run(self.root, self.out, run,
            {'accepted': False, 'decision': 'INCOMPLETE_HOLD', 'independently_verified': False,
             'evidence_path': None, 'errors': ['synthetic']}, resources, envelopes)
        self.assertEqual(row['request_to_package_wall_seconds'], 10)
        self.assertFalse(row['accepted'])
        self.assertEqual(resources[0]['outcome'], 'failed')
        self.assertFalse(envelopes[0]['scope_complete'])

    def test_eight_setup_reports_are_nested_under_driver(self):
        attempts, environments = [], []
        for index in range(8):
            name = f'env-{index}'
            relative = f'data/confirmation-environments/{name}/preparation.json'
            path = self.write(relative, {'complete': True, 'wall_seconds': 3, 'process_cpu_seconds': 1, 'child_cpu_seconds': 2})
            attempts.append({'environment_id': name, 'preparation_path': relative,
                             'preparation_sha256': COLLECT.sha(path), 'complete': True})
            environments.append({'id': name})
        self.write('data/confirmation-inputs/acquisition-summary.json', {
            'freeze_sha256': COLLECT.FREEZE_SHA256, 'attempt_count': 8, 'attempts': attempts,
            'failed_environments': 0, 'driver_wall_seconds': 25, 'driver_child_cpu_seconds_inclusive': 24,
            'driver_process_cpu_seconds': 0.5, 'network_requests': 16, 'network_response_bytes': 100})
        resources = []
        result = COLLECT.acquisition(self.root, self.out, {'environments': environments}, resources)
        self.assertEqual(result['wall_seconds'], 25)
        self.assertEqual(result['child_cpu_seconds'], 24)
        self.assertEqual(result['meter_cpu_seconds'], 0.5)
        self.assertEqual(sum(r['accounting_role'] == 'additive' for r in resources), 1)
        self.assertEqual(sum(r['accounting_role'] == 'nested_evidence' for r in resources), 8)

    def test_live_event_log_is_snapshotted_for_immutable_accounting(self):
        source = self.root / 'metering/research.jsonl'
        source.parent.mkdir()
        source.write_text('{"cost_usd":null}\n')
        resources = []
        COLLECT.lifecycle(self.root, self.out, None, resources)
        snapshot_entry = next(row for row in resources if row.get('format') == 'jsonl')
        snapshot = self.root / snapshot_entry['evidence_path']
        source.write_text(source.read_text() + '{"later_event":true}\n')
        self.assertEqual(COLLECT.sha(snapshot), snapshot_entry['evidence_sha256'])
        self.assertNotEqual(COLLECT.sha(source), snapshot_entry['evidence_sha256'])
        self.assertEqual(snapshot_entry['accounting_role'], 'documentary')

    def test_explicit_prior_delivery_account_is_not_v2_investment(self):
        source = self.root / 'metering/prior-delivery-recovery.jsonl'
        source.parent.mkdir()
        source.write_text('{"cost_account":"prior V1 delivery recovery","cost_usd":null}\n')
        resources = []
        result = COLLECT.lifecycle(self.root, self.out, None, resources)
        self.assertFalse(any(row.get('format') == 'jsonl' for row in resources))
        self.assertTrue(any(row['path'].endswith('prior-delivery-recovery.jsonl') for row in result['exclusions']))


if __name__ == '__main__':
    unittest.main(verbosity=2)
