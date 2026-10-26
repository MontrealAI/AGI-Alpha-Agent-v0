# SPDX-License-Identifier: Apache-2.0
import argparse, concurrent.futures, datetime, hashlib, json, re, urllib.request
from pathlib import Path
from packaging.version import Version, InvalidVersion
from packaging.tags import sys_tags
from packaging.utils import parse_wheel_filename, canonicalize_name

ROOT=Path(__file__).resolve().parent.parent
FAMILIES=['cryptography','eth-account','prometheus-client','pydantic-settings','pyyaml','uvicorn']
def sha(raw): return hashlib.sha256(raw).hexdigest()
def save(path,value): path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,indent=2)+'\n')
def get(url):
    with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'AGI-ALPHA-bounded-research/1.0'}),timeout=30) as r:return r.read()
def check_freeze():
    p=ROOT/'protocol/production-freeze.json';f=json.loads(p.read_text())
    for row in f['files']:
        if sha((ROOT/row['path']).read_bytes())!=row['sha256']:raise ValueError('FROZEN_SOURCE_CHANGED:'+row['path'])
    return sha(p.read_bytes())
def select():
    check_freeze()
    if (ROOT/'protocol/selected-inputs.json').exists():raise ValueError('SELECTION_ALREADY_REGISTERED')
    baseline=json.loads((ROOT/'inputs/development/job.json').read_text()); pins={w['name']:w['version'] for w in baseline['wheels']}
    tags={t:i for i,t in enumerate(sys_tags())}
    def one(name):
        url=f'https://pypi.org/pypi/{name}/json';raw=get(url);data=json.loads(raw)
        p=ROOT/'inputs/release-index'/f'{name}.json';p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
        versions=[]
        for text,files in data['releases'].items():
            try: v=Version(text)
            except InvalidVersion: continue
            if v<Version(pins[name]) and not v.is_prerelease and not v.is_devrelease and any(not f.get('yanked',False) for f in files):versions.append((v,text))
        row={'family':name,'baseline_version':pins[name],'index_url':url,'index_sha256':sha(raw),'metadata_fields_inspected':['releases version strings','filename','file URL','digests.sha256','yanked flag','upload_time_iso_8601'],'dependency_metadata_inspected':False}
        if not versions:row.update(status='NO_ELIGIBLE_RELEASE',version=None,wheel=None);return row
        _,version=max(versions);choices=[]
        for f in data['releases'][version]:
            if f.get('yanked',False) or not f['filename'].endswith('.whl'):continue
            try:n,v,_,wt=parse_wheel_filename(f['filename'])
            except ValueError:continue
            ranks=[tags[t] for t in wt if t in tags]
            if canonicalize_name(n)==name and v==Version(version) and ranks:choices.append((min(ranks),f['filename'],f))
        row.update(version=version,status='SELECTED' if choices else 'NO_COMPATIBLE_WHEEL',wheel=None)
        if choices:
            f=min(choices,key=lambda x:(x[0],x[1]))[2]
            row['wheel']={k:f[k] for k in ['filename','url','size','upload_time_iso_8601']};row['wheel']['sha256']=f['digests']['sha256']
        return row
    def capture(name):
        try:return one(name)
        except Exception as error:return {'family':name,'baseline_version':pins[name],'version':None,'wheel':None,'status':'INDEX_ACQUISITION_FAILED','error':str(error),'dependency_metadata_inspected':False}
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:rows=list(pool.map(capture,FAMILIES))
    out={'schema':'second-investment-input-selection/v1','selected_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'rule':'immediately previous non-yanked stable release below baseline; no replacements','freshness':'New whole-lock research substitutions; source releases are historical public artifacts, not customer orders or actual past application locks','rows':rows}
    save(ROOT/'protocol/selected-inputs.json',out);print(json.dumps({'sha256':sha((ROOT/'protocol/selected-inputs.json').read_bytes()),'rows':[{'family':r['family'],'baseline':r['baseline_version'],'selected':r['version'],'status':r['status']} for r in rows]}))
def acquire():
    freeze_hash=check_freeze()
    selection_path=ROOT/'protocol/selected-inputs.json';selection=json.loads(selection_path.read_text());baseline=json.loads((ROOT/'inputs/development/job.json').read_text());text=(ROOT/'inputs/development/requirements-agent.lock').read_text()
    commitment=json.loads((ROOT/'protocol/input-selection-commitment.json').read_text())
    if commitment['selection_sha256']!=sha(selection_path.read_bytes()) or commitment['source_freeze_sha256']!=freeze_hash:raise ValueError('REGISTERED_SELECTION_IDENTITY')
    if (ROOT/'protocol/confirmation-jobs.json').exists():raise ValueError('CONFIRMATION_ALREADY_ACQUIRED')
    jobs=[]
    for row in selection['rows']:
        if row['status']!='SELECTED':jobs.append({'id':row['family'],'status':row['status'],'job':None});continue
        wheel=row['wheel']
        try:
            check_freeze();raw=get(wheel['url'])
            if sha(raw)!=wheel['sha256'] or len(raw)!=wheel['size']:raise ValueError('PUBLIC_WHEEL_IDENTITY_MISMATCH')
        except Exception as error:
            jobs.append({'id':row['family'],'family':row['family'],'status':'WHEEL_ACQUISITION_FAILED','job':None,'error':str(error)});continue
        (ROOT/'inputs/wheels'/wheel['filename']).write_bytes(raw)
        target=ROOT/'inputs/confirmation'/row['family'];target.mkdir(parents=True,exist_ok=False)
        pattern=r'(?ms)^'+re.escape(row['family'])+r'==[^\n]*\n.*?(?=^[A-Za-z0-9_.-]+==|\Z)'
        replacement=row['family']+'=='+row['version']+' \\\n    --hash=sha256:'+wheel['sha256']+'\n    # research-proposed predecessor; all other pins unchanged\n'
        proposed,n=re.subn(pattern,lambda _:replacement,text)
        if n!=1:raise ValueError('EXACT_ONE_PIN_REPLACEMENT_REQUIRED')
        (target/'requirements.lock').write_text(proposed)
        selected=[dict(w) for w in baseline['wheels']]
        for w in selected:
            if canonicalize_name(w['name'])==row['family']:w.update(filename=wheel['filename'],version=row['version'],sha256=wheel['sha256'])
        job={'schema':'agialpha-lock-job/v1','id':'full-lock-'+row['family']+'-'+row['version'],'lock_path':'requirements.lock','lock_sha256':sha(proposed.encode()),'pyproject_path':'../../development/pyproject.toml','pyproject_sha256':baseline['pyproject_sha256'],'project_extras':baseline['project_extras'],'wheelhouse_path':'../../wheels','wheels':selected,'target_environment':baseline['target_environment']}
        save(target/'job.json',job);save(target/'source.json',row)
        jobs.append({'id':job['id'],'family':row['family'],'job':str((target/'job.json').relative_to(ROOT)),'job_sha256':sha((target/'job.json').read_bytes()),'status':'READY'})
    save(ROOT/'protocol/confirmation-jobs.json',{'schema':'second-investment-confirmation-jobs/v1','selection_sha256':sha(selection_path.read_bytes()),'jobs':jobs,'outcomes_inspected':False});print(json.dumps(jobs))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['select','acquire']);a=p.parse_args();select() if a.mode=='select' else acquire()
