from __future__ import annotations

import hashlib
import json
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
files = []
for folder in ['skills', 'conventional', 'independent', 'production', 'identity', 'workloads']:
    for path in sorted((ROOT / folder).rglob('*')):
        if path.is_file() and path.suffix in ['.py', '.mjs'] and '__pycache__' not in str(path) and 'history' not in path.parts:
            data = path.read_bytes()
            files.append({'path': str(path.relative_to(ROOT)), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()})
for name in ['identity/catalog.json', 'identity/authority-fixtures.json', 'protocol/study-design.json',
             'protocol/contribution-selection.json', 'protocol/admission-pin.json', 'evidence/admission-cached/catalog-admission.json',
             'workloads/seed-commitment.json', 'workloads/ACCEPTANCE_CONTRACT.md']:
    path = ROOT / name
    if path.exists():
        data = path.read_bytes()
        files.append({'path': name, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()})
manifest = {'schema': 'capability-advantage-runtime-source/v1', 'recorded_at': datetime.now(timezone.utc).isoformat(), 'files': files}
(ROOT / 'protocol/runtime-source.json').write_text(json.dumps(manifest, indent=2) + '\n')
print(json.dumps({'files': len(files), 'sha256': hashlib.sha256((ROOT / 'protocol/runtime-source.json').read_bytes()).hexdigest()}))
