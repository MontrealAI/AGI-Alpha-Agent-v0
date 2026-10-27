# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads((ROOT/p).read_text())
def save(p,v):(ROOT/p).write_text(json.dumps(v,indent=2,ensure_ascii=False)+'\n')
def main():
 audit_path=ROOT/'results/independent-followup-audit/summary.json'; audit=json.loads(audit_path.read_text())
 frozen=load('protocol/followup-candidate-freeze.json')
 assets={}
 for arm,label,identifier in [('B','B','source-intake-model-extraction/v1'),('C','C2','source-intake-conventional/v2')]:
  manifest={'schema':'agi-alpha-tested-asset/v1','id':identifier,'label':label,'testedEntryPoint':f'node src/workbench_v2.mjs RAW {arm} OUT'+(' PROPOSAL' if arm=='B' else ''),'candidateFreezeSha256':sha(ROOT/'protocol/followup-candidate-freeze.json'),'campaignSha256':audit['campaignSha256'],'sourceClosure':frozen['files'],'sourceClosureNote':'Full experimental identity closure includes common wrappers and inactive comparator files used only by provenance checks. The arm entry point determines the capability actually executed; no inactive algorithm gets productive credit.','requiredMechanism':'Prospective current-session model extraction, source-bound compiler and unchanged exact core' if arm=='B' else 'Retained ordinary source traversal, source-bound compiler and unchanged exact core','completeAcceptedJobs':audit['byArm'][arm]['completeHandoffAccepted'],'attemptedJobs':4,'productionApproved':False,'completeConstructionUsd':None,'costBoundary':'All discovery, failed candidates, correction, integration and shared allocation must be included. Original C failures are C2 ancestry. Shared pool charged once.'}
  relative=f'protocol/asset-{label}.json';save(relative,manifest)
  assets[arm]={'id':identifier,'path':relative,'sha256':sha(ROOT/relative)}
 evidence={'candidate':sha(ROOT/'protocol/followup-candidate-freeze.json'),'execution':sha(ROOT/'protocol/followup-execution-freeze.json'),'campaign':audit['campaignSha256'],'independentAudit':sha(audit_path),'verifier':audit['verifierSha256'],'assets':assets}
 evidence_sha=hashlib.sha256(json.dumps(evidence,sort_keys=True,separators=(',',':')).encode()).hexdigest()
 bridge={'schema':'agi-alpha-intake-transfer-production/v1','missions':['F01','F02','F03','F04'],'evidenceSHA256':evidence_sha,'evidenceClosure':evidence,'arms':{},'completeAcceptanceEvidence':{'status':'FAIL','scope':'complete-useful-deliverable','independentlyVerified':True,'receiptSHA256':sha(audit_path),'verifierSHA256':audit['verifierSha256']},'executedStepDistinction':{'A':'MODEL_OR_CURATOR','B':'MODEL_EXTRACTION','C':'NO_RUNTIME_MODEL','independentAcceptedScopeEquivalent':False,'evidenceSHA256':sha(audit_path)},'actualCollectionsUsd':0,'interpretation':'Three-arm market admission fails on C2 F03. A/B equivalence on all four registered jobs is independently accepted. No favorable common subset is substituted.'}
 for arm in ['A','B','C']:
  accepted=[r['task'] for r in audit['rows'] if r['arm']==arm and r['completeHandoffAccepted']]
  results=[load(f'results/followup/{task}/{arm}/delivery/result.json') for task in bridge['missions']]
  bridge['arms'][arm]={'attemptedMissionIds':bridge['missions'],'acceptedMissionIds':accepted,'completeRecurringCostCents':None,'completeConstructionCostCents':None,'resources':{'scope':'known-process-lower-bound','cpuSecondsPerAccepted':sum(r['resources']['cpuNs'] for r in results)/1e9/len(accepted),'wallSecondsPerAccepted':sum(r['resources']['wallNs'] for r in results)/1e9/len(accepted),'basis':'All attempted recorded process costs divided by accepted handoffs; outside-process model extraction, authoring, customer effort and full workflow remain unknown.'}}
  if arm!='A':bridge['arms'][arm]['asset']=assets[arm]
 save('market/production-followup.json',bridge)
 save('resources/accounting/final-asset-bindings.json',{'schema':'agi-alpha-asset-bindings/v1','assets':assets,'fullCostsKnown':False,'source':evidence,'C2RuntimeModelCalls':0,'C2CompleteEquivalence':False,'originalCConstructionAndFailuresRetained':True,'commonCostAllocation':'Unknown; not duplicated across mission and asset views.'})
 print(json.dumps({'bridgeSha256':sha(ROOT/'market/production-followup.json'),'assets':assets,'threeArmGate':'FAIL'}))
if __name__=='__main__':main()
