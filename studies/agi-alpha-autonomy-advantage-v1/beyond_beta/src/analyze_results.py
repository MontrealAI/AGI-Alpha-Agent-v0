# SPDX-License-Identifier: Apache-2.0
"""Read-only statistical analysis of the frozen campaign; no world generation."""
from collections import defaultdict, Counter
from pathlib import Path
import argparse, gzip, hashlib, json, math, os
import numpy as np

ROOT=Path(__file__).resolve().parents[1]

def distribution(values):
    x=np.asarray(values,dtype=float)
    if not len(x): return None
    return {'n':len(x),'mean':float(x.mean()),'median':float(np.median(x)),
            'p05':float(np.quantile(x,.05)),'p95':float(np.quantile(x,.95)),
            'min':float(x.min()),'max':float(x.max()),'positive':int((x>0).sum()),'negative':int((x<0).sum())}

def paired(values,rng):
    out=distribution(values);x=np.asarray(values,dtype=float)
    boot=x[rng.integers(0,len(x),(2000,len(x)))].mean(axis=1)
    out['conditionalMeanCI95']=[float(np.quantile(boot,.025)),float(np.quantile(boot,.975))]
    return out

def write(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data,indent=2,allow_nan=False)+'\n')

def dollar(x,digits=0):
    return ('-' if x<0 else '')+'\\$'+f'{abs(x):,.{digits}f}'

def analyze(results):
    campaign=json.loads((results/'summary.json').read_text())
    if campaign['status']!='COMPLETE': raise ValueError('A complete frozen campaign is required')
    p=json.loads((ROOT/'protocol.json').read_text()); rng=np.random.default_rng(601775)
    scenarios=[x['id'] for x in p['scenarios']]; arms=p['experiment']['confirmationArms']
    cells={}; contrasts={}; rows=campaign['rows']; details=defaultdict(list)
    for scenario in scenarios:
        for arm in arms:
            sample=[x for x in rows if x['scenario']==scenario and x['arm']==arm]
            cells[scenario+'|'+arm]={key:distribution([x[key] for x in sample if x.get(key) is not None]) for key in
                ('completeProfitUSD','completeCostsUSD','collectionsUSD','costPerAcceptedUSD','accepted','technicalAccepted','falsePasses','cashRemainingUSD','availableOperatingUSD','admittedAssets','assetUses','retentionResearchProgramNetResourcesUSD')}
            cells[scenario+'|'+arm].update(closedWorlds=sum(x['closed'] for x in sample),cashInvalidWorlds=sum(not x['cashValid'] for x in sample),
                closureReasons=dict(Counter(x.get('closureReason') or 'none' for x in sample)))
        pairs=[x for x in campaign['pairedComparisons'] if x['scenario']==scenario]
        contrasts[scenario]={key:paired([x[key] for x in pairs],rng) for key in
            ('incrementalAlphaMovingUSD','incrementalAlphaFrozenUSD','sharingVersusPrivateUSD','trainedWholePolicyUSD','erosionInteractionUSD')}
    with gzip.open(results/'worlds.jsonl.gz','rt') as f:
        for line in f:
            world=json.loads(line);s=world['summary'];group=s['scenario']+'|'+s['arm'];bills=world['cash']['bills']; accepted=s['accepted']
            spending={key:sum(b['amountMicros'] for b in bills if b.get('ledger','FINANCIAL')==key)/1e6 for key in ('A','B','C','OPERATIONS','FINANCIAL')}
            jobs=world['jobs'];useful=[j for j in jobs if j['usefulAccepted']];offers={o['id']:o for o in world['offers']}
            d={'seed':s['seed'],'profile':s['profile'],'spending':spending,'choices':dict(Counter(o['choice'] for o in world['offers'])),
               'accepted':accepted,'marginalAperAccepted':spending['A']/accepted if accepted else None,
               'recurringPerAccepted':(spending['A']+spending['B']+spending['OPERATIONS']+spending['FINANCIAL']-sum(b['amountMicros'] for b in bills if b['category']=='setup')/1e6)/accepted if accepted else None,
               'humanReferenceAcceptedMean':float(np.mean([offers[j['id']]['humanReferenceUSD'] for j in useful])) if useful else None,
               'priceAcceptedMean':float(np.mean([j['priceUSD'] for j in useful])) if useful else None,
               'priceBelowHumanAccepted':sum(j['priceUSD']<offers[j['id']]['humanReferenceUSD'] for j in useful),
               'acceptedCustomerSavings':sum(offers[j['id']]['humanReferenceUSD']-j['priceUSD'] for j in useful),
               'meanTurnaroundDays':float(np.mean([7*(j['completionWeek']-j['week']) for j in jobs])) if jobs else None,
               'meanInitialQueueDays':float(np.mean([7*(min(a['week'] for a in j['reservation']['allocations'])-j['week']) for j in jobs])) if jobs else None,
               'totalRepairs':sum(j.get('repairs',0) for j in jobs),
               'paidJobCandidates':sum(c['source']=='PAID_JOB_LEARNING_A' for c in world['candidates']),
               'separateResearchCandidates':sum(c['source']=='OPTIONAL_SEPARATE_RESEARCH_C' for c in world['candidates']),
               'paidJobAdmissions':sum(a['source']=='PAID_JOB_LEARNING_A' and a['admittedWeek'] is not None for a in world['assets']),
               'separateResearchAdmissions':sum(a['source']=='OPTIONAL_SEPARATE_RESEARCH_C' and a['admittedWeek'] is not None for a in world['assets']),
               'falseAdmissions':sum(a['admittedWeek'] is not None and not a['trueValid'] for a in world['assets']),
               'candidateStates':dict(Counter(c['state'] for c in world['candidates'])),
               'programDirectNet':s['retentionResearchProgramNetResourcesUSD'],
               'assetDirectNets':[a['realizedDirectNetUSD'] for a in world['assets'] if a['admittedWeek'] is not None],
               'positiveIndividualAssets':s['directlyPositiveAssets'],
               'retentionFunding':dict(Counter(x.get('fundingOrigin','none') for x in world['investmentDecisions'] if x['decision']=='RETAIN')),
               'maxWorkerModelUtilization':0.0,'maxWorkerProofUtilization':0.0,'maxWeeklyTokenUtilization':0.0}
            weekly=defaultdict(lambda:defaultdict(float)); worker=defaultdict(lambda:defaultdict(float))
            for plan in world['resourceSchedules']:
                for allocation in plan['allocations']:
                    for k in ('modelHours','cpuHours'):worker[(allocation['week'],allocation['worker'])][k]+=allocation[k]
                    weekly[allocation['week']]['tokens']+=allocation['tokens']
            if worker:
                d['maxWorkerModelUtilization']=max(v['modelHours']/p['capacity']['modelHoursPerAgentWeek'] for v in worker.values())
                d['maxWorkerProofUtilization']=max(v['cpuHours']/p['capacity']['proofContainerHoursPerAgentWeek'] for v in worker.values())
            override=next(x['overrides'] for x in p['scenarios'] if x['id']==s['scenario'])
            if weekly:d['maxWeeklyTokenUtilization']=max(v['tokens']/(p['capacity']['tokensPerMinuteTotal']*10080*override.get('quotaMultiplier',1)) for v in weekly.values())
            # An accounting threshold under stationary observed composition, not a demand forecast.
            contribution=(s['collectionsUSD']-spending['A']-spending['B']-spending['FINANCIAL'])/accepted if accepted else 0
            d['breakEvenAcceptedWorkload']=(spending['OPERATIONS']+spending['C'])/contribution if contribution>0 else None
            details[group].append(d)
    result={'schema':'paid-job-alpha-analysis/v1','basis':'CONDITIONAL_SIMULATION','analysisSeed':601775,'bootstrapDraws':2000,
            'sourceSummarySHA256':hashlib.sha256((results/'summary.json').read_bytes()).hexdigest(),'cells':cells,'paired':contrasts,'worldDetails':details,
            'limitations':['Bootstrap intervals condition on all scenario assumptions.','Nineteen stress conditions are not a market probability distribution.','No actual job or sale is inferred.']}
    out=ROOT/'analysis';write(out/'analysis.json',result)
    figure_dir=ROOT/'publication/figures';figure_dir.mkdir(parents=True,exist_ok=True)
    os.environ.setdefault('MPLCONFIGDIR',str(ROOT/'publication/.mpl-cache'))
    import matplotlib;matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.size':9,'axes.spines.top':False,'axes.spines.right':False,'axes.labelcolor':'#163044','text.color':'#163044','figure.facecolor':'white','savefig.facecolor':'white'})
    fig,ax=plt.subplots(figsize=(9.1,6.0));ys=np.arange(len(scenarios));colors=[]
    for i,scenario in enumerate(scenarios):
        x=contrasts[scenario]['incrementalAlphaMovingUSD'];lo,hi=x['conditionalMeanCI95'];color='#087F8C' if x['mean']>=0 else '#AA742D'
        ax.errorbar(x['mean'],i,xerr=[[max(0,x['mean']-lo)],[max(0,hi-x['mean'])]],fmt='o',color=color,capsize=2)
    ax.axvline(0,color='#89949b',lw=1);ax.set_yticks(ys,scenarios);ax.invert_yaxis();ax.set_xlabel('Network Alpha minus matched Beta: complete profit (modeled USD)')
    ax.set_title('What retention adds after all costs',loc='left',fontweight='bold');ax.grid(axis='x',alpha=.15);fig.tight_layout();fig.savefig(figure_dir/'alpha-conditions.pdf');fig.savefig(figure_dir/'alpha-conditions.png',dpi=150);plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(9.1,3.5))
    labels=['Trained Beta','Matched Beta','Network Alpha'];names=['trained-beta','moving-beta-only','network-alpha'];colors=['#647789','#ABB8C1','#087F8C']
    values=[[r['completeProfitUSD']/1000 for r in rows if r['scenario']=='reference' and r['arm']==a] for a in names]
    bp=axes[0].boxplot(values,labels=labels,patch_artist=True,showfliers=True)
    for patch,c in zip(bp['boxes'],colors):patch.set_facecolor(c)
    axes[0].axhline(0,color='#89949b',lw=1);axes[0].set_ylabel('Complete profit (modeled USD thousands)');axes[0].set_title('Reference-condition service economics',loc='left',fontsize=10)
    demo=json.loads((results/'demonstration-network-alpha.json').read_text());snap=demo['cash']['snapshots']
    axes[1].plot([x['t']/7 for x in snap],[x['cash']/1000 for x in snap],label='Cash incl. seed',color='#647789')
    axes[1].plot([x['t']/7 for x in snap],[x['availableOperating']/1000 for x in snap],label='Available operating funds',color='#087F8C')
    axes[1].set_xlabel('Week');axes[1].set_ylabel('Modeled USD thousands');axes[1].set_title('Preselected illustration: reference / 1001',loc='left',fontsize=10);axes[1].legend(frameon=False,fontsize=8)
    fig.tight_layout();fig.savefig(figure_dir/'commercial-cash.pdf');fig.savefig(figure_dir/'commercial-cash.png',dpi=150);plt.close(fig)
    print(json.dumps({'analysis':str(out/'analysis.json'),'cells':len(cells),'pairedConditions':len(contrasts),'worlds':sum(map(len,details.values()))}))
    return result

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--results',type=Path,default=ROOT/'results/primary');args=ap.parse_args();analyze(args.results)
