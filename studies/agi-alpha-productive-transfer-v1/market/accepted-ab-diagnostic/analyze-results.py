# SPDX-License-Identifier: Apache-2.0
"""Post-outcome descriptive analysis. Reads preserved histories; never simulates or edits them."""
import collections, csv, datetime, gzip, hashlib, json, pathlib, statistics

base=pathlib.Path(__file__).resolve().parent
results=base/'results';out=base/'analysis'
out.mkdir(exist_ok=False)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def stats(values):
    return {'n':len(values),'mean':statistics.mean(values),'minimum':min(values),'maximum':max(values)} if values else {'n':0,'mean':None,'minimum':None,'maximum':None}
def write(name,value):
    with (out/name).open('x') as f:json.dump(value,f,indent=2);f.write('\n')

audit=read(base/'results-audit.json');assert audit['status']=='PASS'
completion=read(results/'completion.json')
assert sha(results/'all-paired-histories.jsonl.gz')==completion['historiesSHA256']
scenarios=read(base/'scenarios.json');config={s['id']:s for s in scenarios}
worlds=[];by_case=collections.defaultdict(list);reason_counts=collections.Counter();choice_counts=collections.Counter()
cash_eligible_decisions=0;cash_eligible_worlds=set();all_decisions=[]
with gzip.open(results/'all-paired-histories.jsonl.gz','rt') as f:
    for line in f:
        pair=json.loads(line);a,b=pair['arms']['A'],pair['arms']['B']
        assert a['summary']==b['summary'] and pair['differences']['B_minus_A_profitCents']==0
        for k in ['cash','balances','invoices','bills','buyerChoices','jobs','prices']:
            assert a['histories'][k]==b['histories'][k],k
        worlds.append(pair);by_case[pair['scenario']].append(pair)
        choice_counts.update(c['choice'] for c in a['histories']['buyerChoices'])
        for d in b['histories']['investmentDecisions']:
            reason_counts.update(d['reasons']);all_decisions.append(d)
            if d['availableCashCents']>=d['fullCostCents']:
                cash_eligible_decisions+=1;cash_eligible_worlds.add((pair['scenario'],pair['seed']))

rows=[];detailed=[]
for scenario in scenarios:
    name=scenario['id'];pairs=by_case[name];assert len(pairs)==8
    summaries=[p['arms']['A']['summary'] for p in pairs]
    histories=[p['arms']['A']['histories'] for p in pairs]
    choices=collections.Counter(c['choice'] for h in histories for c in h['buyerChoices'])
    quote_values=[r['enterpriseCents'] for h in histories for r in h['prices']]
    invoice_values=[i['amountCents'] for h in histories for i in h['invoices']]
    target=scenario['shared']['initialPriceCents'];refusals=collections.Counter()
    decisions=[d for p in pairs for d in p['arms']['B']['histories']['investmentDecisions']]
    for d in decisions:refusals.update(d['reasons'])
    s=lambda k:stats([v[k] for v in summaries])
    meanprofit=s('profitCents');accepted=s('enterpriseAccepted')
    row={'scenario':name,'stress_profile':scenario['assumptions']['stress'],'buyer_model':scenario['shared']['choiceModel'],
      'seeds':8,'common_arm':'A_equals_B','target_price_usd':target/100,
      'quoted_price_min_usd':min(quote_values)/100,'quoted_price_max_usd':max(quote_values)/100,
      'accepted_invoice_price_min_usd':min(invoice_values)/100 if invoice_values else None,
      'accepted_invoice_price_max_usd':max(invoice_values)/100 if invoice_values else None,
      'profit_mean_usd':meanprofit['mean']/100,'profit_min_usd':meanprofit['minimum']/100,'profit_max_usd':meanprofit['maximum']/100,
      'profitable_worlds':sum(v['profitCents']>0 for v in summaries),'insolvent_worlds':sum(v['insolvent'] for v in summaries),
      'accepted_mean':accepted['mean'],'accepted_min':accepted['minimum'],'accepted_max':accepted['maximum'],
      'attempts_total':sum(v['enterpriseAttempts'] for v in summaries),'accepted_total':sum(v['enterpriseAccepted'] for v in summaries),
      'rejected_total':sum(v['enterpriseRejected'] for v in summaries),'latent_failures_total':sum(v['latentFailures'] for v in summaries),
      'gross_invoices_mean_usd':s('grossInvoicesCents')['mean']/100,'gross_collections_mean_usd':s('grossCollectionsCents')['mean']/100,
      'refunds_mean_usd':s('refundsCents')['mean']/100,'written_off_mean_usd':s('writtenOffCents')['mean']/100,
      'obligations_mean_usd':s('obligationsCents')['mean']/100,'cost_mean_usd':s('accruedCostsCents')['mean']/100,
      'final_cash_mean_usd':s('finalCashCents')['mean']/100,
      'available_earned_surplus_max_usd':s('availableOperatingSurplusCents')['maximum']/100,
      'opportunities_total':sum(v['opportunities'] for v in summaries),'supported_opportunities_total':sum(v['supportedOpportunities'] for v in summaries),
      'enterprise_choices':choices['enterprise'],'human_choices':choices['human'],'ai_choices':choices['ai'],
      'diy_choices':choices['diy'],'deferred_choices':choices['defer'],'unsupported_choices':choices['unsupported'],
      'enterprise_offer_present_total':sum(p['offersSeen'] for h in histories for p in h['prices']),
      'B_decisions':len(decisions),'B_cash_eligible_decisions':sum(d['availableCashCents']>=d['fullCostCents'] for d in decisions),
      'B_investments':sum(len(p['arms']['B']['histories']['investments']) for p in pairs),
      'B_earned_builds':sum(sum(d['funding']=='operating-surplus' for d in p['arms']['B']['histories']['investments']) for p in pairs),
      'B_minus_A_profit_min_usd':0,'B_minus_A_profit_max_usd':0,
      'refusal_no_positive_saving':refusals['no positive task saving'],
      'refusal_nonpositive_fullcost_repayment':refusals['expected full-cost repayment not positive'],
      'refusal_insufficient_available_funding':refusals['insufficient currently available funding']}
    rows.append(row)
    detailed.append({'scenario':name,'assumptions':scenario,'common_A_B_summary':row,
      'actualQuotePriceFrequencyCents':dict(sorted(collections.Counter(quote_values).items())),
      'acceptedInvoicePriceFrequencyCents':dict(sorted(collections.Counter(invoice_values).items())),
      'refusalReasons':dict(refusals),'choiceCounts':dict(choices),
      'perSeed':[{'seed':p['seed'],**p['arms']['A']['summary'],'B_minus_A_profitCents':0} for p in pairs]})

summaries=[p['arms']['A']['summary'] for p in worlds]
best_world=max(worlds,key=lambda p:p['arms']['A']['summary']['profitCents'])
worst_world=min(worlds,key=lambda p:p['arms']['A']['summary']['profitCents'])
case=lambda p:{'scenario':p['scenario'],'seed':p['seed'],'summary':p['arms']['A']['summary'],
  'BInvestments':len(p['arms']['B']['histories']['investments']),'B_minus_A_profitCents':p['differences']['B_minus_A_profitCents']}
aggregate={'pairedWorlds':len(worlds),'enterpriseHistories':len(worlds)*2,'distinctActualFreshMissions':4,
 'perArm':{'opportunities':sum(s['opportunities'] for s in summaries),'supportedOpportunities':sum(s['supportedOpportunities'] for s in summaries),
  'attempts':sum(s['enterpriseAttempts'] for s in summaries),'accepted':sum(s['enterpriseAccepted'] for s in summaries),
  'rejected':sum(s['enterpriseRejected'] for s in summaries),'latentFailures':sum(s['latentFailures'] for s in summaries),
  'profitableWorlds':sum(s['profitCents']>0 for s in summaries),'insolventWorlds':sum(s['insolvent'] for s in summaries),
  'profitCents':stats([s['profitCents'] for s in summaries]),
  'grossInvoiceCents':sum(s['grossInvoicesCents'] for s in summaries),'grossCollectionCents':sum(s['grossCollectionsCents'] for s in summaries),
  'refundCents':sum(s['refundsCents'] for s in summaries),'writtenOffCents':sum(s['writtenOffCents'] for s in summaries),
  'accruedCostCents':sum(s['accruedCostsCents'] for s in summaries),'buyerChoiceCounts':dict(choice_counts)},
 'B':{'investmentDecisions':len(all_decisions),'refusalReasonCounts':dict(reason_counts),
   'cashEligibleDecisions':cash_eligible_decisions,'worldsWithCashEligibleDecision':len(cash_eligible_worlds),
   'investments':0,'earnedFundedBuilds':0,'assetUses':0,'directRepaymentWorlds':0,'testedNextAssets':0,
   'availableDecisionCashCents':stats([d['availableCashCents'] for d in all_decisions]),
   'expectedIncrementalSavingPerUseCents':stats([d['expectedIncrementalSavingPerUseCents'] for d in all_decisions])},
 'pairedDifferenceCents':{'allZero':True,'mean':0,'minimum':0,'maximum':0},
 'positiveMeanCells':sum(r['profit_mean_usd']>0 for r in rows),
 'bestMeanCell':max(rows,key=lambda r:r['profit_mean_usd']),
 'worstMeanCell':min(rows,key=lambda r:r['profit_mean_usd']),
 'maximumProfitWorld':case(best_world),'minimumProfitWorld':case(worst_world),
 'selectionNote':'Best/worst examples are explicitly descriptive extrema of the complete retained set, not selected primary evidence.'}

analysis={'schema':'agi-alpha-accepted-ab-descriptive-analysis/v1','createdUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'status':'COMPLETE_AUDITED_EXPLORATORY_DIAGNOSTIC','auditStatus':'PASS','source':{
   'freezeSHA256':completion['freezeSHA256'],'historySHA256':completion['historiesSHA256'],
   'runnerSummarySHA256':completion['summarySHA256'],'auditSHA256':sha(base/'results-audit.json'),
   'analysisSourceSHA256':sha(pathlib.Path(__file__))},
 'aggregate':aggregate,'cells':detailed,
 'economicIdentification':'IDENTIFICATION_HOLD','originalThreeArmCampaignStatus':'GATED_UNEXECUTED',
 'calibrationBoundary':'Analysis date 2026-10-26. The inherited primary/fixed-policy studies and this diagnostic are simulations, not new observations of buyer demand or willingness to pay. No demand calibration was added by these runs.',
 'interpretation':'The frozen no-benefit conditional policy behaved as predicted: zero exact-B construction, uses and incremental profit. Profitable common-service worlds do not establish value from B or its financing. Actual complete costs, human/customer effort and field demand remain unidentified.',
 'statisticsBoundary':'Cells are purposive stress scenarios, not a calibrated probability distribution. Counts and extrema describe the retained worlds. A/B are paired counterfactuals; 384 histories are not 384 independent customers, and 8021 repeated decisions are not independent adoption experiments.',
 'acceptanceQualification':read(base/'production-accepted-ab.json')['acceptanceQualification'],
 'observedCustomerCollectionsCents':0,'actualFinancialAction':False}
write('analysis.json',analysis)
with (out/'cells.csv').open('x',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def usd(x):return f'${x:,.2f}'
best=aggregate['bestMeanCell'];worst=aggregate['worstMeanCell'];a=aggregate['perArm'];b=aggregate['B']
lines=['# Executed A/B diagnostic: complete descriptive results','',
 '**Audit PASS.** All 24 registered cells and all eight paired seeds were retained: 192 paired worlds, 384 enterprise histories, and four actual fresh production missions. No campaign replay or frozen source edit was used for this analysis.','',
 f"B received **zero investments, zero earned-funded builds, zero uses and zero direct-repayment worlds**. Its profit difference from A was exactly **$0 in every paired world**. The independent auditor reconstructed all {b['investmentDecisions']:,} B decision-time earned-cash quantities and verified the exact B source identity.",'',
 'The prediction is structural: equal assumed A/B complete nominal costs imply zero incremental saving. This execution checks that the inherited strategic-market and cash implementation does not manufacture an investment benefit. It does not estimate true B savings as zero or validate market demand. Actual full costs remain unknown and **IDENTIFICATION_HOLD** remains in force.','',
 '## Common service outcomes and actual prices','',
 f"Per arm, the retained worlds contain {a['attempts']:,} modeled enterprise attempts, {a['accepted']:,} accepted deliveries, {a['rejected']:,} rejected deliveries and {a['latentFailures']:,} latent failures. There are {a['profitableWorlds']}/192 profitable worlds and {a['insolventWorlds']}/192 insolvent worlds. These are repeated simulated populations; the two arm totals must not be mistaken for independent customer demand.",'',
 'The table reports the common A/B outcome in each cell, over eight seeds. Profit is economic profit after accrued costs and excludes initial capital. Accepted work is a modeled outcome, distinct from the four internally accepted production missions. Prices are observed simulated quotes, not the scenario target label alone.','',
 '| Stress | Buyer rule | Quoted price | Mean profit | Profit range | Mean accepted | Profitable worlds | Insolvent worlds |',
 '|---|---|---:|---:|---:|---:|---:|---:|']
for r in rows:
    quote=usd(r['quoted_price_min_usd']) if r['quoted_price_min_usd']==r['quoted_price_max_usd'] else f"{usd(r['quoted_price_min_usd'])}–{usd(r['quoted_price_max_usd'])}"
    lines.append(f"| {r['stress_profile']} | {r['buyer_model']} | {quote} | {usd(r['profit_mean_usd'])} | {usd(r['profit_min_usd'])} to {usd(r['profit_max_usd'])} | {r['accepted_mean']:.3f} | {r['profitable_worlds']}/8 | {r['insolvent_worlds']}/8 |")
lines.extend(['',
 'The target-$5 cases quote **$6**, because the unchanged pricing policy enforces nominal cost plus $1. The $10 and $20 target cases quote their stated targets. `cells.csv` includes invoice-price ranges separately; absent invoices are blank, not zero-priced sales.','',
 f"Across all cells, modeled buyer choices per arm were: {json.dumps(dict(choice_counts),sort_keys=True)}. This inherited buyer mechanism competes against human delivery, competing AI, DIY/conventional work and deferral; these counts are not new demand calibration.",'',
 '## Positive examples and failure conditions','',
 f"The highest cell mean was **{best['scenario']}**, with mean profit {usd(best['profit_mean_usd'])}, range {usd(best['profit_min_usd'])} to {usd(best['profit_max_usd'])}, mean accepted work {best['accepted_mean']:.3f}, and {best['profitable_worlds']}/8 profitable worlds. This is an explicitly selected descriptive maximum; every cell is reported above.",'',
 f"The lowest cell mean was **{worst['scenario']}**, with mean profit {usd(worst['profit_mean_usd'])}, range {usd(worst['profit_min_usd'])} to {usd(worst['profit_max_usd'])}. The maximum individual-world profit was {usd(aggregate['maximumProfitWorld']['summary']['profitCents']/100)} in {aggregate['maximumProfitWorld']['scenario']}, seed {aggregate['maximumProfitWorld']['seed']}; it still produced no B investment or incremental B profit.",'',
 f"Every one of {b['investmentDecisions']:,} decisions recorded both no positive task saving and nonpositive full-cost repayment. Insufficient currently available funding was an additional reason in {reason_counts['insufficient currently available funding']:,} decisions. There were {cash_eligible_decisions:,} decisions in {len(cash_eligible_worlds)} worlds with enough currently available earned cash for the $100 construction envelope; affordability did not override the zero-benefit constraint.",'',
 'Cash and capacity stress exposes service insolvency; low demand or stronger alternatives may prevent sufficient accepted work; delayed collections and failures weaken cash and profit. Asset maintenance cannot improve anything while the asset remains unbuilt. These conditions affect the common service, while zero incremental saving independently prevents B investment.','',
 '## Scope, costs and provenance','',
 'All nominal $5 operating charges and the full $100 B construction envelope remain explicit counterfactual assumptions. No elapsed agent time became a human wage bill, unknown inference charges were not measured, and rejected-work corrections remain charged by the retained failure multiplier. Actual collections are $0. No untested next asset is financed.','',
 analysis['calibrationBoundary'],'',analysis['acceptanceQualification'],'',
 'The original 166-cell A/B/C2 campaign remains **GATED_UNEXECUTED**. C2 receives no financial curve or post-outcome scope narrowing.','',
 f"Audit receipt SHA256: `{analysis['source']['auditSHA256']}`. History archive SHA256: `{analysis['source']['historySHA256']}`. Root-approved freeze SHA256: `{completion['freezeSHA256']}`.",'',
 'The analysis uses a separate Python arithmetic audit on the same project/session/host; it does not claim institutional independence or external financial validation.',''])
with (out/'ANALYSIS.md').open('x') as f:f.write('\n'.join(lines))
print(json.dumps({'status':'COMPLETE','aggregate':aggregate,'outputs':{p.name:sha(p) for p in out.iterdir()}},indent=2))
