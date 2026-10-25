# SPDX-License-Identifier: Apache-2.0
import collections,datetime,hashlib,json,resource,sys,time
from pathlib import Path
BASE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(BASE/'upstream'))
from alpha_factory_v1.core.runtime.successor.workbench import invoke,write_artifacts

def main():
    out=BASE/'raw/successor-report';out.mkdir(parents=True,exist_ok=False)
    start=time.perf_counter();own0=resource.getrusage(resource.RUSAGE_SELF);child0=resource.getrusage(resource.RUSAGE_CHILDREN)
    paths=[BASE/'raw/showcase/output/guide-result.json']+sorted((BASE/'raw/primary').glob('*/output/guide-result.json'))
    rows=[];lineage=[];groups=collections.defaultdict(list)
    for path in paths:
        result=json.loads(path.read_text());receipt=json.loads((path.parent.parent/'receipt.json').read_text())
        if not receipt['accepted']:raise ValueError('Unaccepted parent output cannot feed successor')
        context=receipt['context'];value=result['metrics']['fieldDifferences'];rows.append(context+','+str(value));groups[context].append(value)
        lineage.append({'job_id':receipt['job_id'],'guide_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'field_differences':value,'context':context,'retained_tool_sha256':receipt['retained_tool_sha256']})
    csv='group,amount\n'+'\n'.join(rows)+'\n'
    spec=invoke({'operation':'example','family':'public-data'})
    spec.update({'name':'Portfolio exception workload','owner':'study-local-controller','rights':{'dataClass':'synthetic','source':'Public release inventory plus controlled reconciliation outputs; exact parent identities in lineage.json','license':'Apache-2.0 / study synthetic data CC0'}})
    spec['inputs']={'csv':csv,'unit':'field differences requiring review'}
    plan=invoke({'operation':'plan','spec':spec});pack=invoke({'operation':'run','spec':spec})
    write_artifacts(pack,out/'output')
    data=json.loads(next(a['content'] for a in pack['result']['artifacts'] if a['name']=='analysis.json'))
    expected=[{'group':k,'count':len(v),'total':sum(v),'min':min(v),'max':max(v)} for k,v in sorted(groups.items())]
    checks={'all_37_parent_outputs_present':len(paths)==37,'total':data['total']==sum(sum(v) for v in groups.values()),'groups':data['groups']==expected,
        'no_settlement':pack['evaluation']['authority']==[] and pack['evaluation']['settlement']=='NOT_CONNECTED' and pack['frozen']['authority']==[]}
    acceptance={'accepted':all(checks.values()),'checks':checks,'scope':'independent Python arithmetic against source-linked accepted outputs; not external human acceptance'}
    for name,value in [('lineage.json',lineage),('plan.json',plan),('acceptance.json',acceptance),('expected.json',{'groups':expected,'total':sum(sum(v) for v in groups.values())})]:(out/name).write_text(json.dumps(value,indent=2)+'\n')
    own=resource.getrusage(resource.RUSAGE_SELF);child=resource.getrusage(resource.RUSAGE_CHILDREN)
    receipt={'job_id':'successor-exception-report','accepted':acceptance['accepted'],'worker_wall_seconds':time.perf_counter()-start,
        'total_cpu_seconds':own.ru_utime+own.ru_stime+child.ru_utime+child.ru_stime,
        'cpu_scope':'worker from startup plus child processes, through acceptance; final receipt tail excluded',
        'parent_count':len(paths),'model_calls':0,'human_review_minutes':None,'fully_allocated_cost':None,'scope':'composition of retained reconciliation evidence and released descriptive-report adapter',
        'new_human_trial':'NOT_RUN','market_comparison':'MODELLED_WITH_SOURCED_BENCHMARKS','execution':'pure native workbench worker; no Journal identity or connected executor'}
    (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt));return 0 if acceptance['accepted'] else 1

if __name__=='__main__':sys.exit(main())
