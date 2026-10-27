#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Mechanical commercial-first publication, after COMPLETE only.

No engine import, new worlds, price search or policy selection. Aggregation uses
all costs of independently selected trained-Beta histories, including histories
with zero useful acceptances. Alpha contrasts remain a separate reporting layer.
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import gzip
import hashlib
import json
import math
from pathlib import Path
import statistics

LANE=Path(__file__).resolve().parents[1]
PROFILE_ORDER=('burdensome','reference','efficient')
SCENARIO_LABELS={
 'reference':'Reference','beta-v2-erases-contracts':'Beta supplies contracts',
 'beta-v3-erases-all':'Beta supplies all equivalents','alpha-zero':'Zero Alpha effect',
 'alpha-harm':'Harmful Alpha effect','high-overlap':'High initial overlap',
 'sharing-adaptation-fails':'Adaptation fails','cash-delay':'Collections delayed',
 'low-repeat':'Low repeat demand','resource-cost-4x':'Resource prices x4',
 'correlated-spec-errors':'Correlated specification errors','rapid-baseline':'Rapid Beta',
 'no-demand':'No demand','high-repeat':'Repeat opportunities x6',
 'slow-beta':'Slow Beta','high-repeat-slow-beta':'High repeat / slow Beta',
 'diverse-hard':'More composed jobs','quota-tight':'Tight quotas',
 'short-alpha-life':'Short asset lifetime'
}
BUCKETS=('A','B_initial_retention','B_reuse_integration_upkeep','C','shared_setup',
         'shared_recurring_operations','FINANCIAL')

def read(path):
    return json.loads(path.read_text())

def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1048576),b''):h.update(block)
    return h.hexdigest()

def safe_div(x,n):
    return x/n if n else None

def quantile(values,p):
    if not values:return None
    x=sorted(values);position=(len(x)-1)*p;a=int(position);b=min(a+1,len(x)-1)
    return x[a]+(x[b]-x[a])*(position-a)

def distribution(values):
    return dict(n=len(values),mean=statistics.mean(values) if values else None,
                median=statistics.median(values) if values else None,
                p05=quantile(values,.05),p95=quantile(values,.95),
                minimum=min(values) if values else None,maximum=max(values) if values else None)

def identity(row):
    return row['scenario'],int(row['seed']),row['arm']

def nearly(a,b,tol=.00002):
    return abs(float(a)-float(b))<=tol

class Aggregate:
    def __init__(self,label):
        self.label=label;self.n=0;self.counts=Counter();self.profiles=Counter()
        self.closures=Counter();self.choices=Counter();self.cash=defaultdict(int)
        self.costs=defaultdict(float);self.values=defaultdict(list);self.exposure=0
        self.accepted_human=0.;self.accepted_price=0.;self.offered_price=0.;self.eligible_human=0.
        self.latency_attempt_sum=0.;self.latency_useful_sum=0.;self.queue_sum=0.
        self.customer_attempt_hours=0.;self.customer_useful_hours=0.;self.threshold=None
        self.policy_ids=set()

    def add(self,world,extra,p):
        s=world['summary'];self.n+=1;self.profiles[s['profile']]+=1;self.policy_ids.add(s['policyId'])
        jobs=world['jobs'];useful=[j for j in jobs if j['usefulAccepted']]
        technical=sum(bool(j.get('technicalAccepted')) for j in jobs)
        false=sum(bool(j.get('technicalAccepted')) and not j['usefulAccepted'] for j in jobs)
        if len(useful)!=s['accepted'] or technical!=s['technicalAccepted'] or false!=s['falsePasses']:
            raise ValueError('Acceptance denominator differs from raw job records: '+str(identity(s)))
        self.threshold=p['engineDefaults']['qualityEligibilityFalsePassMax']
        self.counts.update(usefulAccepted=len(useful),technicalAccepted=technical,falsePasses=false,
                           orders=len(jobs),opportunities=len(world['offers']),
                           worldsZeroUsefulAccepted=int(not useful),
                           worldsZeroTechnicalAccepted=int(not technical),
                           positiveProfitWorlds=int(s['completeProfitUSD']>0),
                           lossWorlds=int(s['completeProfitUSD']<0),
                           closedWorlds=int(s['closed']),cashInvalidWorlds=int(not s['cashValid']),
                           worldsWithFalsePasses=int(false>0),
                           worldsAboveTrainingFalsePassBound=int(technical>0 and false/technical>self.threshold))
        self.closures[s.get('closureReason') or 'none']+=1
        self.choices.update(o['choice'] for o in world['offers'])
        funds=world['cash']['funds']
        for key in ('collected','accrued','paid','unpaid','cash','reserve','availableOperating',
                    'baseReserve','taxReserve','warrantyReserve','receivable'):
            self.cash[key]+=funds[key+'Micros']
        self.cash['seed']+=world['cash']['seedMicros']
        for key in BUCKETS:self.costs[key]+=extra['costBucketsUSD'].get(key,0)
        if not nearly(sum(extra['costBucketsUSD'].values()),s['completeCostsUSD']):
            raise ValueError('Supplement cost buckets do not reconcile: '+str(identity(s)))
        if not nearly((funds['collectedMicros']-funds['accruedMicros'])/1e6,s['completeProfitUSD']):
            raise ValueError('Pre-tax-reserve profit does not reconcile')
        for key in ('completeProfitUSD','completeCostsUSD','collectionsUSD','cashRemainingUSD',
                    'availableOperatingUSD'):
            self.values[key].append(s[key])
        self.values['endingReservesUSD'].append(funds['reserve'])
        self.values['endingUnpaidObligationsUSD'].append(funds['unpaid'])
        self.exposure+=s.get('operatingHorizonWeeks',p['experiment']['weeks'])
        offers={o['id']:o for o in world['offers']}
        eligible=[o for o in world['offers'] if o['utilities'].get('network') is not None]
        self.counts['eligibleOfferedQuotes']+=len(eligible)
        self.values['eligibleOfferedPriceUSD'].extend(o['priceUSD'] for o in eligible)
        self.values['computedPriceAcrossOpportunitiesUSD'].extend(o['priceUSD'] for o in world['offers'])
        self.offered_price+=sum(o['priceUSD'] for o in eligible)
        self.eligible_human+=sum(o['humanReferenceUSD'] for o in eligible)
        self.counts['eligibleQuotesBelowOwnHumanReference']+=sum(o['priceUSD']<o['humanReferenceUSD'] for o in eligible)
        self.values['humanReferenceAcrossOpportunitiesUSD'].extend(o['humanReferenceUSD'] for o in world['offers'])
        customer_hours=p['buyers']['customerIntakeHours'][{'efficient':0,'reference':1,'burdensome':2}[s['profile']]]
        self.customer_attempt_hours+=len(jobs)*customer_hours
        self.customer_useful_hours+=len(useful)*customer_hours
        for job in jobs:
            days=7*(job['completionWeek']-job['week'])
            self.latency_attempt_sum+=days;self.values['allOrderTurnaroundDays'].append(days)
            allocations=job['reservation']['allocations']
            if allocations:
                queue=7*(min(a['week'] for a in allocations)-job['week'])
                self.queue_sum+=queue
            if not job['usefulAccepted']:continue
            price=job['priceUSD'];human=offers[job['id']]['humanReferenceUSD']
            self.accepted_price+=price;self.accepted_human+=human
            self.values['acceptedContractPriceUSD'].append(price)
            self.values['matchedHumanReferenceUSD'].append(human)
            self.values['customerReferenceMinusPriceUSD'].append(human-price)
            self.latency_useful_sum+=days;self.values['usefulTurnaroundDays'].append(days)
            self.counts['usefulPricedBelowOwnHumanReference']+=int(price<human)
            self.counts['usefulPricedAtOrAboveOwnHumanReference']+=int(price>=human)

    def result(self,p):
        n=self.counts['usefulAccepted'];t=self.counts['technicalAccepted'];orders=self.counts['orders']
        money={key:value/1e6 for key,value in self.cash.items()}
        money['completePreTaxReserveProfit']=money['collected']-money['accrued']
        ongoing=sum(self.costs[k] for k in ('A','B_reuse_integration_upkeep','shared_recurring_operations','FINANCIAL'))
        savings=self.accepted_human-self.accepted_price
        return dict(label=self.label,arm='trained-beta',worlds=self.n,profileMix=dict(self.profiles),
                    policyIds=sorted(self.policy_ids),counts=dict(self.counts),closureReasons=dict(self.closures),
                    buyerChoices=dict(self.choices),costBucketsUSD=dict(self.costs),
                    totalsUSD=money,
                    perEnterpriseMeansUSD={k:v/self.n for k,v in money.items()},
                    pooledUnitCostsUSD=dict(deliveryA=safe_div(self.costs['A'],n),
                        recurringOperating=safe_div(ongoing,n),fullAllocated=safe_div(money['accrued'],n),
                        fullCostDenominator=n,zeroUsefulWorldCostsIncluded=True),
                    quality=dict(usefulAcceptedPerOrder=safe_div(n,orders),
                        technicalAcceptancePerOrder=safe_div(t,orders),
                        falsePassesPerTechnicalAcceptance=safe_div(self.counts['falsePasses'],t),
                        trainingSelectionBound=self.threshold,
                        exceedsTrainingSelectionBound=(self.counts['falsePasses']/t>self.threshold) if t else None,
                        interpretation='Held-out descriptive quality; the training eligibility bound does not certify confirmation.'),
                    frequency=dict(positiveProfit=self.counts['positiveProfitWorlds']/self.n,
                        closures=self.counts['closedWorlds']/self.n,
                        cashInvalid=self.counts['cashInvalidWorlds']/self.n),
                    priceAndHumanComparison=dict(
                        eligibleOfferedPriceMeanUSD=safe_div(self.offered_price,self.counts['eligibleOfferedQuotes']),
                        matchedHumanReferenceAtEligibleQuotesMeanUSD=safe_div(self.eligible_human,self.counts['eligibleOfferedQuotes']),
                        eligibleQuotesBelowOwnHumanReferenceFraction=safe_div(self.counts['eligibleQuotesBelowOwnHumanReference'],self.counts['eligibleOfferedQuotes']),
                        acceptedContractPriceMeanUSD=safe_div(self.accepted_price,n),
                        matchedHumanReferenceMeanUSD=safe_div(self.accepted_human,n),
                        sumUsefulContractPricesUSD=self.accepted_price,
                        sumMatchedHumanReferencesUSD=self.accepted_human,
                        pooledReferenceMinusPriceSavingsUSD=savings,
                        meanReferenceMinusPriceSavingsUSD=safe_div(savings,n),
                        pooledSavingsFractionOfHumanReference=safe_div(savings,self.accepted_human),
                        usefulBelowOwnHumanReferenceFraction=safe_div(self.counts['usefulPricedBelowOwnHumanReference'],n),
                        scope='Signed modeled price difference on the same useful accepted jobs; not observed customer savings, willingness to pay or total welfare. Absolute pricing does not guarantee a discount.'),
                    service=dict(enterpriseExposureWeeks=self.exposure,
                        usefulAcceptedPerEnterpriseWeek=safe_div(n,self.exposure),
                        usefulAcceptedPerAgentWeek=safe_div(n,self.exposure*p['network']['agentCount']),
                        usefulTurnaroundMeanDays=safe_div(self.latency_useful_sum,n),
                        allOrderTurnaroundMeanDays=safe_div(self.latency_attempt_sum,orders),
                        allOrderInitialQueueMeanDays=safe_div(self.queue_sum,orders),
                        customerIntakeHoursPerUsefulOrder=safe_div(self.customer_useful_hours,n),
                        customerHoursAllAttemptsPerUsefulOutcome=safe_div(self.customer_attempt_hours,n),
                        totalCustomerHoursAcrossAttempts=self.customer_attempt_hours,
                        humanTurnaroundAssumedDays=p['engineDefaults']['humanDeliveryDays']),
                    distributions={k:distribution(v) for k,v in self.values.items()},
                    aggregation='Observed confirmation mixture; ratios use pooled sums, including all zero-useful-output world costs. Conditions are not pooled into a market distribution.')

def latex_escape(text):
    translation={'\\':r'\textbackslash{}','&':r'\&','%':r'\%','$':r'\$','#':r'\#',
                 '_':r'\_','{':r'\{','}':r'\}','~':r'\textasciitilde{}','^':r'\textasciicircum{}'}
    return ''.join(translation.get(c,c) for c in str(text))

def number(x,d=0):
    return r'\textemdash' if x is None else f'{x:,.{d}f}'

def dollars(x,d=0):
    if x is None:return r'\textemdash'
    return ('-' if x<0 else '')+r'\$'+f'{abs(x):,.{d}f}'

def percent(x):
    return r'\textemdash' if x is None else f'{100*x:.1f}'+r'\%'

def fraction(n,d):
    return f'{n:,}/{d:,}'

def table(columns,head,rows,size=r'\small'):
    out=['{'+size,r'\setlength{\tabcolsep}{4pt}',r'\begin{tabular}{@{}'+columns+r'@{}}',r'\toprule',
         ' & '.join(head)+r' \\',r'\midrule']
    out+=[' & '.join(row)+r' \\' for row in rows]
    return '\n'.join(out+[r'\bottomrule',r'\end{tabular}','}'])

def contrast_row(label,row):
    ci=row['conditionalMeanCI95']
    return [latex_escape(label),dollars(row['mean']),dollars(ci[0])+' to '+dollars(ci[1])]

def main_tex(data):
    r=data['commercialCore']['reference'];n=r['worlds'];c=r['counts'];u=r['pooledUnitCostsUSD']
    m=r['priceAndHumanComparison'];q=r['quality'];svc=r['service'];cash=r['totalsUSD']
    means=r['perEnterpriseMeansUSD'];p=data['protocolConstants'];bounds=data['alphaComparisons']['reference']
    parts=[r'\section{Commercial core before additional Alpha}\label{sec:commercial-core-results}',
        'This section evaluates the independently price-trained Beta policy, with no retained Alpha investment. '
        'The buyer can select the network, a human service, postponement or decline. '
        'Every amount below is a conditional simulation in USD: actual customer jobs and collections remain zero, '
        'and complete actual study cost remains unknown. Human work hours are assumed task breakdowns; '
        'their cost-derived service reference is not an observed consulting quotation.',
        f'The reference condition contains {n:,} independent enterprises over {p["weeks"]} operating weeks each. '
        'Its observed profile mixture is retained without reweighting. All declared delivery, research, shared operations, '
        'failed attempts, fees and refunds enter company cost, including costs in worlds that deliver no useful accepted output.',
        r'\subsection{Accepted service, price and complete cost}',
        table(r'p{0.62\linewidth}r',['Reference-condition measure','Pooled result'],[
            ['Useful / technical accepts / false passes',f'{c["usefulAccepted"]:,} / {c["technicalAccepted"]:,} / {c["falsePasses"]:,}'],
            ['Held-out false passes / technical accepts',percent(q['falsePassesPerTechnicalAcceptance'])],
            ['Eligible network quotes / recorded opportunities',fraction(c['eligibleOfferedQuotes'],c['opportunities'])],
            ['Mean eligible offered / useful accepted contract price',dollars(m['eligibleOfferedPriceMeanUSD'])+' / '+dollars(m['acceptedContractPriceMeanUSD'])],
            ['Matched human reference on the same useful outputs',dollars(m['matchedHumanReferenceMeanUSD'])],
            ['Delivery A / recurring operating / full cost per useful output',dollars(u['deliveryA'])+' / '+dollars(u['recurringOperating'])+' / '+dollars(u['fullAllocated'])],
            ['Useful output throughput per enterprise-week',number(svc['usefulAcceptedPerEnterpriseWeek'],2)],
            ['Mean useful-output / all-order turnaround, days',number(svc['usefulTurnaroundMeanDays'],1)+' / '+number(svc['allOrderTurnaroundMeanDays'],1)],
            ['Customer hours over all attempts per useful outcome',number(svc['customerHoursAllAttemptsPerUsefulOutcome'],2)]
        ]),
        r'\par\smallskip '
        'The full unit-cost denominator is the sum of useful accepted outputs; its numerator includes every '
        f'world, including {c["worldsZeroUsefulAccepted"]:,} with zero useful output. It is not an average of surviving worlds\' unit costs. '
        'Recurring operating cost includes A, reuse/integration/upkeep B, recurring company operations and financial charges; '
        'the full allocation also includes initial retention, separate research, setup and the declared opening research allowance.',
        f'On matched useful jobs, {fraction(c["usefulPricedBelowOwnHumanReference"],c["usefulAccepted"])} '
        f'({percent(m["usefulBelowOwnHumanReferenceFraction"])}) were priced below their own human reference. '
        f'The pooled signed reference-minus-price difference is {dollars(m["pooledReferenceMinusPriceSavingsUSD"])}, '
        f'or {dollars(m["meanReferenceMinusPriceSavingsUSD"])} per useful outcome '
        f'({percent(m["pooledSavingsFractionOfHumanReference"])} of the matched reference total). '
        'The price grid is absolute: a provider can have low delivery cost while quoting above the human reference on some jobs. '
        'These are hypothetical price differences, not measured customer savings or willingness to pay.',
        r'\textbf{Quality remains a separate condition.} '
        f'Training used a {percent(p["trainingFalsePassBound"])} false-pass eligibility bound; it does not certify held-out reliability. '
        f'The reference held-out pooled rate is {percent(q["falsePassesPerTechnicalAcceptance"])}. '
        'The condition appendix reports the same measure for every stress, including correlated specification errors.',
        r'\subsection{Finite company economics and profile sensitivity}',
        table(r'p{0.42\linewidth}rr',['Reference-condition financial measure','All worlds','Mean / enterprise'],[
            ['Gross modeled collections',dollars(cash['collected']),dollars(means['collected'])],
            ['Declared complete accrued costs',dollars(cash['accrued']),dollars(means['accrued'])],
            ['Complete profit before tax reserve',dollars(cash['completePreTaxReserveProfit']),dollars(means['completePreTaxReserveProfit'])],
            ['Spendable operating-generated funds',dollars(cash['availableOperating']),dollars(means['availableOperating'])],
            ['Ending cash, seed included',dollars(cash['cash']),dollars(means['cash'])],
            ['Ending reserves / unpaid obligations',dollars(cash['reserve'])+' / '+dollars(cash['unpaid']),dollars(means['reserve'])+' / '+dollars(means['unpaid'])]
        ]),
        r'\par\smallskip '
        f'Positive complete profit occurs in {fraction(c["positiveProfitWorlds"],n)} worlds; '
        f'{fraction(c["closedWorlds"],n)} close and {fraction(c["cashInvalidWorlds"],n)} incur insolvency. '
        'Closure reasons are retained separately from insolvency: preserving reserves can cause a financially forced stop, '
        'and exhausted operational capacity can also stop new business. Totals across histories are accounting aggregates, '
        'not one enterprise\'s pooled bank account.',
        r'Profit is collected receipts minus declared accrued expenses. The tax reserve is not a paid tax expense; '
        r'reserves reduce spendable funds without being subtracted twice from profit. Seed is financing, never revenue. '
        r'Terminal figures include the declared settlement and warranty runoff. Demand, collection, quality, trust and prices remain assumptions.',
        table('lrrrrrr',['Reference profile','Worlds','Useful','Full / useful','Profit / world','Positive','False-pass rate'],[
            [latex_escape(profile.title()),str(x['worlds']),number(x['counts']['usefulAccepted']),dollars(x['pooledUnitCostsUSD']['fullAllocated']),
             dollars(x['perEnterpriseMeansUSD']['completePreTaxReserveProfit']),fraction(x['counts']['positiveProfitWorlds'],x['worlds']),
             percent(x['quality']['falsePassesPerTechnicalAcceptance'])]
            for profile,x in data['commercialCore']['referenceProfiles'].items()
        ],r'\footnotesize'),
        r'\par\smallskip '
        'These profiles jointly change execution assumptions and the human-hours reference; they are not isolated causal estimates '
        'of one parameter. The full 19-condition table prevents a favorable profile from substituting for the complete campaign.',
        r'\subsection{What retained Alpha adds, reported separately}',
        'A viable ordinary service does not establish useful retention. The following paired reference-condition comparisons '
        'include all delivery, retention, separate research and business costs:',
        table(r'p{0.49\linewidth}rr',['Complete-profit contrast','Mean','Conditional 95\\% interval'],[
            contrast_row('Network Alpha minus matched-price Beta',bounds['incrementalAlphaMovingUSD']),
            contrast_row('Network Alpha minus independently trained Beta',bounds['trainedWholePolicyUSD']),
            contrast_row('Network availability minus private availability',bounds['sharingVersusPrivateUSD'])
        ],r'\footnotesize'),
        r'\par\smallskip '
        'The first comparison isolates optional retention under the selected Alpha pricing controller; the second compares independently '
        'selected whole policies; the third concerns the availability ablation. Intervals describe Monte Carlo variation conditional on '
        'the assumed model, not empirical uncertainty about real demand or frontier competence. Graph-specific economic superiority is not isolated. '
        'A positive service margin, positive Alpha value, net sharing benefit and operating-funded succession remain different claims. '
        'The fixed 20-day human delivery assumption and asymmetric hard precision gate are explicit limitations in the buyer-threshold appendix.'
    ]
    return '\n\n'.join(parts)+'\n'

def appendix_tex(data):
    rows=[]
    for sid,x in data['commercialCore']['allScenarios'].items():
        c=x['counts'];m=x['priceAndHumanComparison']
        rows.append([latex_escape(SCENARIO_LABELS.get(sid,sid)),number(c['usefulAccepted']),
                     dollars(m['acceptedContractPriceMeanUSD'])+' / '+dollars(m['matchedHumanReferenceMeanUSD']),
                     dollars(x['pooledUnitCostsUSD']['fullAllocated']),
                     dollars(x['perEnterpriseMeansUSD']['completePreTaxReserveProfit']),
                     fraction(c['positiveProfitWorlds'],x['worlds']),fraction(c['closedWorlds'],x['worlds']),
                     percent(x['quality']['falsePassesPerTechnicalAcceptance'])])
    return '\n\n'.join([
        r'\section{All prespecified commercial-core conditions}\label{app:commercial-core-conditions}',
        'Every row is independently trained Beta without retained Alpha. Price and human reference are acceptance-weighted on the same useful jobs. '
        'Full cost divides all company costs, including zero-output worlds, by useful acceptances. Profit is the mean per enterprise before the tax reserve. '
        'A dash denotes an undefined denominator, not zero cost or certified quality. Positive-profit and closure columns retain frequencies.',
        r'{\scriptsize\setlength{\tabcolsep}{3pt}',
        r'\resizebox{\linewidth}{!}{%',
        table('lrrrrrrr',['Condition','Useful','Price / human','Full / useful','Profit / world','Positive','Closed','False / tech'],rows,r'\scriptsize'),
        '}','}',
        r'\par\smallskip '
        'False-pass rates use technical accepts as denominator and are held-out observations inside the simulation. '
        'The training selection bound is not a confirmation certificate. Conditions are sensitivity interventions, '
        'not samples from a market distribution; their outcomes are not pooled into an expected market profit. '
        'The JSON companion preserves offered-price distributions, customer-effort and latency measures, reserves, closure reasons, '
        'all three cost layers, profile composition and separate Alpha contrasts for every condition.'
    ])+'\n'

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--publish',action='store_true')
    ap.add_argument('--results',type=Path,default=LANE/'results/primary');args=ap.parse_args()
    if not args.publish:
        print(json.dumps(dict(status='NOT_RUN',classification='PUBLICATION_ONLY',requires='COMPLETE summary plus analysis.json and reporting-supplement.json; explicit --publish.')));return
    paths=dict(protocol=LANE/'protocol.json',summary=args.results/'summary.json',
               analysis=LANE/'analysis/analysis.json',supplement=LANE/'analysis/reporting-supplement.json',
               worlds=args.results/'worlds.jsonl.gz',trainingFreeze=args.results/'training-selection-freeze.json',
               sourceFreeze=LANE/'protocol/source-freeze.json')
    missing=[str(path) for path in paths.values() if not path.exists()]
    if missing:raise SystemExit('Refusing incomplete inputs; missing '+', '.join(missing))
    campaign=read(paths['summary'])
    if campaign.get('status')!='COMPLETE':raise SystemExit('Refusing partial or unqualified campaign; COMPLETE is required.')
    p=read(paths['protocol']);analysis=read(paths['analysis']);supplement=read(paths['supplement'])
    chosen=read(paths['trainingFreeze']);freeze=read(paths['sourceFreeze'])
    if p['status']!='FROZEN_BEFORE_OUTCOMES':raise ValueError('Frozen protocol required')
    if analysis['sourceSummarySHA256']!=digest(paths['summary']):raise ValueError('Analysis is not bound to this completed summary')
    if freeze['protocolSHA256']!=digest(paths['protocol']):raise ValueError('Protocol differs from source freeze')
    if supplement.get('changesEconomicOutcomes') is not False:raise ValueError('Supplement must be a reporting-only correction')
    if campaign['trainingHistories']!=p['experiment']['trainingHistories'] or campaign['confirmationHistories']!=p['experiment']['confirmationHistories']:
        raise ValueError('Campaign does not contain the declared history counts')
    if chosen['confirmationHistoriesAlreadyRun']!=0:raise ValueError('Training selection must predate confirmation')
    beta_id=campaign['selection']['bestBeta']['policy']['id']
    if beta_id!=chosen['selectedRuleIds']['bestBeta']:raise ValueError('Independently selected Beta policy changed')
    rowmap={identity(x):x for x in campaign['rows']}
    extra={identity(x):x for x in supplement['worlds']}
    if len(rowmap)!=len(campaign['rows']) or set(rowmap)!=set(extra) or len(extra)!=len(supplement['worlds']):
        raise ValueError('Summary/supplement history identities are missing or duplicated')
    scenario_ids=[x['id'] for x in p['scenarios']]
    if len(scenario_ids)!=19:raise ValueError('This publication requires the declared 19-condition design')
    all_groups={sid:Aggregate(sid) for sid in scenario_ids}
    profile_groups={profile:Aggregate('reference|'+profile) for profile in PROFILE_ORDER}
    seen=set()
    with gzip.open(paths['worlds'],'rt') as stream:
        for line in stream:
            world=json.loads(line);s=world['summary'];key=identity(s)
            if key in seen or key not in rowmap or rowmap[key]!=s:raise ValueError('Raw history differs from completed summary: '+str(key))
            seen.add(key)
            if s['arm']!='trained-beta':continue
            if s['policyId']!=beta_id:raise ValueError('Commercial core substituted another price policy')
            if extra[key]['profile']!=s['profile']:raise ValueError('Profile binding differs')
            all_groups[s['scenario']].add(world,extra[key],p)
            if s['scenario']=='reference':profile_groups[s['profile']].add(world,extra[key],p)
    if seen!=set(rowmap):raise ValueError('Incomplete raw confirmation histories')
    expected=len(p['experiment']['confirmationSeeds'])
    if any(group.n!=expected for group in all_groups.values()):raise ValueError('Missing trained-Beta history in a condition')
    commercial={sid:group.result(p) for sid,group in all_groups.items()}
    alpha_quality={}
    for sid in scenario_ids:
        alpha_quality[sid]={}
        for arm in ('moving-beta-only','network-alpha','private-alpha-availability-ablation','trained-beta'):
            rows=[r for r in campaign['rows'] if r['scenario']==sid and r['arm']==arm]
            technical=sum(r['technicalAccepted'] for r in rows);false=sum(r['falsePasses'] for r in rows)
            alpha_quality[sid][arm]=dict(worlds=len(rows),usefulAccepted=sum(r['accepted'] for r in rows),
                technicalAccepted=technical,falsePasses=false,falsePassRate=safe_div(false,technical),
                admittedAssets=sum(r['admittedAssets'] for r in rows),assetUses=sum(r['assetUses'] for r in rows))
    bound=[dict(name=name,path=str(path.relative_to(LANE.parent)),sha256=digest(path)) for name,path in paths.items()]
    data=dict(schema='beyond-beta-commercial-core/v1',classification='POST_FREEZE_MECHANICAL_COMMERCIAL_FIRST_REPORTING',
              createdAtUtc=datetime.now(timezone.utc).isoformat(),sourceFreezeId=freeze['sourceId'],
              boundInputs=bound,scriptSha256=digest(Path(__file__)),economicWorldsExecuted=0,changesEconomicOutcomes=False,
              actualCustomerJobs=0,actualRevenueUSD=0,actualCompleteStudyCostUSD=None,
              selectedBetaPolicy=campaign['selection']['bestBeta']['policy'],
              protocolConstants=dict(weeks=p['experiment']['weeks'],agents=p['network']['agentCount'],
                  trainingFalsePassBound=p['engineDefaults']['qualityEligibilityFalsePassMax'],
                  humanTurnaroundAssumedDays=p['engineDefaults']['humanDeliveryDays'],
                  initialSeedUSD=p['company']['seedUsd'],baseReserveUSD=p['company']['reserveUsd']),
              commercialCore=dict(reference=commercial['reference'],
                  referenceProfiles={key:value.result(p) for key,value in profile_groups.items()},
                  allScenarios=commercial),
              alphaComparisons=analysis['paired'],alphaQuality=alpha_quality,
              limitations=[
                  'All commercial outcomes are conditional simulations; actual demand and willingness to pay remain unknown.',
                  'Full cost is the declared complete-category scenario cost, not measured actual provider or study expenditure.',
                  'All zero-useful-output worlds retain their costs in pooled unit-cost numerators.',
                  'Cost, price, collections, human reference and customer price difference are distinct quantities.',
                  'Absolute pricing does not require a discount to human replacement cost.',
                  'Human hours are assumed WBS values and the human-service price is cost-derived, not a consulting quotation.',
                  'Profit is before the tax reserve; reserves reduce spendable funds without a second expense.',
                  'Held-out false-pass rates are not certified by training eligibility.',
                  'Nineteen conditions are not a probability-weighted market distribution.',
                  'Static human timing and asymmetric quality screening remain primary buyer-model limitations.'
              ])
    outputs={LANE/'analysis/commercial-core.json':json.dumps(data,ensure_ascii=False,separators=(',',':'))+'\n',
             LANE/'publication/commercial-results.tex':main_tex(data),
             LANE/'publication/commercial-scenarios.tex':appendix_tex(data)}
    if any(path.exists() for path in outputs):raise FileExistsError('Preserve existing reporting artifacts; version any correction explicitly.')
    for path,content in outputs.items():path.parent.mkdir(parents=True,exist_ok=True);path.write_text(content)
    print(json.dumps(dict(status='PUBLISHED_MECHANICALLY',conditions=19,referenceProfiles=3,
          commercialHistories=sum(g.n for g in all_groups.values()),economicWorldsExecuted=0,
          files=[str(path) for path in outputs])))

if __name__=='__main__':main()
