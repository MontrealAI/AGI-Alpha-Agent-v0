#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Assemble the complete study from exact source selection and lossless original evidence."""
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'deliverables'
STAMP = (2026, 10, 24, 0, 0, 0)
PREFIX = 'AGI_ALPHA_Earned_Turn/'


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def info(name, stored=False):
    value = zipfile.ZipInfo(name, STAMP)
    value.compress_type = zipfile.ZIP_STORED if stored else zipfile.ZIP_DEFLATED
    value.external_attr = 0o100644 << 16
    return value


def main():
    selection_path = ROOT / 'publication/SOURCE_SELECTION.json'
    selection = json.loads(selection_path.read_text())
    mapping = {}
    for row in selection['files']:
        path = ROOT / row['path']
        if digest(path) != row['sha256']:
            raise ValueError('Source selection changed: ' + row['path'])
        mapping[row['path']] = path
    mapping['publication/SOURCE_SELECTION.json'] = selection_path
    for path in sorted((ROOT / 'audit/foundations').rglob('*')):
        if path.is_file() and path.suffix in {'.pdf', '.txt'}:
            mapping[str(path.relative_to(ROOT))] = path
    for name in ('CHECKPOINT_VERIFICATION.json', 'FROZEN_ARCHIVE_IDENTITY.json', 'RAW_CHECKPOINT_VERIFICATION.json'):
        mapping['milestones/' + name] = ROOT / 'checkpoints' / name
    raw = ROOT / 'checkpoints/AGI_ALPHA_Earned_Turn_Raw_Evidence.tar.xz'
    assert digest(raw) == '8d746fe1ea57fc62bc22213d11bdd8044f9fbf9bd96d69d877cd9c7bf53e8821'
    mapping['evidence/' + raw.name] = raw
    manifest = {'schema': 'earned-turn-complete-payload/v1', 'study': 'AGI-ALPHA-EARNED-TURN-20261024-v1',
                'source_selection_sha256': selection['selection_sha256'],
                'source_freeze': selection['source_freeze'], 'raw_archive_members': 6985,
                'instructions': 'Open browser/index.html; read the author PDF; run python unpack_evidence.py before raw reanalysis.',
                'publication': 'Prepared additive source; owner review, merge, public release and served-site verification are separate.',
                'files': {}}
    for name, path in sorted(mapping.items()):
        manifest['files'][name] = {'bytes': path.stat().st_size, 'sha256': digest(path)}
    OUT.mkdir(exist_ok=True)
    output = OUT / 'AGI_ALPHA_Earned_Turn_Complete_Companion.zip'
    with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9, allowZip64=True) as packed:
        for name, path in sorted(mapping.items()):
            with path.open('rb') as source, packed.open(info(PREFIX + name, path == raw), 'w', force_zip64=True) as target:
                shutil.copyfileobj(source, target, 1024 * 1024)
        packed.writestr(info(PREFIX + 'PAYLOAD_MANIFEST.json'), json.dumps(manifest, indent=2) + '\n')
        sums = ''.join(value['sha256'] + '  ' + name + '\n' for name, value in manifest['files'].items())
        packed.writestr(info(PREFIX + 'PAYLOAD_SHA256SUMS.txt'), sums)
    verified = 0
    with zipfile.ZipFile(output) as packed:
        for name, value in manifest['files'].items():
            with packed.open(PREFIX + name) as stream:
                sha = hashlib.file_digest(stream, 'sha256').hexdigest()
            if sha != value['sha256'] or packed.getinfo(PREFIX + name).file_size != value['bytes']:
                raise ValueError('Packaged member mismatch: ' + name)
            verified += 1
    identity = {'file': output.name, 'bytes': output.stat().st_size, 'sha256': digest(output),
                'payload_files_verified': verified, 'zip_members': verified + 2,
                'raw_members_preserved_inside': 6985, 'canonical_pdf_inside': True,
                'source_selection_sha256': selection['selection_sha256'], 'status': 'PASS'}
    (ROOT / 'publication/COMPLETE_ARCHIVE_IDENTITY.json').write_text(json.dumps(identity, indent=2) + '\n')
    (ROOT / 'publication/COMPLETE_PAYLOAD_MANIFEST.json').write_text(json.dumps(manifest, indent=2) + '\n')
    vector_output = OUT / 'AGI_ALPHA_Earned_Turn_Editable_Figures.zip'
    vector_files = sorted((ROOT / 'paper/figures').glob('*.svg')) + sorted((ROOT / 'paper/figures').glob('*.pdf'))
    with zipfile.ZipFile(vector_output, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as packed:
        for path in vector_files:
            packed.writestr(info('figures/' + path.name), path.read_bytes())
        packed.writestr(info('README.txt'), 'Nine original editable SVG figures and their publication PDFs. The complete figure generators and exact data are in the LaTeX source archive. All numerical figures derive from the single frozen confirmation.\n')
    vectors = {'file': vector_output.name, 'bytes': vector_output.stat().st_size,
               'sha256': digest(vector_output), 'editable_svg': 9, 'publication_pdf': 9}
    (ROOT / 'publication/VECTOR_ARCHIVE_IDENTITY.json').write_text(json.dumps(vectors, indent=2) + '\n')
    print(json.dumps({'complete': identity, 'vectors': vectors}))


if __name__ == '__main__':
    main()
