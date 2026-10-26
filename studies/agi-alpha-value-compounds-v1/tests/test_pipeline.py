# SPDX-License-Identifier: Apache-2.0
"""Meaningful integrity and no-op controls for the local adapter."""
import json
from pathlib import Path
import tempfile
import unittest
import dossier
from pipeline import assess,native_inventory,source_tree

class PipelineControls(unittest.TestCase):
    def test_unchanged_source_is_noop(self):
        r=assess({'p.py':'def f(): pass\n'},{'p.py':'def f(): pass\n'},repository='example/public',before_ref='a'*40,after_ref='b'*40,consumer_files=[],arm='retained')
        self.assertEqual(r['status'],'NO_OP');self.assertEqual(r['new_customer_jobs'],0)
    def test_native_size_policy_stays_intact(self):
        r=native_inventory('#'+('x'*65536),'p.py','example/public','a'*40)
        self.assertEqual(r['status'],'native-policy-refusal')
    def test_snapshot_tamper_and_asset_change_refused(self):
        with tempfile.TemporaryDirectory() as d:
            store=dossier.SnapshotStore(Path(d));source='def f(a): pass\n';store.get(source)
            p=next(Path(d).glob('*.json'));entry=json.loads(p.read_text());entry['facts']['schema']='tampered';p.write_text(json.dumps(entry))
            with self.assertRaisesRegex(ValueError,'SNAPSHOT_INTEGRITY'):store.get(source)
            entry['asset_sha256']='0'*64;p.write_text(json.dumps(entry))
            with self.assertRaisesRegex(ValueError,'STALE_OR_WRONG'):store.get(source)
    def test_byte_inventory_preserves_crlf(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d,'p.py').write_bytes(b'def f(): pass\r\n');self.assertEqual(source_tree(Path(d))['p.py'].encode(),b'def f(): pass\r\n')
    def test_source_symlink_refused(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d,'actual.txt').write_text('def f(): pass\n');Path(d,'p.py').symlink_to(Path(d,'actual.txt'))
            with self.assertRaisesRegex(ValueError,'symlink'):source_tree(Path(d))
