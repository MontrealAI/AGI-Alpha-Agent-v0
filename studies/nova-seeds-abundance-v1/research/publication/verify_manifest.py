# SPDX-License-Identifier: Apache-2.0
"""Run at the extracted archive root; no network and no optional dependency."""
import hashlib
import json
from pathlib import Path
root=Path(__file__).resolve().parent
manifest=json.loads((root/'MANIFEST.json').read_text())
errors=[]
for item in manifest['files']:
    path=root/item['path']
    if not path.is_file():
        errors.append({'path':item['path'],'error':'missing'});continue
    raw=path.read_bytes()
    if len(raw)!=item['bytes'] or hashlib.sha256(raw).hexdigest()!=item['sha256']:
        errors.append({'path':item['path'],'error':'identity mismatch'})
pdf=root/manifest['canonicalPdf']['path']
if hashlib.sha256(pdf.read_bytes()).hexdigest()!=manifest['canonicalPdf']['sha256']:
    errors.append({'path':str(pdf),'error':'canonical PDF mismatch'})
print(json.dumps({'checked':len(manifest['files']),'errors':errors,'canonicalPdf':manifest['canonicalPdf']},indent=2))
raise SystemExit(bool(errors))
