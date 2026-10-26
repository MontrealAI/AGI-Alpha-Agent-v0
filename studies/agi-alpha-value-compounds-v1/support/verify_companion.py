# SPDX-License-Identifier: Apache-2.0
"""Verify the complete immutable companion file inventory without executing inputs."""
from pathlib import Path
import hashlib,json
R=Path(__file__).resolve().parents[1]
manifest=json.loads((R/'COMPANION_MANIFEST.json').read_text())
failed=[]
for row in manifest['files']:
 p=R/row['path']
 if not p.resolve().is_relative_to(R) or p.is_symlink() or not p.is_file():failed.append({'path':row['path'],'reason':'path-or-presence'});continue
 raw=p.read_bytes()
 if len(raw)!=row['bytes'] or hashlib.sha256(raw).hexdigest()!=row['sha256']:failed.append({'path':row['path'],'reason':'byte-identity'})
print(json.dumps({'schema':'companion-verification/v1','files':len(manifest['files']),'failures':failed,'money_cost_attestation':False}))
raise SystemExit(bool(failed))
