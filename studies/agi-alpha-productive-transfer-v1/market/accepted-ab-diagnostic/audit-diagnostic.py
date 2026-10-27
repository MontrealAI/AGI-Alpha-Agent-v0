# SPDX-License-Identifier: Apache-2.0
import argparse, collections, datetime, gzip, hashlib, json, math, pathlib, time

parser=argparse.ArgumentParser(description='Reconcile every new source-intake enterprise history using independent arithmetic.')
parser.add_argument('results',type=pathlib.Path)
parser.add_argument('output',type=pathlib.Path)
args=parser.parse_args()
root=pathlib.Path(__file__).resolve().parents[2]
if args.output.exists():parser.error('Refusing to replace an earlier audit receipt')
checks,counts=collections.Counter(),collections.Counter()
failures=[]
start=time.perf_counter()

def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def ck(ok,name,ctx):
    checks[name]+=1
    if not ok and len(failures)<100:failures.append({'check':name,'context':ctx})

completion=json.loads((args.results/'completion.json').read_text())
summary=json.loads((args.results/'summary.json').read_text())
freeze_path=args.results/'freeze-used.json'
freeze=json.loads(freeze_path.read_text())
protocol=json.loads((root/freeze['protocol']).read_text())
production=json.loads((root/freeze['production']).read_text())
scenarios={x['id']:x for x in json.loads((root/freeze['scenarios']).read_text())}
acceptance=production.get('independentAcceptance',{})
ck(acceptance.get('scope')=='complete-useful-deliverable' and acceptance.get('independentlyVerified') is True and
   len(acceptance.get('rows',[]))==8 and all(r['completeHandoffAccepted'] for r in acceptance['rows']),
   'complete useful A/B deliverable acceptance gate','production')
ck(production['missions']==['F01','F02','F03','F04'],'no favorable mission subset','production')
ck(production['sourceThreeArmBridge']['campaignStatus']=='GATED_UNEXECUTED','original three-arm gate preserved','production')
for a in ['A','B']:
    ck(sorted(production['arms'][a]['acceptedMissionIds'])==sorted(production['missions']),
       'entire registered mission set accepted without narrowing',a)
ck(sha(args.results/'all-paired-histories.jsonl.gz')==completion['historiesSHA256'],'full history archive identity','closure')
ck(sha(args.results/'summary.json')==completion['summarySHA256'],'summary identity','closure')
ck(sha(freeze_path)==completion['freezeSHA256'],'freeze identity','closure')
for f in freeze['files']:ck(sha(root/f['path'])==f['sha256'],'frozen source input unchanged',f['path'])
rows=collections.defaultdict(list)
seeds=set()
seen=set()
with gzip.open(args.results/'all-paired-histories.jsonl.gz','rt') as stream:
    for line in stream:
        pair=json.loads(line)
        name=pair['scenario'];seed=pair['seed'];scenario=scenarios[name]
        ck((name,seed) not in seen,'one result per preregistered world',(name,seed));seen.add((name,seed));seeds.add(seed)
        ck(pair['sourceProductionSHA256']==production['evidenceSHA256'],'production bridge identity',(name,seed))
        ck(pair['observedCustomerCollectionsCents']==0 and not pair['actualFinancialAction'],'no actual transaction claim',(name,seed))
        for arm,r in pair['arms'].items():
            ctx=(name,seed,arm);s,h,c=r['summary'],r['histories'],r['config'];cost=scenario['costs'][arm]
            rows[(name,arm)].append(s)
            counts['enterprise_histories']+=1
            counts['enterprise_attempts']+=s['enterpriseAttempts']
            counts['investments']+=len(h['investments'])
            counts[arm+'_investments']+=len(h['investments'])
            counts['earned_funded_investments']+=sum(x['funding']=='operating-surplus' for x in h['investments'])
            counts[arm+'_profitable_worlds']+=s['profitCents']>0
            ck(c['computeAndToolCents']==scenario['costs']['A']['completeRecurringCostCents'],'incumbent complete nominal cost mapping',ctx)
            ck(c['activeComputeAndToolCents']==cost['completeRecurringCostCents'],'active complete nominal cost mapping',ctx)
            ck(c['authoringCostCents']==cost['completeConstructionCostCents'],'complete reconstruction envelope mapping',ctx)
            ck(c['constructionHours']==0 and c['adoptionInferenceCents']==0 and c['hourlyProviderCents']==0,'no additional wage or duplicate construction charge',ctx)
            ck(c['investmentCostBasis']=='prospective-reconstruction','same-asset prospective reconstruction basis',ctx)
            ck(c['ordinaryFinalizationMinutes']==0 and c['assetResidualMinutes']==0,'no unmeasured human-minute savings',ctx)
            ck(c['pricingPolicy']=='fixed' and c['initialPriceCents']==scenario['shared']['initialPriceCents'],'predeclared price policy',ctx)
            own=[j for j in h['jobs'] if j['provider']=='enterprise']
            jobs={j['id']:j for j in own}
            ck(len(jobs)==len(own)==s['enterpriseAttempts'],'unique equivalent enterprise job accounting',ctx)
            ck(sum(j['accepted'] for j in own)==s['enterpriseAccepted'],'accepted job count',ctx)
            bills={b['id']:b for b in h['bills']};invoices={i['id']:i for i in h['invoices']}
            ck(len(bills)==len(h['bills']) and len(invoices)==len(h['invoices']),'unique bill and invoice identities',ctx)
            cash=c['initialCashCents'];collected=set();paid=set()
            for event in h['cash']:
                cash+=event['amountCents']
                ck(cash==event['cashAfterCents'] and cash>=0,'every cash balance conserved and nonnegative',ctx)
                ref=event['reference']
                if event['amountCents']<0:
                    ck(ref in bills and ref not in paid and bills[ref]['amountCents']==-event['amountCents'],'bill paid once at its value',ctx)
                    paid.add(ref)
                else:
                    ck(ref in invoices and ref not in collected and invoices[ref]['amountCents']==event['amountCents'],'invoice collected once at its value',ctx)
                    collected.add(ref)
            pending=sum(x['amountCents'] for x in h['invoices'] if x['status']=='pending')
            unpaid=sum(b['amountCents'] for b in h['bills'] if not b['paid'])
            ck(cash==s['finalCashCents'],'terminal cash conservation',ctx)
            ck(s['profitCents']==cash+pending-unpaid-c['initialCashCents'],'economic profit excludes initial capital',ctx)
            ck(sum(b['amountCents'] for b in h['bills'])==s['accruedCostsCents'],'all accrued expenses retained once',ctx)
            ck(sum(b['amountCents'] for b in h['bills'] if b['paid'])==s['paidCostsCents'],'cash expenses distinct from accrued expenses',ctx)
            ck(unpaid==s['obligationsCents'],'unpaid obligations retained',ctx)
            for j in own:
                ck(j['accepted'] or not j['invoiceCreated'],'rejected work never invoiced',ctx)
                if j['assetUsed']:
                    ck(j['sourceAssetSHA256']==production['arms'][arm]['asset']['sha256'],'actual tested financed asset identity',ctx)
                nominal=cost['completeRecurringCostCents'] if j['assetUsed'] else scenario['costs']['A']['completeRecurringCostCents']
                expected=math.floor(nominal*(1 if j['qualityGood'] else c['failureCorrectionMultiplier'])+0.5)
                ck(j['deliveryCostCents']==expected,'nominal and failure correction charged without duplication',ctx)
            for inv in h['invoices']:
                j=jobs.get(inv['mission'])
                ck(j is not None and j['accepted'] and j['priceCents']==inv['amountCents'],'invoice follows accepted agreed deliverable',ctx)
            for b in h['balances']:
                ck(b['availableCashCents']==b['cashCents']-b['obligationsCents']-b['reserveCents'],'reserves and obligations encumber liquidity',ctx)
                ck(b['earnedAvailableCents']==min(b['availableCashCents'],b['cumulativeCollectionsCents']-b['accruedCostsCents']-b['reserveCents']),'earned funds exclude seed and receivables',ctx)
            for decision in h['investmentDecisions']:
                ck(decision['asset']['sha256']==production['acceptedAsset']['sha256'],'all decisions name exact tested B asset',ctx)
                ck(decision['expectedIncrementalSavingPerUseCents']==0,'no invented incremental unit saving',ctx)
                ck(decision['action']=='retain-incumbent' and 'no positive task saving' in decision['reasons'],'no forced unjustified adoption',ctx)
                week=decision['week']
                pre_bills=[b for b in h['bills'] if b['week']<week or (b['week']==week and b['category'] not in ['delivery','capability'])]
                pre_ids={b['id'] for b in pre_bills}
                pre_events=[e for e in h['cash'] if e['week']<week or (e['week']==week and (e['amountCents']>0 or e['reference'] in pre_ids))]
                before=c['initialCashCents']+sum(e['amountCents'] for e in pre_events)
                old_unpaid=sum(b['amountCents'] for b in pre_bills if not b['paid'] or b['paidWeek']>week)
                old_cost=sum(b['amountCents'] for b in pre_bills)
                collected_before=sum(e['amountCents'] for e in pre_events if e['amountCents']>0)
                available=min(before-old_unpaid-c['reserveCents'],collected_before-old_cost-c['reserveCents'])
                ck(available==decision['availableCashCents'],'decision-time available earned cash independently reconstructed',ctx)
                expected=-decision['productiveWeeksAfterAdoption']*cost['maintenancePerWeekCents']-cost['completeConstructionCostCents']-decision['expectedForegoneContributionCents']
                ck(expected==decision['expectedNetBenefitCents'] and expected<=0,'nonpositive forecast follows complete costs',ctx)
                ck(decision['fullCostCents']==cost['completeConstructionCostCents'],'refused asset full construction envelope retained',ctx)
            ck(not h['investments'] and not s['assetActive'],'zero-benefit exact asset remains unbuilt',ctx)
            for inv in h['investments']:
                ck(inv['availableCashCents']>=inv['fullCostCents'] and inv['expectedNetBenefitCents']>0,'affordable justified decision-time investment',ctx)
                ck(inv['fullCostCents']==cost['completeConstructionCostCents'],'complete asset envelope charged',ctx)
                ck(inv['asset']['sha256']==production['arms'][arm]['asset']['sha256'],'investment binds actual constructed source',ctx)
                ck(inv['funding']==scenario['financing'],'predeclared source of financing',ctx)
                ck(all(not(inv['week']<=j['week']<inv['availableWeek']) for j in own),'construction pauses delivery until availability',ctx)
                cap=[(i,b) for i,b in enumerate(h['bills']) if b['category']=='capability' and b['reference']==inv['asset']['sha256'] and b['week']==inv['week']]
                ck(len(cap)==1,'one complete capability liability',ctx)
                if len(cap)==1:
                    bi,b=cap[0];events=[(i,e) for i,e in enumerate(h['cash']) if e['reference']==b['id']]
                    ck(len(events)==1,'one complete capability payment',ctx)
                    if len(events)==1:
                        ei,e=events[0];before=e['cashAfterCents']-e['amountCents']
                        old_unpaid=sum(x['amountCents'] for x in h['bills'][:bi] if not x['paid'] or x['paidWeek']>inv['week'])
                        old_cost=sum(x['amountCents'] for x in h['bills'][:bi])
                        old_collections=sum(x['amountCents'] for x in h['cash'][:ei] if x['amountCents']>0)
                        available=min(before-old_unpaid-c['reserveCents'],old_collections-old_cost-c['reserveCents'])
                        ck(available==inv['availableCashCents'] and available>=inv['fullCostCents'],'independent decision-time earned funding reconstruction',ctx)
            ck(all(b['committedCents']<=b['budgetCents'] for b in h['buyerProcurement']),'finite buyer procurement budget',ctx)
            ck(r['canonical']['cash']['summary']['observed']['revenue']==0 and s['actualRevenueCents']==0,'canonical observed revenue remains zero',ctx)
            ck(r['nextInvestment']['action']=='retain-reserves' and not r['nextInvestment']['actualFinancialAction'],'no untested next asset',ctx)
        for a,b,key in [('B','A','B_minus_A_profitCents')]:
            ck(pair['differences'][key]==pair['arms'][a]['summary']['profitCents']-pair['arms'][b]['summary']['profitCents'],'paired causal difference reconstruction',(name,seed,key))
        ck(pair['arms']['A']['summary']==pair['arms']['B']['summary'],'A B symmetry without invented benefit',(name,seed))
for item in summary['summaries']:
    for arm in ['A','B']:
        values=rows[(item['scenario'],arm)];reported=item['arms'][arm]
        for field,label in [('profitCents','profitCents'),('enterpriseAccepted','accepted')]:
            mean=sum(x[field] for x in values)/len(values)
            ck(math.isclose(mean,reported[label]['mean'],abs_tol=1e-8),'aggregate mean reconstruction',(item['scenario'],arm,field))
        ck(sum(v['investmentWeek'] is not None for v in values)==reported['investments'],'aggregate investment count',(item['scenario'],arm))
ck(len(seen)==len(scenarios)*protocol['seedCount'],'every registered paired world retained','completion')
ck(seeds==set(range(protocol['seedFirst'],protocol['seedFirst']+protocol['seedCount'])),'exact new seed set','completion')
report={'schema':'agi-alpha-accepted-ab-diagnostic-arithmetic-audit/v1','createdUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'status':'PASS' if not failures else 'FAIL','pairedWorlds':len(seen),'counts':dict(counts),'checks':dict(checks),'failures':failures,
 'auditSourceSHA256':sha(pathlib.Path(__file__)),'historiesSHA256':completion['historiesSHA256'],
 'wallSeconds':time.perf_counter()-start,'originalThreeArmCampaignStatus':'GATED_UNEXECUTED','independence':'Separate Python arithmetic implementation, same project/session/host; not institutional independence or field validation.'}
with args.output.open('x') as f:json.dump(report,f,indent=2);f.write('\n')
print(json.dumps({k:report[k] for k in ['status','pairedWorlds','counts','wallSeconds']}))
raise SystemExit(bool(failures))
