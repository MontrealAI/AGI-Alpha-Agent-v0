from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--registration-url', required=True)
    parser.add_argument('--directory', type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    root = args.directory.resolve()
    protocol_path = root / 'market-protocol.json'
    freeze_path = root / 'market-freeze.json'
    if freeze_path.exists():
        raise ValueError('EXISTING_MARKET_FREEZE_IS_IMMUTABLE')
    protocol = json.loads(protocol_path.read_text())
    if protocol['status'] != 'DRAFT_NOT_EXECUTED' or protocol['market_outcomes_inspected'] is not False:
        raise ValueError('PROSPECTIVE_DRAFT_REQUIRED')
    check = subprocess.run(['node', str(root / 'run_market.mjs'), '--validate-only',
                            f'--protocol={protocol_path}'], capture_output=True, text=True, check=True)
    checked = json.loads(check.stdout)
    if checked.get('market_outcomes_run') != 0:
        raise ValueError('STATIC_VALIDATION_ONLY')
    timestamp = datetime.now(timezone.utc).isoformat()
    protocol['status'] = 'FROZEN_BEFORE_MARKET_OUTCOMES'
    protocol['frozen_at_utc'] = timestamp
    protocol['registration_url'] = args.registration_url
    protocol_path.write_text(json.dumps(protocol, indent=2) + '\n')
    paths = [root / name for name in ['market-protocol.json', 'calibration.json', 'network_market.mjs',
        'run_market.mjs', 'build_calibration.py', 'freeze_market.py', 'test_network_market.mjs',
        'test_build_calibration.py', 'PRIMITIVES_TRANSFORMATION.json', 'INHERITED_SOURCE.json']]
    paths += list((root / 'inherited').rglob('*.mjs'))
    rows = [{'path': str(path.relative_to(root)), 'bytes': path.stat().st_size,
             'sha256': hashlib.sha256(path.read_bytes()).hexdigest()} for path in sorted(paths)]
    freeze = {'schema': 'capability-advantage-market-source-freeze/v1',
        'frozen_at_utc': timestamp, 'market_outcomes_inspected': False,
        'registration_url': args.registration_url,
        'primary_calibration_already_observed': True,
        'static_validation': checked,
        'expected_worlds': protocol['expected']['paired_worlds'],
        'wall_and_cpu_envelope_seconds': protocol['limits'], 'files': rows}
    with freeze_path.open('x') as stream:
        stream.write(json.dumps(freeze, indent=2) + '\n')
    print(json.dumps({'market_freeze': str(freeze_path),
        'sha256': hashlib.sha256(freeze_path.read_bytes()).hexdigest(),
        'files': len(rows), 'paired_worlds': protocol['expected']['paired_worlds'], 'market_outcomes_run': 0}))


if __name__ == '__main__':
    main()
