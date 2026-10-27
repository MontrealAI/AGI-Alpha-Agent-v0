# SPDX-License-Identifier: Apache-2.0
"""Replay published evidence in an isolated checkout without altering originals."""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time


ROOT = Path(__file__).resolve().parent
OLD_EPLUS_PACKET = '/workspace/scratch/9738c9c6b885/connected-fresh-curation/source_packet'


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + '\n')


def normalize(value: object, omitted: set[str]) -> object:
    if isinstance(value, dict):
        return {k: normalize(v, omitted) for k, v in value.items() if k not in omitted}
    if isinstance(value, list):
        return [normalize(x, omitted) for x in value]
    return value


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True, help='New directory outside the original study')
    parser.add_argument('--dependency-studies', type=Path, default=ROOT.parent,
                        help='Directory containing the two preserved predecessor studies')
    parser.add_argument('--external-osf-file', type=Path,
                        help='Optional locally obtained original Experiment 1 CSV; never fetched or redistributed')
    args = parser.parse_args()
    out = args.out.resolve()
    if out == ROOT or out.is_relative_to(ROOT):
        raise ValueError('Replay output must be outside the original study')
    out.mkdir(parents=True, exist_ok=False)
    workspace = out / 'checkout' / 'studies'
    study = workspace / ROOT.name
    snapshots = {}
    copied = []

    def copy_file(source: Path, destination: Path) -> None:
        if source.is_symlink() or not source.is_file():
            raise ValueError('Expected ordinary source file: ' + str(source))
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
        snapshots[str(source)] = sha(source)
        copied.append({'source': str(source), 'copy': str(destination), 'sha256': snapshots[str(source)]})

    excluded = json.loads((ROOT / 'assay/source_packet/source_receipt.json').read_text())['excluded_from_redistribution']
    forbidden = {x['file'] for x in excluded} | {'source_packet.tar.gz'}
    directories = ['data', 'instrument', 'assay', 'economics', 'integration',
                   'validation/development-review', 'validation/independent-confirmation',
                   'validation/fresh-report-adjudication']
    for directory in directories:
        for source in sorted((ROOT / directory).rglob('*')):
            if not source.is_file() or '__pycache__' in source.parts or source.suffix in {'.pyc', '.log'}:
                continue
            if source.name in forbidden:
                raise ValueError('Nonredistributed material unexpectedly present: ' + source.name)
            copy_file(source, study / source.relative_to(ROOT))
    for name in ['development_pilot.py', 'run_development.py']:
        copy_file(ROOT / name, study / name)
    (study / 'results/development').mkdir(parents=True, exist_ok=True)
    dependency_studies = args.dependency_studies.resolve()
    previous = dependency_studies / 'agi-alpha-capability-opportunity-v1/integration'
    if not (previous / 'source_manifest.json').is_file():
        raise FileNotFoundError('Preserved native integration closure missing; provide --dependency-studies')
    source_manifest = json.loads((previous / 'source_manifest.json').read_text())
    closure = ['bridge.py', 'source_manifest.json', *[x['local_path'] for x in source_manifest['files']]]
    for relative in closure:
        source = previous / relative
        copy_file(source, workspace / 'agi-alpha-capability-opportunity-v1/integration' / relative)
    ledger = dependency_studies / 'agi-alpha-opportunity-discovery-v1/economics/economics.py'
    if not ledger.is_file():
        raise FileNotFoundError('Preserved exact-cent ledger missing; provide --dependency-studies')
    copy_file(ledger, workspace / 'agi-alpha-opportunity-discovery-v1/economics/economics.py')
    write(out / 'source-copy-receipt.json', copied)
    env = dict(os.environ)
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    stages = []
    mappings = []

    def execute(name: str, path: Path, arguments: list[str] | None = None) -> str:
        started = time.perf_counter()
        result = subprocess.run([sys.executable, str(path), *(arguments or [])], cwd=study,
                                text=True, capture_output=True, env=env, timeout=120)
        (out / (name + '.stdout.txt')).write_text(result.stdout)
        (out / (name + '.stderr.txt')).write_text(result.stderr)
        stages.append({'stage': name, 'exit_code': result.returncode,
                       'elapsed_seconds': time.perf_counter() - started})
        if result.returncode:
            write(out / 'failed-stage.json', stages[-1])
            raise RuntimeError('Replay stage failed; inspect isolated log: ' + name)
        return result.stdout

    def compare(reference: Path, replay: Path, omit: set[str] | None = None) -> None:
        before = normalize(json.loads(reference.read_text()), omit or set())
        after = normalize(json.loads(replay.read_text()), omit or set())
        if before != after:
            raise AssertionError('Semantic replay mismatch: ' + str(reference.relative_to(ROOT)))

    execute('development-pilot', study / 'development_pilot.py')
    compare(ROOT / 'results/development/minimal-pilot.json', study / 'results/development/minimal-pilot.json')
    execute('development-construction', study / 'run_development.py')
    compare(ROOT / 'results/development/constructed-delivery.json', study / 'results/development/constructed-delivery.json')
    execute('independent-development', study / 'validation/development-review/check_development.py')
    compare(ROOT / 'validation/development-review/development-independent-golden.json',
            study / 'validation/development-review/development-independent-golden.json')
    execute('numeric-confirmation', study / 'validation/independent-confirmation/run_confirmation.py')
    compare(ROOT / 'validation/independent-confirmation/results.json',
            study / 'validation/independent-confirmation/results.json',
            {'executed_at_utc', 'duration_seconds', 'generated_cases_sha256'})
    compare(ROOT / 'validation/independent-confirmation/generated-cases.json',
            study / 'validation/independent-confirmation/generated-cases.json', {'generated_at_utc'})

    for arm, script, reference in [('u', 'calculate.py', 'calculations.json'),
                                   ('e', 'calculation.py', 'calculation_results.json'),
                                   ('eplus', 'calculate.py', 'calculation_results.json')]:
        path = study / 'assay' / ('recipient_' + arm) / script
        if arm == 'eplus':
            before = path.read_text()
            if before.count(OLD_EPLUS_PACKET) != 1:
                raise ValueError('Unexpected frozen E+ path; inspect before relocating')
            original_digest = sha(path)
            path.write_text(before.replace(OLD_EPLUS_PACKET, str(study / 'assay/source_packet')))
            mappings.append({'file': str(path.relative_to(study)), 'original_sha256': original_digest,
                             'adapted_sha256': sha(path), 'old_literal': OLD_EPLUS_PACKET,
                             'new_literal': str(study / 'assay/source_packet'),
                             'scope': 'Temporary path relocation only; original untouched'})
        output = execute('recipient-' + arm, path)
        target = out / ('recipient-' + arm + '-replay.json')
        target.write_text(output)
        compare(ROOT / 'assay' / ('recipient_' + arm) / reference, target, {'versions'})

    public_dir = out / 'public-verifier'
    public_dir.mkdir()
    for source in (study / 'assay/source_packet').iterdir():
        if source.is_file():
            shutil.copyfile(source, public_dir / source.name)
    shutil.copytree(study / 'assay/source_packet', public_dir / 'source_packet')
    verifier_original = ROOT / 'validation/fresh-report-adjudication/private_verify.py'
    text = verifier_original.read_text()
    first = text.index("raw=(R/'Error_correction_PI_Experiment_1.csv')")
    last = text.index("n=ka['n_per_focal_cell']", first)
    replacement = (
        "reported=' '.join(plain(a.find('.//body')).split())\n"
        "check('A_reported_N_public_only_OSF_rows_NOT_replayed', '120 university students' in reported "
        "and 'retrieval (n = 30)' in reported and 'restudy (n = 30)' in reported)\n"
    )
    adapted = text[:first] + replacement + text[last:]
    adapted = adapted.replace("'private_verification.json'", "'public_verification_replay.json'")
    verifier = public_dir / 'public_subset_verify.py'
    verifier.write_text(adapted)
    shutil.copyfile(ROOT / 'validation/fresh-report-adjudication/private_answer_key.json', public_dir / 'private_answer_key.json')
    mappings.append({'file': 'public-verifier/public_subset_verify.py', 'original_sha256': sha(verifier_original),
                     'adapted_sha256': sha(verifier), 'scope': 'Explicit public-subset derivative, not original full verifier',
                     'replaced_check': 'OSF raw-data group-count cross-check',
                     'substitute': 'Publisher-reported N and n checked; raw group counts NOT replayed',
                     'output_name': 'public_verification_replay.json'})
    execute('public-source-verification', verifier)
    public_result = json.loads((public_dir / 'public_verification_replay.json').read_text())
    public_result['mode'] = 'PUBLIC_PUBLISHER_SUBSET_NOT_FULL_HISTORICAL_PRIVATE_VERIFIER'
    public_result['osf_raw_count_check_replayed'] = False
    public_result['limits'] = ['Publisher reported N/n are checked; actual OSF row grouping is not.',
                             'Original recipients also had OSF files; their whole model sessions are not replayed.']
    write(out / 'public-source-verification.json', public_result)

    external_status = {'status': 'SKIPPED_OPTIONAL_EXTERNAL_DATA_NOT_REDISTRIBUTED',
                       'source_url': 'https://osf.io/download/7hxf4/', 'network_fetches': 0,
                       'redistribution_license_verified': False}
    if args.external_osf_file:
        external = args.external_osf_file.resolve()
        expected = next(x['sha256'] for x in excluded if x['file'] == 'Error_correction_PI_Experiment_1.csv')
        if sha(external) != expected:
            raise ValueError('Optional external original CSV hash mismatch')
        with tempfile.TemporaryDirectory(prefix='evidence-private-verifier-') as temp:
            temp_root = Path(temp)
            for name in json.loads((public_dir / 'private_answer_key.json').read_text())['source_hashes']:
                shutil.copyfile(public_dir / name, temp_root / name)
            shutil.copytree(study / 'assay/source_packet', temp_root / 'source_packet')
            shutil.copyfile(public_dir / 'private_answer_key.json', temp_root / 'private_answer_key.json')
            shutil.copyfile(verifier_original, temp_root / 'private_verify.py')
            shutil.copyfile(external, temp_root / 'Error_correction_PI_Experiment_1.csv')
            execute('optional-original-private-verifier', temp_root / 'private_verify.py')
            shutil.copyfile(temp_root / 'private_verification.json', out / 'optional-original-private-verification.json')
        external_status['status'] = 'ORIGINAL_VERIFIER_REPLAYED_WITH_USER_SUPPLIED_HASH_MATCHED_DATA'
        external_status['raw_bytes_in_output'] = False

    execute('economics-v1', study / 'economics/run_economics.py', ['--out', str(study / 'economics/replayed-v1')])
    for name in ['results.json', 'paths.json', 'fresh-worlds.json']:
        compare(ROOT / 'economics/results-v1' / name, study / 'economics/replayed-v1' / name)
    shutil.rmtree(study / 'economics/results-v1_1')
    execute('capacity-correction-v1.1', study / 'economics/check_capacity_v1_1.py')
    for name in ['diagnostics.json', 'fresh-capacity-cases.json']:
        compare(ROOT / 'economics/results-v1_1' / name, study / 'economics/results-v1_1' / name)
    execute('residual-obligations', study / 'economics/residual_obligations.py')
    compare(ROOT / 'economics/residual-obligations-results.json', study / 'economics/residual-obligations-results.json')
    execute('modeled-actual-byte-transfer', study / 'integration/run_transfer.py')
    transferred = study / 'integration/results/recovered-capability-v1.zip'
    if sha(transferred) != sha(ROOT / 'instrument/capability-v1.zip'):
        raise AssertionError('Recovered byte mismatch')
    execute('native-accounting', study / 'integration/replay_accounting.py')
    for name in ['native-modeled-accounting.json', 'native-actual-unknown.json']:
        before = json.loads((ROOT / 'integration/results' / name).read_text())
        after = json.loads((study / 'integration/results' / name).read_text())
        if before['report'] != after['report']:
            raise AssertionError('Native accounting report differs')

    changed = [path for path, digest in snapshots.items() if sha(Path(path)) != digest]
    if changed:
        raise AssertionError('Original input files changed during replay')
    versions = {'python': sys.version}
    for name in ['numpy', 'scipy', 'pydantic', 'cryptography', 'httpx']:
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            versions[name] = 'not-installed'
    summary = {'schema': 'portable-evidence-replay/v1', 'status': 'passed', 'stages': stages,
               'source_files_checked_unchanged': len(snapshots), 'versions': versions,
               'numeric_confirmation': '32/32 same bounded cases and outcomes',
               'capacity_confirmation': '8/8 cases and 17 reference monetary/acceptance regressions',
               'recipient_replay': 'Deterministic calculation programs only; no new frontier-model trial or timing comparison',
               'path_mappings': mappings, 'optional_external_data': external_status,
               'actual_customer_revenue': 0, 'actual_complete_cost': None,
               'native_authority': 'Ephemeral local keys and fixture principals; no live ENS or production admission',
               'no_source_outputs_overwritten': True, 'network_fetches': 0}
    write(out / 'summary.json', summary)
    print(json.dumps({'status': summary['status'], 'stages': len(stages),
                      'original_files_unchanged': len(snapshots), 'optional_external_data': external_status['status'],
                      'summary': str(out / 'summary.json')}, indent=2))


if __name__ == '__main__':
    main()
