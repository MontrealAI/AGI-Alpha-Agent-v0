# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import re
import resource
import shutil
import subprocess
import sys
import time
import tomllib
from typing import Any
from urllib.parse import unquote, urlparse

import packaging
from packaging.markers import default_environment
from packaging.requirements import Requirement
from packaging.specifiers import SpecifierSet
from packaging.utils import canonicalize_name, parse_wheel_filename
from packaging.version import Version


def sha256(path: Path) -> str:
    result = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1 << 20), b''):
            result.update(block)
    return result.hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')


def exact_json(text: str) -> dict[str, Any]:
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        value: dict[str, Any] = {}
        for key, item in items:
            if key in value:
                raise ValueError('duplicate JSON field')
            value[key] = item
        return value
    value = json.loads(text, object_pairs_hook=pairs)
    if not isinstance(value, dict):
        raise ValueError('job must be an object')
    return value


def load_lock(text: str, environment: dict[str, str]) -> dict[str, dict[str, Any]]:
    if len(text.encode()) > 2_000_000:
        raise ValueError('lock exceeds bounded input size')
    logical = re.sub(r'\\\r?\n', ' ', text)
    pins: dict[str, dict[str, Any]] = {}
    for raw in logical.splitlines():
        line = re.sub(r'\s+#.*$', '', raw).strip()
        if not line or line.startswith('#'):
            continue
        hashes = re.findall(r'--hash=sha256:([a-fA-F0-9]{64})(?=\s|$)', line)
        requirement_text = re.sub(r'--hash=sha256:[a-fA-F0-9]{64}(?=\s|$)', '', line).strip()
        if not hashes or '--' in requirement_text:
            raise ValueError('lock requires exact hashed package requirements only')
        requirement = Requirement(requirement_text)
        specifiers = list(requirement.specifier)
        if requirement.url or len(specifiers) != 1 or specifiers[0].operator != '==':
            raise ValueError('lock contains unsupported nonexact requirement')
        version = specifiers[0].version
        Version(version)
        if requirement.marker and not requirement.marker.evaluate(environment={**environment, 'extra': ''}):
            continue
        name = canonicalize_name(requirement.name)
        if name in pins:
            raise ValueError('duplicate active locked package')
        pins[name] = {'version': version, 'hashes': sorted(set(value.lower() for value in hashes))}
    if not 1 <= len(pins) <= 256:
        raise ValueError('lock must contain between one and 256 active exact pins')
    return pins


def root_requirements(project: dict[str, Any], extras: list[str], pins: dict[str, dict[str, Any]],
                      environment: dict[str, str]) -> tuple[list[str], list[str]]:
    issues: list[str] = []
    required_python = project.get('requires-python')
    if not isinstance(required_python, str) or not required_python:
        raise ValueError('root requires-python is missing')
    if not SpecifierSet(required_python).contains(environment['python_full_version'], prereleases=True):
        issues.append('Root Requires-Python ' + required_python + ' excludes ' + environment['python_full_version'])
    optional = project.get('optional-dependencies', {})
    if not isinstance(optional, dict) or any(extra not in optional for extra in extras):
        raise ValueError('unknown root extra')
    entries: list[tuple[str, list[str]]] = [(raw, ['', *extras]) for raw in project.get('dependencies', [])]
    for extra in extras:
        entries.extend((raw, [extra]) for raw in optional[extra])
    rendered: set[str] = set()
    for raw, contexts in entries:
        req = Requirement(raw)
        if req.url:
            raise ValueError('root URL requirements are outside offline scope')
        if req.marker and not any(req.marker.evaluate(environment={**environment, 'extra': extra}) for extra in contexts):
            continue
        name = canonicalize_name(req.name)
        if name not in pins:
            raise ValueError('root dependency absent from supplied lock: ' + name)
        pin = pins[name]
        if not req.specifier.contains(pin['version'], prereleases=True):
            issues.append('Root requirement ' + str(req) + ' excludes locked ' + name + '==' + pin['version'])
        requested = '[' + ','.join(sorted(req.extras)) + ']' if req.extras else ''
        rendered.add(name + requested + '==' + pin['version'] + ' ' +
                     ' '.join('--hash=sha256:' + value for value in pin['hashes']))
    return sorted(rendered), issues


def resolve_input(parent: Path, raw: str) -> Path:
    if not isinstance(raw, str) or not raw:
        raise ValueError('input path must be nonempty text')
    return (parent / raw).resolve()


def decode(value: str | bytes | None) -> str:
    return value.decode('utf-8', errors='replace') if isinstance(value, bytes) else value or ''


def build(job_path: Path, output: Path) -> dict[str, Any]:
    started = time.perf_counter()
    own_cpu = time.process_time()
    children = resource.getrusage(resource.RUSAGE_CHILDREN)
    child_cpu = children.ru_utime + children.ru_stime
    output.mkdir(parents=True, exist_ok=False)
    result: dict[str, Any] = {
        'schema': 'agialpha-lock-result/v1', 'builder': 'conventional-c-pip-adoption/v1',
        'job_sha256': None, 'job_id': None, 'decision': 'INCOMPLETE', 'pip_exit_code': -1,
        'files': {'stdout': 'pip.stdout.txt', 'stderr': 'pip.stderr.txt', 'report': None},
        'tool_versions': {'python': sys.version.split()[0], 'pip': importlib.metadata.version('pip'),
                          'packaging': packaging.__version__},
        'commands': [], 'target_environment': default_environment(), 'root_issues': [], 'input_issues': [],
        'application_qualified': False, 'authority': [], 'financial_action': False,
        'scope': 'Offline dependency metadata consistency for the exact supplied lock and native environment only.',
        'actual_receipts': 0, 'model_calls_during_production': 0,
    }
    stdout, stderr = '', ''
    report_path = output / 'pip-report.json'
    try:
        original = job_path.read_bytes()
        if len(original) > 1_000_000:
            raise ValueError('job exceeds bounded input size')
        result['job_sha256'] = hashlib.sha256(original).hexdigest()
        job = exact_json(original.decode('utf-8'))
        fields = {'schema', 'id', 'lock_path', 'lock_sha256', 'pyproject_path', 'pyproject_sha256',
                  'project_extras', 'wheelhouse_path', 'wheels', 'target_environment'}
        if set(job) != fields or job['schema'] != 'agialpha-lock-job/v1':
            raise ValueError('unsupported job schema or fields')
        if not isinstance(job['id'], str) or not job['id'].strip() or len(job['id']) > 200:
            raise ValueError('invalid job identifier')
        result['job_id'] = job['id']
        environment = default_environment()
        if job['target_environment'] != environment:
            raise ValueError('target environment does not match this native process')
        extras = job['project_extras']
        if not isinstance(extras, list) or any(not isinstance(extra, str) for extra in extras) or len(set(extras)) != len(extras):
            raise ValueError('invalid root extras')
        lock = resolve_input(job_path.parent, job['lock_path'])
        pyproject = resolve_input(job_path.parent, job['pyproject_path'])
        wheelhouse = resolve_input(job_path.parent, job['wheelhouse_path'])
        for path, expected in ((lock, job['lock_sha256']), (pyproject, job['pyproject_sha256'])):
            if not isinstance(expected, str) or not re.fullmatch('[0-9a-f]{64}', expected) or sha256(path) != expected:
                raise ValueError('source file hash mismatch')
        lock_text = lock.read_text(encoding='utf-8')
        pins = load_lock(lock_text, environment)
        (output / 'requirements.lock').write_bytes(lock.read_bytes())
        (output / 'pyproject.toml').write_bytes(pyproject.read_bytes())
        project = tomllib.loads(pyproject.read_text(encoding='utf-8'))['project']
        roots, issues = root_requirements(project, extras, pins, environment)
        result['root_issues'] = issues
        (output / 'root-requirements.txt').write_text('\n'.join(roots) + '\n', encoding='utf-8')
        wheels = job['wheels']
        if not isinstance(wheels, list) or not 1 <= len(wheels) <= 512:
            raise ValueError('invalid wheel inventory')
        selected = output / 'selected-wheels'
        selected.mkdir()
        declared: dict[str, dict[str, str]] = {}
        for wheel in wheels:
            if not isinstance(wheel, dict) or set(wheel) != {'filename', 'name', 'version', 'sha256'}:
                raise ValueError('invalid wheel record')
            filename = wheel['filename']
            if not isinstance(filename, str) or Path(filename).name != filename or '\\' in filename or filename in declared:
                raise ValueError('invalid or duplicate wheel filename')
            name, version, _, _ = parse_wheel_filename(filename)
            if canonicalize_name(wheel['name']) != name or Version(wheel['version']) != version:
                raise ValueError('wheel filename does not match declared package')
            if not re.fullmatch('[0-9a-f]{64}', wheel['sha256']):
                raise ValueError('invalid wheel digest')
            source = wheelhouse / filename
            if not source.is_file() or source.is_symlink() or sha256(source) != wheel['sha256']:
                raise ValueError('wheel missing or hash mismatch: ' + filename)
            if name not in pins or Version(pins[name]['version']) != version or wheel['sha256'] not in pins[name]['hashes']:
                raise ValueError('wheel is not admitted by the exact active lock: ' + filename)
            destination = selected / filename
            try:
                os.link(source, destination)
            except OSError:
                shutil.copyfile(source, destination)
            declared[filename] = wheel
        result['input_identities'] = {'lock_sha256': job['lock_sha256'], 'pyproject_sha256': job['pyproject_sha256'],
                                      'wheels': wheels, 'project_extras': extras}
        command = [sys.executable, '-m', 'pip', '--isolated', '--disable-pip-version-check', '--no-input',
                   'install', '--dry-run', '--ignore-installed', '--no-index', '--find-links', str(selected.resolve()),
                   '--only-binary=:all:', '--require-hashes', '--report', str(report_path.resolve()),
                   '-r', str((output / 'requirements.lock').resolve()),
                   '-r', str((output / 'root-requirements.txt').resolve())]
        result['commands'].append(command)
        environment_for_pip = {name: value for name, value in os.environ.items()
                               if name in {'PATH', 'SYSTEMROOT', 'WINDIR', 'TMPDIR', 'LANG', 'LC_ALL'}}
        environment_for_pip['PIP_CONFIG_FILE'] = os.devnull
        completed = subprocess.run(command, capture_output=True, text=True, timeout=120,
                                   env=environment_for_pip, check=False)
        stdout, stderr = completed.stdout, completed.stderr
        result['pip_exit_code'] = completed.returncode
        for filename, wheel in declared.items():
            if sha256(selected / filename) != wheel['sha256']:
                raise ValueError('wheel changed during resolver execution')
        if sha256(lock) != job['lock_sha256'] or sha256(pyproject) != job['pyproject_sha256']:
            raise ValueError('input source changed during resolver execution')
        if completed.returncode == 0:
            report = exact_json(report_path.read_text(encoding='utf-8'))
            actual: dict[str, str] = {}
            for item in report['install']:
                name = canonicalize_name(item['metadata']['name'])
                version = item['metadata']['version']
                if name in actual:
                    raise ValueError('pip report duplicates a package')
                actual[name] = version
                uri = urlparse(item['download_info']['url'])
                candidate = Path(unquote(uri.path))
                if uri.scheme != 'file' or candidate.parent != selected.resolve() or candidate.name not in declared:
                    raise ValueError('pip selected an undeclared wheel')
                claimed = item['download_info']['archive_info']['hashes']['sha256']
                if claimed != declared[candidate.name]['sha256']:
                    raise ValueError('pip wheel hash differs from input identity')
            expected = {name: entry['version'] for name, entry in pins.items()}
            if actual != expected or report['environment'] != environment:
                raise ValueError('pip report does not match every active lock pin and environment')
            result['files']['report'] = report_path.name
            result['decision'] = 'CONFLICT' if issues else 'CONSISTENT'
        elif 'ResolutionImpossible' in stdout + stderr or 'conflicting dependencies' in stdout + stderr:
            result['decision'] = 'CONFLICT'
        elif issues:
            result['decision'] = 'CONFLICT'
        else:
            result['input_issues'].append('pip did not produce a complete resolved dependency report')
    except subprocess.TimeoutExpired as error:
        stdout, stderr = decode(error.stdout), decode(error.stderr)
        result['input_issues'].append('offline resolver exceeded the 120-second task bound')
    except (OSError, ValueError, KeyError, TypeError) as error:
        result['decision'] = 'INCOMPLETE'
        result['input_issues'].append(type(error).__name__ + ': ' + str(error))
    (output / 'pip.stdout.txt').write_text(stdout, encoding='utf-8')
    (output / 'pip.stderr.txt').write_text(stderr, encoding='utf-8')
    result['file_sha256'] = {filename: sha256(output / filename)
                             for filename in result['files'].values() if filename is not None}
    result['next_action'] = {
        'CONSISTENT': {'en': 'Dependency metadata is consistent for this exact environment. Continue with application tests; this is not application qualification.',
                       'fr': 'Les métadonnées des dépendances sont cohérentes pour cet environnement exact. Poursuivez les tests applicatifs; ceci ne qualifie pas l’application.'},
        'CONFLICT': {'en': 'Retain the incumbent. Resolve the recorded dependency constraints before installation or application qualification.',
                     'fr': 'Conservez la configuration actuelle. Résolvez les contraintes signalées avant l’installation ou la qualification applicative.'},
        'INCOMPLETE': {'en': 'Do not clear the proposed lock. Supply the missing or matching evidence, then repeat the bounded offline check.',
                       'fr': 'Ne validez pas le verrou proposé. Fournissez les preuves manquantes ou concordantes, puis reprenez la vérification hors ligne bornée.'},
    }[result['decision']]
    usage = resource.getrusage(resource.RUSAGE_CHILDREN)
    result['elapsed_wall_seconds'] = time.perf_counter() - started
    result['cpu_seconds'] = time.process_time() - own_cpu + usage.ru_utime + usage.ru_stime - child_cpu
    result['cost_unknowns'] = ['provider/model authoring fees', 'human attention', 'hardware price', 'maintenance price']
    write_json(output / 'result.json', result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--job', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    result = build(args.job.resolve(), args.out.resolve())
    print(json.dumps({'job_id': result['job_id'], 'decision': result['decision'],
                      'elapsed_wall_seconds': result['elapsed_wall_seconds'], 'cpu_seconds': result['cpu_seconds']}))


if __name__ == '__main__':
    main()
