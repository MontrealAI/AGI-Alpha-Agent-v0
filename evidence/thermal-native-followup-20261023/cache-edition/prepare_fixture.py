# SPDX-License-Identifier: Apache-2.0
"""Retain three exact public main worker bodies as the preceding cache edition."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path('/workspace/scratch/5d02e86cc826/alpha-thermal-native')
COMMIT = 'e7fbd7e7fd0599f66c70ea8fe5e26b178e04f541'
TREE = 'd76f2b6f5772e773fcae261b8a595e5e0f58aa41'
assert subprocess.check_output(['git', 'rev-parse', COMMIT + '^{tree}'], cwd=ROOT, text=True).strip() == TREE
catalog = json.loads(subprocess.check_output(['git', 'show', COMMIT + ':docs/successor/capabilities/sources.json'], cwd=ROOT))
assert catalog['sourceHash'] == '54769dbfde99ae13708a33292866f0ca7e6b8b7792a7a944f76bf2fbf1de1358'
expected = {
    'docs/service-worker.js': (23275, 'ac1621a5e9efd104e56ff3865c0784e22a968975dc7b8465682b5528e9e967fd'),
    'docs/assets/service-worker.js': (23707, '64654fce9864c5f792e6b7e5bb595d85366ae4491ba179f7595e1bfa24d5e161'),
    'docs/alpha_factory_v1/demos/alpha_agi_insight_v1/service-worker.js':
        (26299, 'be9396acf43738b48a233c24517e8a3d06a8b1a36a00448b50be7e8792b7b8a3'),
}
fixture = {'sourceCommit': COMMIT, 'sourceTree': TREE, 'sourceHash': catalog['sourceHash'], 'files': {}}
for name, identity in expected.items():
    raw = subprocess.check_output(['git', 'show', COMMIT + ':' + name], cwd=ROOT)
    assert (len(raw), hashlib.sha256(raw).hexdigest()) == identity
    current = (ROOT / name).read_bytes()
    assert re.sub(br'^const CACHE = .*;$', b'const CACHE = "fixed";', raw, flags=re.M) == re.sub(
        br'^const CACHE = .*;$', b'const CACHE = "fixed";', current, flags=re.M)
    fixture['files'][name] = {'bytes': identity[0], 'sha256': identity[1], 'text': raw.decode('utf-8')}
target = ROOT / 'tests/fixtures/capability-checkout-enterprise-139-presentation-workers.json'
with target.open('x') as stream:
    json.dump(fixture, stream, indent=2)
    stream.write('\n')
print(json.dumps({'fixture': str(target), 'bytes': target.stat().st_size,
                  'sha256': hashlib.sha256(target.read_bytes()).hexdigest(),
                  'historicalSource': COMMIT, 'workerCount': len(fixture['files']),
                  'onlyCacheLineDiffersFromCandidate': True}, sort_keys=True))
