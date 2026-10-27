#!/usr/bin/env python3
"""Offline reproduction into a new directory; never overwrite registered outputs."""
from pathlib import Path
import argparse, hashlib, json, shutil, subprocess

ROOT = Path(__file__).resolve().parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output', type=Path, required=True, help='New empty output directory')
parser.add_argument('--mode', choices=['tests', 'confirmation', 'full'], default='confirmation')
args = parser.parse_args()
target = args.output.resolve()
if target.exists() and any(target.iterdir()):
    raise SystemExit('Output must be new or empty; registered outputs are never removed.')
freeze = json.loads((ROOT / 'protocol/freeze.json').read_text())
amendment = json.loads((ROOT / 'protocol/beta_symmetry_amendment.json').read_text())
if hashlib.sha256((ROOT / 'model/beta_symmetry.mjs').read_bytes()).hexdigest() != amendment['amendmentCodeSHA256']:
    raise SystemExit('The preserved Beta-policy amendment implementation has changed.')
for name, expected in freeze['sourceHashes'].items():
    source = ROOT / name
    if not source.is_file():
        raise SystemExit(f'Missing frozen companion file: {name}. Restore the complete supplied experiment packet; the source-only Git draft intentionally excludes binaries.')
    if hashlib.sha256(source.read_bytes()).hexdigest() != expected:
        raise SystemExit(f'Frozen hash mismatch: {name}')
    destination = target / name
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
for name in ['protocol/freeze.json', 'protocol/freeze.sha256', 'model/beta_symmetry.mjs',
             'protocol/beta_symmetry_amendment.json', 'protocol/initial_selected_policies.json']:
    destination = target / name
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / name, destination)
(target / 'results').mkdir(exist_ok=True)
def run(*command):
    print(' '.join(command), flush=True)
    subprocess.run(command, cwd=target, check=True)

tests = sorted(str(p.relative_to(target)) for p in (target / 'model').glob('*.test.mjs'))
run('node', '--test', *tests, 'graph/lifecycle.test.mjs')
if args.mode == 'tests':
    raise SystemExit(0)
if args.mode == 'full':
    run('node', 'model/run.mjs', 'train')
    repeated = json.loads((target / 'protocol/selected_policies.json').read_text())
    preserved = json.loads((target / 'protocol/initial_selected_policies.json').read_text())
    if repeated['selected'] != preserved['selected']:
        raise SystemExit('Repeated development outcomes differ from the preserved initial selection.')
    run('node', 'model/beta_symmetry.mjs', 'run')
else:
    shutil.copy2(ROOT / 'protocol/selected_policies.json', target / 'protocol/selected_policies.json')
run('node', 'model/run.mjs', 'confirm')
if args.mode == 'full':
    run('node', 'model/run.mjs', 'sensitivity')
    run('node', 'model/run.mjs', 'scale')
    frozen_sha = hashlib.sha256((target / 'protocol/freeze.json').read_bytes()).hexdigest()
    run('node', 'model/meta_experiment.mjs', 'run', '--freeze-sha', frozen_sha)
print(f'Reproduction complete: {target}')
