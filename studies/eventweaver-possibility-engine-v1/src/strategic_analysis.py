import json, random, math
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[1]

def game():
 r=random.Random(65001);n=4000;buyers=[]
 for _ in range(n):
  value=6500*r.lognormvariate(0,.4);urgency=r.uniform(3,18);hours=r.uniform(6,16)+r.uniform(4,8);review=405
  outside=max(0,.94*value-hours*135-review-14*urgency,.91*value-(hours+4)*135-review-21*urgency)
  buyers.append((.94*value-review-250-10*urgency,.96*value-review-50-7*urgency,outside))
 b=np.array(buyers);prices=np.arange(900,3001,300);report={}
 for arrangement,cost in [('individual',900),('shared_core_same_rights_for_both',720)]:
  pa=np.zeros((len(prices)+1,len(prices)+1));pb=pa.copy();qa=pa.copy();qb=pa.copy()
  for i in range(len(prices)+1):
   for j in range(len(prices)+1):
    u=b[:,0]-prices[i] if i<len(prices) else np.full(n,-np.inf)
    v=b[:,1]-prices[j] if j<len(prices) else np.full(n,-np.inf)
    ca=(u>v)&(u>=b[:,2]);cb=(v>=u)&(v>=b[:,2]);a=20*ca.mean();c=20*cb.mean();qa[i,j]=a;qb[i,j]=c
    pa[i,j]=a*(prices[i]-cost)-23000 if i<len(prices) else 0
    pb[i,j]=c*(prices[j]-cost) if j<len(prices) else 0
  active=[];entry=[]
  for i in range(len(prices)):
   for j in range(len(prices)):
    if pa[i,j]>=pa[:-1,j].max()-1e-8 and pb[i,j]>=pb[i,:-1].max()-1e-8:
     active.append({'ours_price':int(prices[i]),'rival_price':int(prices[j]),'ours_profit':float(pa[i,j]),'rival_contribution':float(pb[i,j]),'ours_orders':float(qa[i,j]),'rival_orders':float(qb[i,j])})
  for i in range(len(prices)+1):
   for j in range(len(prices)+1):
    if pa[i,j]>=pa[:,j].max()-1e-8 and pb[i,j]>=pb[i,:].max()-1e-8:
     entry.append({'ours_action':int(prices[i]) if i<len(prices) else 'do_not_enter','rival_action':int(prices[j]) if j<len(prices) else 'exit','ours_profit':float(pa[i,j]),'rival_contribution':float(pb[i,j])})
  xa=np.ones(len(prices)+1)/(len(prices)+1);xb=xa.copy();temp=500
  for _ in range(500):
   va=pa@xb;vb=xa@pb;na=np.exp((va-va.max())/temp);nb=np.exp((vb-vb.max())/temp);na/=na.sum();nb/=nb.sum();xa=.8*xa+.2*na;xb=.8*xb+.2*nb
  report[arrangement]={'unit_cost_assumption_both':cost,'startup_ours':23000,'incumbent_incremental_fixed_cost':0,'conditional_active_pure_nash':active,'entry_pure_nash':entry,'bounded_rational_logit_temperature_usd':temp,'logit_ours_exit_probability':float(xa[-1]),'logit_rival_exit_probability':float(xb[-1]),'payoffs_ours':pa.tolist(),'payoffs_rival':pb.tolist(),'price_actions':prices.tolist()+['exit']}
 return {'scope':'Separate stylized finite price game, not a fitted market model or a replacement for the frozen lifecycle simulation. Conditional on4000 synthetic buyer types and20 expected qualified opportunities. Shared arrangement available equally to rival.','information':'Buyers privately know value, urgency and internal cost. Firms know the assumed type distribution and post prices simultaneously. Buyers select maximal expected utility including internal/free/do-nothing alternatives. Firms may decline entry.','behavior':'Pure best responses on finite grid; ties favor incumbent. Logit responses test bounded rationality. Lifecycle bargaining uses observed counter-bids rather than private reservation prices; no truthfulness claim.','seed':65001,'games':report,'collection_subgame':{'rule':'A buyer with final source and no penalty can save the remaining balance by withholding payment. Compliance requires expected enforcement/reputation/support loss at least as large as the unpaid balance.','illustration':'At a USD1140 negotiated fee and40% deposit, remaining balance684. An assumed0.75 enforcement probability times1.5times balance plus50continuation value exceeds684. These are unmeasured assumptions. The no_collection_recourse scenario sets all postdelivery balances to default.','policy_implication':'Escrow or payment-before-final-source handoff could change incentives, but must permit independent buyer inspection and be tested under a new contract; not assumed into frozen results.'},'supplier_bargaining':{'rule':'Supplier quotes a rate and scarce capacity; buyer refuses above fixed USD180/hour reservation. Cost/capacity shocks are conditional scenarios, not an inferred bargaining equilibrium. Supplier outside wages and switching costs remain unknown.'}}

if __name__=='__main__':
 report=game();(ROOT/'results/strategic_game.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps({k:{'active':v['conditional_active_pure_nash'],'entry':v['entry_pure_nash'],'exit_probability':v['logit_ours_exit_probability']} for k,v in report['games'].items()},indent=2))
