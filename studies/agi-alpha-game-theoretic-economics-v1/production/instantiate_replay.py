# SPDX-License-Identifier: Apache-2.0
"""Materialize the frozen production inputs into a fresh self-contained replay root."""
from pathlib import Path
import argparse
import datetime
import hashlib
import json
import sys


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    source = Path(__file__).resolve().parents[1]
    target = args.out.absolute()
    if target.exists() or target.is_symlink():
        raise ValueError('Use a new replay root; original evidence is never overwritten.')
    target.mkdir(parents=True)
    freeze_file = source / 'production/joint-freeze.json'
    freeze = json.loads(freeze_file.read_text())
    for entry in freeze['files']:
        relative = Path(entry['path'])
        if relative.is_absolute() or '..' in relative.parts:
            raise ValueError('Unsafe frozen path')
        data = (source / relative).read_bytes()
        if len(data) != entry['bytes'] or hashlib.sha256(data).hexdigest() != entry['sha256']:
            raise ValueError('Frozen input changed: ' + str(relative))
        path = target / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    (target / 'production/joint-freeze.json').write_bytes(freeze_file.read_bytes())
    receipt = {'schema': 'game-market-joint-replay-instantiation/v1',
               'created_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
               'files': len(freeze['files']), 'freeze_sha256': hashlib.sha256(freeze_file.read_bytes()).hexdigest(),
               'replay_root': str(target), 'new_primary_missions': 0, 'new_customer_jobs': 0,
               'scope': 'Reproduction of already recorded outcomes. Original candidate source and frozen inputs remain unchanged.'}
    (target / 'REPLAY.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt))
    print('Prepare: ' + sys.executable + ' ' + str(target / 'production/run_joint_missions.py') + ' prepare')
    print('Advance: ' + sys.executable + ' ' + str(target / 'production/run_joint_missions.py') + ' advance')
    print('When an A arm pauses, inspect its before/after verifier records and supply the supported disposition explicitly.')


if __name__ == '__main__':
    main()
