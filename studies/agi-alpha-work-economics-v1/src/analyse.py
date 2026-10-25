# SPDX-License-Identifier: Apache-2.0
import collections,json,math,random,statistics
from pathlib import Path
BASE=Path(__file__).resolve().parents[1]

def percentile(values,p):
    x=sorted(values);k=(len(x)-1)*p;i=int(k);return x[i] if i+1==len(x) else x[i]+(x[i+1]-x[i])*(k-i)
def stats(values):
    missing=sum(v is None for v in values);values=[v for v in values if v is not None]
    if not values:return {'n':0,'missing':missing,'median':None,'minimum':None,'maximum':None,'p95':None,'median_bootstrap_95':None}
    rng=random.Random(20261025);medians=[statistics.median(rng.choices(values,k=len(values))) for _ in range(10000)]
    return {'n':len(values),'missing':missing,'median':statistics.median(values),'minimum':min(values),'maximum':max(values),'p95':percentile(values,.95),'median_bootstrap_95':[percentile(medians,.025),percentile(medians,.975)]}
def wilson(k,n):
    z=1.959963984540054;p=k/n;d=1+z*z/n;c=(p+z*z/(2*n))/d;r=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/d;return [c-r,c+r]
def main():
    primary=json.loads((BASE/'raw/primary/results.json').read_text())['records'];scale=json.loads((BASE/'raw/scale/results.json').read_text())
    out={'primary_jobs':len(primary),'primary_accepted':sum(r['accepted'] for r in primary),'acceptance_wilson_95':wilson(sum(r['accepted'] for r in primary),len(primary)),
      'primary_turnaround_seconds':stats([r['process_turnaround_seconds'] for r in primary]),'primary_cpu_seconds':stats([r['total_cpu_seconds'] for r in primary]),
      'primary_total_cpu_seconds':sum(r['total_cpu_seconds'] for r in primary) if all(r['total_cpu_seconds'] is not None for r in primary) else None,
      'primary_known_cpu_seconds_subtotal':sum(r['total_cpu_seconds'] for r in primary if r['total_cpu_seconds'] is not None),
      'primary_cpu_missing_count':sum(r['total_cpu_seconds'] is None for r in primary),'primary_total_process_seconds':sum(r['process_turnaround_seconds'] for r in primary),
      'new_human_trial':'NOT_RUN','market_comparison':'MODELLED_WITH_SOURCED_BENCHMARKS','fully_allocated_cost_measured':False,'by_complexity':{},'by_context':{},'scale':{}}
    for label in ['complexity','context']:
        for value in sorted({r[label] for r in primary}):
            rows=[r for r in primary if r[label]==value]
            out['by_'+label][value]={'accepted':sum(r['accepted'] for r in rows),'attempts':len(rows),'turnaround_seconds':stats([r['process_turnaround_seconds'] for r in rows]),'cpu_seconds':stats([r['total_cpu_seconds'] for r in rows])}
    for c in [1,2,4]:
        batches=[b for b in scale['batches'] if b['concurrency']==c];rows=[r for r in scale['records'] if r['concurrency']==c]
        out['scale'][str(c)]={'jobs':len(rows),'accepted':sum(r['accepted'] for r in rows),'batch_throughput_per_minute':stats([b['accepted_per_minute'] for b in batches]),
          'process_seconds':stats([r['process_turnaround_seconds'] for r in rows]),'submit_to_delivery_seconds':stats([r['submission_to_acceptance_seconds'] for r in rows]),
          'mean_cpu_seconds':statistics.mean(r['total_cpu_seconds'] for r in rows if r['total_cpu_seconds'] is not None) if any(r['total_cpu_seconds'] is not None for r in rows) else None,
          'cpu_missing_count':sum(r['total_cpu_seconds'] is None for r in rows),'initial_queued_backlog':batches[0]['initial_queued_backlog']}
    out['showcase']=json.loads((BASE/'raw/showcase/receipt.json').read_text());out['successor']=json.loads((BASE/'raw/successor-report/receipt.json').read_text())
    (BASE/'raw/ANALYSIS.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))

if __name__=='__main__':main()
