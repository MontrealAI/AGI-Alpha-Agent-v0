import argparse, collections, datetime, gzip, hashlib, json, math, pathlib, statistics, sys

root=pathlib.Path(__file__).resolve().parents[1]
market=root/'market'
parser=argparse.ArgumentParser(description='Independently reconcile every supplied enterprise history, funding event and aggregate. Existing audit receipts are never overwritten.')
parser.add_argument('results',nargs='?',type=pathlib.Path,default=market/'results/primary-01',help='Completed campaign directory containing complete-runs.jsonl.gz and its manifests')
parser.add_argument('output',nargs='?',type=pathlib.Path,default=root/'review/frozen-outcome-audit.json',help='New JSON report path; must not already exist')
campaign=parser.add_mutually_exclusive_group()
campaign.add_argument('--exploratory',action='store_true',help='Audit the 206-configuration postprimary exploration')
campaign.add_argument('--policy-diagnostic',action='store_true',help='Audit the 160-configuration post-exploratory policy diagnostic and its matched prior histories')
campaign.add_argument('--deployment-robustness',action='store_true',help='Audit the 128-configuration fresh-seed deployment and funding-ceiling extension')
args=parser.parse_args()
results,out=args.results,args.output
exploratory,policy_diagnostic=args.exploratory,args.policy_diagnostic
deployment=args.deployment_robustness
if out.exists(): parser.error(f'Refusing to overwrite prior audit receipt: {out}. Choose a new output path.')
expected_configs,expected_seeds=(128,24) if deployment else (160,12) if policy_diagnostic else (206,12) if exploratory else (87,24)
freeze_path=market/('deployment-robustness/freeze.json' if deployment else 'policy-diagnostic/freeze.json' if policy_diagnostic else 'exploratory/freeze.json' if exploratory else 'protocol/freeze.json')
checks=collections.Counter()
failures=[]
failure_count=0
context='closure'
def ck(ok,name,detail=None):
    global failure_count
    checks[name]+=1
    if not ok:
        failure_count+=1
        if len(failures)<50: failures.append({'context':context,'check':name,'detail':detail})
def same(actual,expected,name): ck(actual==expected,name,{'actual':actual,'expected':expected} if actual!=expected else None)
def close(actual,expected,name): ck(math.isclose(actual,expected,rel_tol=1e-10,abs_tol=1e-6),name,{'actual':actual,'expected':expected} if not math.isclose(actual,expected,rel_tol=1e-10,abs_tol=1e-6) else None)
def digest(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for block in iter(lambda:f.read(1<<20),b''): h.update(block)
    return h.hexdigest()
def jsround(x): return math.floor(x+0.5)
freeze=json.loads(freeze_path.read_text())
completion=json.loads((results/'completion.json').read_text())
summary=json.loads((results/'summary.json').read_text())
configurations=json.loads((results/'configurations.json').read_text())
configs={c['id']:c for c in configurations}
same(len(configs),expected_configs,'declared configuration count')
same(len(summary['seeds']),expected_seeds,'declared seed count')
same(completion['completed'],True,'campaign completion')
for f in freeze['files']:
    p=market/f['path']
    same(p.stat().st_size,f['bytes'],'frozen source byte length')
    same(digest(p),f['sha256'],'frozen source digest')
same(digest(results/'complete-runs.jsonl.gz'),completion['completeRunsSHA256'],'complete outcome archive digest')
same(digest(results/'summary.json'),completion['summarySHA256'],'aggregate summary digest')
same(digest(freeze_path),summary['freezeSHA256'],'summary binds source freeze')
if exploratory:
    same(summary['status'],'POSTPRIMARY_EXPLORATORY_NOT_CONFIRMATION','exploratory results not relabeled confirmatory')
    same(summary['originalPrimaryPreserved'],True,'primary result preservation declared')
if deployment:
    same(summary['status'],'FRESH_SEED_USER_AUTHORIZED_EXTENSION','fresh extension status explicit')
    same(summary['allPreviousCampaignsPreserved'],True,'all earlier campaigns preserved')
    same(summary['seeds'],list(range(3001,3025)),'exact new seed set')
    same(summary['actualSecondInvestments'],0,'no second asset purchase without qualification')
    same(summary['unpricedIncrementalDiscoveryCostCents'],None,'new discovery cost remains unknown')
    same(completion['budgetsSatisfied'],True,'declared scientific budget satisfied')
    same(completion['cutoffSatisfied'],True,'declared scientific cutoff satisfied')
    same(completion['mode'],'ORIGINAL_BOUNDED_RESEARCH','original bounded extension mode')
    same(completion['configurations'],128,'bounded configuration count in completion')
    same(completion['pairedWorlds'],3072,'bounded paired-world count in completion')
    same(completion['enterpriseRuns'],9216,'bounded enterprise count in completion')
    same(completion['competitorFirmAccounts'],18432,'bounded competitor count in completion')
    same(completion['actualSecondInvestments'],0,'completion has no second purchase')
    same(completion['observedCollectionsCents'],0,'extension no observed collections')
    same(completion['actualTransactions'],0,'extension no actual financial transaction')
    ck(completion['resources']['wallSeconds']<=120 and completion['resources']['cpuSeconds']<=120,'finite market CPU and wall envelope')
    gate_digest=digest(root/'review/second-capability-gate.json')
if policy_diagnostic:
    same(summary['status'],'POST_EXPLORATORY_POLICY_DIAGNOSTIC','policy diagnosis not relabeled confirmatory')
    same(summary['allPriorResultsPreserved'],True,'all prior result preservation declared')
    prior_dir=market/'exploratory/results-01'
    prior_completion=json.loads((prior_dir/'completion.json').read_text())
    same(digest(prior_dir/'complete-runs.jsonl.gz'),prior_completion['completeRunsSHA256'],'matched prior archive digest')
    prior_rows={}
    with open(prior_dir/'outcomes.jsonl') as f:
        for line in f:
            row=json.loads(line);prior_rows[(row['scenario'],row['seed'],row['arm'])]=row
    prior_identities={}
    needed_prior={row['priorHeuristicScenario'] for row in summary['scenarios']}
    def opportunity_fingerprint(run):
        pairs=sorted((x['mission'],x['choice']=='unsupported') for x in run['histories']['buyerChoices'])
        return hashlib.sha256(json.dumps(pairs,separators=(',',':')).encode()).hexdigest()
    with gzip.open(prior_dir/'complete-runs.jsonl.gz','rt') as f:
        for line in f:
            pair=json.loads(line)
            if pair['config']['id'] in needed_prior:
                for arm,run in pair['arms'].items():
                    prior_identities[(pair['config']['id'],pair['seed'],arm)]=opportunity_fingerprint(run)
expected_assets={
    'B':('useful-work-v2-retained-producer','0b4eb1ae2392176ff61ef91b7da0d13df3c6400ee0b3e317439238881adc182d'),
    'C':('useful-work-v2-conventional-producer','cd28579ecf72eba5bdfffa6b3b5483aaaa960322989d2a2369da5431062207ba')}
seen=set()
records=collections.defaultdict(list)
totals=collections.Counter()
def price_range(values):
    return {'minimumCents':min(values),'maximumCents':max(values)} if values else None
def combine_ranges(ranges):
    return price_range([x[k] for x in ranges if x is not None for k in ('minimumCents','maximumCents')])

def audit_run(r,scenario,seed,arm):
    global context
    context=f'{scenario}:{seed}:{arm}'
    c=r['config'];s=r['summary'];h=r['histories']
    same(c,configs[scenario],'run uses declared exact configuration')
    same(r['seed'],seed,'arm seed identity')
    same(r['arm'],arm,'arm identity')
    same(r['basis'],'SIMULATED','market basis explicit')
    same(r['observedCustomerCollectionsCents'],0,'no observed customer collections')
    same(s['actualRevenueCents'],0,'no actual revenue')
    same(r['nextInvestment']['actualFinancialAction'],False,'no actual financial action')
    same(r['nextInvestment']['action'],'retain-reserves','no untested successor purchase')
    jobs={j['id']:j for j in h['jobs']}
    same(len(jobs),len(h['jobs']),'unique simulated mission identities')
    own=[j for j in h['jobs'] if j['provider']=='enterprise']
    same(len(own),s['enterpriseAttempts'],'enterprise attempts reconstructed')
    same(sum(j['accepted'] for j in own),s['enterpriseAccepted'],'enterprise acceptance reconstructed')
    same(sum(not j['accepted'] for j in own),s['enterpriseRejected'],'enterprise rejection reconstructed')
    same(sum(j['accepted'] and not j['qualityGood'] for j in own),s['latentFailures'],'latent failures reconstructed')
    bills=h['bills'];invoices=h['invoices'];cash=h['cash']
    same(len({b['id'] for b in bills}),len(bills),'unique bill identities')
    same(len({i['id'] for i in invoices}),len(invoices),'unique invoice identities')
    total_bills=sum(b['amountCents'] for b in bills)
    paid_bills=sum(b['amountCents'] for b in bills if b['paid'])
    unpaid_bills=total_bills-paid_bills
    gross_invoices=sum(i['amountCents'] for i in invoices)
    collections_total=sum(i['amountCents'] for i in invoices if i['status']=='collected')
    defaults=sum(i['amountCents'] for i in invoices if i['status']=='defaulted')
    pending=sum(i['amountCents'] for i in invoices if i['status']=='pending')
    same(total_bills,s['accruedCostsCents'],'accrual expense sum')
    same(paid_bills,s['paidCostsCents'],'cash expense sum')
    same(unpaid_bills,s['obligationsCents'],'unpaid obligations sum')
    same(gross_invoices,s['grossInvoicesCents'],'invoice sum')
    same(collections_total,s['grossCollectionsCents'],'collections sum')
    same(defaults,s['writtenOffCents'],'uncollectible sum')
    same(gross_invoices,collections_total+defaults+pending,'receivable conservation')
    same(s['profitCents'],gross_invoices-defaults-total_bills,'accrual profit from invoices and expenses')
    same(s['profitCents'],s['finalCashCents']+pending-unpaid_bills-c['initialCashCents'],'equity conservation excludes opening finance')
    balance=c['initialCashCents'];used_payments=set();used_collections=set()
    billmap={b['id']:b for b in bills};invoicemap={i['id']:i for i in invoices}
    for e in cash:
        ck(isinstance(e['amountCents'],int),'integer cash event amount')
        balance+=e['amountCents']
        same(balance,e['cashAfterCents'],'cash balance after every event')
        ck(balance>=0,'no negative cash spending')
        ref=e['reference']
        if e['amountCents']<0:
            ck(ref not in used_payments,'bill paid at most once');used_payments.add(ref)
            ck(ref in billmap,'cash payment references bill')
            if ref in billmap:
                b=billmap[ref]
                same(-e['amountCents'],b['amountCents'],'payment equals bill amount')
                same(e['week'],b['paidWeek'],'payment week matches liability settlement')
                ck(e['week']>=b['dueWeek'],'bill not paid before declared due week')
        else:
            ck(ref not in used_collections,'invoice collected at most once');used_collections.add(ref)
            ck(ref in invoicemap,'collection references invoice')
            if ref in invoicemap:
                i=invoicemap[ref]
                same(e['amountCents'],i['amountCents'],'collection equals invoice amount')
                same(e['week'],i['collectedWeek'],'collection week matches invoice')
                ck(e['week']>=i['dueWeek'],'collection not before due date')
    same(balance,s['finalCashCents'],'terminal cash balance')
    same(c['initialCashCents']+collections_total-paid_bills,balance,'independent terminal cash equation')
    for i in invoices:
        ck(i['mission'] in jobs,'invoice mission exists')
        j=jobs[i['mission']]
        same(j['provider'],'enterprise','enterprise invoice provider identity')
        same(j['accepted'],True,'rejected mission never invoiced')
        same(j['priceCents'],i['amountCents'],'invoice equals agreed price')
        same(j['week'],i['week'],'invoice timing equals accepted delivery')
    for b in h['balances']:
        same(b['cashCents']-c['initialCashCents'],b['cumulativeCollectionsCents']-b['paidCostsCents'],'weekly cash conservation')
        same(b['availableCashCents'],b['cashCents']-b['obligationsCents']-b['reserveCents'],'reserve encumbrance distinct from expense')
        same(b['earnedAvailableCents'],min(b['availableCashCents'],b['cumulativeCollectionsCents']-b['accruedCostsCents']-b['reserveCents']),'earned funds exclude initial seed and invoices')
    for b in h['buyerProcurement']:
        committed=sum(j['priceCents'] for j in h['jobs'] if j['buyer']==b['id'] and j['invoiceCreated'])
        same(committed,b['committedCents'],'buyer commitments from accepted invoices')
        ck(b['committedCents']<=b['budgetCents'],'finite buyer budget binds')
    choices={x['mission']:x for x in h['buyerChoices']}
    same(len(choices),len(h['buyerChoices']),'unique buyer opportunity identity')
    same(len(choices),s['opportunities'],'simulated opportunity count')
    same(sum(x['choice']!='unsupported' for x in choices.values()),s['supportedOpportunities'],'supported opportunity count')
    same(sum(x['choice']=='defer' for x in choices.values()),s['declined'],'outside option count')
    for j in h['jobs']:
        same(choices[j['id']]['choice'],j['provider'],'delivered provider chosen by buyer')
        ck(0<=j['probabilityAssumption']<=1,'quality probability bounded')
        if not j['accepted']: same(j['invoiceCreated'],False,'rejection has no invoice')
    for i in h['investments']:
        ck(i['availableCashCents']>=i['fullCostCents'],'investment affordability from declared available funds')
        ck(i['remainingUsesForecast']>=0,'nonnegative investment forecast')
        ck(i['expectedNetBenefitCents']>0,'investment has positive declared forecast')
        for j in own:
            if i['success']: ck(not(i['week']<=j['week']<i['availableWeek']),'service pauses during successful adoption')
            else: same(j['assetUsed'],None,'immediate failed integration never activates asset')
            if j['assetUsed']: ck(j['week']>=i['availableWeek'],'no asset use before availability')
        cap=[(idx,b) for idx,b in enumerate(bills) if b['category']=='capability' and b['reference']==i['asset']['sha256'] and b['week']==i['week']]
        if i['fullCostCents']>0:
            same(len(cap),1,'one capability payment liability')
            if len(cap)==1:
                bi,b=cap[0]
                events=[(ei,e) for ei,e in enumerate(cash) if e['reference']==b['id']]
                same(len(events),1,'capability paid exactly once')
                if len(events)==1:
                    ei,e=events[0]
                    cash_before=e['cashAfterCents']-e['amountCents']
                    prior_unpaid=sum(x['amountCents'] for x in bills[:bi] if not x['paid'] or x['paidWeek']>i['week'])
                    prior_cost=sum(x['amountCents'] for x in bills[:bi])
                    prior_collections=sum(x['amountCents'] for x in cash[:ei] if x['amountCents']>0)
                    available=cash_before-prior_unpaid-c['reserveCents']
                    if i['funding']=='operating-surplus': available=min(available,prior_collections-prior_cost-c['reserveCents'])
                    same(i['availableCashCents'],available,'investment funding independently reconstructed at event time')
                    ck(cash_before-prior_unpaid-c['reserveCents']>=i['fullCostCents'],'investment preserves preexisting encumbrances and reserve')
    assetjobs=[j for j in own if j['assetUsed']]
    same(len(assetjobs),s['assetUses'],'asset-use count')
    for j in assetjobs:
        same((j['assetUsed'],j['sourceAssetSHA256']),expected_assets[arm],'financed exact asset identity')
    unit=jsround((c['commonResidualMinutes']+c['ordinaryFinalizationMinutes'])*c['hourlyProviderCents']/60)+c['computeAndToolCents']
    direct=sum(jsround(unit*(1 if j['qualityGood'] else c['failureCorrectionMultiplier']))-j['deliveryCostCents'] for j in assetjobs)
    asset_cost=sum(b['amountCents'] for b in bills if b['category'] in ('capability','maintenance'))
    same(direct,s['directAvoidedCostCents'],'direct fixed-task saving uses correction multiplier')
    same(asset_cost,s['assetFullCostAndUpkeepCents'],'complete scenario asset cost plus upkeep')
    same(direct-asset_cost,s['directNetSavingCents'],'direct saving net of complete asset charge')
    same(bool(assetjobs) and direct>=asset_cost,s['directCostPayback'],'direct cost repayment classification')
    same(r['exactAssetDirectCostRepayment']['jobBreakEvenReuses'],None,'cohort repayment not mislabeled as job threshold')
    for projection in (r['canonical']['economic'],r['canonical']['cash']):
        same(projection['summary']['observed']['revenue'],0,'canonical observed collections zero')
        for e in projection['ledger']['events']:
            if e['type']=='revenue' and e['category']=='collected': same(e['amountMinor'],0,'no simulated receipt promoted to observed')
            if e['type']=='revenue' and e['category']=='price': same(e['basis'],'assumed','market price stays assumed')
    if arm=='A':
        same(s['assetUses'],0,'ordinary arm no selected investment')
        same(len(h['investments']),0,'ordinary arm investment disabled')
    totals['enterprise_histories']+=1
    totals['simulated_jobs_all_providers']+=len(h['jobs'])
    totals['enterprise_attempts']+=len(own)
    totals['cash_events']+=len(cash)
    totals['invoices']+=len(invoices)
    totals['bills']+=len(bills)
    totals['investment_events']+=len(h['investments'])

def audit_competitor(run,identifier,firm):
    global context
    c=run['config'];h=run['histories'];context=f"{c['id']}:{run['seed']}:{run['arm']}:competitor:{identifier}"
    jobs=[j for j in h['jobs'] if j['provider']==identifier];jobmap={j['id']:j for j in jobs}
    bills=firm['bills'];invoices=firm['invoices'];events=firm['cashEvents']
    billmap={b['id']:b for b in bills};invoicemap={i['id']:i for i in invoices}
    same(firm['id'],identifier,'native competitor identity')
    same(firm['openingCashCents'],c['competitorInitialCashCents'],'native competitor finite opening cash')
    same(firm['balanceHistory'],[],'native empty competitor weekly array retained honestly')
    same(len(billmap),len(bills),'native competitor unique liabilities')
    same(len(invoicemap),len(invoices),'native competitor unique invoices')
    same(firm['attempts'],len(jobs),'native competitor attempts from jobs')
    same(firm['accepted'],sum(j['accepted'] for j in jobs),'native competitor accepted jobs')
    same(firm['rejected'],sum(not j['accepted'] for j in jobs),'native competitor rejected jobs')
    same(firm['latentFailures'],sum(j['accepted'] and not j['qualityGood'] for j in jobs),'native competitor latent failures')
    accrued=sum(b['amountCents'] for b in bills);paid=sum(b['amountCents'] for b in bills if b['paid']);unpaid=accrued-paid
    gross=sum(i['amountCents'] for i in invoices);collected=sum(i['amountCents'] for i in invoices if i['status']=='collected')
    defaults=sum(i['amountCents'] for i in invoices if i['status']=='defaulted');pending=sum(i['amountCents'] for i in invoices if i['status']=='pending')
    same(firm['grossInvoicesCents'],gross,'native competitor gross invoices')
    same(firm['grossCollectionsCents'],collected,'native competitor actual modeled collections')
    same(firm['writtenOffCents'],defaults,'native competitor defaults')
    same(gross,collected+defaults+pending,'native competitor receivable conservation')
    same(sum(firm['costs'].values()),accrued,'native competitor accrued expense sum')
    same(sum(firm['paidCosts'].values()),paid,'native competitor paid expense sum')
    for category,amount in firm['costs'].items(): same(amount,sum(b['amountCents'] for b in bills if b['category']==category),'native competitor expense category')
    for category,amount in firm['paidCosts'].items(): same(amount,sum(b['amountCents'] for b in bills if b['category']==category and b['paid']),'native competitor paid category')
    balance=firm['openingCashCents'];payment_indices={};collection_ids=set();last_week=-1
    for index,event in enumerate(events):
        ck(event['week']>=last_week,'native competitor event chronology');last_week=event['week']
        ck(isinstance(event['amountCents'],int),'native competitor integer cash event')
        balance+=event['amountCents'];same(balance,event['cashAfterCents'],'native competitor every cash balance');ck(balance>=0,'native competitor no negative cash')
        if event['type']=='simulated_collection':
            ck(event['reference'] not in collection_ids,'native competitor invoice collected once');collection_ids.add(event['reference'])
            invoice=invoicemap[event['reference']]
            same(event['amountCents'],invoice['amountCents'],'native competitor collection matches invoice')
            same(invoice['status'],'collected','native competitor invoice status')
            same(event['week'],invoice['collectedWeek'],'native competitor collection date')
            ck(event['week']>=invoice['dueWeek'],'native competitor collection not early')
        else:
            ck(event['reference'] not in payment_indices,'native competitor bill paid once');payment_indices[event['reference']]=index
            bill=billmap[event['reference']]
            same(event['amountCents'],-bill['amountCents'],'native competitor payment matches liability')
            same(bill['paid'],True,'native competitor paid liability flag')
            same(event['week'],bill['paidWeek'],'native competitor payment date')
            ck(event['week']>=bill['dueWeek'],'native competitor liability not paid early')
    same(balance,firm['cashCents'],'native competitor terminal cash')
    same(balance,firm['openingCashCents']+collected-paid,'native competitor independent cash equation')
    same(balance+pending-unpaid-firm['openingCashCents'],gross-defaults-accrued,'native competitor equity excludes seed')
    expected={'cashCents':balance,'accepted':firm['accepted'],'insolvent':firm['insolvent'],'collectionsCents':collected,'accruedCostCents':accrued}
    same(run['competitorSummary'][identifier],expected,'native competitor summary agrees with detailed state')
    invoice_count=collections.Counter();delivery_cost=collections.Counter()
    for invoice in invoices:
        j=jobmap[invoice['mission']];invoice_count[invoice['mission']]+=1
        same(j['accepted'],True,'rejected competitor work has no invoice')
        same(j['priceCents'],invoice['amountCents'],'native competitor agreed price')
        same(j['week'],invoice['week'],'native competitor invoice on delivery')
    for bill in bills:
        ck(isinstance(bill['amountCents'],int) and bill['amountCents']>=0,'native competitor nonnegative liability')
        ck(bill['dueWeek']>=bill['week'],'native competitor liability due after accrual')
        if bill['category']=='delivery': delivery_cost[bill['reference']]+=bill['amountCents']
        if bill['category']=='refund':
            invoice=invoicemap[bill['reference']]
            same(invoice['status'],'collected','native competitor refund requires prior collection')
            same(invoice['refund'],True,'native competitor declared refund obligation')
            same(bill['amountCents'],invoice['amountCents'],'native competitor refund amount')
            same(bill['week'],invoice['collectedWeek'],'native competitor refund accrual date')
            same(bill['dueWeek'],bill['week']+c['refundDelayWeeks'],'native competitor refund due date')
    for j in jobs:
        same(invoice_count[j['id']],int(j['accepted']),'only accepted competitor jobs invoiced once')
        same(delivery_cost[j['id']],j['deliveryCostCents'],'native competitor job cost charged')
        if firm['insolvent']: ck(j['week']<=firm['insolventWeek'],'native competitor stops after insolvency')
    for count in collections.Counter(j['week'] for j in jobs).values(): ck(count<=c['humanSlotsPerWeek' if identifier=='human' else 'aiSlotsPerWeek'],'native competitor capacity binds')
    automation=[a for a in h['competitorActions'] if a['provider']==identifier and a['action']=='adopt-automation']
    capital=[(n,b) for n,b in enumerate(bills) if b['category']=='capability']
    same(len(capital),sum(a['costCents']>0 for a in automation),'native competitor automation liability count')
    for n,bill in capital:
        ck(bill['id'] in payment_indices,'native competitor automation paid')
        if bill['id'] in payment_indices:
            index=payment_indices[bill['id']];event=events[index]
            before=event['cashAfterCents']-event['amountCents']
            encumbered=sum(b['amountCents'] for b in bills[:n] if b['id'] not in payment_indices or payment_indices[b['id']]>index)
            ck(before-encumbered>=bill['amountCents'],'native competitor automation affordable after obligations')
            same(bill['amountCents'],c['competitorImitationCostCents'],'native competitor declared automation cost')
            same(sum(a['week']==bill['week'] and a['costCents']==bill['amountCents'] for a in automation),1,'native competitor automation event identity')
    totals['competitorFirmAccounts']+=1;totals['competitorInvoices']+=len(invoices)
    totals['competitorBills']+=len(bills);totals['competitorCashEvents']+=len(events);totals['competitorAutomationEvents']+=len(automation)

with gzip.open(results/'complete-runs.jsonl.gz','rt') as f:
    for line in f:
        pair=json.loads(line);scenario=pair['config']['id'];seed=pair['seed'];context=f'{scenario}:{seed}'
        ck((scenario,seed) not in seen,'unique paired world');seen.add((scenario,seed))
        ck(scenario in configs and seed in summary['seeds'],'registered configuration and seed only')
        for arm in ('A','B','C'):
            audit_run(pair['arms'][arm],scenario,seed,arm)
            if deployment:
                same(set(pair['arms'][arm]['competitorAccounts']),{'human','ai'},'complete native competitor set')
                for identifier,firm in pair['arms'][arm]['competitorAccounts'].items(): audit_competitor(pair['arms'][arm],identifier,firm)
        context=f'{scenario}:{seed}:paired'
        a,b,c=(pair['arms'][x] for x in ('A','B','C'))
        same(a['summary']['opportunities'],b['summary']['opportunities'],'shared arrival count A/B')
        same(a['summary']['supportedOpportunities'],b['summary']['supportedOpportunities'],'shared support-scope count A/B')
        identities=lambda r:{x['mission'] for x in r['histories']['buyerChoices']}
        same(identities(a),identities(b),'shared exact external opportunity identities A/B')
        same(identities(b),identities(c),'shared exact external opportunity identities B/C')
        same(b['summary'],c['summary'],'B/C symmetric summaries exactly match')
        same(pair['causal']['B_C_behaviorallyIdentical'],True,'B/C tie flag honest')
        for label,x,y in [('B_minus_A',b,a),('C_minus_A',c,a),('B_minus_C',b,c)]:
            same(pair['causal'][label+'_profitCents'],x['summary']['profitCents']-y['summary']['profitCents'],'paired causal arithmetic')
        if exploratory:
            capital=sum(x['amountCents'] for x in b['histories']['bills'] if x['category']=='capability')
            same(pair['exploratory']['status'],'POSTPRIMARY_EXPLORATORY','per-world exploratory label')
            same(pair['exploratory']['B_oneoffCapabilityIncurredCents'],capital,'path-fixed capital cost sum')
            same(pair['exploratory']['B_fixedPathMaximumOneoffCostCents'],pair['causal']['B_minus_A_profitCents']+capital,'path-fixed threshold arithmetic')
        if policy_diagnostic:
            pd=pair['policyDiagnostic'];conf=pair['config']
            same(pd['status'],'POST_EXPLORATORY_NOT_CONFIRMATION','per-world policy diagnostic label')
            same(conf['pricingPolicy'],'fixed','declared fixed-target policy')
            same(pd['targetPriceCents'],conf['initialPriceCents'],'declared price target identity')
            regime=('full' if conf['investmentCostBasis']=='full-history' else 'adoption')+('-earned' if conf['investmentFunding']=='operating-surplus' else '-seed')
            prior_id=f"explore-i{conf['integrationCents']}-a{conf['arrivalProbability']:g}-m{conf['ordinaryFinalizationMinutes']:g}-{conf['choiceModel']}-{regime}"
            same(pd['priorHeuristicScenario'],prior_id,'matching prior scenario derived independently')
            capital=sum(x['amountCents'] for x in b['histories']['bills'] if x['category']=='capability')
            same(pd['B_oneoffCapabilityIncurredCents'],capital,'policy path-fixed capital cost sum')
            same(pd['B_fixedPathMaximumOneoffCostCents'],pair['causal']['B_minus_A_profitCents']+capital,'policy path-fixed threshold arithmetic')
            for arm,run in pair['arms'].items():
                key=(prior_id,seed,arm);prices=run['histories']['prices']
                jobs=[j for j in run['histories']['jobs'] if j['provider']=='enterprise' and j['accepted']]
                same(pd['policyMinusHeuristicProfitCents'][arm],run['summary']['profitCents']-prior_rows[key]['profitCents'],'paired policy-minus-heuristic arithmetic')
                same(opportunity_fingerprint(run),prior_identities[key],'exact prior-policy arrival and supported-scope identities')
                for q in prices:
                    minutes=conf['commonResidualMinutes']+(conf['assetResidualMinutes'] if q['assetActive'] else conf['ordinaryFinalizationMinutes'])
                    floor=jsround(minutes*conf['hourlyProviderCents']/60)+conf['computeAndToolCents']+100
                    same(q['enterpriseCents'],max(conf['initialPriceCents'],floor),'every weekly quote obeys fixed-target cost floor')
                expected_ranges={
                    'computedWeeklyQuotes':price_range([q['enterpriseCents'] for q in prices]),
                    'offeredQuotes':price_range([q['enterpriseCents'] for q in prices if q['offersSeen']>0]),
                    'offeredBeforeAdoption':price_range([q['enterpriseCents'] for q in prices if q['offersSeen']>0 and not q['assetActive']]),
                    'offeredAfterAdoption':price_range([q['enterpriseCents'] for q in prices if q['offersSeen']>0 and q['assetActive']]),
                    'acceptedDeliveryPrices':price_range([j['priceCents'] for j in jobs]),
                    'acceptedBeforeAdoption':price_range([j['priceCents'] for j in jobs if not j['assetUsed']]),
                    'acceptedAfterAdoption':price_range([j['priceCents'] for j in jobs if j['assetUsed']])}
                same(pd['priceRanges'][arm],expected_ranges,'quoted offered and accepted price scopes independently reconstructed')
        if deployment:
            ext=pair['successionAvailability'];conf=pair['config']
            same(ext['status'],'FRESH_SEED_BOUNDED_EXTENSION','per-world fresh extension label')
            same(ext['unpricedIncrementalDiscoveryCostCents'],None,'discovery not silently priced at zero')
            same(ext['allInSpendableResourcesIdentified'],False,'all-in funding not falsely identified')
            same(ext['secondAssetGate']['status'],'NO_GO','failed second-candidate gate retained')
            same(ext['secondAssetGate']['candidate'],None,'no hypothetical successor substituted')
            same(ext['secondAssetGate']['actualSecondInvestmentCents'],0,'no fabricated second purchase')
            same(ext['secondAssetGate']['earmarkedGeneratedFundsCents'],0,'no unqualified earmark')
            same(ext['secondAssetGate']['recordSHA256'],gate_digest,'source-bound second-asset no-go decision')
            capital=sum(x['amountCents'] for x in b['histories']['bills'] if x['category']=='capability')
            same(ext['B_oneoffCapabilityIncurredCents'],capital,'fresh extension actual capital charge')
            same(ext['B_fixedRealizedPathMaximumOneoffCostBeforeUnpricedDiscoveryCents'],pair['causal']['B_minus_A_profitCents']+capital,'fresh fixed-path threshold arithmetic')
            extension_prices={}
            for arm,run in pair['arms'].items():
                f=ext['fundingByArm'][arm];h=run['histories'];historical=[]
                prices=h['prices'];accepted=[j for j in h['jobs'] if j['provider']=='enterprise' and j['accepted']]
                for q in prices:
                    minutes=conf['commonResidualMinutes']+(conf['assetResidualMinutes'] if q['assetActive'] else conf['ordinaryFinalizationMinutes'])
                    floor=jsround(minutes*conf['hourlyProviderCents']/60)+conf['computeAndToolCents']+100
                    same(q['enterpriseCents'],max(conf['initialPriceCents'],floor),'fresh quote obeys fixed-target cost floor')
                extension_prices[arm]={'computedWeeklyQuoteRange':price_range([q['enterpriseCents'] for q in prices]),
                    'actuallyOfferedQuoteRange':price_range([q['enterpriseCents'] for q in prices if q['offersSeen']>0]),
                    'acceptedDeliveryPriceRange':price_range([j['priceCents'] for j in accepted])}
                same(f['unpricedIncrementalDiscoveryCostCents'],None,'per-arm discovery cost unknown')
                same(f['allInSpendableResourcesIdentified'],False,'per-arm all-in funds unidentified')
                same(f['actualSecondInvestmentCents'],0,'funding view creates no investment')
                same(f['earmarks'],[],'no generated resource commitment without candidate')
                same((f['sourceScenario'],f['sourceSeed'],f['sourceArm']),(scenario,seed,arm),'funding view source identity')
                if conf['investmentCostBasis']=='full-history' and conf['historicalCostTiming']=='opening':
                    for bill in h['bills']:
                        if bill['category']!='capability' or bill['reference']!='upfront historical R&D cost stress; paid from seed if affordable, never labeled earned financing' or bill['week']!=0 or not bill['paid'] or bill['paidWeek']!=0: continue
                        payment=next((n for n,e in enumerate(h['cash']) if e['reference']==bill['id'] and e['type']=='expense_payment' and e['week']==0 and e['amountCents']==-bill['amountCents']),None)
                        if payment is not None and not any(e['type']=='simulated_collection' for e in h['cash'][:payment]): historical.append(bill)
                H=sum(x['amountCents'] for x in historical)
                same(f['historicalRDCentsExcluded'],H,'only paid opening research receives generation addback')
                ck(H<=conf['initialCashCents'],'historical source allocation fits initial seed')
                same({x['billId'] for x in f['historicalBillsExcludedFromGeneratedRecovery']},{x['id'] for x in historical},'historical allocation exact bill identities')
                same(len(f['weekly']),len(h['balances']),'funding covers all original weeks')
                generated=[];within=[];first=None;first_service=None
                for got,bal in zip(f['weekly'],h['balances']):
                    cashcap=bal['cashCents']-bal['obligationsCents']-conf['reserveCents'];generation=bal['cumulativeCollectionsCents']-bal['accruedCostsCents']+H
                    G=max(0,min(cashcap,generation));full=max(0,min(cashcap,bal['cumulativeCollectionsCents']-bal['accruedCostsCents']))
                    expected={'week':bal['week'],'cashCents':bal['cashCents'],'unpaidObligationsCents':bal['obligationsCents'],
                      'reserveCents':conf['reserveCents'],'collectedCents':bal['cumulativeCollectionsCents'],'allAccruedCostsCents':bal['accruedCostsCents'],
                      'explicitlySeedPaidOpeningHistoricalRDCents':H,'prospectiveAccruedCostsToRecoverCents':bal['accruedCostsCents']-H,
                      'cashCapBeforeEarmarksCents':cashcap,'generatedBeforeEarmarksCents':generation,'outstandingUnaccruedEarmarksCents':0,
                      'cashCapAfterEarmarksCents':cashcap,'generatedAfterEarmarksCents':generation,
                      'fundingCeilingBeforeUnpricedDiscoveryCents':G,'fullCostRecoveryCeilingBeforeUnpricedDiscoveryCents':full,
                      'originalStrictEarnedAvailableCents':bal['earnedAvailableCents']}
                    same(got,expected,'independent weekly funding ceiling from cash and accrued expenses')
                    generated.append(G)
                    if G>0 and first is None: first=bal['week']
                    if bal['week']<conf['weeks']:
                        within.append(G)
                        if G>0 and first_service is None: first_service=bal['week']
                same(f['terminal'],f['weekly'][-1],'funding terminal row identity')
                same(f['firstPositiveFundingCeilingWeek'],first,'first funding date from collected history')
                same(f['firstPositiveDuringServiceFundingCeilingWeek'],first_service,'future receipts cannot finance earlier service')
                same(f['maximumFundingCeilingBeforeUnpricedDiscoveryCents'],max(generated),'maximum funding ceiling')
                same(f['maximumDuringServiceFundingCeilingBeforeUnpricedDiscoveryCents'],max(within,default=0),'in-horizon maximum funding ceiling')
            same(ext['B_minus_A_terminalFundingCeilingCents'],ext['fundingByArm']['B']['terminal']['fundingCeilingBeforeUnpricedDiscoveryCents']-ext['fundingByArm']['A']['terminal']['fundingCeilingBeforeUnpricedDiscoveryCents'],'paired generated-funding difference')
        records[scenario].append({'seed':seed,'A':a['summary'],'B':b['summary'],'C':c['summary'],'causal':pair['causal'],'exploratory':pair.get('exploratory'),'policyDiagnostic':pair.get('policyDiagnostic'),'successionAvailability':pair.get('successionAvailability'),'extensionPrices':extension_prices if deployment else None})
        if len(seen)%250==0: print(json.dumps({'auditedPairedWorlds':len(seen),'failures':failure_count}),flush=True)

context='aggregate'
same(len(seen),expected_configs*expected_seeds,'all declared paired worlds present')
same(totals['enterprise_histories'],expected_configs*expected_seeds*3,'all declared enterprise histories present')
if deployment: same(totals['competitorFirmAccounts'],expected_configs*expected_seeds*6,'all declared native competitor accounts present')
same(seen,{(s,z) for s in configs for z in summary['seeds']},'complete configuration-by-seed Cartesian product')
def verify_stats(actual,values):
    n=len(values);mean=sum(values)/n;sd=statistics.stdev(values) if n>1 else 0;ordered=sorted(values)
    same(actual['n'],n,'aggregate sample count')
    close(actual['mean'],mean,'aggregate arithmetic mean')
    close(actual['sd'],sd,'aggregate sample standard deviation')
    for got,want in zip(actual['meanInterval95'],[mean-1.96*sd/math.sqrt(n),mean+1.96*sd/math.sqrt(n)]): close(got,want,'normal approximation Monte Carlo interval')
    for k,p in [('minimum',0),('p05',.05),('median',.5),('p95',.95),('maximum',1)]:
        if k in actual: same(actual[k],ordered[math.floor((n-1)*p)],'empirical lower quantile convention')
for row in summary['scenarios']:
    context=f"aggregate:{row['scenario']}";rs=records[row['scenario']]
    for arm in ('A','B','C'):
        profit_label='profitBeforeUnpricedDiscoveryCents' if deployment else 'profitCents'
        for label,key in [(profit_label,'profitCents'),('accepted','enterpriseAccepted'),('collectionsCents','grossCollectionsCents'),('finalCashCents','finalCashCents')]: verify_stats(row['arms'][arm][label],[r[arm][key] for r in rs])
        viable_label='positiveModeledProfitBeforeUnpricedDiscoveryRate' if deployment else 'viableRate'
        for label,predicate in [('investmentRate',lambda s:s['investmentWeek'] is not None),('insolvencyRate',lambda s:s['insolvent']),(viable_label,lambda s:s['profitCents']>0 and not s['insolvent'] and s['obligationsCents']==0),('directRepaymentRate',lambda s:s['directCostPayback'])]: close(row['arms'][arm][label],sum(predicate(r[arm]) for r in rs)/len(rs),'aggregate outcome rate')
    causal_label='causalBeforeUnpricedDiscovery' if deployment else 'causal'
    for key in ('B_minus_A_profitCents','C_minus_A_profitCents','B_minus_C_profitCents'): verify_stats(row[causal_label][key],[r['causal'][key] for r in rs])
    close(row['B_positive_incremental_rate'],sum(r['causal']['B_minus_A_profitCents']>0 for r in rs)/len(rs),'positive paired-effect rate')
    close(row['B_negative_incremental_rate'],sum(r['causal']['B_minus_A_profitCents']<0 for r in rs)/len(rs),'negative paired-effect rate')
    if exploratory: verify_stats(row['pathFixedMaximumOneoffCostCents'],[r['exploratory']['B_fixedPathMaximumOneoffCostCents'] for r in rs])
    if policy_diagnostic:
        verify_stats(row['pathFixedMaximumOneoffCostCents'],[r['policyDiagnostic']['B_fixedPathMaximumOneoffCostCents'] for r in rs])
        for arm in ('A','B','C'):
            verify_stats(row['arms'][arm]['policyMinusHeuristicProfitCents'],[r['policyDiagnostic']['policyMinusHeuristicProfitCents'][arm] for r in rs])
            for label,key in [('computedWeeklyQuoteRange','computedWeeklyQuotes'),('actualOfferedQuoteRange','offeredQuotes'),('actualBeforeAdoptionQuoteRange','offeredBeforeAdoption'),('actualAfterAdoptionQuoteRange','offeredAfterAdoption'),('acceptedDeliveryPriceRange','acceptedDeliveryPrices')]:
                same(row['arms'][arm][label],combine_ranges([r['policyDiagnostic']['priceRanges'][arm][key] for r in rs]),'aggregate scoped quote or accepted-price range')
    if deployment:
        verify_stats(row['pathFixedMaximumOneoffCostBeforeUnpricedDiscoveryCents'],[r['successionAvailability']['B_fixedRealizedPathMaximumOneoffCostBeforeUnpricedDiscoveryCents'] for r in rs])
        verify_stats(row['incrementalTerminalFundingCeilingCents'],[r['successionAvailability']['B_minus_A_terminalFundingCeilingCents'] for r in rs])
        same(row['actualSecondInvestments'],0,'aggregate no second purchase')
        for arm in ('A','B','C'):
            funds=[r['successionAvailability']['fundingByArm'][arm] for r in rs]
            for label,key in [('terminalFundingCeilingBeforeUnpricedDiscoveryCents','fundingCeilingBeforeUnpricedDiscoveryCents'),('terminalFullCostRecoveryCeilingBeforeUnpricedDiscoveryCents','fullCostRecoveryCeilingBeforeUnpricedDiscoveryCents'),('originalStrictTerminalEarnedCents','originalStrictEarnedAvailableCents')]: verify_stats(row['arms'][arm][label],[f['terminal'][key] for f in funds])
            verify_stats(row['arms'][arm]['maximumDuringServiceFundingCeilingBeforeUnpricedDiscoveryCents'],[f['maximumDuringServiceFundingCeilingBeforeUnpricedDiscoveryCents'] for f in funds])
            close(row['arms'][arm]['positiveTerminalFundingCeilingRate'],sum(f['terminal']['fundingCeilingBeforeUnpricedDiscoveryCents']>0 for f in funds)/len(funds),'positive terminal ceiling rate')
            close(row['arms'][arm]['positiveDuringServiceFundingCeilingRate'],sum(f['maximumDuringServiceFundingCeilingBeforeUnpricedDiscoveryCents']>0 for f in funds)/len(funds),'positive in-horizon ceiling rate')
            close(row['arms'][arm]['failedInvestmentRate'],sum(r[arm]['failedInvestment'] for r in rs)/len(rs),'failed adoption rate')
            for label in ('computedWeeklyQuoteRange','actuallyOfferedQuoteRange','acceptedDeliveryPriceRange'):
                same(row['arms'][arm][label],combine_ranges([r['extensionPrices'][arm][label] for r in rs]),'fresh aggregate quote or accepted-price range')

report={'schema':'agi-alpha-independent-frozen-outcome-audit/v1','executedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'reviewer':'same-session independent economic review; not organizationally independent','primaryInspectionAuthorizedAfterFreeze':True,
    'campaign':'bounded-fresh-seed-deployment-extension' if deployment else 'post-exploratory-policy-diagnostic' if policy_diagnostic else 'postprimary-exploratory' if exploratory else 'preregistered-primary',
    'freezeSHA256':digest(freeze_path),'marketSourceSHA256':digest(market/'src/market.mjs'),
    'completionSHA256':digest(results/'completion.json'),
    'completeRunsSHA256':digest(results/'complete-runs.jsonl.gz'),'summarySHA256':digest(results/'summary.json'),
    'passed':failure_count==0,'failedAssertions':failure_count,'firstFailures':failures,'counts':dict(totals),'checks':dict(checks),
    'statisticalInterpretation':f'Reported 95% mean intervals are 1.96 normal approximations over {expected_seeds} simulated seeds; not Student t intervals and not confidence in real market profitability. Empirical quantiles use the declared lower order-statistic convention.',
    'economicInterpretation':'B/C economic equality follows matched modeled costs, information, policy and effects; it is a symmetry result, not measured equality of complete construction efficiency. Positive enterprise profit, collected operating surplus, direct avoided cost and paired investment benefit remain distinct.',
    'limitations':['Demand, WTP, human duration, full construction and inference costs, reliability and payment behavior remain assumption ranges.','No actual customer adoption, collected revenue, protocol transaction or financed untested successor is established.','Review verifies supplied histories and declared arithmetic, not an independent reconstruction of every physical production result.']}
out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:report[k] for k in ('passed','failedAssertions','counts','marketSourceSHA256','completeRunsSHA256')},indent=2))
if failures: print(json.dumps(failures[:8],indent=2))
sys.exit(0 if failure_count==0 else 1)
