"""Record source-preservation checks without rerunning scientific evaluation."""

from __future__ import annotations

import datetime as dt
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import sys

ROOT = Path('/workspace/scratch/5d02e86cc826/alpha-thermal-native')
OUT = Path(__file__).resolve().parent
before = json.loads((OUT / 'before.json').read_text())


def identity(path: Path) -> dict[str, object]:
    body = path.read_bytes()
    return {'sha256': hashlib.sha256(body).hexdigest(), 'bytes': len(body)}


after = {name: identity(ROOT / name) for name in before['files']}
manifest_path = 'alpha_factory_v1/core/runtime/successor/workbench_sources.json'
worker_path = 'alpha_factory_v1/core/runtime/successor/workbench_worker.mjs'
manifest = json.loads((ROOT / manifest_path).read_text())
without_worker = {key: value for key, value in manifest.items() if key != 'workerSHA256'}
assert without_worker == before['workbenchManifest']
assert manifest['workerSHA256'] == after[worker_path]['sha256']
unchanged = [name for name in before['files'] if name != manifest_path]
for name in unchanged:
    assert before['files'][name] == after[name], name
capability = json.loads((ROOT / 'docs/successor/capabilities/sources.json').read_text())
assert capability == before['capabilityManifest']
for name, expected in capability['sources'].items():
    assert identity(ROOT / name)['sha256'] == expected, name
for name, expected in manifest['sources'].items():
    assert identity(ROOT / name)['sha256'] == expected, name

changed_paths = [
    'scripts/generate_successor_workbench.py',
    manifest_path,
    'tests/runtime/test_successor_workbench_generation.py',
    'examples/successor-workbench/thermal-witness.test.mjs',
]
receipt = {
    'schema': 'thermal-worker-identity-generator-receipt/v1',
    'recordedAt': dt.datetime.now(dt.timezone.utc).isoformat(),
    'baselineHead': before['head'],
    'workingTreeChanges': {name: identity(ROOT / name) for name in changed_paths},
    'workerSHA256': manifest['workerSHA256'],
    'moduleSourceHash': manifest['sourceHash'],
    'moduleSourceCount': len(manifest['sources']),
    'moduleSourcesUnchangedAndMatched': True,
    'manifestOnlyAddsWorkerSHA256': True,
    'unchangedGeneratedPaths': {name: after[name] for name in unchanged},
    'capabilitySourceHash': capability['sourceHash'],
    'capabilitySourceCount': len(capability['sources']),
    'capabilitySourcesUnchangedAndMatched': True,
    'regressions': {
        'actualPythonCasesPassed': 3,
        'result': '3 passed in 0.23s',
        'coverage': [
            'A clean copy of actual source inputs reproduces shipped worker, manifest and browser page; a repeated build is byte-identical.',
            'An input-size-limit wrapper-only change alters the whole-worker digest and leaves sourceHash, source map and page bytes unchanged.',
            'A native-dispatch wrapper-only change alters the whole-worker digest and leaves sourceHash, source map and page bytes unchanged.',
        ],
        'ruffCheck': 'passed',
        'ruffFormatCheck': 'passed',
        'junit': identity(OUT / 'generator-regression.xml'),
    },
    'toolVersions': {'python': sys.version.split()[0], 'pytest': version('pytest'), 'ruff': version('ruff')},
    'ordinarySelector': 'examples/successor-workbench/thermal-witness.test.mjs now includes the new Python test file in its existing pytest invocation.',
    'scope': 'Local generator regression and source-byte checks. Parent owns the combined native selector. No mathematical campaign, historical facade, EVM, hosted CI or live deployment is rerun or qualified by this receipt.',
    'ownership': 'No edits to workbench.py or test_successor_workbench.py; no staging, commits or remote ref mutation.',
    'setupErrorRetained': before['setupErrorRetained'],
    'commands': 'commands.jsonl',
    'unabridgedLogs': 'logs/',
}
body = json.dumps(receipt, indent=2, sort_keys=True) + '\n'
(OUT / 'receipt.json').write_text(body)
print(json.dumps({'receiptSHA256': hashlib.sha256(body.encode()).hexdigest(), 'workerSHA256': manifest['workerSHA256'], 'manifestSHA256': after[manifest_path]['sha256'], 'unchangedPaths': len(unchanged), 'matchedModuleSources': len(manifest['sources']), 'matchedCapabilitySources': len(capability['sources'])}, indent=2))
