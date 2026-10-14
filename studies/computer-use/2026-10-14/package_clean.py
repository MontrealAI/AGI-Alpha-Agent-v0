# SPDX-License-Identifier: Apache-2.0
"""Package only named study deliverables; never include tool caches or local extras."""
from __future__ import annotations
import hashlib
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def package(output: Path) -> None:
    provenance = json.loads((ROOT / 'SOURCE_PROVENANCE.json').read_text(encoding='utf-8'))
    names = set(provenance['originalSourceFiles'])
    names.update(['build_kit.py','_kit_builder.py','package_clean.py','verify_and_replay.py','check_negative_controls.py','publish_preview.py','validate_publication.py','ruff.toml','README.md','PILOT_PROTOCOL.md','PILOT_PROTOCOL.html','START_HERE.html','SOURCE_PROVENANCE.json','LICENSE','original-template.txt','pilot/status.json','pilot/session-template.csv'])
    names.update('01_Report/' + name for name in ['report.html','REPORT.md','study.css','study.js','index.html','results.json','PUBLICATION.md'])
    names.update(['02_Work_Products/Task_A/after/index.html','02_Work_Products/Task_B/after/index.html','02_Work_Products/Task_B/without-portability-fix/index.html'])
    files = {}
    for name in sorted(names):
        path = ROOT / name
        if path.is_symlink() or not path.resolve().is_relative_to(ROOT) or not path.is_file():
            raise ValueError('Missing or unsafe publication input: ' + name)
        files[name] = path.read_bytes()
    sums = ''.join(hashlib.sha256(data).hexdigest() + '  ' + name + '\n' for name,data in sorted(files.items()))
    (ROOT / 'SHA256SUMS').write_text(sums,encoding='utf-8')
    files['SHA256SUMS'] = sums.encode('utf-8')
    output.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(output,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
        for name,data in sorted(files.items()):
            info=zipfile.ZipInfo(name,(2026,10,14,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16
            archive.writestr(info,data,compresslevel=9)
    print(json.dumps({'path':str(output),'files':len(files),'sha256':hashlib.sha256(output.read_bytes()).hexdigest(),'bytes':output.stat().st_size,'unlistedLocalFilesIncluded':False}))
