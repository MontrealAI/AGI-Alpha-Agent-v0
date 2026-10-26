# SPDX-License-Identifier: Apache-2.0
"""Synthetic accounting-integrity controls; no customer or consumer execution."""

import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


SPEC = importlib.util.spec_from_file_location('supplement', Path(__file__).with_name('final_delivery_cost_supplement.py'))
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)


class SupplementControls(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.raw = {'schema': 'synthetic-command/v1', 'complete_success': True, 'wall_seconds': 2.0, 'child_cpu_seconds': None}
        self.save('receipt.json', self.raw)
        self.base = {'capability_id': 'component-compatibility', 'missions': [{'mission_id': name} for name in sorted(MOD.MISSIONS)], 'actual_collections_minor': 0, 'customer_price_minor': None, 'resource_entries': []}
        self.save('base.json', self.base)
        self.save('snapshot.json', {'files': []})
        self.entry = {'id': 'synthetic', 'description': 'Synthetic complete command', 'required': True, 'activity_state': 'completed', 'source_path': 'receipt.json', 'source_sha256': MOD.sha(self.root / 'receipt.json'), 'source_schema': 'synthetic-command/v1', 'completion_check': {'path': ['complete_success'], 'equals': True}, 'resource_fields': {'wall_seconds': ['wall_seconds'], 'child_cpu_seconds': ['child_cpu_seconds']}, 'outcome': 'succeeded', 'accounting_role': 'additive', 'phase': 'synthetic-control', 'aggregation': 'One synthetic envelope', 'covers_sources': []}
        self.plan = {'schema': 'same-capability-delivery-cost-plan/v1', 'capability_id': 'component-compatibility', 'investment_account': 'study-investment', 'base_evidence': {'path': 'base.json', 'sha256': MOD.sha(self.root / 'base.json')}, 'base_cost_snapshot': {'path': 'snapshot.json', 'sha256': MOD.sha(self.root / 'snapshot.json')}, 'entries': [self.entry]}

    def save(self, name, value):
        (self.root / name).write_text(json.dumps(value))

    def repin_raw(self):
        self.save('receipt.json', self.raw)
        self.entry['source_sha256'] = MOD.sha(self.root / 'receipt.json')

    def test_null_is_not_zero(self):
        base, rows, pending = MOD.collect(self.root, self.plan)
        self.assertEqual(base['missions'], self.base['missions'])
        self.assertEqual(pending, [])
        self.assertEqual(rows[0]['resources']['wall_seconds'], 2.0)
        self.assertIsNone(rows[0]['resources']['child_cpu_seconds'])
        self.assertIsNone(rows[0]['resources']['money_usd'])
        self.assertIsNone(MOD.stats(rows)['child_cpu_seconds']['known_subtotal'])

    def test_required_pending_survives(self):
        self.entry['activity_state'] = 'pending'
        self.entry['source_path'] = None
        _, rows, pending = MOD.collect(self.root, self.plan)
        self.assertEqual(rows, [])
        self.assertEqual(len(pending), 1)
        self.assertIs(pending[0]['required'], True)

    def test_collected_snapshot_retains_validated_bytes(self):
        _, rows, _ = MOD.collect(self.root, self.plan)
        original = rows[0]['source_bytes']
        self.save('receipt.json', {'changed_after_collection': True})
        self.assertEqual(json.loads(original), self.raw)
        self.assertNotEqual(MOD.sha(self.root / 'receipt.json'), rows[0]['source']['sha256'])

    def test_wrong_hash_refused(self):
        self.entry['source_sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'hash mismatch'):
            MOD.collect(self.root, self.plan)

    def test_boolean_quantity_refused(self):
        self.raw['wall_seconds'] = True
        self.repin_raw()
        with self.assertRaisesRegex(ValueError, 'number or null'):
            MOD.collect(self.root, self.plan)

    def test_nonfinite_quantity_refused(self):
        self.raw['wall_seconds'] = float('nan')
        self.repin_raw()
        with self.assertRaisesRegex(ValueError, 'finite'):
            MOD.collect(self.root, self.plan)

    def test_copied_receipt_refused(self):
        extra = copy.deepcopy(self.entry)
        extra['id'] = 'copy'
        extra['source_path'] = 'copy.json'
        self.save('copy.json', self.raw)
        self.plan['entries'].append(extra)
        with self.assertRaisesRegex(ValueError, 'copied twice'):
            MOD.collect(self.root, self.plan)

    def test_already_charged_source_refused(self):
        self.save('snapshot.json', {'files': [{'sha256': self.entry['source_sha256']}]})
        self.plan['base_cost_snapshot']['sha256'] = MOD.sha(self.root / 'snapshot.json')
        with self.assertRaisesRegex(ValueError, 'already charged'):
            MOD.collect(self.root, self.plan)

    def test_nested_envelopes_refused(self):
        extra = copy.deepcopy(self.entry)
        extra['id'] = 'nested'
        extra['source_path'] = 'nested.json'
        self.entry['covers_sources'] = ['nested.json']
        self.plan['entries'].append(extra)
        with self.assertRaisesRegex(ValueError, 'Nested cost source'):
            MOD.collect(self.root, self.plan)

    def test_completion_type_mismatch_refused(self):
        self.raw['complete_success'] = 1
        self.repin_raw()
        with self.assertRaisesRegex(ValueError, 'typed activity'):
            MOD.collect(self.root, self.plan)

    def test_schema_mismatch_refused(self):
        self.entry['source_schema'] = 'different/v1'
        with self.assertRaisesRegex(ValueError, 'schema mismatch'):
            MOD.collect(self.root, self.plan)

    def test_duplicate_missions_refused(self):
        self.base['missions'][0] = self.base['missions'][1]
        self.save('base.json', self.base)
        self.plan['base_evidence']['sha256'] = MOD.sha(self.root / 'base.json')
        with self.assertRaisesRegex(ValueError, 'mission inventory'):
            MOD.collect(self.root, self.plan)

    def test_unsafe_id_refused(self):
        self.entry['id'] = '../outside'
        with self.assertRaisesRegex(ValueError, 'safe local'):
            MOD.collect(self.root, self.plan)


if __name__ == '__main__':
    unittest.main()
