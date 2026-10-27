# SPDX-License-Identifier: Apache-2.0
"""Handwritten accounting records; no economic engine or calibrated world runs."""
from copy import deepcopy
from pathlib import Path
import json

from audit_economic_trace import audit_world, AuditFailure, commitment, sum_resources


def fixture():
    def work(tokens, time):
        return {'astraInput':tokens,'astraOutput':0,'terraInput':0,'terraOutput':0,'cpuHours':time,'requests':1,'modelHours':time,'storageGbDays':0,'tools':0}
    producer, verifier, extra = work(10,.2), work(5,.1), work(1,.05)
    delivery = sum_resources([producer,verifier])
    a={'id':'bill-0','ref':'job-0','amountMicros':1_000_000,'ledger':'A','category':'completeDelivery','paid':True,'paidAt':7,'t':7,'due':7,'resource':delivery}
    b={'id':'bill-1','ref':'job-0','amountMicros':200_000,'ledger':'B','category':'retentionDiscoveryAndIntegration','paid':True,'paidAt':7,'t':7,'due':7,'resource':extra}
    for bill in [a,b]:bill['commitment']=commitment(bill)
    funds={'accruedMicros':1_200_000,'paidMicros':1_200_000,'collectedMicros':3_000_000,'cashMicros':11_800_000,'unpaidMicros':0}
    allocations=[{'week':0,'worker':0,'modelHours':.25,'cpuHours':.25,'tokens':11,'requests':2},{'week':0,'worker':1,'modelHours':.1,'cpuHours':.1,'tokens':5,'requests':1}]
    job={'id':'job-0','week':0,'completionWeek':1,'finished':True,'worker':0,'technicalAccepted':True,'usefulAccepted':True,'billId':'bill-0','costUSD':1,'additionalRetentionUSD':.2,'maximumCostUSD':2,'reservation':{'allocations':allocations},'stages':[{'stage':'specify','costUSD':.6,'resources':producer,'role':'producer','worker':0},{'stage':'verify','costUSD':.4,'resources':verifier,'role':'independent-verifier','worker':1}]}
    evidence={'capturedEpoch':1,'costOwnership':{'originJobCosts':[{'jobId':'job-0','ledgerCommitment':a['commitment'],'costMicros':1_000_000,'ownership':'DELIVERY_A_ALREADY_CHARGED'}],'retentionEntries':[{'chargeId':'bill-1','ledgerCommitment':b['commitment'],'costs':{'adaptation':200_000},'ownership':'INCREMENTAL_RETENTION_B'}],'researchEntries':[]},'arms':{'candidate':{'lifecycleCosts':{'adaptation':200_000}}}}
    summary={'scenario':'fixture','profile':'fixture','seed':0,'arm':'fixture','completeProfitUSD':1.8,'completeCostsUSD':1.2,'collectionsUSD':3,'actualRevenueUSD':0,'actualCompleteCostUSD':None,'cashValid':True,'ledgerCostsMicros':{'A':1_000_000,'B':200_000},'retentionResearchProgramCostUSD':.2,'accepted':1,'technicalAccepted':1,'falsePasses':0,'costPerAcceptedUSD':1.2}
    world={'summary':summary,'cash':{'seedMicros':10_000_000,'t':14,'bills':[a,b],'invoices':[{'jobId':'job-0','amountMicros':3_000_000,'status':'collected','warrantyUntil':7}],'funds':funds,'insolvent':False},'pendingEvents':[],'unspentPublicCostHolds':{},'actualModelCalls':0,'costCategoriesMicros':{'completeDelivery':1_000_000,'retentionDiscoveryAndIntegration':200_000},'jobs':[job],'graph':{'records':[{'evidence':evidence}]},'resourceSchedules':[{'allocations':allocations}],'resourceConsumption':[delivery,extra],'investmentDecisions':[]}
    protocol={'experiment':{'weeks':2},'network':{'agentCount':2},'scenarios':[{'id':'fixture','overrides':{}}],'capacity':{'modelHoursPerAgentWeek':1,'proofContainerHoursPerAgentWeek':1,'tokensPerMinuteTotal':100,'requestsPerMinuteTotal':1}}
    return world,protocol


def main():
    w,p=fixture();positive=audit_world(w,p);results=[{'id':'consistent-handwritten-record','passed':positive['status']=='PASS'}]
    controls=[
        ('origin-A-recharged-as-retention',lambda x:x['graph']['records'][0]['evidence']['arms']['candidate']['lifecycleCosts'].update(construction=1_000_000),'Alpha fixed denominator includes B+C exactly and excludes A'),
        ('unbound-incremental-bill',lambda x:x['graph']['records'][0]['evidence']['costOwnership']['retentionEntries'][0].update(chargeId='missing'),'Admission B/C binds the actual bill and immutable commitment'),
        ('accepted-denominator-inflation',lambda x:x['summary'].update(accepted=2),'Accepted denominator contains useful accepted outcomes only'),
        ('pending-work-erased-at-terminal',lambda x:x['pendingEvents'].append(['job',{'completionWeek':99}]),'Settlement leaves no pending operational events or cost holds'),
        ('cost-reclassified-with-stale-commitment',lambda x:x['cash']['bills'][1].update(ledger='A'),'Immutable amount/account commitment bill-1'),
        ('verifier-is-producer',lambda x:x['jobs'][0]['stages'][1].update(worker=0),'Independent checks use another worker job-0'),
        ('actual-resource-exceeds-worker-reservation',lambda x:x['jobs'][0]['reservation']['allocations'][0].update(tokens=1),'Consumed commission resources fit reserved capacity job-0'),
        ('unavailable-funding-claimed',lambda x:x['investmentDecisions'].append({'decision':'RETAIN','reservedUSD':3,'fundsBefore':2}),'Investment respects recorded available finite funds'),
    ]
    for name,mutate,expected in controls:
        bad=deepcopy(w);mutate(bad)
        try:audit_world(bad,p)
        except AuditFailure as exc:
            assert str(exc)==expected,(name,str(exc),expected)
            results.append({'id':name,'passed':True,'refusal':str(exc)})
        else:raise AssertionError('Mutation incorrectly accepted: '+name)
    result={'schema':'beyond-beta-economic-auditor-controls/v1','basis':'HANDWRITTEN_TRACE_CONTROLS_NO_SIMULATOR_EXECUTION','status':'PASS','controls':results,'economicWorldsExecuted':0}
    output=Path(__file__).with_name('economic-auditor-controls-v2.json')
    if output.exists():raise FileExistsError('Preserve old controls; select a new version path before running.')
    output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'status':'PASS','controls':len(results),'economicWorldsExecuted':0}))


if __name__=='__main__':main()
