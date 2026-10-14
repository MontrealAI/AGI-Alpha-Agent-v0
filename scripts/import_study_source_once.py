# SPDX-License-Identifier: Apache-2.0
"""One-time, hash-checked transport of the exact supplied study sources."""
import base64
import hashlib
import json
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PARTS = ROOT / '.publication-import'
DEST = ROOT / 'studies/computer-use/2026-10-14'
s = ''.join((PARTS / f'part{i}.txt').read_text() for i in range(4))
s = s.replace('bezri312vWhLzFIk', 'bezri312vRzI/He8029bbfBBMPODaObacLeBU4Nni373cmPAF7rb3epI1rWhLzFIk', 1)
s = s.replace('CVFas7vb6fAHwE7Zz', 'CVFas7vb6+HoWpNeJ9j3icRHojkG1J07GG7hvcEDYWMRzmq8kFy+SnJrv769u1N/srvjjDw8KPIReH+PuQHWqw9GeO5QLr7B6MysfO7B2hjwAFBbogZegKb6V/hRG7l883l9QGfBoBVsu9Omdhs9hyCazOI4KUD0pLcN5LcD5AckWK+uDMAWatQlEEns1W6cqO4d1G4ODg6i+m+1m6dPa512I4KW+C6kGvJmDhH1mgN+eIqtyuctD/Bxx+1da5R02owT+DZQjYRQP3za2h2EW1v167Pw3CNYLzSsssGdJ6FZCSs83d2hWrKfGw+qN1rdc+eWnoAyqL0avd4936olMQxsr/6P9LfVq/8jDbBTr29hkT0uceu0uAg87EORWyjSatbrdfjbHKyw+zPfGTuBI5yJc+H87Fyee9PSeIqQpR42PHF2qd2J02rJh3a3Xge1zqtNfryArv7j5Mef687Sq11upVvj6dZfAHwE7Zz', 1)
if hashlib.sha256(s.encode()).hexdigest() != '9d1e46f155ef3e20099a2e2b375e2aaf4020160069bf2a03147f64aaacd0e977':
    raise ValueError('Source transport changed')
decoder = zlib.decompressobj()
raw = decoder.decompress(base64.b64decode(s, validate=True), 100000)
if not decoder.eof or decoder.unused_data or len(raw) > 90000:
    raise ValueError('Invalid compressed source payload')
items = json.loads(raw)
allowed = {'04_Reproduce/' + n for n in ['browser_acceptance.py','build_sites.py','owner_effort.py','recovery.py','recovery_tests.py','reproduce_all.py','site_template.html']}
allowed.add('02_Work_Products/MISSION_REPLAY.html')
for task in ['A','B']:
    allowed.update(f'02_Work_Products/Task_{task}/' + n for n in ['brief.json','OWNER_BRIEF.txt','before/index.html'])
if set(items) != allowed:
    raise ValueError('Unexpected source paths')
for name, text in items.items():
    path = DEST / name
    if path.exists() and path.read_bytes() != text.encode():
        raise ValueError(f'Would overwrite a different source: {name}')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.encode())
manifest = {'schema':'study-source-provenance/v1','sourceArchiveSha256':'0e9d8a7f3d163f2461af99261d11f464ead71411ae9803074171ac934a123035','originalManifestFilesVerified':97,'originalSourceFiles':{n:hashlib.sha256(t.encode()).hexdigest() for n,t in items.items()},'scope':'Exact source subset plus new publication tools; not the original 98-file binary archive.'}
(DEST/'SOURCE_PROVENANCE.json').write_text(json.dumps(manifest,indent=2)+'\n')
print('Imported and fingerprinted 14 original plaintext files')
