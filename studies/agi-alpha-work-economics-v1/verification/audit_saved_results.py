import collections, csv, datetime, hashlib, json, math, statistics, sys, zipfile
from pathlib import Path

BASE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(BASE/'src'))
from reference_reconciliation import verify_all

def strict(path):
    return json.loads(path.read_text(),parse_constant=lambda x:(_ for _ in ()).throw(ValueError('Nonstandard '+x)))
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    issues=[];checks=[];packets=[];manifest_leaves=0;zip_members=0
    def check(name,ok,detail=None):
        checks.append(name)
        if not ok: issues.append({'check':name,'detail':detail})
    freeze=strict(BASE/'protocol/FREEZE.json');freeze_sha=sha(BASE/'protocol/FREEZE.json')
    check('freeze_boundary_sha256',freeze_sha=='41b8b56a39993e29dc313faa8633e36abd910872ab43e9a5dbe1ab2edc589407')
    for f in freeze['files']:
        p=BASE/f['path'];check('frozen:'+f['path'],p.is_file() and p.stat().st_size==f['bytes'] and sha(p)==f['sha256'])
    source_audit=strict(BASE/'verification/independent_source_inventory.json')
    for side,tree in zip(['left','right'],source_audit['trees']):
        frozen_inventory=strict(BASE/'protocol'/('public_inventory_'+tree['source_commit'][:8]+'.json'))
        check('independently_fetched_public_inventory:'+side,not tree['truncated'] and frozen_inventory['entries']==tree['entries'])
        with (BASE/'raw/showcase'/(side+'.csv')).open() as f:records=list(csv.DictReader(f))
        check('showcase_matches_public_inventory:'+side,records==[{k:str(v) for k,v in entry.items()} for entry in tree['entries']])
    paths=[BASE/'raw/showcase']+sorted(p.parent for p in (BASE/'raw/primary').glob('*/receipt.json'))+sorted(p.parent for p in (BASE/'raw/scale').glob('*/*/receipt.json'))
    check('145_reconciliation_output_packets',len(paths)==145,len(paths))
    parent=BASE/'raw/showcase/output/successor-tool.mjs';parent_sha=sha(parent)
    check('retained_tool_contains_frozen_engine',parent.read_bytes().startswith((BASE/'upstream/examples/successor-alpha/engine.mjs').read_bytes()+b'\n'))
    public_time=datetime.datetime.fromisoformat('2026-10-25T11:16:16+00:00')
    for i,p in enumerate(paths):
        label=str(p.relative_to(BASE));inp=strict(p/'input.json');receipt=strict(p/'receipt.json');result=verify_all(inp,p/'output')
        packets.append({'path':label,'accepted':result['accepted'],'checks':result['checks'],'failures':result['failures']})
        check('full_oracle:'+label,result['accepted'],result['failures'])
        check('accepted_receipt:'+label,receipt['accepted'] is True and (p==BASE/'raw/showcase' or receipt.get('process_exit_code')==0))
        check('after_public_freeze:'+label,datetime.datetime.fromisoformat(receipt['started_utc'])>public_time,receipt['started_utc'])
        for side in ['left','right']:check('input_consistency:'+label+':'+side,(p/(side+'.csv')).read_bytes()==inp[side+'Csv'].encode())
        if p!=BASE/'raw/showcase':check('retained_identity:'+label,receipt['retained_tool_sha256']==parent_sha)
        check('unknown_complete_cost:'+label,receipt['fully_allocated_cost'] is None and receipt['human_review_minutes'] is None and receipt['human_active_minutes'] is None)
        check('zero_operational_model_calls:'+label,receipt['model_calls']==0 and receipt['model_tokens']==0)
        check('cpu_scope:'+label,isinstance(receipt.get('cpu_scope'),str) and 'final receipt serialization tail excluded' in receipt['cpu_scope'])
        manifest=strict(p/'OUTPUT_MANIFEST.json');manifest_leaves+=len(manifest)
        check('manifest_exact_file_set:'+label,{f['path'] for f in manifest}=={str(x.relative_to(p/'output')) for x in (p/'output').rglob('*') if x.is_file()})
        for f in manifest:
            fp=p/'output'/f['path'];check('output_hash:'+label+':'+f['path'],fp.stat().st_size==f['bytes'] and sha(fp)==f['sha256'])
        for fp in (p/'output').glob('*.json'):
            try:strict(fp);check('strict_json:'+str(fp.relative_to(BASE)),True)
            except Exception as e:check('strict_json:'+str(fp.relative_to(BASE)),False,str(e))
        with zipfile.ZipFile(p/'delivery.zip') as z:
            names=z.namelist();zip_members+=len(names)
            check('zip_members:'+label,len(set(names))==len(names) and set(names)=={f['path'] for f in manifest}|{'acceptance.json','OUTPUT_MANIFEST.json'})
            for name in names:
                disk=p/name if name in ['acceptance.json','OUTPUT_MANIFEST.json'] else p/'output'/name
                check('zip_bytes:'+label+':'+name,z.read(name)==disk.read_bytes())
            check('zip_crc:'+label,z.testzip() is None)
        if (i+1)%30==0:print('Independent packet audits completed:',i+1,flush=True)
    primary=strict(BASE/'raw/primary/results.json')['records'];scale=strict(BASE/'raw/scale/results.json');analysis=strict(BASE/'raw/ANALYSIS.json')
    for r in primary:check('aggregate_receipt_identity:primary:'+r['job_id'],r==strict(BASE/'raw/primary'/r['job_id']/'receipt.json'))
    for r in scale['records']:check('aggregate_receipt_identity:scale:'+r['batch']+':'+r['job_id'],r==strict(BASE/'raw/scale'/r['batch']/r['job_id']/'receipt.json'))
    check('primary_denominator',len(primary)==36 and len({r['job_id'] for r in primary})==36)
    check('primary_balanced_contexts',set(collections.Counter(r['context'] for r in primary).values())=={9})
    check('primary_balanced_difficulty',set(collections.Counter(r['complexity'] for r in primary).values())=={12})
    check('scale_denominator',len(scale['records'])==108 and len(scale['batches'])==9)
    check('scale_12_unique_inputs',len({r['job_id'] for r in scale['records']})==12)
    check('analysis_primary_count',analysis['primary_jobs']==36 and analysis['primary_accepted']==36)
    check('analysis_cpu_sum',math.isclose(analysis['primary_total_cpu_seconds'],sum(r['total_cpu_seconds'] for r in primary),rel_tol=1e-12))
    check('analysis_time_median',analysis['primary_turnaround_seconds']['median']==statistics.median(r['process_turnaround_seconds'] for r in primary))
    for batch in scale['batches']:
        rows=[r for r in scale['records'] if r['batch']==batch['batch']]
        check('batch_count:'+batch['batch'],len(rows)==12 and batch['accepted']==sum(r['accepted'] for r in rows))
        check('batch_throughput:'+batch['batch'],math.isclose(batch['accepted_per_minute'],60*batch['accepted']/batch['wall_seconds'],rel_tol=1e-12))
        check('batch_cpu:'+batch['batch'],math.isclose(batch['cpu_seconds'],sum(r['total_cpu_seconds'] for r in rows),rel_tol=1e-12) and batch['cpu_measurement_missing_count']==0)
        for r in rows:check('queued_latency:'+batch['batch']+':'+r['job_id'],r['submission_to_acceptance_seconds']>=r['queue_wait_seconds']+r['process_turnaround_seconds'])
    ctrl=strict(BASE/'raw/controls/controls.json');check('eight_control_cases',len(ctrl['cases'])==8 and ctrl['passed']==8 and ctrl['businessDeliverablesCounted']==0)
    check('control_case_assertions',all(c['status']=='PASS' and all(a['passed'] for a in c['checks']) for c in ctrl['cases']))
    for f in strict(BASE/'raw/controls/evidence-manifest.json')['files']:
        p=BASE/'raw/controls'/f['path'];check('control_evidence_hash:'+f['path'],p.stat().st_size==f['bytes'] and sha(p)==f['sha256'])
    for name in ['workspace.json','all-differences.csv']:
        q=BASE/'raw/controls/C06_ROLLBACK';check('rollback_exact_bytes:'+name,(q/'prior'/name).read_bytes()==(q/'active'/name).read_bytes() and (q/'later'/name).read_bytes()!=(q/'prior'/name).read_bytes())
    lineage=strict(BASE/'raw/successor-report/lineage.json');check('successor_37_parent_count',len(lineage)==37)
    parents={strict(p/'receipt.json')['job_id']:p for p in paths if 'scale' not in p.relative_to(BASE).parts};groups=collections.defaultdict(list)
    for entry in lineage:
        p=parents[entry['job_id']];guide=strict(p/'output/guide-result.json')
        check('successor_parent_identity:'+entry['job_id'],entry['guide_sha256']==sha(p/'output/guide-result.json') and entry['field_differences']==guide['metrics']['fieldDifferences'])
        groups[entry['context']].append(entry['field_differences'])
    expected=[{'group':k,'count':len(v),'total':sum(v),'min':min(v),'max':max(v)} for k,v in sorted(groups.items())]
    agg=strict(BASE/'raw/successor-report/output/analysis.json');check('successor_exact_groups',agg['groups']==expected);check('successor_exact_total',agg['total']==sum(sum(v) for v in groups.values()))
    check('successor_accepted',strict(BASE/'raw/successor-report/receipt.json')['accepted'] is True)
    successor_evidence=strict(BASE/'raw/successor-report/output/evidence.json')
    check('successor_no_authority',successor_evidence['evaluation']['authority']==[] and successor_evidence['frozen']['authority']==[])
    check('successor_no_settlement',successor_evidence['evaluation']['settlement']=='NOT_CONNECTED')
    report={'schema':'work-economics-independent-review/v1','reviewed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'Revalidation of frozen outputs and evidence; no confirmation job reruns or edits','status':'PASS' if not issues else 'FINDINGS','freeze_sha256':freeze_sha,'frozen_files':len(freeze['files']),'public_freeze_notice':{'url':'https://github.com/MontrealAI/AGI-Alpha-Agent-v0/issues/4850#issuecomment-6396944650','created_at':'2026-10-25T11:16:16Z','independently_fetched':True},'outer_checks':len(checks),'oracle_checks':sum(x['checks'] for x in packets),'manifest_leaves':manifest_leaves,'zip_members':zip_members,'reconciliation_packets':len(paths),'primary_confirmation_jobs':36,'showcase_jobs':1,'successor_report_jobs':1,'load_repeats':108,'controls':8,'retained_tool_sha256':parent_sha,'issues':issues,'packet_audits':packets,'statistical_limits':['36 synthetic controlled jobs do not sample all professional work.','108 operating attempts repeat 12 inputs; they are not 108 fresh jobs.','The natural source-inventory showcase was selected during development.','Machine acceptance is role-independent automated checking, not blinded human/client acceptance.'],'economic_limits':['New matched human trial NOT_RUN; market comparison MODELLED_WITH_SOURCED_BENCHMARKS.','Unknown human attention/setup/maintenance/full cost remain null.','No empirical human speed or cost ratio follows from these outputs.','Per-job local operational model calls are zero; development assistant work is separately unmetered.'],'control_limits':['Pre-aborted cooperative STOP, not arbitrary process kill.','Injected checkpoint interruption with explicit input restart, not internal-checkpoint continuation.','Simulated time boundary, not monetary-spending enforcement.','Local artifact snapshot restoration, not transactional/contract rollback.','No remote worker, persistent daemon or browser-close continuation established.'],'audit_development_note':'An initial evaluator launcher assumed an outer-process receipt field on the directly invoked showcase and stopped with KeyError; no measured result was changed. The evaluator was corrected to use recorded stage exits for that packet.'}
    report['public_source_audit']={'evidence_file':'verification/independent_source_inventory.json','sources':[t['url'] for t in source_audit['trees']],'records_per_source':[len(t['entries']) for t in source_audit['trees']],'complete_tree_responses':all(not t['truncated'] for t in source_audit['trees'])}
    report['measurement_code_review']={'cpu_startup':'run_job CPU counter starts at process zero and sums own plus completed child user/system CPU; final serialization is excluded explicitly.','native_evaluation':'Successor acceptance uses required pack.evaluation authority and settlement fields, plus frozen authority; no default missing-field pass.','configured_review_minutes':successor_evidence['spec']['reviewMinutes'],'configured_review_minutes_status':'Upstream example metadata only; not observed attention. Receipt human_review_minutes remains null.'}
    (BASE/'verification/independent_review.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='packet_audits'},indent=2));return 0 if not issues else 1

if __name__=='__main__':sys.exit(main())
