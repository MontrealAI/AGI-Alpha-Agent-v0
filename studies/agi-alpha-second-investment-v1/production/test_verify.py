import argparse
import hashlib
import json
import shutil
import sys
import time
import zipfile
from pathlib import Path

from packaging.markers import default_environment

from verify import verify


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def put(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def fixture(path, mode):
    path.mkdir(parents=True, exist_ok=False)
    wheelhouse = path / 'wheels'
    wheelhouse.mkdir()
    result_dir = path / 'result'
    result_dir.mkdir()
    entries = [
        {'name': 'candidate-app', 'version': '1.0', 'requires': ['helper>=1.0'], 'python': '>=3.11', 'extras': []},
        {'name': 'helper', 'version': '1.0', 'requires': [], 'python': '>=3.11', 'extras': []}]
    root_req, root_python = 'candidate-app>=1.0', '>=3.11'
    expected, decision, exit_code = ('COMPLETE', 'CONSISTENT'), 'CONSISTENT', 0
    if mode in ['missing-dependency', 'wrong-dependency-version', 'root-version', 'package-python', 'project-python', 'active-marker', 'recursive-extra']:
        expected, decision, exit_code = ('COMPLETE', 'CONFLICT'), 'CONFLICT', 1
    if mode == 'missing-dependency':
        entries = entries[:1]
    elif mode == 'wrong-dependency-version':
        entries[0]['requires'] = ['helper>=2.0']
    elif mode == 'root-version':
        root_req = 'candidate-app>=2.0'
    elif mode == 'package-python':
        entries[0]['python'] = '<3'
    elif mode == 'project-python':
        root_python = '<3'
    elif mode == 'inactive-marker':
        entries[0]['requires'] += ['absent>=1.0; sys_platform == "win32"']
    elif mode == 'active-marker':
        entries[0]['requires'] += ['absent>=1.0; sys_platform == "linux"']
    elif mode == 'recursive-extra':
        entries[0]['requires'] = ['helper[audit]>=1.0']
        entries[1]['extras'] = ['audit']
        entries[1]['requires'] = ['absent>=1.0; extra == "audit"']
    elif mode == 'unknown-extra':
        entries[0]['requires'] = ['helper[unknown]>=1.0']
    elif mode == 'url-requirement':
        entries[0]['requires'] = ['helper @ https://example.invalid/helper.whl']
    elif mode == 'malformed-marker':
        entries[0]['requires'] = ['helper>=1.0; sys_platform ???']
    elif mode == 'false-consistent':
        entries[0]['requires'] = ['helper>=2.0']
    manifest, report_items, lock_lines = [], [], []
    for i, entry in enumerate(entries):
        stem = entry['name'].replace('-', '_') + '-' + entry['version']
        tag = 'cp27-none-win32' if mode == 'unsupported-wheel-tag' and i == 0 else 'py3-none-any'
        filename = stem + '-' + tag + '.whl'
        meta_name = 'wrong-name' if mode == 'metadata-name' and i == 0 else entry['name']
        metadata = '\n'.join(['Metadata-Version: 2.4', 'Name: ' + meta_name, 'Version: ' + entry['version'],
                              'Requires-Python: ' + entry['python'],
                              *['Provides-Extra: ' + x for x in entry['extras']],
                              *['Requires-Dist: ' + x for x in entry['requires']], '', ''])
        with zipfile.ZipFile(wheelhouse / filename, 'w') as archive:
            archive.writestr(stem + '.dist-info/METADATA', metadata)
            archive.writestr(stem + '.dist-info/WHEEL', 'Wheel-Version: 1.0\nGenerator: synthetic-control\nRoot-Is-Purelib: true\nTag: ' + tag + '\n')
        checksum = sha((wheelhouse / filename).read_bytes())
        manifest.append({'filename': filename, 'name': entry['name'], 'version': entry['version'], 'sha256': checksum})
        lock_lines.append(entry['name'] + '==' + entry['version'] + ' --hash=sha256:' + checksum)
        report_items.append({'download_info': {'url': 'file:///recorded/original/location/' + filename,
                              'archive_info': {'hashes': {'sha256': checksum}, 'hash': 'sha256=' + checksum}},
                             'metadata': {'name': meta_name, 'version': entry['version'],
                              'requires_python': entry['python'], 'requires_dist': entry['requires']}})
    if mode == 'duplicate-pin':
        lock_lines.append(lock_lines[0].replace('candidate-app', 'candidate_app'))
    lock = path / 'requirements.lock'
    lock.write_text('\n'.join(lock_lines) + '\n')
    project = path / 'pyproject.toml'
    project.write_text('[project]\nname = "synthetic-root"\nversion = "1.0"\nrequires-python = ' + json.dumps(root_python) + '\ndependencies = [' + json.dumps(root_req) + ']\n[project.optional-dependencies]\nchain = []\n')
    job = {'schema': 'agialpha-lock-job/v1', 'id': 'synthetic-' + mode, 'lock_path': lock.name,
           'lock_sha256': sha(lock.read_bytes()), 'pyproject_path': project.name,
           'pyproject_sha256': sha(project.read_bytes()), 'project_extras': ['chain'],
           'wheelhouse_path': 'wheels', 'wheels': manifest, 'target_environment': default_environment()}
    job_path = path / 'job.json'
    put(job_path, job)
    (result_dir / 'pip.stdout.txt').write_text('Synthetic development fixture; no real pip invocation.\n')
    (result_dir / 'pip.stderr.txt').write_text('Synthetic conflict witness.\n' if exit_code else '')
    report = {'version': '1', 'environment': default_environment(), 'install': report_items}
    if mode == 'report-missing-package':
        report['install'] = report['install'][:1]
    if mode == 'report-metadata-tamper':
        report['install'][0]['metadata']['requires_dist'] = []
    if mode == 'portable-report-path':
        report['install'][0]['download_info']['url'] = 'file:///another/relocation/' + manifest[0]['filename']
    put(result_dir / 'pip-report.json', report)
    result = {'schema': 'agialpha-lock-result/v1', 'job_id': job['id'], 'job_sha256': sha(job_path.read_bytes()),
              'decision': decision, 'pip_exit_code': exit_code,
              'files': {'stdout': 'pip.stdout.txt', 'stderr': 'pip.stderr.txt', 'report': 'pip-report.json' if not exit_code else None},
              'commands': [[sys.executable, '-m', 'pip', 'install', '--dry-run', '--ignore-installed', '--no-index',
                            '--only-binary=:all:', '--require-hashes', '--report', 'pip-report.json', '--find-links', 'wheels', '-r', 'requirements.lock']],
              'tool_versions': {'python': sys.version.split()[0], 'pip': 'synthetic', 'packaging': 'synthetic'},
              'elapsed_wall_seconds': 0.01, 'cpu_seconds': 0.01, 'application_qualified': False,
              'authority': [], 'financial_action': False, 'synthetic_control_only': True}
    if mode == 'stale-job':
        result['job_sha256'] = '0' * 64
    if mode == 'escaping-output':
        result['files']['stdout'] = '../requirements.lock'
    if mode == 'missing-capture':
        (result_dir / 'pip.stderr.txt').unlink()
    if mode == 'invalid-resource':
        result['cpu_seconds'] = float('nan')
    if mode == 'wheel-hash-tamper':
        with (wheelhouse / manifest[0]['filename']).open('ab') as handle:
            handle.write(b'tamper')
    if mode not in ['valid', 'inactive-marker', 'portable-report-path', 'missing-dependency', 'wrong-dependency-version',
                    'root-version', 'package-python', 'project-python', 'active-marker', 'recursive-extra']:
        expected = ('INCOMPLETE', 'INCOMPLETE')
    result_path = result_dir / 'result.json'
    put(result_path, result)
    return job_path, result_path, expected


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    base = Path(args.out)
    if base.exists():
        raise SystemExit('Fresh output directory required')
    base.mkdir(parents=True)
    start = time.perf_counter()
    modes = ['valid', 'missing-dependency', 'wrong-dependency-version', 'root-version', 'package-python',
             'project-python', 'inactive-marker', 'active-marker', 'recursive-extra', 'unknown-extra',
             'wheel-hash-tamper', 'metadata-name', 'unsupported-wheel-tag', 'report-missing-package',
             'stale-job', 'escaping-output', 'missing-capture', 'url-requirement', 'malformed-marker',
             'invalid-resource', 'report-metadata-tamper', 'portable-report-path', 'false-consistent', 'duplicate-pin']
    outcomes = []
    for mode in modes:
        job, result, expected = fixture(base / mode, mode)
        try:
            certificate = verify(job, result)
            put(result.parent / 'certificate.json', certificate)
            observed = (certificate['status'], certificate['verdict'])
            outcomes.append({'control': mode, 'expected': expected, 'observed': observed,
                             'passed': observed == expected, 'errors': certificate['errors']})
        except Exception as error:
            outcomes.append({'control': mode, 'expected': expected, 'passed': False,
                             'exception': type(error).__name__ + ': ' + str(error)})
    output = {'schema': 'agialpha-independent-verifier-controls/v1', 'synthetic_only': True,
              'production_missions': 0, 'actual_customer_jobs': 0, 'controls': outcomes,
              'passed': sum(x['passed'] for x in outcomes), 'total': len(outcomes),
              'wall_seconds': time.perf_counter()-start,
              'verifier_sha256': sha((Path(__file__).parent / 'verify.py').read_bytes())}
    put(base / 'summary.json', output)
    print(json.dumps({k: output[k] for k in ['passed', 'total', 'wall_seconds']}))
    for row in outcomes:
        if not row['passed']:
            print(json.dumps(row))
    return 0 if output['passed'] == output['total'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
