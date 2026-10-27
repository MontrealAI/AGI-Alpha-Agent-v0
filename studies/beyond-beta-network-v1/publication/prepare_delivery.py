#!/usr/bin/env python3
"""Package the complete study core and identify separately delivered full ledgers."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import zipfile


ROOT = Path(__file__).resolve().parents[1]
LEDGERS = {
    'results/confirmation_ledgers.jsonl.gz',
    'results/sensitivity_ledgers.jsonl.gz',
    'results/scale_ledgers.jsonl.gz',
}
UNUSED = {
    'results/analysis/io_xz_registration_draft.json',
    'results/analysis/prepare_xz_writer.py',
    'results/analysis/run_io_xz.mjs.txt',
}
PRIVATE_TRANSPORT = {'results/durable_ledgers.json'}


def digest(path):
    result = hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            result.update(chunk)
    return result.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    destination = args.output.resolve()
    destination.mkdir(parents=True, exist_ok=True)
    archive = destination / 'AGI_ALPHA_Paid_Work_Study_Core.zip'
    if archive.exists():
        raise SystemExit('Refusing to replace an existing delivered packet.')
    freeze = json.loads((ROOT / 'protocol/freeze.json').read_text())
    for relative, expected in freeze['sourceHashes'].items():
        if digest(ROOT / relative) != expected:
            raise SystemExit(f'Frozen source mismatch: {relative}')
    for relative in ['results/confirmation.json', 'results/sensitivity.json',
                     'results/scale.json', 'paper/main.pdf',
                     'paper/evidence_companion.pdf', 'demo/index.html']:
        if not (ROOT / relative).is_file() or not (ROOT / relative).stat().st_size:
            raise SystemExit(f'Incomplete deliverable: {relative}')
    preserved = json.loads((ROOT / 'publication/ledger_identities.json').read_text())
    by_path = {item['path']: item for item in preserved['files']}
    if not LEDGERS.issubset(by_path):
        raise SystemExit('A complete full-ledger preservation receipt is missing.')
    public_ledgers = [{key: by_path[name][key] for key in
                       ['path', 'bytes', 'sha256', 'histories', 'archiveCRCVerified']}
                      for name in sorted(LEDGERS)]
    files = []
    for path in sorted(ROOT.rglob('*')):
        if not path.is_file():
            continue
        relative = path.relative_to(ROOT).as_posix()
        if relative in LEDGERS or relative in UNUSED or relative in PRIVATE_TRANSPORT:
            continue
        if '__pycache__' in path.parts or path.suffix in {'.pyc', '.aux', '.out', '.toc'}:
            continue
        if relative.endswith('working_draft.pdf'):
            continue
        if not path.stat().st_size:
            continue
        files.append({'path': relative, 'bytes': path.stat().st_size,
                      'sha256': digest(path)})
    packet_manifest = {
        'schema': 'paid-alpha-core-packet/v1',
        'evidence': 'Executed simulation and research software; economic events are modeled.',
        'baseFreezeSHA256': digest(ROOT / 'protocol/freeze.json'),
        'selectedPoliciesSHA256': digest(ROOT / 'protocol/selected_policies.json'),
        'coreFiles': files,
        'separatelyDeliveredFullLedgers': public_ledgers,
        'restoration': 'Download each full ledger, place it at its listed path under '
                       'the extracted study root, and verify SHA256 before raw-ledger '
                       'analysis. After restoring the exact frozen historical source '
                       'archive listed in README, source-only simulation reproduction '
                       'regenerates new histories and does not require the old full ledgers.',
    }
    with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED,
                         compresslevel=6, allowZip64=True) as output:
        for item in files:
            output.write(ROOT / item['path'], 'AGI_ALPHA_Paid_Work_Study/' + item['path'])
        output.writestr('AGI_ALPHA_Paid_Work_Study/CORE_PACKET_MANIFEST.json',
                        json.dumps(packet_manifest, indent=2) + '\n')
    with zipfile.ZipFile(archive) as check:
        if check.testzip() is not None:
            raise SystemExit('Core packet ZIP integrity failure.')
    convenience = {
        'paper/main.pdf': 'AGI_ALPHA_Paid_Work_Retained_Alpha.pdf',
        'paper/evidence_companion.pdf': 'AGI_ALPHA_Paid_Work_Evidence_Companion.pdf',
        'demo/index.html': 'AGI_ALPHA_Paid_Work_Explorer_EN_FR.html',
        'evidence/calibration_register.json': 'AGI_ALPHA_Paid_Work_Calibration_Register.json',
    }
    for source, name in convenience.items():
        shutil.copy2(ROOT / source, destination / name)
    delivered = [{'file': path.name, 'bytes': path.stat().st_size,
                  'sha256': digest(path)} for path in sorted(destination.iterdir())
                 if path.is_file() and path.name != 'DELIVERY_MANIFEST.json']
    manifest = {'schema': 'paid-alpha-delivery/v1', 'artifacts': delivered,
                'separatelyDeliveredFullLedgers': public_ledgers,
                'coreMemberCount': len(files), 'coreIntegrityVerified': True}
    (destination / 'DELIVERY_MANIFEST.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps(manifest, indent=2))


if __name__ == '__main__':
    main()
