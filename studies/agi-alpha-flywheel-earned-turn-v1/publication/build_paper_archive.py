#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Create the complete paper-only source archive without changing scientific files."""
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'deliverables'
OUT.mkdir(exist_ok=True)
NAME = 'AGI_ALPHA_Earned_Turn_LaTeX_Source.zip'
files = []
for p in sorted((ROOT / 'paper').rglob('*')):
    rel = p.relative_to(ROOT)
    if not p.is_file() or 'qa' in rel.parts or '__pycache__' in rel.parts:
        continue
    if (len(rel.parts) == 2 and p.suffix in {'.tex', '.bib', '.py', '.sh', '.pdf', '.md'}) or (rel.parts[1] in {'data', 'figures'} and p.suffix in {'.json', '.pdf', '.svg'}):
        files.append(p)
for n in ('LICENSE', 'requirements.txt'):
    files.append(ROOT / n)
manifest = {'schema': 'earned-turn-paper-archive/v1', 'canonical_pdf': 'paper/AGI_ALPHA_FLYWHEEL_Earn_the_Next_Turn.pdf',
            'rebuild': 'bash paper/build.sh', 'files': {}}
for p in files:
    b = p.read_bytes()
    manifest['files'][str(p.relative_to(ROOT))] = {'bytes': len(b), 'sha256': hashlib.sha256(b).hexdigest()}
with zipfile.ZipFile(OUT / NAME, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
    for p in files:
        info = zipfile.ZipInfo(str(p.relative_to(ROOT)), (2026, 10, 24, 0, 0, 0))
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = 0o100644 << 16
        z.writestr(info, p.read_bytes())
    info = zipfile.ZipInfo('PAPER_ARCHIVE_MANIFEST.json', (2026, 10, 24, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o100644 << 16
    z.writestr(info, json.dumps(manifest, indent=2) + '\n')
archive = OUT / NAME
identity = {'file': NAME, 'bytes': archive.stat().st_size,
            'sha256': hashlib.file_digest(archive.open('rb'), 'sha256').hexdigest(),
            'payload_files': len(files), 'canonical_pdf_sha256': manifest['files'][manifest['canonical_pdf']]['sha256']}
(ROOT / 'publication/PAPER_ARCHIVE_IDENTITY.json').write_text(json.dumps(identity, indent=2) + '\n')
print(json.dumps(identity))
