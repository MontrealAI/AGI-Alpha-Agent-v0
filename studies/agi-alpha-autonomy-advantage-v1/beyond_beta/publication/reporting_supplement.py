# SPDX-License-Identifier: Apache-2.0
"""Mechanical post-freeze reporting corrections; no simulation or policy change."""
from pathlib import Path
from collections import Counter,defaultdict
import gzip,json,argparse

ROOT=Path(__file__).resolve().parents[1]

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--results',type=Path,default=ROOT/'results/primary');args=ap.parse_args()
    summary=json.loads((args.results/'summary.json').read_text());assert summary['status']=='COMPLETE'
    out=[]
    with gzip.open(args.results/'worlds.jsonl.gz','rt') as f:
        for line in f:
            w=json.loads(line);s=w['summary'];bills=w['cash']['bills'];a=s['accepted']
            totals=defaultdict(int)
            for b in bills:
                account=b.get('ledger','FINANCIAL');category=b['category']
                if account=='B':bucket='B_initial_retention' if category in ('candidateAssessment','incrementalRetention') else 'B_reuse_integration_upkeep'
                elif account=='OPERATIONS':bucket='shared_setup' if category=='setup' else 'shared_recurring_operations'
                else:bucket=account
                totals[bucket]+=b['amountMicros']
            assert sum(totals.values())==w['cash']['funds']['accruedMicros']
            dollars={k:v/1e6 for k,v in totals.items()}
            recurring=sum(dollars.get(k,0) for k in ['A','B_reuse_integration_upkeep','shared_recurring_operations','FINANCIAL'])
            fixed=sum(dollars.get(k,0) for k in ['B_initial_retention','C','shared_setup','shared_recurring_operations'])
            variable=sum(dollars.get(k,0) for k in ['A','B_reuse_integration_upkeep','FINANCIAL'])
            contribution=(s['collectionsUSD']-variable)/a if a else 0
            decisions=[x for x in w['investmentDecisions'] if x['decision']=='RETAIN']
            out.append({'scenario':s['scenario'],'seed':s['seed'],'arm':s['arm'],'profile':s['profile'],'costBucketsUSD':dollars,
                'deliveryAperAcceptedUSD':dollars.get('A',0)/a if a else None,
                'ongoingPerAcceptedUSD':recurring/a if a else None,'completePerAcceptedUSD':s['costPerAcceptedUSD'],
                'breakEvenAcceptedAtObservedMix':fixed/contribution if contribution>0 else None,
                'wholeInitialProgramFunding':dict(Counter(x['wholeInitialProgramFundingOrigin'] for x in decisions)),
                'assessmentFunding':dict(Counter(x['assessmentFundingOrigin'] for x in decisions)),
                'constructionFunding':dict(Counter(x['constructionFundingOrigin'] for x in decisions)),
                'marginalUpkeepDecisions':dict(Counter(e['decision'] for e in w['events'] if e['type']=='MARGINAL_UPKEEP_DECISION'))})
    target=ROOT/'analysis/reporting-supplement.json';target.parent.mkdir(exist_ok=True)
    target.write_text(json.dumps({'schema':'paid-job-alpha-reporting-supplement/v1','changesEconomicOutcomes':False,'worlds':out},indent=2)+'\n')
    print(json.dumps({'written':str(target),'worlds':len(out)}))

if __name__=='__main__':main()
