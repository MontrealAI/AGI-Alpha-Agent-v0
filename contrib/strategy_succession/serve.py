# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations
import argparse, hashlib, importlib.metadata, json, platform, shutil, subprocess, sys
from pathlib import Path, PurePosixPath
from typing import Any

from fastapi import FastAPI

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'transport'))
sys.path.insert(0, str(ROOT / 'worker'))
from strategy_executor import ExecutorPolicy, Limits, SourceFile, create_strategy_app
from fixed_worker import FixedWorker
from alpha_factory_v1.core.runtime.store import Journal


def qualified_environment(expected: dict[str, Any]) -> str:
    """Refuse unknown installed combinations before opening operator state."""
    fields = {'schema', 'system', 'machine', 'os_id', 'os_version_id', 'libc',
              'python_implementation', 'python_version', 'node_version', 'dependencies'}
    if not isinstance(expected, dict) or set(expected) != fields or expected['schema'] != 'engineering-environment/v1':
        raise ValueError('An exact reviewed environment profile is required')
    if any(not isinstance(expected[name], str) or not expected[name] for name in fields - {'libc', 'dependencies'}):
        raise ValueError('Invalid reviewed environment identity')
    if not isinstance(expected['libc'], dict) or set(expected['libc']) != {'name', 'version'} or any(
            not isinstance(value, str) or not value for value in expected['libc'].values()):
        raise ValueError('Invalid reviewed libc identity')
    inventory = {}
    for line in (ROOT / 'requirements-qualification.txt').read_text().splitlines():
        if line.strip() and not line.lstrip().startswith('#'):
            name, separator, version = line.strip().partition('==')
            if not separator or not name or not version or name in inventory:
                raise ValueError('Invalid exact dependency qualification inventory')
            inventory[name] = version
    if not inventory or expected['dependencies'] != inventory:
        raise ValueError('Reviewed environment must cover the complete pinned dependency inventory')
    try:
        os_release = platform.freedesktop_os_release()
        libc_name, libc_version = platform.libc_ver()
        actual = {'system': platform.system(), 'machine': platform.machine(),
                  'os_id': os_release.get('ID'), 'os_version_id': os_release.get('VERSION_ID'),
                  'libc': {'name': libc_name, 'version': libc_version},
                  'python_implementation': platform.python_implementation(),
                  'python_version': platform.python_version()}
    except (OSError, ValueError) as error:
        raise ValueError('Host environment identity is unqualified') from error
    if any(actual[name] != expected[name] for name in actual):
        raise ValueError('Host or Python environment is unqualified for this installation')
    node = shutil.which('node')
    if node is None:
        raise ValueError('The qualified Node executable is unavailable')
    try:
        node = str(Path(node).resolve(strict=True))
        version = subprocess.run([node, '--version'], check=True, capture_output=True,
                                 text=True, timeout=5).stdout.strip()
    except (OSError, subprocess.SubprocessError) as error:
        raise ValueError('Node environment identity is unqualified') from error
    if version != 'v' + expected['node_version']:
        raise ValueError('Node version is unqualified for this installation')
    for name, version in inventory.items():
        try:
            installed = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError as error:
            raise ValueError('A qualified dependency is unavailable: ' + name) from error
        if installed != version:
            raise ValueError('Dependency version is unqualified: ' + name)
    return node


def create(home: Path, manifest: Path, *, native: bool = False) -> FastAPI:
    if manifest.is_symlink() or not manifest.is_file():
        raise ValueError('A regular reviewed installation profile is required')
    raw_manifest = manifest.read_bytes()
    document = json.loads(raw_manifest)
    if document.get('schema') != 'strategy-engineering-installation/v1':
        raise ValueError('A reviewed engineering installation manifest is required')
    node = qualified_environment(document.get('qualified_environment'))
    import alpha_factory_v1
    runtime_version = importlib.metadata.version('alpha-factory-v1')
    if runtime_version not in document['qualified_runtime_versions']:
        raise ValueError('This runtime version is unqualified for the installed engineering profile')
    package_root = Path(alpha_factory_v1.__file__).resolve().parent
    for name, expected in document['runtime_python_files'].items():
        relative = PurePosixPath(name)
        if relative.is_absolute() or '..' in relative.parts or '\\' in name:
            raise ValueError('Invalid runtime source identity')
        path = package_root / name
        if path.is_symlink() or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError('Public runtime source does not match this qualified profile')
    sources = [SourceFile('installation-profile', manifest.resolve(strict=True),
                          hashlib.sha256(raw_manifest).hexdigest())]
    for name, expected in document['files'].items():
        relative = PurePosixPath(name)
        if relative.is_absolute() or '..' in relative.parts or '\\' in name:
            raise ValueError('Invalid installed source path')
        path = ROOT / name
        if path.is_symlink() or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError('Installed engineering source differs from its reviewed manifest')
        sources.append(SourceFile(name, path, expected))
    for name in document['runtime_enforcement_files']:
        sources.append(SourceFile('runtime/' + name, package_root / name, document['runtime_python_files'][name]))
    if not home.is_dir():
        raise ValueError('Use an existing approved Alpha operator home; this server does not initialize one')
    journal = Journal(home)
    journal.verify()
    if native:
        import scipy
        if scipy.__version__ != document['native_scipy_version']:
            raise ValueError('Native specialist version does not match this engineering profile')
    caps = document['per_plan_caps']
    calls = caps['native_calls'] if native else 0
    seconds = caps['native_solve_seconds'] if native else 0
    total = document['total_caps']
    policy = ExecutorPolicy(
        executor_id=document['executor_id'], sources=tuple(sources),
        methods={
            'run-mission': Limits(caps['service_work'], 0, calls, seconds),
            'construct': Limits(0, caps['improvement_work'], 0, 0),
            'run-journey': Limits(caps['service_work'], caps['improvement_work'], calls, seconds),
        },
        total=Limits(total['service_work'], total['improvement_work'], total['native_calls'] if native else 0,
                     total['native_solve_seconds'] if native else 0),
        max_requests=document['max_requests'], grant_seconds=document['grant_seconds'],
        request_seconds=document['request_seconds'], max_output_bytes=document['max_output_bytes'], allow_native=native,
    )
    worker = FixedWorker(ROOT / 'worker', node=node, python=sys.executable)
    static = ROOT / 'transport' / 'static'
    app = create_strategy_app(journal, worker, policy,
                              static_files={'/': static / 'strategy.html', '/strategy.js': static / 'strategy.js',
                                            '/strategy.css': static / 'strategy.css'})
    app.state.public_runtime = {'version': importlib.metadata.version('alpha-factory-v1'), 'mode': 'fixed-planning-engineering'}
    return app


def main() -> None:
    parser = argparse.ArgumentParser(description='Serve the bounded Strategy Succession engineering contribution')
    parser.add_argument('--home', type=Path, required=True)
    parser.add_argument('--manifest', type=Path, default=ROOT / 'ENGINEERING_MANIFEST.json')
    parser.add_argument('--port', type=int, default=8768)
    parser.add_argument('--native', action='store_true')
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        parser.error('Choose an unprivileged local port')
    import uvicorn
    uvicorn.run(create(args.home, args.manifest, native=args.native), host='127.0.0.1', port=args.port,
                access_log=False, log_level='warning')


if __name__ == '__main__':
    main()
