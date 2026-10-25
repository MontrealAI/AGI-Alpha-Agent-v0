#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Create or verify the prospective source freeze; never overwrites a freeze."""
import argparse, datetime, hashlib, json, platform, subprocess
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
FREEZE = ROOT / 'protocol' / 'STUDY_FREEZE.json'

def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def files():
    chosen = set()
    groups = {
        'companion': {'.mjs','.py','.json'},
        'review': {'.py'},
        'operations': {'.mjs','.py'},
        'analysis': {'.mjs','.py'},
        'protocol': {'.json','.md'},
        'scripts': {'.py','.mjs'},
    }
    for directory, suffixes in groups.items():
        for p in (ROOT/directory).rglob('*'):
            if p.is_file() and p.suffix in suffixes and '__pycache__' not in p.parts:
                if p.name != 'STUDY_FREEZE.json' and 'results' not in p.parts and 'load-results' not in p.parts:
                    chosen.add(p)
    # Presentation and recorded results may change after confirmation. Execution
    # logic, checker and fixtures are part of the prospective scientific freeze.
    for p in (ROOT/'browser').glob('*.mjs'): chosen.add(p)
    for p in (ROOT/'browser').glob('*.json'):
        if 'fixture' in p.name.lower(): chosen.add(p)
    for name in ['requirements.txt','package.json']:
        p=ROOT/name
        if p.exists(): chosen.add(p)
    return sorted(chosen)

def manifest():
    return {str(p.relative_to(ROOT)): {'sha256':digest(p), 'bytes':p.stat().st_size} for p in files()}

def verify():
    saved=json.loads(FREEZE.read_text())
    current=manifest()
    errors=[]
    for p, item in saved['files'].items():
        if current.get(p)!=item: errors.append(p)
    extras=sorted(set(current)-set(saved['files']))
    if errors or extras:
        raise SystemExit(json.dumps({'verified':False,'changed_or_missing':errors,'extra_scientific_sources':extras},indent=2))
    print(json.dumps({'verified':True,'freeze_sha256':digest(FREEZE),'files':len(current)}))
    return saved

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--create',action='store_true');args=ap.parse_args()
    if not args.create: verify();return
    if FREEZE.exists(): raise SystemExit('Refusing to replace an existing freeze. Amend explicitly in a new namespace.')
    record={'schema':'agi-alpha-strategy-freeze/v1','status':'FROZEN_BEFORE_CONFIRMATION',
            'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'description':'New experiment, not a recreation of historical Strategy Laboratory numbers.',
            'files':manifest(),'environment':{'python':platform.python_version(),
            'node':subprocess.check_output(['node','--version'],text=True).strip(),
            'platform':platform.platform()},
            'limits':'Unsigned local manifest; durable copy and prospective public hash strengthen custody, not institutional independence.'}
    FREEZE.write_text(json.dumps(record,indent=2)+'\n')
    verify()
if __name__=='__main__':main()
