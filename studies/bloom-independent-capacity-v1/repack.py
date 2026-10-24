#!/usr/bin/env python3
"""Rebuild the exact delivered ZIP from an extracted, verified bundle."""
import argparse
import json
from pathlib import Path
import zipfile
from verify_bundle import verify

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--root', default='.')
p.add_argument('--output', required=True)
a = p.parse_args()
root = Path(a.root).resolve()
out = Path(a.output).resolve()
if out.exists():
    raise SystemExit('Choose a new output path; existing archives are preserved.')
verify(root)
m = json.loads((root / 'MANIFEST.json').read_text())
out.parent.mkdir(parents=True, exist_ok=True)
with zipfile.ZipFile(out, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
    for name in [r['path'] for r in m['files']] + ['MANIFEST.json']:
        info = zipfile.ZipInfo(m['bundle_root'] + '/' + name, tuple(m['zip_member_timestamp']))
        info.create_system = 3
        info.external_attr = 0o100644 << 16
        info.compress_type = zipfile.ZIP_DEFLATED
        z.writestr(info, (root / name).read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
print('Rebuilt: ' + str(out))
