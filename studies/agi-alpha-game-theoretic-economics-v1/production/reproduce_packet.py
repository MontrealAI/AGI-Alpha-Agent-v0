# SPDX-License-Identifier: Apache-2.0
"""Export the unchanged source-qualified historical packet, without operator adoption."""
from pathlib import Path
import argparse
import datetime
import hashlib
import json
import os
import resource
import subprocess
import sys
import time
import zipfile


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    vendor = root / 'vendor/product'
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    snapshot = json.loads((root / 'production/product-snapshot.json').read_text())

    def verify_sources():
        for entry in snapshot['files']:
            data = (vendor / entry['path']).read_bytes()
            if hashlib.sha256(data).hexdigest() != entry['sha256']:
                raise ValueError('source identity changed: ' + entry['path'])

    verify_sources()
    command = [sys.executable, '-B', '-m', 'contrib.upgrade_decision.export_packet',
               '--output', str(out / 'AGI_ALPHA_Upgrade_Decision_Packet.zip')]
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    wall, parent = time.perf_counter(), time.process_time()
    child = resource.getrusage(resource.RUSAGE_CHILDREN)
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', PYTHONPATH=str(vendor))
    run = subprocess.run(command, cwd=vendor, env=env, capture_output=True, timeout=60)
    child_after = resource.getrusage(resource.RUSAGE_CHILDREN)
    measures = {'wall_seconds': time.perf_counter() - wall,
                'meter_cpu_seconds': time.process_time() - parent,
                'child_cpu_seconds': child_after.ru_utime + child_after.ru_stime - child.ru_utime - child.ru_stime,
                'child_peak_rss_kib': child_after.ru_maxrss}
    (out / 'stdout.txt').write_bytes(run.stdout)
    (out / 'stderr.txt').write_bytes(run.stderr)
    verify_sources()
    packet = None
    if run.returncode == 0:
        path = out / 'AGI_ALPHA_Upgrade_Decision_Packet.zip'
        data = path.read_bytes()
        with zipfile.ZipFile(path) as archive:
            assert archive.testzip() is None
            names = archive.namelist()
            assert len(names) == len(set(names))
            assert all(not Path(n).is_absolute() and '..' not in Path(n).parts for n in names)
            packet = {'path': path.name, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest(),
                      'members': len(names), 'crc_valid': True}
    receipt = {'schema': 'game-market-historical-packet-export/v1', 'started_at': started,
               'ended_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
               'source_commit': snapshot['source_commit'], 'source_unchanged': True,
               'command': command, 'exit_code': run.returncode,
               'python': sys.version, 'node': subprocess.check_output(['node', '--version'], text=True).strip(),
               'resources': measures, 'packet': packet, 'new_missions': 0, 'customer_jobs': 0,
               'complete_cost_usd': None, 'human_attention_minutes': None,
               'actual_collections_usd': 0,
               'scope': 'Actual inert export and revalidation of original historical consumer observations. No new consumer mission, operator grant, full-application acceptance, collection or production deployment.'}
    (out / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt))
    raise SystemExit(run.returncode)


if __name__ == '__main__':
    main()
