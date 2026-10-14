from pathlib import Path
import os,shutil
import tempfile,json,hashlib,subprocess,sys,time,copy,base64
from recovery import make,head,atomic_json,restore
from browser_acceptance import load,expected,cents
from playwright.sync_api import sync_playwright
R=Path(__file__).resolve().parents[1];O=R/'03_Evidence/recovery';tests=[]
def record(name,fn):
    try:
        detail=fn();ok=bool(detail)
    except Exception as e:ok=False;detail=type(e).__name__+': '+str(e)
    tests.append({'test':name,'passed':ok,'detail':detail})
with tempfile.TemporaryDirectory() as td:
    t=Path(td);source=(R/'02_Work_Products/Task_A/after/index.html').read_bytes();config=(R/'02_Work_Products/Task_A/brief.json').read_bytes();art={'site/index.html':source,'brief.json':config}
    pack=make('task-a',2,art);atomic_json(O/'A-checkpoint.json',pack);atomic_json(O/'A-trusted-head.json',head(pack))
    code="""import time,sys\nfrom recovery import atomic_json,read\np=read(sys.argv[1]);atomic_json(sys.argv[2],p);atomic_json(sys.argv[3],{'taskId':p['taskId'],'revision':p['revision'],'root':p['root']});print('CHECKPOINT_DURABLE',flush=True);time.sleep(60)"""
    child=subprocess.Popen([sys.executable,'-c',code,str(O/'A-checkpoint.json'),str(t/'child.json'),str(t/'head.json')],cwd=R/'04_Reproduce',stdout=subprocess.PIPE,text=True)
    marker=child.stdout.readline().strip();child.terminate();child.wait(timeout=5)
    record('Actual worker termination after durable checkpoint',lambda:{'marker':marker,'returncode':child.returncode} if marker=='CHECKPOINT_DURABLE' and child.returncode<0 else False)
    for i in range(5):
        dest=t/f'restored-{i}';cp=subprocess.run([sys.executable,str(R/'04_Reproduce/recovery.py'),str(t/'child.json'),str(t/'head.json'),str(dest),'--task','task-a'],capture_output=True,text=True)
        record(f'Fresh-process artifact restore {i+1}',lambda d=dest,c=cp:c.returncode==0 and (d/'site/index.html').read_bytes()==source and (d/'brief.json').read_bytes()==config)
    def rejected(mod,expected_error,anchor=head(pack),task='task-a'):
        x=copy.deepcopy(pack);mod(x);atomic_json(t/'bad.json',x);atomic_json(t/'bad-head.json',anchor)
        dest=t/('negative-'+expected_error)
        try:restore(t/'bad.json',t/'bad-head.json',dest,task);return False
        except (ValueError,FileNotFoundError) as e:return str(e)==expected_error and not dest.exists()
    record('Tampered checkpoint refused',lambda:rejected(lambda x:x.update(revision=20),'CHECKPOINT_INTEGRITY'))
    record('Older valid snapshot rejected against newer retained head',lambda:rejected(lambda x:None,'STALE_OR_UNTRUSTED_HEAD',anchor={'taskId':'task-a','revision':3,'root':'f'*64}))
    record('Wrong task refused',lambda:rejected(lambda x:None,'TASK_MISMATCH',task='task-b'))
    pending=make('task-a',2,art,[{'actionId':'external-write-1','status':'UNKNOWN'}]);atomic_json(t/'pending.json',pending);atomic_json(t/'pending-head.json',head(pending))
    def unknown():
        try:restore(t/'pending.json',t/'pending-head.json',t/'pending-restore','task-a');return False
        except ValueError as e:return str(e)=='RECONCILIATION_REQUIRED' and not (t/'pending-restore').exists()
    record('Unknown-effect checkpoint stops; no replay attempted',unknown)
    def traversal():
        bad=make('task-a',4,{'../escape.txt':b'no'});atomic_json(t/'traversal.json',bad);atomic_json(t/'traversal-head.json',head(bad))
        try:restore(t/'traversal.json',t/'traversal-head.json',t/'traversal-output','task-a');return False
        except ValueError as e:return str(e)=='PATH_POLICY' and not (t/'escape.txt').exists()
    record('Parent-directory path rejected even with valid hash',traversal)
    def nooverwrite():
        try:restore(O/'A-checkpoint.json',O/'A-trusted-head.json',t/'restored-0','task-a');return False
        except ValueError as e:return str(e)=='DESTINATION_EXISTS' and (t/'restored-0/site/index.html').read_bytes()==source
    record('Existing recovered work never overwritten',nooverwrite)
    record('No approval or authority inherited',lambda:pack['acceptance'] is None and pack['authority']==[])
    def missing():
        try:restore(t/'never-saved.json',O/'A-trusted-head.json',t/'missing','task-a');return False
        except FileNotFoundError:return not (t/'missing').exists()
    record('Unsaved work absence is a failure, not invented recovery',missing)
# Actual fresh browser processes and file downloads, not merely object round-trips.
with sync_playwright() as p:
    cfg=json.loads((R/'02_Work_Products/Task_B/brief.json').read_text());html=(R/'02_Work_Products/Task_B/after/index.html').read_text();draft=R/'03_Evidence/browser_downloads/B_after_recovery.json';original=(R/'03_Evidence/browser_downloads/B_after_quote.json').read_bytes()
    for i in range(5):
        b=p.chromium.launch(executable_path=os.environ.get('BROWSER_EXECUTABLE') or shutil.which('chromium') or shutil.which('google-chrome'),args=['--no-sandbox','--disable-dev-shm-usage']);c,page,_,_=load(b,html)
        page.locator('#restore').set_input_files(draft);page.wait_for_function("document.querySelector('#status').textContent.includes('restored')")
        cleared=not page.locator('#accept').is_checked() and page.locator('#download').is_disabled();page.locator('#calculate').click();page.locator('#accept').check()
        with page.expect_download() as d:page.locator('#download').click()
        path=O/f'B-recovered-quote-{i+1}.json';d.value.save_as(path)
        record(f'Fresh-browser offline recovery {i+1}: exact quote bytes and new review',lambda v=cleared,path=path:v and path.read_bytes()==original)
        if i==0:page.locator('.grid').screenshot(path=str(R/'03_Evidence/screenshots/B_recovered_review.png'))
        b.close()
report={'tests':tests,'passed':sum(x['passed'] for x in tests),'total':len(tests),'scope':'Controlled local artifacts and browser drafts; no live external transaction or power-loss experiment','independentHeadWarning':'Example head is supplied beside the example for reproducibility. Real freshness requires retaining the latest head outside the recovery package.'}
(O/'RESULTS.json').write_text(json.dumps(report,indent=2)+'\n');print(report['passed'],report['total'])
for x in tests:
    if not x['passed']:print(x)
