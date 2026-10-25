"""Recompute recorded evidence without importing producer, oracle or solver code.

This is separate implementation and role in one commission/session. It does not
establish blinded review, source-code security, human acceptance or live service.
"""
from __future__ import annotations
import copy, hashlib, html, json, math, re, statistics
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
REPORT=ROOT/'review/INDEPENDENT_EVIDENCE_AUDIT.json'
checks=0; failures=[]

def read(p):return json.loads(p.read_text())
def sha(b):return hashlib.sha256(b).hexdigest()
def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False)
def digest(domain,x):return sha(('successor-omega/v1:'+domain+'\0'+canonical(x)).encode())
def without(x,k):return {a:b for a,b in x.items() if a!=k}
def require(ok,label):
    global checks
    checks+=1
    if not ok:failures.append(label)
def approx(a,b):return math.isclose(a,b,rel_tol=1e-11,abs_tol=1e-7)

def inspect_result(p,r,prev,arm,label,path_keys=False):
    """Verify a recorded mission, including digests omitted by original oracle."""
    before=len(failures);prefix=label+': '
    req=lambda ok,msg:require(ok,prefix+msg)
    comp={c['id']:c for c in p['components']}
    evidence={e['id']:e for e in r['assurance']['components']}
    req(len(comp)==len(p['components'])==len(evidence)==len(r['assurance']['components']),'unique complete inventory')
    closure={k:set() for k in comp}
    for _ in comp:
        for k,c in comp.items():
            for dep in c['deps']:closure[k].update({dep}|closure[dep])
    keys={};current={k:sha(c['content'].encode()) for k,c in comp.items()}
    todo=set(comp)
    while todo:
        ready=sorted(k for k in todo if set(comp[k]['deps'])<=keys.keys())
        if not ready:raise ValueError('Non-DAG in recorded input')
        for k in ready:
            c=comp[k]
            body={'id':k,'source':current[k],'url':c['source_url'],'source_sha256':c['source_sha256'],'deps':[[d,keys[d]] for d in sorted(c['deps'])]}
            if path_keys:body['path']=c['path']
            keys[k]=digest('evidence-node',body);todo.remove(k)
    old=prev['index'] if prev else {};changed=[]
    for k,c in comp.items():
        e=evidence[k];lines=c['content'].split('\n')
        req(e['id']==k and e['path']==c['path'],'inventory identity '+k)
        req(e['source_url']==c['source_url'] and e['original_source_sha256']==c['source_sha256'],'source provenance '+k)
        req(e['current_sha256']==current[k] and e['synthetic_modified']==(current[k]!=c['source_sha256']),'content identity '+k)
        req(e['bytes']==len(c['content'].encode()) and e['line_count']==len(lines),'source size '+k)
        req(e['deps']==sorted(c['deps']) and set(e['transitive_dependencies'])==closure[k],'declared and transitive dependencies '+k)
        license_line=next((x.strip() for x in lines if 'SPDX-License-Identifier:' in x),None)
        imports=sorted(set(a or b for a,b in re.findall(r'''(?:from\s+['"]([^'"]+)['"]|import\s+['"]([^'"]+)['"])''',c['content'])))
        names=sorted(set(re.findall(r'(?:export\s+(?:async\s+)?(?:function|class|const)\s+|^def\s+|^class\s+|contract\s+)([A-Za-z_][A-Za-z_0-9]*)',c['content'],re.M)))
        req(e['spdx']==license_line and e['literal_imports']==imports and e['declared_names']==names,'literal fields '+k)
        req(e['dependency_key']==keys[k],'recomputed evidence key '+k)
        prior=old.get(k)
        if not prior or any([prior['hash']!=current[k],sorted(prior['deps'])!=sorted(c['deps']),prior['evidence']['path']!=c['path'],prior['evidence']['source_url']!=c['source_url'],prior['evidence']['original_source_sha256']!=c['source_sha256']]):changed.append(k)
    removed=sorted(set(old)-set(comp));affected=sorted(k for k in comp if k in changed or closure[k].intersection(changed))
    req(r['impact']['changed']==sorted(changed),'direct changes')
    req(r['impact']['removed']==removed,'deleted components')
    req(r['impact']['invalidated']==affected and r['impact']['unchanged']==sorted(set(comp)-set(affected)),'current affected complement')
    req(r['impact']['predecessor']==(prev['integrity'] if prev else None),'impact predecessor')
    req(r['impact']['digest']==digest('change-impact',without(r['impact'],'digest')),'impact digest')
    req(r['assurance']['project_id']==p['id'] and r['assurance']['cycle']==p['cycle'],'assurance revision')
    req(r['assurance']['dependency_edges']==sorted([d,k] for k,c in comp.items() for d in c['deps']),'complete edge table')
    plan=r['plan'];task=p['task'];jobs={j['id']:j for j in task['jobs']};schedule=plan['result']['schedule'];slots={s['id']:s for s in schedule}
    req(plan['task']==task and plan['project_id']==p['id'] and plan['cycle']==p['cycle'],'plan revision/task')
    req(plan['result']['task_id']==task['id'],'plan result task identity')
    req(len(schedule)==len(slots)==len(jobs) and set(slots)==set(jobs),'complete unique schedule')
    usage=[0]*len(task['capacity']);movement=0
    for k,j in jobs.items():
        s=slots[k];valid=type(s['start']) is int and type(s['end']) is int and 0<=s['start']<s['end']<=len(usage)
        req(valid and s['end']-s['start']==j['duration'],'duration/horizon '+k)
        req(s['start']>=task.get('release',{}).get(k,0),'release '+k)
        req(k not in task.get('locked',{}) or s['start']==task['locked'][k],'frozen start '+k)
        req(all(slots[d]['end']<=s['start'] for d in j['deps']),'precedence '+k)
        if valid:
            for t in range(s['start'],s['end']):usage[t]+=j['crew']
        movement+=abs(s['start']-task.get('baseline',{}).get(k,s['start']))
    req(all(u<=cap for u,cap in zip(usage,task['capacity'])),'capacity calendar')
    req(max(s['end'] for s in schedule)==plan['result']['makespan']<=task['deadline'],'makespan and deadline')
    req(movement==plan['result']['movement']<=task.get('movement_limit',10**9),'movement budget')
    task_key=digest('release-task',without(task,'id'));req(plan['task_key']==task_key,'task semantic key')
    state=r['state'];req(state['project_id']==p['id'] and state['cycle']==p['cycle'],'state revision')
    req(state['integrity']==digest('productive-state',without(state,'integrity')),'state integrity')
    req(state['task_key']==task_key and state['plan']==plan,'retained plan')
    req(set(state['index'])==set(comp),'retained inventory')
    for k,e in evidence.items():req(state['index'][k]=={'hash':current[k],'key':keys[k],'deps':e['deps'],'evidence':e},'retained record '+k)
    if prev:req(prev['project_id']==p['id'],'predecessor project isolation')
    co=r['consistency'];req(co['project_id']==p['id'] and co['cycle']==p['cycle'],'common revision')
    req(co['source_keys']==keys,'common keys')
    req(co['assurance_digest']==digest('assurance',r['assurance']),'assurance digest')
    req(co['planning_digest']==digest('planning',plan),'planning digest')
    req(co['impact_digest']==r['impact']['digest'],'impact digest link')
    req(co['parent_integrity']==(prev['integrity'] if prev else None) and co['locked_starts']==task.get('locked',{}),'common parent and locks')
    pack=r['pack'];arts={a['name']:a for a in pack['result']['artifacts']}
    req(len(arts)==len(pack['result']['artifacts'])==5,'unique complete export set')
    for name,obj in [('release-assurance.json',r['assurance']),('rollout-plan.json',plan),('change-impact.json',r['impact']),('consistency.json',co)]:req(json.loads(arts[name]['content'])==obj,'exported '+name)
    document=arts['release-dossier.html']['content'];req(sha(document.encode())==co['dossier_sha256'],'document digest')
    for k,c in comp.items():
        req(html.escape(c['path'],quote=False) in document and html.escape(c['source_url'],quote=True) in document and current[k] in document,'document evidence '+k)
    req('Décision' in document and 'Decision' in document,'bilingual headings')
    for name,a in arts.items():req(a['digest']==digest('workbench-artifact',without(a,'digest')),'workbench artifact '+name)
    req(pack['integrityDigest']==digest('workbench-pack',without(pack,'integrityDigest')),'workbench envelope digest')
    req(pack['releaseDigest']==digest('workbench-release',pack['frozen']),'workbench frozen digest')
    semantic={k:v for k,v in pack['spec'].items() if k not in ['name','language']}
    req(pack['frozen']['missionDigest']==digest('workbench-mission',semantic),'workbench mission digest')
    req(pack['evaluation']['independentProof'] is False and pack['evaluation']['admission']=='HOLD' and pack['evaluation']['settlement']=='NOT_CONNECTED','local authority limits')
    stages=['Identify','Out-Learn','Out-Think','Out-Design','Out-Strategise','Out-Execute','Out-Evolve']
    req([s['stage'] for s in r['trace']]==stages,'seven stage artifact records')
    for s in r['trace']:req(s['artifact_digest']==digest(s['stage'].lower(),s['artifact']),'stage digest '+s['stage'])
    req(pack['result']['evidence']['stages']==r['trace'] and pack['result']['evidence']['metrics']==r['metrics'],'enclosed trace/metrics')
    req(r['trace'][-1]['artifact']['retained_state']==state['integrity'],'retained stage link')
    reused=sum(arm!='full_rebuild' and k in old and old[k]['key']==keys[k] for k in comp)
    lines=sum(len(comp[k]['content'].split('\n')) for k in comp if arm=='full_rebuild' or k not in old or old[k]['key']!=keys[k])
    req(r['metrics']['reused_items']==reused and r['metrics']['built_items']==len(comp)-reused,'retained work counts')
    req(r['metrics']['lines_examined']==lines and r['metrics']['source_bytes_read']==sum(len(c['content'].encode()) for c in comp.values()),'measured-work definitions')
    parent={'id':'evidence-index-v1','schema':'evidence-index/v1','project_id':p['id'],'previous_integrity':prev['integrity'] if prev else None,'hashes':current,'keys':keys,'closures':{k:sorted(v) for k,v in closure.items()},'changed':sorted(changed),'removed':removed}
    if arm=='flywheel':
        call=pack['result']['evidence']['parent_call']
        req(call['input_digest']==digest('productive-project',p) and call['output_digest']==digest('evidence-index',parent),'actual parent invocation digest')
        req(call['reads']==len(comp) and call['source_bytes']==sum(len(c['content'].encode()) for c in comp.values()),'parent read metrics')
        if 'parent_digest' in r['impact']:req(r['impact']['parent_digest']==digest('evidence-index',parent),'child current parent link')
    return {'accepted_by_review':len(failures)==before,'parent':parent,'failures':failures[before:]}

def main():
    freeze_path=ROOT/'protocol/experiment-FREEZE.json';freeze=read(freeze_path);freeze_hash=sha(freeze_path.read_bytes())
    for e in freeze['entries']:
        b=(ROOT/e['path']).read_bytes();require(len(b)==e['bytes'] and sha(b)==e['sha256'],'frozen file '+e['path'])
    require(sha(canonical(freeze['entries']).encode())==freeze['entries_sha256'],'freeze aggregate')
    manifest=read(ROOT/'data/source_manifest.json')
    for e in manifest:
        b=(ROOT/'data/sources'/e['local']).read_bytes();require(sha(b)==e['sha256'] and len(b)==e['bytes'],'pinned source '+e['id'])
        require(hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==e['git_sha'],'Git blob identity '+e['id'])
        require('/blob/'+e['commit']+'/' in e['url'],'pinned source URL '+e['id'])
    records=[json.loads(x) for x in (ROOT/'outputs/records.jsonl').read_text().splitlines()]
    summary=read(ROOT/'outputs/summary.json');prev={};children={};reviewed=[];raw_acceptance=0
    for rec in records:
        location=ROOT/rec['relative_directory'];p=read(location/'input.json');wrapper=read(location/'execution.json');r=wrapper['result'];key=(rec['project_id'],rec['arm'])
        old=prev.get(key);audit=inspect_result(p,r,old,rec['arm'],location.name)
        require(rec['cycle']==p['cycle'] and rec['project_id']==p['id'],'record identity '+location.name)
        require(r['pack']['frozen']['sourceHash']==freeze_hash,'source freeze binding '+location.name)
        require(r['pack']['createdAt'][:19]>=freeze['created_at_utc'][:19],'after-freeze timestamp '+location.name)
        require(rec['metrics']==r['metrics'] and rec['retained_integrity']==r['state']['integrity'],'raw metrics/state '+location.name)
        require(rec['predecessor_integrity']==(old['integrity'] if old else None),'raw predecessor '+location.name)
        require(rec['provider_model_calls']==0 and rec['human_interventions'] is None,'unmeasured human and zero local provider distinction '+location.name)
        for a in r['pack']['result']['artifacts']:require((location/a['name']).read_bytes()==a['content'].encode(),'persisted artifact '+location.name+'/'+a['name'])
        require(read(location/'state.json')==r['state'],'persisted state '+location.name)
        receipt=read(location/'acceptance.json');require(receipt['accepted']==rec['accepted'] and receipt['checks']==rec['checks'] and receipt['failures']==rec['failures'],'acceptance receipt '+location.name)
        raw_acceptance+=receipt['accepted']
        if rec['arm']=='flywheel' and rec['cycle']==2:
            built=read(location/'construction.json')['result'];children[rec['project_id']]=built['child']
            require(built['parent']==audit['parent'],'construction actual parent '+location.name)
            require(built['child']['parent_digest']==digest('evidence-index',built['parent']),'construction origin '+location.name)
            require(built['child']['digest']==digest('dependency-repair',without(built['child'],'digest')),'constructed child identity '+location.name)
        if rec['arm']=='flywheel' and rec['cycle']>=2:
            require(r['impact']['child_digest']==children[rec['project_id']]['digest'],'actual retained child use '+location.name)
        if receipt['accepted']:prev[key]=r['state']
        reviewed.append({'mission':location.name,'accepted_by_review':audit['accepted_by_review']})
    require(len(records)==summary['joint_runs']==72,'joint run count')
    require(raw_acceptance==summary['accepted_joint_runs'],'accepted count')
    require(summary['family_checks']==len(records)*3,'shared family checks not independent tasks')
    for row in summary['joint_rows']:
        rs=[r for r in records if r['cycle']==row['cycle'] and r['arm']==row['arm']]
        label=f"summary c{row['cycle']} {row['arm']}"
        for field,value in [('projects',len(rs)),('accepted',sum(r['accepted'] for r in rs)),('failed',sum(not r['accepted'] for r in rs)),('work_units',sum(r['metrics']['lines_examined'] for r in rs)),('reused_items',sum(r['metrics']['reused_items'] for r in rs)),('built_items',sum(r['metrics']['built_items'] for r in rs)),('parent_calls',sum(r['metrics']['parent_calls'] for r in rs)),('child_calls',sum(r['metrics']['child_calls'] for r in rs))]:require(row[field]==value,label+' '+field)
        require(approx(row['total_wall_ms'],sum(r['wall_ms'] for r in rs)) and approx(row['total_cpu_ms'],sum(r['cpu_ms'] for r in rs)),label+' cost sums')
        require(approx(row['median_wall_ms'],statistics.median(r['wall_ms'] for r in rs)),label+' median')
    for field,key in [('wall_ms','wall_ms'),('cpu_ms','cpu_ms'),('assertions','checks')]:require(approx(summary['totals'][field],sum(r[key] for r in records)),'summary total '+field)
    for field in ['parent_calls','child_calls']:require(summary['totals'][field]==sum(r['metrics'][field] for r in records),'summary total '+field)
    require(all(row['shared_joint_cost'] for row in summary['rows']),'shared cost labels')
    require(all(g['refused'] for g in read(ROOT/'outputs/guards.json')),'unsupported input controls')
    # A concrete negative control verifies that this auditor catches two original-oracle gaps.
    rec=records[0];location=ROOT/rec['relative_directory'];p=read(location/'input.json');r=read(location/'execution.json')['result'];negatives=[]
    for name,mutate in [('false-assurance-digest',lambda x:x['consistency'].__setitem__('assurance_digest','0'*64)),('false-inventory-path',lambda x:x['assurance']['components'][0].__setitem__('path','invented'))]:
        altered=copy.deepcopy(r);mutate(altered);start=len(failures);audit=inspect_result(p,altered,None,rec['arm'],'NEGATIVE_CONTROL '+name);caught=not audit['accepted_by_review'];detected=failures[start:];del failures[start:]
        require(caught,'auditor negative control '+name);negatives.append({'case':name,'detected':caught,'rejection_labels':detected})
    changed={arm:sum(r['cpu_ms'] for r in records if r['arm']==arm and r['cycle']>=2) for arm in ['full_rebuild','flywheel','conventional_cache']}
    report={'status':'PASS' if not failures else 'FAIL','checks':checks,'failures':failures,'confirmation_joint_runs':len(records),'accepted_by_review':sum(x['accepted_by_review'] for x in reviewed),'producer_assertions_reconciled':summary['totals']['assertions'],'frozen_files_verified':len(freeze['entries']),'source_blobs_verified':len(manifest),'construction_origins_verified':len(children),'changed_cycle_cpu_ms':changed,'changed_flywheel_vs_cache_percent':100*(changed['flywheel']/changed['conventional_cache']-1),'negative_controls':negatives,'reviewed_missions':reviewed,'independence':'Separate reviewer-authored Python; imports no producer, oracle or solver module. Same commission, session, model family, source access and shared host. Digest algorithms follow published source specification. No fresh replay, live authentication, human judgment or external deployment attestation.','limits':['Only the finite recorded inputs are verified; original boundary defects remain.','Timing/resource counters are checked for arithmetic and record consistency, not independently metered.','Literal source extraction is not security, functional or licensing advice.','The workbench graph contains inherited generic aggregation scaffolding; no semantic gate or operational authority is inferred.','Seven stage records are artifact provenance, not separately measured/controlled stage execution.']}
    REPORT.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n');print(json.dumps({k:v for k,v in report.items() if k not in ['reviewed_missions','negative_controls']},indent=2));return not failures
if __name__=='__main__':raise SystemExit(0 if main() else 1)
