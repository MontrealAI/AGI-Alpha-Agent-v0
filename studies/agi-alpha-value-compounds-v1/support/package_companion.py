# SPDX-License-Identifier: Apache-2.0
"""Seal an offline research companion with an exact regular-file inventory."""
from __future__ import annotations
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import resource
import time
import zipfile

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE_ROOT = 'agi-alpha-value-compounds-v1'
SKIP_PARTS = {'__pycache__', '.pytest_cache', '.git'}
SKIP_PREFIXES = ('deps/site/', 'publication/render/')
SKIP_FILES = {'COMPANION_MANIFEST.json', 'publication/public-draft-manifest.json',
              'publication/public-draft-manifest-deliverables.json', 'publication/publication-receipt.json'}


def included(path: Path) -> bool:
    relative = path.relative_to(ROOT).as_posix()
    if any(part in SKIP_PARTS for part in path.relative_to(ROOT).parts):
        return False
    if relative.startswith(SKIP_PREFIXES) or relative in SKIP_FILES:
        return False
    if relative.startswith('publication/demo/') and path.suffix == '.png':
        return False
    if path.suffix in {'.aux', '.out', '.pyc', '.toc', '.synctex', '.zip'}:
        return False
    return True


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--receipt', required=True, type=Path)
    args = parser.parse_args()
    if args.out.exists() or args.receipt.exists():
        raise ValueError('OUTPUT_EXISTS; preserve earlier editions')
    start = time.perf_counter()
    cpu_start = resource.getrusage(resource.RUSAGE_SELF)
    files = sorted(p for p in ROOT.rglob('*') if p.is_file() and included(p))
    rows = []
    for path in files:
        if path.is_symlink():
            raise ValueError('SYMLINK_NOT_ALLOWED: ' + str(path))
        raw = path.read_bytes()
        rows.append({'path': path.relative_to(ROOT).as_posix(), 'bytes': len(raw), 'sha256': digest(raw)})
    manifest = {'schema': 'value-compounds-complete-companion/v1',
                'sealed_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                'root_directory': ARCHIVE_ROOT, 'files': rows,
                'file_count_excluding_manifest': len(rows),
                'uncompressed_bytes_excluding_manifest': sum(row['bytes'] for row in rows),
                'status': 'Complete local research companion; not a production or release qualification',
                'excluded_reconstructable_or_presentation_files': ['installed deps/site cache', 'Python bytecode',
                    'PDF rendering images', 'browser QA screenshots', 'LaTeX auxiliary files',
                    'later external publication receipt and public text-draft manifest'],
                'money_cost_attestation': False,
                'cost_boundary': 'Archive construction, verification, transfer and publication are additional unpriced inclusive research investment.'}
    manifest_path = ROOT / 'COMPANION_MANIFEST.json'
    manifest_path.write_text(json.dumps(manifest, indent=2) + '\n')
    files.append(manifest_path)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(args.out, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=6, allowZip64=True) as archive:
        for path in files:
            relative = path.relative_to(ROOT).as_posix()
            entry = zipfile.ZipInfo(ARCHIVE_ROOT + '/' + relative, date_time=(2026, 10, 26, 0, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            entry.external_attr = 0o100644 << 16
            archive.writestr(entry, path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=6)
    expected = {ARCHIVE_ROOT + '/' + row['path']: row for row in rows}
    manifest_raw = manifest_path.read_bytes()
    expected[ARCHIVE_ROOT + '/COMPANION_MANIFEST.json'] = {'bytes': len(manifest_raw), 'sha256': digest(manifest_raw)}
    with zipfile.ZipFile(args.out) as archive:
        if len(archive.namelist()) != len(set(archive.namelist())) or set(archive.namelist()) != set(expected):
            raise ValueError('ARCHIVE_ENTRY_SET_MISMATCH')
        for name, row in expected.items():
            raw = archive.read(name)
            if len(raw) != row['bytes'] or digest(raw) != row['sha256']:
                raise ValueError('ARCHIVE_BYTE_MISMATCH: ' + name)
    cpu_end = resource.getrusage(resource.RUSAGE_SELF)
    receipt = {'schema': 'companion-archive-verification/v1', 'archive': str(args.out.resolve()),
               'sha256': digest(args.out.read_bytes()), 'bytes': args.out.stat().st_size,
               'verified_entries': len(expected), 'archive_entry_errors': 0,
               'manifest_sha256': digest(manifest_raw),
               'uncompressed_bytes': sum(row['bytes'] for row in expected.values()),
               'wall_seconds': time.perf_counter() - start,
               'cpu_seconds': cpu_end.ru_utime + cpu_end.ru_stime - cpu_start.ru_utime - cpu_start.ru_stime,
               'monetary_cost_usd': None, 'cost_account': 'same call-compatibility research investment',
               'browser_screenshots_included': False}
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt))


if __name__ == '__main__':
    main()
