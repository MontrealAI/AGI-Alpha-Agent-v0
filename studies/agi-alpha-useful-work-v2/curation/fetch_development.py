# SPDX-License-Identifier: Apache-2.0
"""Acquire exact public development wheels; no package is executed here."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import time
import urllib.request

from packaging.tags import sys_tags
from packaging.utils import parse_wheel_filename

ROOT = Path(__file__).resolve().parents[1]
PINS = {
    'starlette': '1.7.0', 'anyio': '4.15.1', 'pydantic': '2.13.5',
    'pydantic-core': '2.46.5', 'annotated-types': '0.8.0',
    'typing-extensions': '4.16.0', 'typing-inspection': '0.4.4', 'idna': '3.20',
}


def main():
    start = time.perf_counter()
    cpu = time.process_time()
    target = ROOT / 'data' / 'development-environment'
    wheels = target / 'wheels'
    wheels.mkdir(parents=True, exist_ok=True)
    tags = {tag: i for i, tag in enumerate(sys_tags())}
    lock_source = (ROOT / 'discovery/requirements/requirements-agent.lock').read_text()
    records = []
    requests = []
    try:
        for name, version in PINS.items():
            url = f'https://pypi.org/pypi/{name}/{version}/json'
            t = time.perf_counter()
            with urllib.request.urlopen(url, timeout=30) as response:
                raw = response.read(8_000_001)
            if len(raw) > 8_000_000:
                raise ValueError('METADATA_BOUND')
            requests.append({'url': url, 'bytes': len(raw), 'seconds': time.perf_counter() - t})
            metadata = json.loads(raw)
            (target / f'{name}-{version}-metadata.json').write_bytes(raw)
            candidates = []
            for item in metadata['urls']:
                if item['packagetype'] != 'bdist_wheel' or item.get('yanked'):
                    continue
                _, _, _, supported = parse_wheel_filename(item['filename'])
                ranks = [tags[tag] for tag in supported if tag in tags]
                if ranks:
                    candidates.append((min(ranks), item['filename'], item))
            if not candidates:
                raise ValueError('NO_COMPATIBLE_WHEEL: ' + name)
            item = min(candidates)[2]
            expected = item['digests']['sha256']
            if expected not in lock_source:
                raise ValueError('WHEEL_NOT_IN_NATIVE_LOCK: ' + name)
            t = time.perf_counter()
            with urllib.request.urlopen(item['url'], timeout=30) as response:
                raw = response.read(20_000_001)
            requests.append({'url': item['url'], 'bytes': len(raw), 'seconds': time.perf_counter() - t})
            if len(raw) > 20_000_000 or hashlib.sha256(raw).hexdigest() != expected:
                raise ValueError('WHEEL_IDENTITY')
            (wheels / item['filename']).write_bytes(raw)
            records.append({'name': name, 'version': version, 'filename': item['filename'],
                            'sha256': expected, 'bytes': len(raw), 'url': item['url'],
                            'requires_dist': metadata['info'].get('requires_dist', []),
                            'native_lock_hash_present': True})
        text = ''.join(f"{r['name']}=={r['version']} --hash=sha256:{r['sha256']}\n" for r in records)
        (target / 'requirements.lock').write_text(text)
        status = 'COMPLETE'
        error = None
    except Exception as exc:
        status = 'FAILED'
        error = f'{type(exc).__name__}: {exc}'
    result = {'schema': 'component-development-environment/v1', 'status': status, 'error': error,
              'profile': 'Exact imported component projection of native requirements-agent.lock; not the whole agent installation',
              'python': sys.version, 'wheels': records, 'requests': requests,
              'wall_seconds': time.perf_counter() - start, 'cpu_seconds': time.process_time() - cpu,
              'money_usd': None, 'source_execution': False, 'confirmation_input': False}
    (target / 'acquisition.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k not in {'wheels', 'requests'}}))
    if error:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
