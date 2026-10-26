#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Explain recorded policy/delay effects using existing histories only; no market execution."""
import collections
import gzip
import hashlib
import json
import math
from pathlib import Path

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'results-01'
records={}
variants={'base':'robust-main','undercut':'robust-stress-undercut',
          'delay6':'robust-stress-collections-week6','delay13':'robust-stress-collections-week13'}
selected={f'{prefix}-i{i}-a0.5-{choice}-adoption-only':(variant,i,choice)
          for variant,prefix in variants.items() for i in [0,500] for choice in ['deterministic','logit']}
for line in gzip.open(OUT/'complete-runs.jsonl.gz','rt'):
    pair=json.loads(line);identity=selected.get(pair['config']['id'])
    if identity:
        run=pair['arms']['B']
        records[(*identity,pair['seed'])]={'config':pair['config'],'summary':run['summary'],
            'histories':run['histories'],'competitors':run['competitorAccounts'],
            'funding':pair['successionAvailability']['fundingByArm']['B']}
assert len(records)==384

def mean(values):return sum(values)/len(values)
def span(values):return [min(values),max(values)] if values else None
def random_draw(seed,*keys):
    # Exact reconstruction of an already-used buyer-type input, not a new market draw.
    h=(seed&0xffffffff)^2166136261
    for char in '|'.join(map(str,keys)):
        h=((h^ord(char))*16777619)&0xffffffff
    h^=h>>16;h=(h*0x7feb352d)&0xffffffff
    h^=h>>15;h=(h*0x846ca68b)&0xffffffff
    h^=h>>16
    return (h+.5)/4294967296

def firm_before_choice(run,provider,week,mission):
    history=run['histories'];prior=[]
    for choice in history['buyerChoices']:
        if choice['week']!=week:continue
        if choice['mission']==mission:break
        prior.append(choice['mission'])
    prior=set(prior)
    if provider=='enterprise':
        bills=history['bills'];events=history['cash'];opening=run['config']['initialCashCents']
    else:
        firm=run['competitors'][provider];bills=firm['bills'];events=firm['cashEvents'];opening=firm['openingCashCents']
    by_id={b['id']:b for b in bills}
    visible_bills=[b for b in bills if b['week']<week or b['week']==week and (b['category']!='delivery' or b['reference'] in prior)]
    # All selected conditions have expenseDelay=0 and paymentDelay>0. Non-delivery
    # cash events occur before the buyer loop; current-week delivery bills identify its order.
    visible_events=[e for e in events if e['week']<week or e['week']==week and
        (by_id.get(e['reference'],{}).get('category')!='delivery' or by_id[e['reference']]['reference'] in prior)]
    paid={e['reference'] for e in visible_events if e['amountCents']<0}
    cash=opening+sum(e['amountCents'] for e in visible_events)
    unpaid=sum(b['amountCents'] for b in visible_bills if b['id'] not in paid)
    reserve=run['config']['reserveCents'] if provider=='enterprise' else 0
    return {'cashCents':cash,'unpaidCents':unpaid,'reserveCents':reserve,'cashLessObligationsAndReserveCents':cash-unpaid-reserve}

def first_divergence(base,delayed,seed):
    a=base['histories']['buyerChoices'];b=delayed['histories']['buyerChoices']
    assert [(x['week'],x['mission']) for x in a]==[(x['week'],x['mission']) for x in b]
    pair=next(((x,y) for x,y in zip(a,b) if x['choice']!=y['choice']),None)
    if pair is None:return None
    before,after=pair;week=before['week'];mission=before['mission'];index=int(before['buyer'].split('-')[1])
    details={}
    for label,run in [('base',base),('delay13',delayed)]:
        c=run['config'];minutes=c['humanMinutes'][math.floor(random_draw(seed,'type-minutes',index)*len(c['humanMinutes']))]
        active=any(e['success'] and e['availableWeek']<=week for e in run['histories']['investments'])
        pending=any(e['success'] and e['week']<=week<e['availableWeek'] for e in run['histories']['investments'])
        imitated=any(e['provider']=='ai' and e['action']=='adopt-automation' and e['week']<=week for e in run['histories']['competitorActions'])
        ai_cost=math.floor(c['aiCostCents']*(1-c['competitorCostReduction'])+.5) if imitated else c['aiCostCents']
        unit=math.floor((c['commonResidualMinutes']+(c['assetResidualMinutes'] if active else c['ordinaryFinalizationMinutes']))*c['hourlyProviderCents']/60+.5)+c['computeAndToolCents']
        required={'enterprise':unit*c['failureCorrectionMultiplier'],
                  'human':math.floor(minutes*c['humanHourlyCents']/60*c['failureCorrectionMultiplier']+.5),
                  'ai':math.floor(ai_cost*c['failureCorrectionMultiplier']+.5)}
        states={p:firm_before_choice(run,p,week,mission) for p in ['enterprise','human','ai']}
        for p,state in states.items():
            state['requiredCashForThisBuyerCents']=required[p]
            state['cashGatePasses']=state['cashLessObligationsAndReserveCents']>=required[p]
        prices=next(x for x in run['histories']['prices'] if x['week']==week)
        details[label]={'choice':before['choice'] if label=='base' else after['choice'],
                        'enterprisePending':pending,'cashStates':states,
                        'computedAIQuoteCents':prices['aiCents'],'computedEnterpriseQuoteCents':prices['enterpriseCents'],
                        'humanMarkup':prices['humanMarkup'],'AIImitated':imitated}
    return {'seed':seed,'week':week,'mission':mission,'buyerHumanMinutes':minutes,**details}

groups=[];divergences=[]
for integration in [0,500]:
    for choice in ['deterministic','logit']:
        item={'integrationCents':integration,'choiceModel':choice,'investmentCostBasis':'adoption-only','armsExamined':['B'],'variants':{}}
        for variant in variants:
            runs=[records[(variant,integration,choice,seed)] for seed in range(3001,3025)]
            quotes=[p['aiCents'] for run in runs for p in run['histories']['prices']]
            ai_prices=[j['priceCents'] for run in runs for j in run['histories']['jobs'] if j['provider']=='ai' and j['accepted']]
            liquidity={}
            for provider in ['human','ai']:
                firms=[run['competitors'][provider] for run in runs]
                liquidity[provider]={'insolventFirms':sum(f['insolvent'] for f in firms),
                    'minimumRecordedCashCents':min([f['openingCashCents'] for f in firms]+[e['cashAfterCents'] for f in firms for e in f['cashEvents']]),
                    'meanAccepted':mean([f['accepted'] for f in firms]),
                    'meanFinalCashCents':mean([f['cashCents'] for f in firms])}
            item['variants'][variant]={'meanEnterpriseProfitBeforeUnknownDCents':mean([r['summary']['profitCents'] for r in runs]),
                'meanEnterpriseAccepted':mean([r['summary']['enterpriseAccepted'] for r in runs]),
                'computedAIWeeklyQuoteRangeCents':span(quotes),'meanComputedAIWeeklyQuoteCents':mean(quotes),
                'computedAIQuotesBelow1600Count':sum(p<1600 for p in quotes),'computedAIQuoteCount':len(quotes),
                'acceptedAIInvoicePriceRangeCents':span(ai_prices),'acceptedAIJobCount':len(ai_prices),
                'competitorLiquidity':liquidity,
                'meanMaximumDuringServiceFundingCeilingBeforeUnknownDCents':mean([r['funding']['maximumDuringServiceFundingCeilingBeforeUnpricedDiscoveryCents'] for r in runs]),
                'meanTerminalFundingCeilingBeforeUnknownDCents':mean([r['funding']['terminal']['fundingCeilingBeforeUnpricedDiscoveryCents'] for r in runs])}
        for seed in range(3001,3025):
            example=first_divergence(records[('base',integration,choice,seed)],records[('delay13',integration,choice,seed)],seed)
            if example:divergences.append({'integrationCents':integration,'choiceModel':choice,**example})
        groups.append(item)

result={'schema':'agi-alpha-existing-history-mechanism-comparisons/v1',
    'sourceArchiveSHA256':json.loads((OUT/'completion.json').read_text())['completeRunsSHA256'],
    'method':'Arithmetic inspection of recorded histories only; no new market simulation. All four main I0/I500,deterministic/logit,adoption-only B reference cells and all24 fresh seeds are compared to their recorded undercut/delay6/delay13 counterparts.',
    'newEconomicScenarios':0,'priceScope':'Computed weekly AI quotes can be unseen; accepted AI invoice prices are reported separately.',
    'firstDivergenceMethod':'Exact pre-choice cash is reconstructed from retained event/bill order. Current-week non-delivery events precede buyer loop for these expenseDelay0/paymentDelay>0 records; current-week delivery costs are included only for preceding buyer missions. Original buyer-type input is reconstructed from the frozen semantic random key.',
    'groups':groups,'allDelay13FirstChoiceDivergences':divergences,
    'limitations':['Undercut is relative to the enterprise price and need not be cheaper than the baseline AI adaptive markdowns.',
        'The delay intervention applies to every finite provider. Reallocation can benefit one provider even when payment delay is not beneficial in general.',
        'Finite initial capital, no borrowing/interest and horizon collection drain are declared scenario assumptions, not observed market facts.',
        'All profit and funding quantities precede unknown incremental second-asset discovery cost D.']}
(OUT/'mechanism-comparisons.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'groups':groups,'firstDivergences':len(divergences),'firstExamples':divergences[:4]},indent=2))
