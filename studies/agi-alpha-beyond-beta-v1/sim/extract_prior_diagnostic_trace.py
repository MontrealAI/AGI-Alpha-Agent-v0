# SPDX-License-Identifier: Apache-2.0
"""Extract an existing useful-use, nonpayback illustration; no new simulation."""
import csv
import gzip
import hashlib
import json
import math
from pathlib import Path
from datetime import datetime,timezone

ROOT=Path(__file__).resolve().parent.parent
SOURCE=ROOT/'results/paid_work_prior_diagnostic'
ARMS=('frozen_beta','frozen_network','posterior_coherent_network')


def main():
    rows=list(csv.DictReader((SOURCE/'worlds.csv').open()))
    candidates=[r for r in rows if r['diagnostic_arm']=='posterior_coherent_network' and float(r['operating_funded_true_paid_source_useful_projects'])>0 and float(r['investment_cost'])==0]
    if not candidates:
        print('No eligible useful-use illustration in the completed diagnostic.');return
    world=min(int(r['world']) for r in candidates);selected={r['diagnostic_arm']:r for r in rows if int(r['world'])==world};records={};checks=0
    for arm in ARMS:
        with gzip.open(SOURCE/f'{arm}_complete_records.jsonl.gz','rt') as stream:
            for line in stream:
                record=json.loads(line)
                if record['world']==world:
                    records[arm]=record;break
        assert arm in records
        for key,value in records[arm]['metrics'].items():
            text=selected[arm][key]
            if value is None:assert text==''
            elif isinstance(value,bool):assert str(value)==text
            elif isinstance(value,(float,int)):assert math.isclose(value,float(text),rel_tol=1e-12,abs_tol=1e-7),(arm,key,value,text)
            else:continue
            checks+=1
    network=records['posterior_coherent_network'];base=records['frozen_beta'];delta=network['metrics']['net_profit']-base['metrics']['net_profit'];quality_delta=network['metrics']['quality_adjusted_profit']-base['metrics']['quality_adjusted_profit'];assert delta<0 and quality_delta<0
    chain=None
    for job_id,job in sorted(network['job_records'].items(),key=lambda item:(item[1].get('attempt_month',0),item[0])):
        if not job.get('true_useful_for_analysis_only'):continue
        for cid in job.get('used_capability_ids',[]):
            event=next((e for e in network['events'] if e['kind']=='retention_purchase' and e['id']==cid),None)
            if not event or event['seed_funded']!=0 or event['operating_funded']<=0:continue
            source=network['job_records'].get(event['origin']['job_id'],{})
            if source.get('true_useful_for_analysis_only') and source.get('net_customer_receipts_after_refund_obligations',0)>0:
                chain={'capability_id':cid,'origin_job_id':event['origin']['job_id'],'recipient_job_id':job_id,'retention_purchase':event,'origin_job':source,'recipient_job':job};break
        if chain:break
    assert chain is not None
    out=SOURCE/'selected_useful_nonpayback';out.mkdir(exist_ok=True)
    for arm,record in records.items():(out/f'{arm}.json').write_text(json.dumps(record,indent=2))
    (out/'chain.json').write_text(json.dumps(chain,indent=2))
    manifest={'status':'SELECTED USEFUL-REUSE ILLUSTRATION WITH NEGATIVE COMPLETE NETWORK VALUE; NOT PROFITABLE FEEDBACK OR A NEW TRIAL','selection_rule':'Lowest existing diagnostic world ID with an operating-funded retained package, useful collected source, useful fresh recipient use, and no optional C campaign.','world':world,'seed':json.loads((SOURCE/'diagnostic_design.json').read_text())['seed'],'scalar_matches':checks,'all_three_saved_arms_matched':True,'network_vs_beta_profit':delta,'network_vs_beta_quality_adjusted_profit':quality_delta,'strict_paid_job_feedback':False,'source_completed_run_manifest_sha256':hashlib.sha256((SOURCE/'run_manifest.json').read_bytes()).hexdigest(),'extracted_at_utc':datetime.now(timezone.utc).isoformat(),'chain':{k:chain[k] for k in ['capability_id','origin_job_id','recipient_job_id']}}
    (out/'selection_manifest.json').write_text(json.dumps(manifest,indent=2));print(json.dumps(manifest,indent=2))


if __name__=='__main__':main()
