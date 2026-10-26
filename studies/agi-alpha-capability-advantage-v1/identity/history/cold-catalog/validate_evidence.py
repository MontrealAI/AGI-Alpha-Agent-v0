from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'workloads'))
from verifier import verify

request = json.loads(sys.stdin.read())
reports = []
for case in request['cases']:
    task = json.loads((ROOT / case['task']).read_text())
    result = json.loads((ROOT / case['result']).read_text())
    oracle = json.loads((ROOT / case['oracle']).read_text())
    parent_task = json.loads((ROOT / case['parent_task']).read_text()) if case.get('parent_task') else None
    parent_result = json.loads((ROOT / case['parent_result']).read_text()) if case.get('parent_result') else None
    reports.append(verify(task, result, oracle, parent_task=parent_task, parent_result=parent_result))
print(json.dumps({'accepted': bool(reports) and all(r['accepted'] for r in reports), 'checks': len(reports), 'reports': reports}, allow_nan=False))
