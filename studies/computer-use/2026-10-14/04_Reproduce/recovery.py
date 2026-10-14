"""Study checkpoint: integrity and freshness require a separately retained head.
Not encryption, not an authenticated third-party attestation, not a production sandbox.
"""
from pathlib import Path, PurePosixPath
import argparse, base64, hashlib, json, os, shutil, tempfile

MAX_BYTES=5_000_000

def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
def digest(value):return hashlib.sha256(canonical(value)).hexdigest()
def exact(value,fields):
    if not isinstance(value,dict) or set(value)!=set(fields):raise ValueError('SCHEMA')
def pairs(items):
    d={}
    for k,v in items:
        if k in d:raise ValueError('DUPLICATE_KEY')
        d[k]=v
    return d

def read(path):
    p=Path(path)
    if p.stat().st_size>MAX_BYTES:raise ValueError('SIZE_LIMIT')
    return json.loads(p.read_text(encoding='utf-8'),object_pairs_hook=pairs)

def atomic_json(path,value):
    p=Path(path);p.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(prefix='.checkpoint-',dir=p.parent)
    try:
        with os.fdopen(fd,'wb') as f:f.write(canonical(value));f.flush();os.fsync(f.fileno())
        os.replace(tmp,p)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)

def make(task_id,revision,artifacts,pending=None):
    if not isinstance(revision,int) or revision<1:raise ValueError('REVISION')
    entries={name:{'sha256':hashlib.sha256(data).hexdigest(),'base64':base64.b64encode(data).decode()}for name,data in artifacts.items()}
    body={'schema':'study-checkpoint/v1','taskId':task_id,'revision':revision,'phase':'AWAITING_FRESH_REVIEW','artifacts':entries,'pendingEffects':pending or [],'authority':[],'acceptance':None}
    return {**body,'root':digest(body)}

def head(pack):return {'taskId':pack['taskId'],'revision':pack['revision'],'root':pack['root']}

def restore(checkpoint,anchor,destination,expected_task):
    pack=read(checkpoint);trusted=read(anchor)
    exact(pack,['schema','taskId','revision','phase','artifacts','pendingEffects','authority','acceptance','root'])
    exact(trusted,['taskId','revision','root']);root=pack['root'];body={k:v for k,v in pack.items() if k!='root'}
    if pack['schema']!='study-checkpoint/v1' or digest(body)!=root:raise ValueError('CHECKPOINT_INTEGRITY')
    if pack['taskId']!=expected_task or trusted['taskId']!=expected_task:raise ValueError('TASK_MISMATCH')
    if trusted!=head(pack):raise ValueError('STALE_OR_UNTRUSTED_HEAD')
    if pack['pendingEffects']:raise ValueError('RECONCILIATION_REQUIRED')
    if pack['authority'] or pack['acceptance'] is not None:raise ValueError('NO_INHERITED_AUTHORITY')
    if not isinstance(pack['artifacts'],dict) or not 1<=len(pack['artifacts'])<=40:raise ValueError('ARTIFACT_COUNT')
    contents={};total=0
    for name,item in pack['artifacts'].items():
        exact(item,['sha256','base64']);path=PurePosixPath(name)
        if not isinstance(name,str) or path.is_absolute() or not name or '\\' in name or ':' in name or any(x in ('','..','.') for x in name.split('/')):raise ValueError('PATH_POLICY')
        data=base64.b64decode(item['base64'],validate=True);total+=len(data)
        if total>MAX_BYTES or hashlib.sha256(data).hexdigest()!=item['sha256']:raise ValueError('ARTIFACT_INTEGRITY')
        contents[name]=data
    dest=Path(destination)
    if dest.exists() or dest.is_symlink():raise ValueError('DESTINATION_EXISTS')
    dest.parent.mkdir(parents=True,exist_ok=True);tmp=Path(tempfile.mkdtemp(prefix='.restore-',dir=dest.parent))
    try:
        for name,data in contents.items():
            path=tmp/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
        os.rename(tmp,dest)
    except BaseException:shutil.rmtree(tmp,ignore_errors=True);raise
    return {'taskId':expected_task,'revision':pack['revision'],'restoredFiles':len(contents),'root':root,'authority':[],'acceptance':None,'state':'AWAITING_FRESH_REVIEW'}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('checkpoint');p.add_argument('anchor');p.add_argument('destination');p.add_argument('--task',required=True);a=p.parse_args()
    print(json.dumps(restore(a.checkpoint,a.anchor,a.destination,a.task),indent=2))
