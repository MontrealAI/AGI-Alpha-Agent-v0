import argparse
import email.policy
import hashlib
import json
import math
import os
import re
import sys
import time
import tomllib
import zipfile
from email.parser import BytesParser
from pathlib import Path
from urllib.parse import unquote, urlparse

import packaging
from packaging.markers import default_environment
from packaging.requirements import Requirement
from packaging.specifiers import SpecifierSet
from packaging.tags import parse_tag, sys_tags
from packaging.utils import canonicalize_name, parse_wheel_filename
from packaging.version import Version


def digest(value):
    return hashlib.sha256(value).hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text())


def frozen_path(base, value):
    if not isinstance(value, str) or not value:
        raise ValueError('missing input path')
    p = Path(value)
    if p.is_absolute():
        raise ValueError('input paths must be relative to job')
    return (base / p).resolve()


def output_path(base, value):
    if not isinstance(value, str) or not value or Path(value).is_absolute():
        raise ValueError('invalid result artifact path')
    path = (base / value).resolve()
    if not path.is_relative_to(base.resolve()) or path.is_symlink() or not path.is_file():
        raise ValueError('result artifact absent or outside result directory')
    return path


def applies(requirement, env, extras=()):
    if requirement.marker is None:
        return True
    return any(requirement.marker.evaluate(environment={**env, 'extra': extra})
               for extra in ['', *sorted(extras)])


def parse_lock(raw, env):
    text = raw.decode('utf-8')
    logical, current = [], ''
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith('#'):
            continue
        current += ' ' + stripped.removesuffix('\\').strip()
        if not stripped.endswith('\\'):
            logical.append(current.strip())
            current = ''
    if current:
        raise ValueError('unterminated lock continuation')
    result, seen = {}, set()
    for line in logical:
        line = line.split(' #', 1)[0]
        hashes = re.findall(r'--hash=sha256:([a-f0-9]{64})(?=\s|$)', line)
        requirement_text = re.sub(r'\s*--hash=sha256:[a-f0-9]{64}(?=\s|$)', '', line).strip()
        if '--' in requirement_text or not hashes:
            raise ValueError('only hash-bound requirements supported')
        req = Requirement(requirement_text)
        pins = list(req.specifier)
        name = canonicalize_name(req.name)
        if req.url or len(pins) != 1 or pins[0].operator != '==' or '*' in pins[0].version:
            raise ValueError('only exact named pins supported')
        if name in seen:
            raise ValueError('duplicate normalized lock name: ' + name)
        seen.add(name)
        if applies(req, env):
            result[name] = {'requirement': req, 'version': str(Version(pins[0].version)),
                            'hashes': set(hashes)}
    if not result:
        raise ValueError('empty active lock')
    return result


def metadata_from_wheel(path, identity, lock_entry, native_tags):
    raw = path.read_bytes()
    sha = digest(raw)
    if sha != identity['sha256'] or sha not in lock_entry['hashes']:
        raise ValueError('wheel bytes do not match job and lock: ' + path.name)
    name, version, _, filename_tags = parse_wheel_filename(path.name)
    expected_name = canonicalize_name(identity['name'])
    expected_version = str(Version(identity['version']))
    if name != expected_name or str(version) != expected_version or expected_version != lock_entry['version']:
        raise ValueError('wheel filename, manifest and pin disagree: ' + path.name)
    if not filename_tags.intersection(native_tags):
        raise ValueError('wheel tags unsupported for declared current target: ' + path.name)
    with zipfile.ZipFile(path) as archive:
        members = archive.namelist()
        if len(members) != len(set(members)):
            raise ValueError('duplicate wheel archive member')
        paths = [p for p in members if p.endswith('.dist-info/METADATA')]
        if len(paths) != 1:
            raise ValueError('wheel requires one METADATA')
        metadata_bytes = archive.read(paths[0])
        wheel_bytes = archive.read(paths[0].rsplit('/', 1)[0] + '/WHEEL')
    metadata = BytesParser(policy=email.policy.compat32).parsebytes(metadata_bytes)
    wheel = BytesParser(policy=email.policy.compat32).parsebytes(wheel_bytes)
    for field in ['Metadata-Version', 'Name', 'Version']:
        if len(metadata.get_all(field, [])) != 1:
            raise ValueError('missing or duplicate wheel field: ' + field)
    if Version(metadata['Metadata-Version']).major > 2:
        raise ValueError('unsupported metadata major version')
    if canonicalize_name(metadata['Name']) != name or Version(metadata['Version']) != version:
        raise ValueError('wheel METADATA and filename disagree')
    wheel_tags = set()
    for tag in wheel.get_all('Tag', []):
        wheel_tags.update(parse_tag(tag))
    if wheel_tags != filename_tags:
        raise ValueError('WHEEL tags and filename disagree')
    python_rows = metadata.get_all('Requires-Python', [])
    if len(python_rows) > 1:
        raise ValueError('duplicate Requires-Python')
    requires_python = python_rows[0] if python_rows else ''
    SpecifierSet(requires_python)
    requirements = [Requirement(x) for x in metadata.get_all('Requires-Dist', [])]
    if any(x.url for x in requirements):
        raise ValueError('direct URL dependency outside closed specification')
    extras = {canonicalize_name(x) for x in metadata.get_all('Provides-Extra', [])}
    return {'name': name, 'version': str(version), 'filename': path.name, 'sha256': sha,
            'metadata_sha256': digest(metadata_bytes), 'requires_python': requires_python,
            'requirements': requirements, 'extras': extras}


def verify(job_path, result_path):
    start, cpu = time.perf_counter(), time.process_time()
    errors, conflicts, evidence, rows = [], [], {}, []
    independent_verdict = 'INCOMPLETE'
    job_path, result_path = Path(job_path).resolve(), Path(result_path).resolve()
    job_raw, result_raw = job_path.read_bytes(), result_path.read_bytes()
    job, result = json.loads(job_raw), json.loads(result_raw)
    try:
        if job.get('schema') != 'agialpha-lock-job/v1' or result.get('schema') != 'agialpha-lock-result/v1':
            raise ValueError('schema mismatch')
        if result.get('job_id') != job.get('id') or result.get('job_sha256') != digest(job_raw):
            raise ValueError('stale or wrong job binding')
        if not isinstance(job.get('id'), str) or not job['id']:
            raise ValueError('missing job identity')
        env = job.get('target_environment')
        native = default_environment()
        if env != native:
            raise ValueError('only exact current interpreter/platform marker environment supported')
        if result.get('application_qualified') is not False or result.get('authority') != [] or result.get('financial_action') is not False:
            raise ValueError('unsupported authority or application claim')
        for field in ['elapsed_wall_seconds', 'cpu_seconds']:
            value = result.get(field)
            if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
                raise ValueError('invalid resource measurement: ' + field)
        if type(result.get('pip_exit_code')) is not int:
            raise ValueError('pip exit status absent')
        if not isinstance(result.get('tool_versions'), dict) or any(
            not isinstance(result['tool_versions'].get(k), str) or not result['tool_versions'][k]
            for k in ['python', 'pip', 'packaging']):
            raise ValueError('tool version capture absent')
        commands = result.get('commands', [])
        pip_commands = [c for c in commands if isinstance(c, list) and all(isinstance(v, str) for v in c)
                        and 'pip' in c and 'install' in c]
        if len(pip_commands) != 1:
            raise ValueError('one raw pip resolution command required')
        command = pip_commands[0]
        for flag in ['--dry-run', '--ignore-installed', '--no-index', '--require-hashes', '--report', '--find-links']:
            if flag not in command:
                raise ValueError('required pip boundary absent: ' + flag)
        if '--only-binary=:all:' not in command and not any(command[i:i+2] == ['--only-binary', ':all:'] for i in range(len(command)-1)):
            raise ValueError('wheel-only resolution required')
        if any(flag in command for flag in ['--no-deps', '--ignore-requires-python', '--no-require-hashes', '--index-url', '--extra-index-url']):
            raise ValueError('unsupported pip bypass option')
        files = result.get('files', {})
        for key in ['stdout', 'stderr']:
            path = output_path(result_path.parent, files.get(key))
            evidence[key + '_sha256'] = digest(path.read_bytes())
        lock_path = frozen_path(job_path.parent, job['lock_path'])
        project_path = frozen_path(job_path.parent, job['pyproject_path'])
        lock_raw, project_raw = lock_path.read_bytes(), project_path.read_bytes()
        if digest(lock_raw) != job['lock_sha256'] or digest(project_raw) != job['pyproject_sha256']:
            raise ValueError('lock or project source identity mismatch')
        lock = parse_lock(lock_raw, env)
        project = tomllib.loads(project_raw.decode())['project']
        requested_extras = job['project_extras']
        if not isinstance(requested_extras, list) or len(requested_extras) != len(set(requested_extras)) or any(not isinstance(x, str) for x in requested_extras):
            raise ValueError('invalid selected project extras')
        optional = project.get('optional-dependencies', {})
        if any(x not in optional for x in requested_extras):
            raise ValueError('unknown requested project extra')
        root_texts = list(project.get('dependencies', []))
        for extra in requested_extras:
            root_texts += optional[extra]
        root_requirements = [Requirement(x) for x in root_texts]
        if any(x.url for x in root_requirements):
            raise ValueError('direct URL root outside scope')
        project_python = project.get('requires-python', '')
        if not SpecifierSet(project_python).contains(env['python_full_version'], prereleases=True):
            conflicts.append({'kind': 'project_python', 'requires': project_python, 'actual': env['python_full_version']})
        wheelhouse = frozen_path(job_path.parent, job['wheelhouse_path'])
        identities = job.get('wheels')
        if not isinstance(identities, list):
            raise ValueError('wheel identity closure absent')
        manifest = {}
        for item in identities:
            if not isinstance(item, dict) or any(not isinstance(item.get(k), str) for k in ['filename', 'name', 'version', 'sha256']):
                raise ValueError('wheel identity row incomplete')
            if Path(item['filename']).name != item['filename'] or '/' in item['filename'] or '\\' in item['filename']:
                raise ValueError('wheel filename must be basename')
            name = canonicalize_name(item['name'])
            if name in manifest or not re.fullmatch('[a-f0-9]{64}', item['sha256']):
                raise ValueError('duplicate or invalid wheel identity')
            manifest[name] = item
        if set(manifest) != set(lock):
            raise ValueError('selected wheel manifest must cover exactly active lock rows')
        tags = set(sys_tags())
        distributions = {name: metadata_from_wheel(wheelhouse / item['filename'], item, lock[name], tags)
                         for name, item in manifest.items()}
        extras = {name: {canonicalize_name(x) for x in row['requirement'].extras} for name, row in lock.items()}
        root_rows = []
        for requirement in root_requirements:
            active = applies(requirement, env, requested_extras)
            name = canonicalize_name(requirement.name)
            root_rows.append({'requirement': str(requirement), 'active': active})
            if active:
                if name not in lock:
                    conflicts.append({'kind': 'missing_root_pin', 'requirement': str(requirement)})
                elif not requirement.specifier.contains(lock[name]['version'], prereleases=True):
                    conflicts.append({'kind': 'root_version', 'requirement': str(requirement), 'actual': lock[name]['version']})
                if name in extras:
                    extras[name].update(canonicalize_name(x) for x in requirement.extras)
        for _ in range(1 + len(distributions) * 20):
            changed = False
            for name, dist in distributions.items():
                if not extras[name].issubset(dist['extras']):
                    raise ValueError('unknown requested distribution extra: ' + name)
                for req in dist['requirements']:
                    target = canonicalize_name(req.name)
                    if applies(req, env, extras[name]) and target in extras:
                        old = len(extras[target])
                        extras[target].update(canonicalize_name(x) for x in req.extras)
                        changed |= old != len(extras[target])
            if not changed:
                break
        else:
            raise ValueError('extras closure bound exceeded')
        for name, dist in sorted(distributions.items()):
            if not SpecifierSet(dist['requires_python']).contains(env['python_full_version'], prereleases=True):
                conflicts.append({'kind': 'distribution_python', 'package': name, 'requires': dist['requires_python'], 'actual': env['python_full_version']})
            for index, req in enumerate(dist['requirements']):
                active = applies(req, env, extras[name])
                target = canonicalize_name(req.name)
                satisfied = not active or (target in lock and req.specifier.contains(lock[target]['version'], prereleases=True))
                row = {'source': name, 'source_version': dist['version'], 'metadata_sha256': dist['metadata_sha256'],
                       'metadata_requirement_index': index, 'requirement': str(req), 'active': active,
                       'target': target, 'selected_version': lock.get(target, {}).get('version'), 'satisfied': satisfied}
                rows.append(row)
                if active and not satisfied:
                    conflicts.append({'kind': 'dependency_version' if target in lock else 'missing_dependency_pin', **row})
        independent_verdict = 'CONFLICT' if conflicts else 'CONSISTENT'
        if result['pip_exit_code'] == 0:
            report_path = output_path(result_path.parent, files.get('report'))
            report_raw = report_path.read_bytes()
            report = json.loads(report_raw)
            evidence['pip_report_sha256'] = digest(report_raw)
            if report.get('version') != '1' or report.get('environment') != env:
                raise ValueError('pip report version or environment mismatch')
            observed = {}
            for item in report['install']:
                metadata = item['metadata']
                name = canonicalize_name(metadata['name'])
                if name in observed or name not in distributions:
                    raise ValueError('unexpected or duplicate pip report distribution')
                dist = distributions[name]
                archive = item['download_info']['archive_info']
                reported_hash = archive.get('hashes', {}).get('sha256')
                legacy = archive.get('hash')
                if reported_hash != dist['sha256'] or (legacy and legacy != 'sha256=' + dist['sha256']):
                    raise ValueError('pip report archive hash mismatch')
                filename = Path(unquote(urlparse(item['download_info']['url']).path)).name
                if filename != dist['filename'] or Version(metadata['version']) != Version(dist['version']):
                    raise ValueError('pip report wheel identity mismatch')
                reported_requirements = sorted(str(Requirement(x)) for x in metadata.get('requires_dist', []))
                actual_requirements = sorted(str(x) for x in dist['requirements'])
                if reported_requirements != actual_requirements or metadata.get('requires_python', '') != dist['requires_python']:
                    raise ValueError('pip report metadata not exact selected wheel metadata')
                observed[name] = True
            if set(observed) != set(lock):
                raise ValueError('pip report selected set incomplete')
        elif not conflicts:
            raise ValueError('pip failure has no independently substantiated metadata contradiction')
        if result.get('decision') != independent_verdict:
            raise ValueError('builder verdict does not match independent result')
        evidence.update({'lock_sha256': digest(lock_raw), 'pyproject_sha256': digest(project_raw),
                         'active_lock_count': len(lock), 'roots': root_rows,
                         'selected_extras': {k: sorted(v) for k, v in sorted(extras.items())},
                         'wheels': [{k: d[k] for k in ['name', 'version', 'filename', 'sha256', 'metadata_sha256', 'requires_python']}
                                    for _, d in sorted(distributions.items())]})
    except (ValueError, TypeError, KeyError, OSError, zipfile.BadZipFile, UnicodeError, email.errors.MessageError) as error:
        errors.append(type(error).__name__ + ': ' + str(error))
    return {'schema': 'agialpha-independent-lock-certificate/v1',
            'status': 'INCOMPLETE' if errors else 'COMPLETE',
            'verdict': 'INCOMPLETE' if errors else independent_verdict,
            'job_id': job.get('id'), 'job_sha256': digest(job_raw), 'result_sha256': digest(result_raw),
            'independent_metadata_verdict': independent_verdict, 'errors': errors,
            'substantiated_witnesses': conflicts, 'dependency_edges': rows, 'evidence': evidence,
            'application_qualified': False, 'authority': [], 'financial_action': False,
            'scope': 'Exact declared native interpreter and wheel metadata dependency constraints only; no application behavior, security, runtime, release or installation qualification.',
            'evidence_limit': 'Independent byte and metadata checking of supplied artifacts and recorded pip output; no hostile-recorder attestation or fresh consumer execution.',
            'verifier': {'source_sha256': digest(Path(__file__).read_bytes()), 'python': sys.version.split()[0],
                         'packaging': packaging.__version__, 'wall_seconds': time.perf_counter()-start,
                         'cpu_seconds': time.process_time()-cpu}}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--job', required=True)
    parser.add_argument('--result', required=True)
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    result = verify(args.job, args.result)
    target = Path(args.out)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'status': result['status'], 'verdict': result['verdict'], 'errors': result['errors']}))
    return 0 if result['status'] == 'COMPLETE' else 2


if __name__ == '__main__':
    raise SystemExit(main())
