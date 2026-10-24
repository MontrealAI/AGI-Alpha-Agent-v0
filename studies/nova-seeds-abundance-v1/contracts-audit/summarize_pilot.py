# SPDX-License-Identifier: Apache-2.0
from pathlib import Path
from collections import defaultdict
import argparse, hashlib, json

parser = argparse.ArgumentParser()
parser.add_argument('--input', type=Path, default=Path(__file__).resolve().parents[1]/'research/results/pilot-03/missions.jsonl')
parser.add_argument('--output', type=Path, default=Path(__file__).resolve().parent/'tests/contracts/evidence/pilot-03-binding-summary.json')
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
raw = args.input.read_bytes()
rows = [json.loads(line) for line in raw.splitlines() if line.strip()]
methods = defaultdict(list)
for row in rows:
    methods[row['method']].append(row)
summary = {
    'schema': 'nova-seeds.writer10.development-binding-summary/v1',
    'scope': 'Actual completed development pilot-03 only; local-EVM mechanism binding, not holdout outcomes or physical instrument proof',
    'source': {'path': str(args.input.resolve().relative_to(root)), 'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)},
    'rows': len(rows),
    'worlds': len({(r['seed'], r['epoch'], r['scenario']) for r in rows}),
    'scenarios': sorted({r['scenario'] for r in rows}),
    'perMethod': {name: {
        'rows': len(rs),
        'usefulUtility': sum(r['outcome']['utility'] for r in rs),
        'completedJobs': sum(r['outcome']['completedJobs'] for r in rs),
        'failures': sum(r['outcome']['failures'] for r in rs),
        'attemptedJobs': sum(r['outcome']['attemptedJobs'] for r in rs),
        'simulatedInstrumentTicks': sum(r['simulated']['instrumentOccupationTicks'] for r in rs),
        'simulatedCalibrationAcquisitions': sum(r['simulated']['calibrationAcquisitions'] for r in rs),
        'measuredMethodCpuMicros': sum(sum(r['measured']['methodCpuMicros'].values()) for r in rs)
    } for name, rs in sorted(methods.items())},
    'money': {'revenue': None, 'profit': None, 'humanEffort': None},
    'claim': 'Same exact public evidence bytes bound by local contract graph and alternative signed registry; no productive service advantage inferred from token quantities'
}
assert summary['rows'] == 42 and summary['worlds'] == 6
args.output.parent.mkdir(parents=True, exist_ok=True)
args.output.write_text(json.dumps(summary, indent=2)+'\n')
