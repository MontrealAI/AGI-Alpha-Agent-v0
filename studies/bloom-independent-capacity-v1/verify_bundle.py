#!/usr/bin/env python3
"""Verify the delivered BLOOM bundle without executing scientific or native code."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import sys
import zipfile


def checked_name(value):
    path = PurePosixPath(value)
    if path.is_absolute() or '..' in path.parts or not path.parts:
        raise ValueError('Unsafe manifest member: ' + value)
    return path


def verify(target):
    archive = zipfile.ZipFile(target) if target.is_file() else None
    try:
        if archive:
            names = archive.namelist()
            if len(names) != len(set(names)):
                raise ValueError('Duplicate ZIP members')
            matches = [n for n in names if n.endswith('/MANIFEST.json') and n.count('/') == 1]
            if len(matches) != 1:
                raise ValueError('Expected one top-level bundle manifest')
            prefix = matches[0].rsplit('/', 1)[0] + '/'
            manifest = json.loads(archive.read(matches[0]))
            read = lambda name: archive.read(prefix + str(checked_name(name)))
        else:
            manifest = json.loads((target / 'MANIFEST.json').read_text())
            read = lambda name: (target / checked_name(name)).read_bytes()
        count = 0
        for row in manifest['files']:
            data = read(row['path'])
            if len(data) != row['bytes'] or hashlib.sha256(data).hexdigest() != row['sha256']:
                raise ValueError('Content mismatch: ' + row['path'])
            count += 1
        freeze = json.loads(read('protocol/FREEZE.json'))
        for row in freeze['files']:
            if hashlib.sha256(read(row['path'])).hexdigest() != row['sha256']:
                raise ValueError('Frozen source changed: ' + row['path'])
        pdf = read(manifest['authoritative_pdf']['path'])
        if hashlib.sha256(pdf).hexdigest() != manifest['authoritative_pdf']['sha256']:
            raise ValueError('Authoritative publication PDF mismatch')
        print(json.dumps({'status': 'VERIFIED', 'members': count, 'frozen_sources': len(freeze['files']),
                          'pdf_sha256': hashlib.sha256(pdf).hexdigest(),
                          'note': 'Integrity does not itself establish semantic validity or current authority.'}, indent=2))
    finally:
        if archive:
            archive.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('target', nargs='?', default='.', help='Extracted study directory or complete ZIP')
    args = parser.parse_args()
    try:
        verify(Path(args.target))
    except (OSError, ValueError, KeyError, zipfile.BadZipFile) as error:
        print('VERIFICATION FAILED: ' + str(error), file=sys.stderr)
        raise SystemExit(1)
