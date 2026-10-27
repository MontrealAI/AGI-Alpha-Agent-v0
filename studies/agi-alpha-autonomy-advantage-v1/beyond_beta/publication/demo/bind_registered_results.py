# SPDX-License-Identifier: Apache-2.0
"""Mechanical publication binding of the completed registered study.

Never runs the economic engine or chooses a new world, policy, price or skill.
The default world and first-paid-candidate rule are declared before inspection.
"""
from collections import Counter
from pathlib import Path
import argparse
import gzip
import hashlib
import json
import statistics

HERE=Path(__file__).resolve().parent
LANE=HERE.parents[1]
ROOT=LANE.parent


def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def load(path):return json.loads(Path(path).read_text())
def money(x,fr=False):
    if x is None:return 'indéfini' if fr else 'undefined'
    text=f'{x:,.0f}'
    return text.replace(',','\u202f')+' USD' if fr else 'USD '+text


def first_paid(world):
    candidate=next((x for x in world['candidates'] if x['source']=='PAID_JOB_LEARNING_A'),None)
    if candidate is None:return None
    origin=next(j for j in world['jobs'] if j['id']==candidate['originJobId'])
    bills=world['cash']['bills'];invoice=next((x for x in world['cash']['invoices'] if x['jobId']==origin['id']),None)
    receipt=(invoice['amountMicros']/1e6 if invoice and invoice['status']=='collected' else 0)
    if invoice:receipt-=sum(b['amountMicros']/1e6 for b in bills if b['ref']==invoice['id'] and b['category'] in ('paymentFees','refunds'))
    asset=next((x for x in world['assets'] if x['id']==candidate['id']),None)
    decision=next((x for x in world['investmentDecisions'] if x['candidateId']==candidate['id']),None)
    checkpoint=decision.get('cashCheckpoint') if decision else None
    earned=checkpoint['funds']['availableOperating']-sum(checkpoint['publicHoldsUSD'].values()) if checkpoint else None
    return {'id':candidate['id'],'originJobId':origin['id'],'originUsefulAccepted':origin['usefulAccepted'],'originNetReceiptUSD':receipt,
            'state':candidate['state'],'originCompletionWeek':origin['completionWeek'],'originCollectionWeek':invoice['collectedAt']/7 if invoice and invoice.get('collectedAt') is not None else None,'decisionWeek':decision['week'] if decision else None,'originDeliveryAUSD':sum(b['amountMicros'] for b in bills if b['ref']==origin['id'] and b.get('ledger')=='A')/1e6,
            'retentionBUSD':sum(b['amountMicros'] for b in bills if b['ref']==candidate['id'] and b.get('ledger')=='B')/1e6,
            'researchCUSD':sum(b['amountMicros'] for b in bills if b['ref']==candidate['id'] and b.get('ledger')=='C')/1e6,
            'availableDecisionFundsUSD':decision['fundsBefore'] if decision else None,'earnedFundsAfterHoldsUSD':earned,
            'wholeInitialFunding':decision.get('wholeInitialProgramFundingOrigin') if decision else None,
            'freshQualificationCases':sum(len(x['cases']) for x in asset.get('qualificationTruth',[])) if asset else 0,
            'subsequentUses':asset['useCount'] if asset else 0,'directAttributedNetUSD':asset.get('realizedDirectNetUSD') if asset else None}


def normalized_world(world,protocol):
    s=world['summary'];useful=[j for j in world['jobs'] if j['usefulAccepted']];offers={o['id']:o for o in world['offers']};bills=world['cash']['bills']
    spending={key:sum(b['amountMicros'] for b in bills if b.get('ledger','FINANCIAL')==key)/1e6 for key in ('A','B','C','OPERATIONS','FINANCIAL')}
    profile_index={'efficient':0,'reference':1,'burdensome':2}[s['profile']]
    metrics={'priceAcceptedMean':statistics.mean(j['priceUSD'] for j in useful) if useful else None,
             'humanReferenceAcceptedMean':statistics.mean(offers[j['id']]['humanReferenceUSD'] for j in useful) if useful else None,
             'meanTurnaroundDays':statistics.mean(7*(j['completionWeek']-j['week']) for j in world['jobs']) if world['jobs'] else None,
             'customerIntakeHours':protocol['buyers']['customerIntakeHours'][profile_index]}
    return {'summary':s,'spending':spending,'metrics':metrics,'seedUSD':world['cash']['seedUsd'],
            'remainingReservedUSD':world['cash']['funds']['reserve']+world['cash']['funds']['unpaid'],
            'cashRows':[[r['t']/7,round(r['cash'],2),round(r['availableOperating'],2)] for r in world['cash']['snapshots']] if s['scenario']=='reference' and s['seed']==1001 else [],
            'candidateStates':dict(Counter(c['state'] for c in world['candidates'])),
            'firstPaidCandidate':first_paid(world),
            'initialRetentionFunding':dict(Counter(d.get('wholeInitialProgramFundingOrigin','NOT_RECORDED') for d in world['investmentDecisions'] if d['decision']=='RETAIN'))}


def claims(worlds,analysis):
    ref=[w for w in worlds if w['summary']['scenario']=='reference'];beta=[w for w in ref if w['summary']['arm']=='trained-beta'];net=[w for w in ref if w['summary']['arm']=='network-alpha']
    accepted=sum(w['summary']['accepted'] for w in beta);full=sum(w['summary']['completeCostsUSD'] for w in beta)/accepted if accepted else None
    human=sum((w['metrics']['humanReferenceAcceptedMean'] or 0)*w['summary']['accepted'] for w in beta)/accepted if accepted else None
    positive=sum(w['summary']['completeProfitUSD']>0 for w in beta);n=len(beta)
    p=analysis['paired']['reference'];alpha=p['incrementalAlphaMovingUSD'];sharing=p['sharingVersusPrivateUSD'];erosion=p['erosionInteractionUSD']
    interval=lambda row,fr=False:f"{money(row['mean'],fr)} [{money(row['conditionalMeanCI95'][0],fr)}, {money(row['conditionalMeanCI95'][1],fr)}]"
    funded=sum(w['initialRetentionFunding'].get('OPERATING_GENERATED',0) for w in net)
    return [
      {'id':'claimDelivery','status':'conditional','en':f'The trained Beta policy delivers {accepted:,} useful accepted modeled jobs across the 40 reference histories; {positive}/{n} have positive complete profit. No actual customer jobs were executed.','fr':f'La politique Bêta choisie livre {accepted:,} travaux utiles acceptés dans les 40 historiques de référence; {positive}/{n} ont un bénéfice complet positif. Aucun travail client réel n’a été exécuté.'},
      {'id':'claimHuman','status':'conditional','en':f'Pooled full Beta cost per useful accepted job: {money(full)}. Matched human-service reference: {money(human)}. The latter is a task/rate assumption, not observed human labor or a quote.','fr':f'Coût Bêta complet par travail utile accepté, calculé globalement: {money(full,True)}. Référence de service humain correspondante: {money(human,True)}. Cette référence repose sur des hypothèses de travail et de taux, sans mesure de travail humain ni devis.'},
      {'id':'claimAlpha','status':'conditional','en':'Reference paired complete-profit increment, mean [conditional 95% interval]: '+interval(alpha)+'. All A/B/C and business costs remain included.','fr':'Écart apparié du bénéfice complet en référence, moyenne [intervalle conditionnel à 95%]: '+interval(alpha,True)+'. Tous les coûts A/B/C et d’exploitation restent inclus.'},
      {'id':'claimSharing','status':'conditional','en':'Shared availability minus creator-private availability: '+interval(sharing)+'. Availability and reuse counts alone are not net value.','fr':'Disponibilité partagée moins disponibilité privée du créateur: '+interval(sharing,True)+'. La disponibilité et le nombre d’utilisations ne suffisent pas à établir une valeur nette.'},
      {'id':'claimGraph','status':'notTested','en':'A separate graph-versus-strong-registry economic advantage was not isolated. The implemented admission graph supplies governed availability.','fr':'Un avantage économique distinct du graphe sur un registre robuste n’a pas été isolé. Le graphe d’admission implémenté régit la disponibilité.'},
      {'id':'claimLifecycle','status':'observed','en':'Local encryption, signatures, typed commitments and canonical reuse gates execute in offline fixtures. They do not establish live ENS identity, task correctness or commercial value.','fr':'Le chiffrement, les signatures, les engagements typés et les contrôles d’utilisation canoniques sont exécutés dans des fixtures hors ligne. Ils n’établissent ni une identité ENS en production, ni la justesse du travail, ni sa valeur commerciale.'},
      {'id':'claimErosion','status':'conditional','en':'Moving-versus-frozen Alpha interaction in the reference condition: '+interval(erosion)+'. Future Beta versions are scenario assumptions, not forecasts validated against future models.','fr':'Interaction d’Alpha avec Bêta mobile ou figé en référence: '+interval(erosion,True)+'. Les versions futures de Bêta sont des hypothèses de scénario, sans validation sur des modèles futurs.'},
      {'id':'claimFunding','status':'conditional','en':f'{funded} initial retention decisions in the 40 reference network histories are tagged as entirely operating-funded, including assessment. This count alone does not establish net investment value or self-acceleration.','fr':f'{funded} décisions initiales de conservation dans les 40 historiques de référence en réseau sont identifiées comme entièrement financées par l’exploitation, évaluation comprise. Ce nombre seul n’établit ni une valeur nette d’investissement ni une auto-accélération.'}
    ]


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--bind',action='store_true');args=parser.parse_args()
    if not args.bind:print('No result files read. Use --bind only after COMPLETE and the independent audits.');return
    results=LANE/'results/primary';freeze_path=LANE/'protocol/source-freeze.json';freeze=load(freeze_path);protocol=load(LANE/'protocol.json');selection_rule=load(HERE/'demo-selection.json')
    for item in freeze['files']:
        path=ROOT/item['path']
        if path.stat().st_size!=item['bytes'] or sha(path)!=item['sha256']:raise ValueError('Frozen source changed: '+item['path'])
    expected=hashlib.sha256(json.dumps(freeze['files'],sort_keys=True,separators=(',',':')).encode()).hexdigest()
    if expected!=freeze['sourceId'] or sha(LANE/'protocol.json')!=freeze['protocolSHA256']:raise ValueError('Source freeze identity mismatch')
    if selection_rule['world']!=protocol['experiment']['demonstrationPreselection'] or selection_rule['protocolSHA256']!=freeze['protocolSHA256']:raise ValueError('Prospective demo selection changed')
    campaign=load(results/'summary.json');selection=load(results/'training-selection-freeze.json');analysis_path=LANE/'analysis/analysis.json';analysis=load(analysis_path)
    if campaign['status']!='COMPLETE':raise ValueError('Completed registered campaign required')
    if campaign['trainingHistories']!=protocol['experiment']['trainingHistories'] or campaign['confirmationHistories']!=protocol['experiment']['confirmationHistories']:raise ValueError('Incomplete history counts')
    if selection['confirmationHistoriesAlreadyRun']!=0 or selection['trainingWorldsSha256']!=sha(results/'training-worlds.jsonl.gz') or selection['trainingSelectionSha256']!=sha(results/'training-selection.json'):raise ValueError('Training selection does not bind its untouched inputs')
    audit_paths=[LANE/'validation/economic-audit-training.json',LANE/'validation/economic-audit-confirmation.json']
    diagnostic_paths=[LANE/'validation/economic-audit-training-epoch-diagnostic.json',LANE/'validation/economic-audit-confirmation-epoch-diagnostic.json']
    audit_record=[]
    for audit_path,diagnostic_path,worldfile,count in zip(audit_paths,diagnostic_paths,['training-worlds.jsonl.gz','worlds.jsonl.gz'],[campaign['trainingHistories'],campaign['confirmationHistories']]):
        audit=load(audit_path);diagnostic=load(diagnostic_path);input_sha=sha(results/worldfile)
        if audit['worlds']!=count or audit['inputSha256']!=input_sha:raise ValueError('Original independent audit does not bind all matching histories: '+str(audit_path))
        if diagnostic['status']!='PASS' or diagnostic['worlds']!=count or diagnostic['inputSha256']!=input_sha or diagnostic['originalAuditSha256']!=sha(audit_path) or diagnostic['originalAuditStatus']!=audit['status'] or not diagnostic['allOriginalFailuresExplainedExactly']:raise ValueError('Post-freeze diagnostic does not explain the preserved original audit: '+str(diagnostic_path))
        if diagnostic['economicWorldsExecuted']!=0 or diagnostic['economicHistoriesModified']!=0 or diagnostic['selectionModified']:raise ValueError('Diagnostic cannot regenerate histories or change selection')
        if diagnostic['diagnosticSha256']!=sha(LANE/'validation/audit_epoch_diagnostic.py'):raise ValueError('Diagnostic source identity changed')
        audit_record.append({'historyFile':worldfile,'worlds':count,'originalStatus':audit['status'],'originalFailureCount':len(audit['failures']),'originalChecks':audit['checks'],'diagnosticStatus':diagnostic['status'],'diagnosticChecks':diagnostic['checks'],'diagnosticReuseReceipts':diagnostic['historicalReuseReceiptsAudited'],'explainedEpochMismatchWorlds':len(diagnostic['epochMismatchWorlds']),'explainedEpochMismatchUses':diagnostic['epochMismatchUses'],'allOriginalFailuresExplainedExactly':diagnostic['allOriginalFailuresExplainedExactly']})
    if analysis['sourceSummarySHA256']!=sha(results/'summary.json'):raise ValueError('Analysis summary binding mismatch')
    worlds=[]
    with gzip.open(results/'worlds.jsonl.gz','rt') as stream:
        for line in stream:worlds.append(normalized_world(json.loads(line),protocol))
    identity=lambda s:(s['scenario'],s['seed'],s['arm'])
    if len(worlds)!=campaign['confirmationHistories'] or {identity(w['summary']) for w in worlds}!={identity(s) for s in campaign['rows']}:raise ValueError('Missing or substituted world')
    row_map={identity(s):s for s in campaign['rows']}
    if any(w['summary']!=row_map[identity(w['summary'])] for w in worlds):raise ValueError('World summaries changed')
    conditions=[]
    for scenario in protocol['scenarios']:
        sid=scenario['id'];paired=analysis['paired'][sid];beta=next(c for c in campaign['cells'] if c['scenario']==sid and c['arm']=='trained-beta')
        conditions.append({'scenario':sid,'pairedWorlds':paired['incrementalAlphaMovingUSD']['n'],'betaMeanCompleteProfitUSD':beta['meanCompleteProfitUSD'],'meanOptionalCompleteProfitUSD':next(c['meanCompleteProfitUSD'] for c in campaign['cells'] if c['scenario']==sid and c['arm']=='network-alpha'),'meanWholePolicyIncrementUSD':paired['trainedWholePolicyUSD']['mean'],'meanAlphaIncrementUSD':paired['incrementalAlphaMovingUSD']['mean'],'meanSharingIncrementUSD':paired['sharingVersusPrivateUSD']['mean'],'pairedDistributions':paired})
    files=[freeze_path,LANE/'protocol.json',HERE/'demo-selection.json',HERE/'REPORTING_PRIORITY_AMENDMENT.md',results/'run-inputs.json',results/'summary.json',results/'worlds.jsonl.gz',results/'training-worlds.jsonl.gz',results/'training-selection-freeze.json',results/'training-selection.json',analysis_path,*audit_paths,*diagnostic_paths,LANE/'validation/audit_epoch_diagnostic.py',LANE/'validation/native-temporal-source-review.json',Path(__file__)]
    operational={'continuationUsed':campaign.get('operationalContinuation',False),'originalFailure':None,'continuation':None,'recovery':None,'recordedCampaignWallSecondsLowerBound':campaign.get('wallSeconds'),'originalCpuTimeUnavailable':campaign.get('originalCpuTimeUnavailable',False),'timingBoundary':'Partial operational lower bound only. Original interrupted computation, recovery, research and publication costs are not completely measured; this is not complete study time or service turnaround.'}
    if operational['continuationUsed']:
        for name in ['failure.json','continuation-start.json','continuation-completion.json']:
            files.append(results/name)
        failure=load(results/'failure.json');completion=load(results/'continuation-completion.json');start=load(results/'continuation-start.json')
        operational['originalFailure']=failure;operational['continuation']=completion
        operational['originalRecordedWallSecondsLowerBound']=failure['wallSeconds']
        operational['continuationCompletionWallSeconds']=completion['continuationWallSeconds']
        operational['combinedCompletionWindowLowerBoundSeconds']=failure['wallSeconds']+completion['continuationWallSeconds']
        operational['timingCheckpointNote']='Campaign summary closes before final completion-manifest writing; its partial wall-time checkpoint and the later completion-manifest elapsed time are retained separately.'
        files.extend([LANE/'publication/RUNTIME_CONTINUATION_AMENDMENT.md',LANE/'publication/continue_prespecified_campaign.py'])
        recovery_path=results/'recovery-manifest.json'
        if recovery_path.exists():
            recovery=load(recovery_path);recovered=load(results/recovery['recordHashLedger'])
            original=results/'training-interrupted-original.jsonl.gz';tail=results/'interrupted-unfinished-tail.bin'
            if sha(original)!=recovery['originalSHA256'] or original.stat().st_size!=recovery['originalBytes']:raise ValueError('Preserved interrupted byte stream changed')
            if sha(tail)!=recovery['unfinishedTailSHA256'] or tail.stat().st_size!=recovery['unfinishedTailBytes']:raise ValueError('Preserved interrupted tail changed')
            if len(recovered)!=recovery['recoveredCompleteRecords'] or failure['historiesWritten']!=len(recovered):raise ValueError('Recovery count mismatch')
            with gzip.open(results/'training-worlds.jsonl.gz','rb') as stream:
                for i,entry in enumerate(recovered):
                    line=stream.readline()
                    if entry['index']!=i or len(line)!=entry['bytes'] or hashlib.sha256(line).hexdigest()!=entry['sha256']:raise ValueError('Recovered complete record changed at '+str(i))
            prefix=start['originalPrefixes']['training-worlds.jsonl.gz'];h=hashlib.sha256()
            with (results/'training-worlds.jsonl.gz').open('rb') as stream:
                remaining=prefix['bytes']
                while remaining:
                    block=stream.read(min(1024*1024,remaining))
                    if not block:raise ValueError('Missing recovered compressed prefix')
                    h.update(block);remaining-=len(block)
            if h.hexdigest()!=prefix['sha256'] or prefix['sha256']!=recovery['recoveredGzipSHA256']:raise ValueError('Recovered gzip prefix changed')
            operational['recovery']=recovery
            operational['recoveryVerification']={'completeRecordHashesVerified':len(recovered),'originalBytesVerified':True,'unfinishedTailVerified':True,'recoveredCompressedPrefixVerified':True,'newEconomicHistoriesExecuted':0}
            files.extend([recovery_path,results/recovery['recordHashLedger'],original,tail,LANE/'publication/recover_storage_prefix.py'])
    record={'schema':'beyond-beta-demo-results/v1','classification':'MECHANICAL_POST_RUN_PUBLICATION_BINDING_NO_NEW_HISTORIES','sourceFreezeId':freeze['sourceId'],'sourceRegistrationUrl':'https://github.com/MontrealAI/AGI-Alpha-Agent-v0/issues/4850#issuecomment-6430094089','demonstrationPreselection':selection_rule['world'],'candidateSelectionRule':selection_rule['candidateRule'],'reportingPriority':'Commercial trained-Beta viability first; optional retention, sharing and investment afterward. Original fixed example unchanged.',
            'boundFiles':[{'path':str(path.relative_to(ROOT)),'sha256':sha(path)} for path in files],'campaignCounts':{'training':campaign['trainingHistories'],'confirmation':campaign['confirmationHistories']},'selection':campaign['selection'],
            'worlds':worlds,'conditions':conditions,'claims':claims(worlds,analysis),'audits':audit_record,'auditBoundary':'Original confirmation audit passes. Original training audit retains 51 epoch flags. The separately labeled post-freeze diagnostic counts Beta/policy epoch advances omitted by the frozen auditor and rechecks every preserved history without changing selection or simulation data.','operational':operational,'embeddedCashSelection':'Reference/1001 across all six arms, fixed before outcome inspection; every other full cash trace stays in the bound archive.',
            'displayRounding':'Cash-chart USD coordinates rounded to cents; all original summaries and complete raw traces remain unchanged and hash-bound.',
            'reportingCorrection':'Funding summaries use final engine wholeInitialProgramFundingOrigin/assessmentFundingOrigin/constructionFundingOrigin. The frozen analyzer legacy fundingOrigin aggregate is not used. No economic history, policy or cost is altered.',
            'uncertainty':'Conditional bootstrap intervals describe Monte Carlo variation inside all declared assumptions, not empirical uncertainty about actual future demand or model competence. Stress conditions are not pooled as a market distribution.',
            'actualCommercialJobs':0,'actualRevenueUSD':0,'actualCompleteCostUSD':None}
    destination=HERE/'registered-results.json'
    if destination.exists():raise FileExistsError('Preserve the existing binding; inspect and version any correction explicitly.')
    destination.write_text(json.dumps(record,ensure_ascii=False,separators=(',',':'))+'\n')
    print(json.dumps({'status':'BOUND','worlds':len(worlds),'conditions':len(conditions),'file':str(destination),'economicWorldsExecuted':0}))


if __name__=='__main__':main()
