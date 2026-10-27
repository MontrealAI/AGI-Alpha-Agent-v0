# SPDX-License-Identifier: Apache-2.0
"""Freeze/verify the distinct paid-job learning source closure; never runs worlds."""
from pathlib import Path
import argparse
import hashlib
import json
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[2]
STUDY = ROOT / 'beyond_beta'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def freeze():
    paths = {STUDY/'protocol.json', STUDY/'CHARTER.md', STUDY/'run_experiment.py'}
    for directory in ('src', 'tests', 'calibration', 'foundations'):
        for path in (STUDY/directory).rglob('*'):
            if path.is_file() and '__pycache__' not in path.parts and path.suffix in ('.py', '.mjs', '.json', '.md'):
                paths.add(path)
    for path in (STUDY/'validation').glob('*.py'):
        paths.add(path)
    for name in ('venture_creation/src/finance_capacity.py', 'venture_creation/src/authority_fixture.py',
                 'venture_creation/src/native_integration.mjs', 'human_market/validation/skill_admission.mjs',
                 'native_snapshot/canonical/shadow-ledger.mjs', 'native_snapshot/manifest.json',
                 'native_snapshot/canonical/provenance.json'):
        paths.add(ROOT/name)
    rows = [dict(path=str(p.relative_to(ROOT)), bytes=p.stat().st_size, sha256=sha(p)) for p in sorted(paths)]
    return dict(schema='paid-job-alpha-source-freeze/v1', createdAt=datetime.now(timezone.utc).isoformat(),
                sourceId=hashlib.sha256(json.dumps(rows,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
                protocolSHA256=sha(STUDY/'protocol.json'), files=rows,
                noCalibratedHistoriesBeforeFreeze=True,
                evidenceBoundary='Fictional controls and source reviews precede the freeze; simulated market outcomes follow it.',
                actualProductionModelCalls=0, actualCommercialRevenueUSD=0, actualCompleteResearchCostUSD=None)


def verify(path):
    record = json.loads(Path(path).read_text())
    for item in record['files']:
        p=ROOT/item['path']
        if p.stat().st_size != item['bytes'] or sha(p) != item['sha256']:
            raise ValueError('Frozen input changed: '+item['path'])
    return dict(valid=True, sourceId=record['sourceId'], files=len(record['files']))


if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('--create',type=Path); ap.add_argument('--verify',type=Path)
    args=ap.parse_args()
    if bool(args.create)==bool(args.verify): ap.error('Exactly one of --create/--verify is required')
    if args.verify: print(json.dumps(verify(args.verify)))
    else:
        record=freeze();args.create.parent.mkdir(parents=True,exist_ok=True)
        with args.create.open('x') as f: json.dump(record,f,indent=2); f.write('\n')
        print(json.dumps({k:record[k] for k in ('sourceId','protocolSHA256','createdAt')}|{'files':len(record['files'])}))
