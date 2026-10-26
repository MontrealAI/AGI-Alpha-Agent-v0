# SPDX-License-Identifier: Apache-2.0
"""Package exact prior evidence and verify portable path derivation; no trial reruns."""
import datetime
import hashlib
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import zipfile

market=pathlib.Path(__file__).resolve().parent
study=market.parent
workspace=study.parent
origin=pathlib.Path('/workspace/scratch/da407bff0020/study')
deliverables=workspace/'deliverables';deliverables.mkdir(exist_ok=True)
archive=deliverables/'AGI_ALPHA_Prior_Audit_Inputs.zip'
prefix='AGI_ALPHA_Prior_Audit_Inputs'
prior=json.loads((market/'prior-audit.json').read_text())
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

paths=['market/src/market.mjs','LICENSE']
campaigns=[('primary','market/results/primary-01'),('exploratory','market/exploratory/results-01'),
 ('policy-diagnostic','market/policy-diagnostic/results-01')]
for campaign,rel in campaigns:
    paths.extend(f'{rel}/{name}' for name in ['complete-runs.jsonl.gz','completion.json','configurations.json','outcomes.jsonl'])
sources={p:origin/p for p in paths}
roles={p:'original-owner-input' for p in paths}
for name in ['audit_original.py','prior-audit.json','reproduce-prior-audit.py']:
    sources['market/'+name]=market/name;roles['market/'+name]='portable-audit-companion'
readme='''# Preserved prior-study audit inputs

This optional data archive contains the exact original histories and metadata
for the primary, exploratory and fixed-price policy-diagnostic campaigns. It
preserves the original negative results. These are modeled markets, not actual
customer purchases, collections or fresh demand calibration.

## Reproduce the prior accounting audit

Only Python 3.11 or later and its standard library are required. No network,
credentials, original workspace, Node installation or third-party package is
needed for this arithmetic audit. The included original market/src/market.mjs
is read for its source hash; the market simulation is not rerun.

After extracting the archive, from the directory containing the extracted root:

```sh
python AGI_ALPHA_Prior_Audit_Inputs/market/reproduce-prior-audit.py --data-root AGI_ALPHA_Prior_Audit_Inputs --out prior-audit-rerun-001
```

The output directory must be new and outside the extracted data root. For a
byte-identity and path-derivation check without running the full arithmetic
audit, use a different new output directory and add --verify-only:

```sh
python AGI_ALPHA_Prior_Audit_Inputs/market/reproduce-prior-audit.py --data-root AGI_ALPHA_Prior_Audit_Inputs --out prior-input-check-001 --verify-only
```

The wrapper checks the preserved audit_original.py hash and the original audit
receipt. It validates every manifest file and all three histories against the
prior-audit source identities. It derives a temporary script by changing ONLY
the origin and out path assignments. It checks that all other AST nodes are
structurally identical, then executes the original arithmetic audit unchanged.
The original audit source, data and prior receipt are never overwritten.

## Preserved campaign boundaries

| Campaign | Configurations | Seeds | Paired worlds | Enterprise histories |
|---|---:|---:|---:|---:|
| Primary | 87 | 24 | 2,088 | 6,264 |
| Exploratory | 206 | 12 | 2,472 | 7,416 |
| Policy diagnostic | 160 | 12 | 1,920 | 5,760 |

The existing audit passed all 19,440 enterprise histories. Packaging performs
only data-hash verification and portable path/AST validation; it does not rerun
the trials or the full accounting audit. The primary zero-investment result is
not replaced by exploratory or policy diagnostics. Existing prior-audit.json
is retained as a historical receipt, not presented as a newly executed audit.

## Contents and identity

Each campaign directory retains complete-runs.jsonl.gz, completion.json,
configurations.json and outcomes.jsonl. The original core and LICENSE are also
included. SOURCE_MANIFEST.json records the original source path, exact byte
length and SHA256 for every payload file, separating original-owner inputs
from companion tooling and this documentation. The manifest excludes itself
to avoid a circular hash; the separate whole-archive SHA256 binds it.

The three gzip streams are copied byte-for-byte and stored without recompression
inside the ZIP. Other files may be ZIP-compressed; their extracted bytes remain
exact. This large evidence archive is distributed separately from the code
repository. Source and result license notices are preserved in LICENSE.

Authoring, inference and complete monetary packaging charges remain unknown.
Measured packaging process resources are separate from money and human time;
agent elapsed time is not a wage bill.
'''.encode()
files=[]
for rel,path in sorted(sources.items()):
    files.append({'path':rel,'bytes':path.stat().st_size,'sha256':sha(path),'role':roles[rel],
      'sourcePathAtPackaging':str(path)})
files.append({'path':'README.md','bytes':len(readme),'sha256':hashlib.sha256(readme).hexdigest(),
 'role':'packaging-documentation','sourcePathAtPackaging':None})
identities={f['path']:f for f in files}
for item in prior['source_identities']:
    rel=str(pathlib.Path(item['path']).relative_to(origin));actual=identities[rel]
    assert actual['bytes']==item['bytes'] and actual['sha256']==item['sha256'],item['campaign']
assert identities['market/src/market.mjs']['sha256']==prior['original_market_core_sha256']
assert identities['market/audit_original.py']['sha256']=='e7720802d65609d81c6633cadb90bd6f4a3888ab5a08fce16ab190384ca27c97'
manifest={'schema':'agi-alpha-prior-audit-input-manifest/v1','createdUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'archiveRoot':prefix,'sourceOwnerStudyRootAtPackaging':str(origin),'files':files,
 'manifestSelfHash':'Excluded to avoid a circular reference; whole archive SHA256 is distributed separately.',
 'originalOwnerPayloadFiles':14,'gzipHistoryArchives':3,'campaigns':prior['source_identities'],
 'priorAuditStatus':prior['status'],'priorAuditReceiptSHA256':sha(market/'prior-audit.json'),
 'priorAuditedEnterpriseHistories':19440,'fullAuditRerunForPackaging':False,
 'largeDataDistribution':'Separate optional data download; not for committing to the GitHub code repository.',
 'license':'Original LICENSE copied unchanged; companion wrapper uses SPDX Apache-2.0.',
 'observedCustomerCollectionsCents':0,'actualFinancialAction':False}
manifest_bytes=(json.dumps(manifest,indent=2)+'\n').encode()
with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6,allowZip64=True) as z:
    for rel,path in sorted(sources.items()):
        z.write(path,f'{prefix}/{rel}',compress_type=zipfile.ZIP_STORED if rel.endswith('.gz') else zipfile.ZIP_DEFLATED)
    z.writestr(f'{prefix}/README.md',readme)
    z.writestr(f'{prefix}/SOURCE_MANIFEST.json',manifest_bytes)

verified=[]
with zipfile.ZipFile(archive) as z:
    names=z.namelist()
    assert len(names)==len(files)+1 and sum(x.endswith('.gz') for x in names)==3
    assert z.read(f'{prefix}/SOURCE_MANIFEST.json')==manifest_bytes
    for f in files:
        with z.open(f"{prefix}/{f['path']}") as stream:actual=hashlib.file_digest(stream,'sha256').hexdigest()
        assert actual==f['sha256'] and z.getinfo(f"{prefix}/{f['path']}").file_size==f['bytes'],f['path']
        verified.append(f['path'])
    with tempfile.TemporaryDirectory(prefix='agi-alpha-prior-data-verify-') as temp:
        temporary=pathlib.Path(temp)
        z.extractall(temporary)
        wrapper=temporary/prefix/'market/reproduce-prior-audit.py'
        verification_out=temporary/'portable-validation'
        run=subprocess.run([sys.executable,str(wrapper),'--data-root',str(temporary),'--out',str(verification_out),'--verify-only'],
          cwd=temporary,capture_output=True,text=True,check=True)
        portable_derivation=json.loads((verification_out/'portable-derivation.json').read_text())
        portable_completion=json.loads((verification_out/'portable-completion.json').read_text())
        assert portable_completion['verifyOnly'] and not portable_completion['fullAuditExecuted']
        assert portable_derivation['replacedAssignments']==['origin','out']
        assert portable_completion['preservedAuditSourceUnchanged']

for rel,path in sources.items():assert sha(path)==identities[rel]['sha256'],f'Original source changed: {rel}'
archive_sha=sha(archive)
with (deliverables/'AGI_ALPHA_Prior_Audit_Inputs.zip.sha256').open('x') as f:f.write(f'{archive_sha}  {archive.name}\n')
validation={'schema':'agi-alpha-prior-input-packaging-validation/v1','createdUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'status':'PASS','archivePath':str(archive),'archiveBytes':archive.stat().st_size,'archiveSHA256':archive_sha,
 'sourceManifestSHA256':hashlib.sha256(manifest_bytes).hexdigest(),'payloadFilesVerified':len(verified),
 'originalOwnerPayloadFiles':14,'gzipArchives':3,'sourceIdentitiesMatchPriorAudit':True,'originalSourcesUnchanged':True,
 'standaloneExtractedWrapperPassed':True,'portableDerivation':portable_derivation,'portableCompletion':portable_completion,
 'fullArithmeticAuditRerun':False,'marketTrialsRerun':False,'verificationStdout':run.stdout,
 'packagingSourceSHA256':sha(pathlib.Path(__file__)),'monetaryCostCents':None,'authoringInferenceCostCents':None,
 'humanMinutes':None,'resourceReceipt':'resources/prior-audit-input-packaging/receipt.json',
 'resourceBoundary':'The enclosing metered packaging command includes hashing, ZIP copying and standalone verification. Do not add nested wrapper timings to the enclosing process resources.'}
with (market/'prior-inputs-packaging-validation.json').open('x') as f:json.dump(validation,f,indent=2);f.write('\n')
print(json.dumps({k:validation[k] for k in ['status','archivePath','archiveBytes','archiveSHA256','payloadFilesVerified','gzipArchives','standaloneExtractedWrapperPassed','fullArithmeticAuditRerun']}))
