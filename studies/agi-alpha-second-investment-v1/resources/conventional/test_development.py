from pathlib import Path
import copy
import hashlib
import json
import resource
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
original = json.loads((HERE / 'development-job.json').read_text())
cases = []
root_conflict = copy.deepcopy(original)
project = (HERE / root_conflict['pyproject_path']).read_text().replace('httpx>=0.28,<1', 'httpx>=99,<100')
project_path = HERE / 'development-conflicting-pyproject.toml'
project_path.write_text(project)
root_conflict['pyproject_path'] = project_path.name
root_conflict['pyproject_sha256'] = hashlib.sha256(project_path.read_bytes()).hexdigest()
cases.append(('root-conflict', root_conflict, 'CONFLICT'))
missing = copy.deepcopy(original)
missing['wheels'] = [item for item in missing['wheels'] if item['name'] != 'httpx']
cases.append(('missing-wheel', missing, 'INCOMPLETE'))
hash_mismatch = copy.deepcopy(original)
hash_mismatch['lock_sha256'] = '0' * 64
cases.append(('hash-mismatch', hash_mismatch, 'INCOMPLETE'))
target_mismatch = copy.deepcopy(original)
target_mismatch['target_environment']['python_version'] = '3.11'
cases.append(('target-mismatch', target_mismatch, 'INCOMPLETE'))
started = time.perf_counter()
cpu = time.process_time()
children = resource.getrusage(resource.RUSAGE_CHILDREN)
child = children.ru_utime + children.ru_stime
results = []
for name, job, expected in cases:
    job['id'] = 'C-development-' + name
    job_path = HERE / ('job-v2-' + name + '.json')
    job_path.write_text(json.dumps(job, indent=2) + '\n')
    out = HERE / ('development-v2-' + name)
    cmd = [sys.executable, str(ROOT / 'production/conventional.py'), '--job', str(job_path), '--out', str(out)]
    ran = subprocess.run(cmd, capture_output=True, text=True, check=False)
    record = json.loads((out / 'result.json').read_text())
    results.append({'case': name, 'expected': expected, 'observed': record['decision'],
                    'passed': record['decision'] == expected and ran.returncode == 0,
                    'command': cmd, 'exit_code': ran.returncode, 'stdout': ran.stdout, 'stderr': ran.stderr,
                    'result_sha256': hashlib.sha256((out / 'result.json').read_bytes()).hexdigest()})
after = resource.getrusage(resource.RUSAGE_CHILDREN)
summary = {'schema': 'conventional-development-checks/v1', 'fresh_confirmation': False,
           'source_sha256': hashlib.sha256((ROOT / 'production/conventional.py').read_bytes()).hexdigest(),
           'wall_seconds': time.perf_counter() - started,
           'cpu_seconds': time.process_time() - cpu + after.ru_utime + after.ru_stime - child,
           'results': results, 'passed': all(item['passed'] for item in results)}
(HERE / 'development-checks.json').write_text(json.dumps(summary, indent=2) + '\n')
print(json.dumps({'passed': summary['passed'], 'cases': len(results), 'wall_seconds': summary['wall_seconds']}))
raise SystemExit(0 if summary['passed'] else 1)
