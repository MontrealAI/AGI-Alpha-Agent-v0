# SPDX-License-Identifier: Apache-2.0
"""Build a selective complete publication archive and reopen every byte.

Excludes download caches, copied whole repositories, credentials, copyrighted
reading copies, transient render outputs, and previous publication archives.
"""
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'output/final'
OUT.mkdir(parents=True,exist_ok=True)
prefix='nova-seeds-abundance-v1'
pdf=ROOT/'research/paper/paper.pdf'
tex=ROOT/'research/paper/nova-seeds-abundance-v1.tex'
assert pdf.is_file() and tex.is_file()
deliver_pdf=OUT/'Nova_Seeds_Abundance_v1.pdf'
deliver_tex=OUT/'Nova_Seeds_Abundance_v1.tex'
shutil.copyfile(pdf,deliver_pdf);shutil.copyfile(tex,deliver_tex)
files={
    'Nova_Seeds_Abundance_v1.pdf':deliver_pdf,
    'Nova_Seeds_Abundance_v1.tex':deliver_tex,
    'README.md':OUT/'README.md' if (OUT/'README.md').is_file() else ROOT/'README.md',
    'LICENSE':ROOT/'research/vendor/alpha/LICENSE',
    'verify_manifest.py':ROOT/'research/publication/verify_manifest.py',
}
skip_parts={'__pycache__','.git','node_modules','npm-cache','cache','artifacts','rendered','pdf-qa'}
def add_tree(directory, allowed=None):
    for path in sorted(directory.rglob('*')):
        if not path.is_file() or any(part in skip_parts for part in path.relative_to(ROOT).parts):continue
        if path.suffix in {'.pyc','.aux','.fdb_latexmk','.fls','.log','.synctex','.out','.toc'}:continue
        if 'review-copy' in path.name:continue
        if allowed is not None and not allowed(path):continue
        if path.is_symlink():raise RuntimeError('Unexpected source symlink: '+str(path))
        files[path.relative_to(ROOT).as_posix()]=path

for name in ['src','vendor','protocol','analysis','audit','tests','results','evidence','review','figures','publication']:
    add_tree(ROOT/'research'/name)
add_tree(ROOT/'research/paper',lambda p:p.suffix in {'.tex','.bib','.bbl'})
for name in ['evidence','vendor']:
    add_tree(ROOT/'foundations'/name)
for path in (ROOT/'foundations').iterdir():
    if path.is_file() and path.suffix in {'.md','.py','.mjs','.json'}:
        files[path.relative_to(ROOT).as_posix()]=path
add_tree(ROOT/'contracts-audit')
add_tree(ROOT/'literature',lambda p:p.suffix in {'.bib','.md','.json'})
for name in ['Nova_Seeds_Writer10_Initial_Checkpoint.zip','Nova_Seeds_Preconfirmation_Frozen_Source.zip','preconfirmation-receipt.json']:
    path=ROOT/'output/checkpoints'/name
    if path.is_file():files['provenance/'+name]=path
for path in sorted((ROOT/'research').glob('*.log')):
    files[path.relative_to(ROOT).as_posix()]=path

sha=lambda raw:hashlib.sha256(raw).hexdigest()
pdf_sha=sha(deliver_pdf.read_bytes())
identity=OUT/'CANONICAL_PDF_SHA256.txt'
identity.write_text(pdf_sha+'  Nova_Seeds_Abundance_v1.pdf\n')
files['CANONICAL_PDF_SHA256.txt']=identity
entries=[]
for name,path in sorted(files.items()):
    raw=path.read_bytes()
    markers=[b'-----BEGIN '+kind+b'PRIVATE KEY-----' for kind in (b'',b'RSA ',b'EC ')]
    if any(marker in raw for marker in markers):
        raise RuntimeError('Private-key marker in publication member: '+name)
    entries.append({'path':name,'bytes':len(raw),'sha256':sha(raw)})
manifest={'schema':'nova-seeds-publication-manifest/v1','edition':prefix,
    'canonicalPdf':{'path':'Nova_Seeds_Abundance_v1.pdf','sha256':pdf_sha,'bytes':deliver_pdf.stat().st_size},
    'sourceFreezeSha256':sha((ROOT/'research/protocol/source-freeze.json').read_bytes()),
    'files':entries,'exclusions':'Manifest does not include its own digest. ZIP digest is recorded externally. No private keys, source caches or third-party reading copies.'}
manifest_raw=(json.dumps(manifest,indent=2)+'\n').encode()
(OUT/'MANIFEST.json').write_bytes(manifest_raw)
archive=OUT/'Nova_Seeds_Abundance_v1_Source.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9,allowZip64=True) as z:
    for name,path in sorted(files.items()):z.write(path,prefix+'/'+name)
    z.writestr(prefix+'/MANIFEST.json',manifest_raw)
with zipfile.ZipFile(archive) as z:
    bad=z.testzip()
    if bad:raise RuntimeError('CRC failure: '+bad)
    actual_manifest=json.loads(z.read(prefix+'/MANIFEST.json'))
    for entry in actual_manifest['files']:
        raw=z.read(prefix+'/'+entry['path'])
        if len(raw)!=entry['bytes'] or sha(raw)!=entry['sha256']:
            raise RuntimeError('Reopened member identity failure: '+entry['path'])
    assert sha(z.read(prefix+'/Nova_Seeds_Abundance_v1.pdf'))==pdf_sha
receipt={'schema':'nova-seeds-archive-reopen/v1','archive':archive.name,
    'archiveSha256':sha(archive.read_bytes()),'archiveBytes':archive.stat().st_size,
    'payloadFilesVerified':len(entries),'crcErrors':0,'canonicalPdf':manifest['canonicalPdf'],
    'standaloneTex':{'sha256':sha(deliver_tex.read_bytes()),'bytes':deliver_tex.stat().st_size},
    'sourceFreezeSha256':manifest['sourceFreezeSha256'],'privateKeyMarkerScan':'no marker in any payload member',
    'scope':'Local ZIP reopened and all manifest members checked; durable remote round trip recorded separately.'}
(OUT/'ARCHIVE_RECEIPT.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt,indent=2))
