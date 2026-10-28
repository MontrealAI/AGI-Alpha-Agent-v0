import csv,gzip,json,math,statistics,sys
from collections import defaultdict
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch,FancyArrowPatch
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'paper/figures';OUT.mkdir(parents=True,exist_ok=True)
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False,'axes.labelcolor':'#23364a','text.color':'#13283b','axes.edgecolor':'#ccd5de','xtick.color':'#40576a','ytick.color':'#40576a','figure.facecolor':'white','savefig.facecolor':'white','pdf.fonttype':42,'svg.fonttype':'none'})
NAVY='#102a43';TEAL='#087f8c';GOLD='#d69a2d';RED='#b94046';BLUE='#5572b9'
def save(fig,name):
 fig.savefig(OUT/(name+'.pdf'),bbox_inches='tight');fig.savefig(OUT/(name+'.svg'),bbox_inches='tight');fig.savefig(OUT/(name+'.png'),dpi=150,bbox_inches='tight');plt.close(fig)
report=json.loads((ROOT/'results/business_confirmation.json').read_text());base=report['summaries']['base'];tech=json.loads((ROOT/'results/technical_confirmation/summary.json').read_text());suc=json.loads((ROOT/'results/successor_confirmation/summary.json').read_text())
rows=list(csv.DictReader((ROOT/'results/business_confirmation.csv').open()));br=[r for r in rows if r['scenario']=='base'];costs=defaultdict(float);prices=[];counts=defaultdict(int);realized=[];finaldays=[]
with gzip.open(ROOT/'results/business_confirmation_journals.jsonl.gz','rt') as f:
 for line in f:
  d=json.loads(line)
  if d['scenario']!='base':continue
  for j in d['journal']:
   if j['debit'].startswith('expense:'):costs[j['debit'][8:]]+=j['cents']/100
  for l in d['lifecycle']:
   counts[l['status']]+=1
   if l['status']=='acceptance':
    buyer=next(b for b in d['buyers'] if b['id']==l['buyer']);prices.append(buyer['price'])
  if d['mean_buyer_realized_benefit'] is not None:realized.append(d['mean_buyer_realized_benefit'])
  finaldays.append(d['final_day'])
costs={k:v/1024 for k,v in costs.items()};direct_keys=['delivery','inference','compute_tools','correction','support','warranty_repair','common_mode_repair','renewal_delivery','renewal_sales','bad_debt','shared_batch_validation','coordination'];direct=sum(costs.get(k,0) for k in direct_keys);other=sum(costs.values())-direct;n=base['accepted']['mean'];rpu=base['net_revenue']['mean']/n;dpu=direct/n;margin=rpu-dpu
derived={'cost_categories_mean':costs,'mean_negotiated_accepted_price':statistics.mean(prices),'revenue_including_renewals_per_accepted':rpu,'direct_cost_including_failed_work_per_accepted':dpu,'marginal_contribution_accounting_approximation':margin,'other_project_costs':other,'break_even_accepted_at_constant_mix':math.ceil(other/margin) if margin>0 else None,'break_even_price_addition_at_unchanged_demand':-base['full_profit']['mean']/n,'required_accepted_price_at_unchanged_demand':statistics.mean(prices)-base['full_profit']['mean']/n,'direct_cost_reduction_needed_for_break_even':-base['full_profit']['mean']/direct,'max_orders_from_reserved_capacity_180days':int(18*(180/7)/(3+8)),'loss_precision_se_usd':base['full_profit']['se_mean'],'ratio_of_mean_profit_to_mean_cost':base['full_profit']['mean']/base['expenses']['mean'],'variable_human_hours_per_accepted':base['human_hours']['mean']/n,'mean_realized_modeled_buyer_gain':statistics.mean(realized),'max_runoff_day_base':max(finaldays),'lifecycle_totals_base':dict(counts),'notes':['Break-even equations hold customer mix and prices/costs constant; they are feasibility diagnostics, not demand forecasts.','Capacity denominator uses3delivery+8reserved support hours; quota/human scheduling is conservative aggregate accounting, not a verified calendar SLA.','Mean modeled buyer gain is conditional on simulated private values; not a customer testimonial or observed saving.']}
(ROOT/'results/derived_economics.json').write_text(json.dumps(derived,indent=2)+'\n')
fig,ax=plt.subplots(figsize=(9,3.9));names=['Net revenue','Discovery / failed work','Core / verification','Successor / retention','Acquisition / operations','Delivery / obligations','Full-project profit'];vals=[base['net_revenue']['mean'],-4000,-13000,-4600,-(other-21600),-direct,base['full_profit']['mean']];running=0
for i,v in enumerate(vals):
 if i in [0,len(vals)-1]:bottom=0;height=v
 else:bottom=running;height=v
 ax.bar(i,height/1000,bottom=bottom/1000,color=TEAL if v>0 else RED if i==len(vals)-1 else NAVY,width=.72)
 end=height+bottom;ax.text(i,end/1000+(0.7 if v>=0 else -1.1),f'{v/1000:+.1f}',ha='center',va='bottom' if v>=0 else 'top',fontsize=9)
 if i<len(vals)-1:running+=v
ax.axhline(0,color='#a4b1bd',lw=.8);ax.set_xticks(range(len(vals)),[x.replace(' / ',' /\n').replace('Full-project ','Full-project\n') for x in names],fontsize=8);ax.set_ylabel('USD thousands');ax.set_ylim(-35,15);ax.set_title('Working delivery does not cover the complete enterprise',loc='left',fontweight='bold');fig.tight_layout();save(fig,'economics_waterfall')
fig,(ax,ay)=plt.subplots(1,2,figsize=(9,3.5),gridspec_kw={'width_ratios':[1.25,1]});profits=np.array([float(r['full_profit']) for r in br]);capital=np.array([float(r['required_capital']) for r in br]);ax.hist(profits/1000,bins=30,color=TEAL,alpha=.9);ax.axvline(profits.mean()/1000,color=RED,lw=2);ax.set(xlabel='Full-project profit, USD thousands',ylabel='Simulated campaigns');ax.set_title('1,024 fresh base histories',loc='left',fontweight='bold');ay.plot(np.sort(capital)/1000,np.arange(1,len(capital)+1)/len(capital),color=NAVY,lw=2.5);ay.axvline(45,color=GOLD,ls='--');ay.set(xlabel='Unrestricted capital required, USD thousands',ylabel='Fraction of modeled histories covered',ylim=(0,1.03));ay.set_title('Deposits remain restricted',loc='left',fontweight='bold');fig.tight_layout();save(fig,'uncertainty_cash')
labels={'base':'Base','price_war':'Competitor price response','weak_demand':'Weak demand','supplier_shock':'Supplier cost / capacity shock','slow_payment':'Late collections / defaults','correlated_downturn':'Correlated downturn','identical_free_library':'Identical free library','conditional_ai_improvement':'AI improves for everyone','no_collection_recourse':'No payment enforcement','high_demand':'2.5× demand, fixed capacity'}
fig,ax=plt.subplots(figsize=(9,4.8));keys=list(labels);means=np.array([report['summaries'][k]['full_profit']['mean']/1000 for k in keys]);lo=np.array([report['summaries'][k]['full_profit']['p05']/1000 for k in keys]);hi=np.array([report['summaries'][k]['full_profit']['p95']/1000 for k in keys]);y=np.arange(len(keys));ax.hlines(y,lo,hi,color='#bdcbd6',lw=6);ax.scatter(means,y,color=[TEAL]+[NAVY]*9,s=36,zorder=3);ax.axvline(0,color=RED,ls='--');ax.set_yticks(y,[labels[k] for k in keys]);ax.invert_yaxis();ax.set_xlabel('Full-project profit, USD thousands; point = mean, band = 5th–95th percentile');ax.set_xlim(min(lo)-2,1);ax.set_title('No tested scenario earns commercial expansion',loc='left',fontweight='bold');fig.tight_layout();save(fig,'scenario_results')
dev=json.loads((ROOT/'results/business_development.json').read_text());fig,ax=plt.subplots(figsize=(8.5,3.7))
for arr,color,label in [('bespoke',NAVY,'Bespoke service'),('pooled',GOLD,'Three-order shared core'),('supported_library',TEAL,'Supported library')]:
 d=[x for x in dev['candidates'] if x['policy']['arrangement']==arr];ax.plot([x['policy']['price'] for x in d],[x['summary']['full_profit']['mean']/1000 for x in d],'-o',label=label,color=color)
ax.axhline(0,color=RED,ls='--',label='Do not launch');ax.set(xlabel='Posted service fee, USD',ylabel='Mean full-project profit, USD thousands',ylim=(-36,2));ax.set_title('Arrangement and price searched before confirmation',loc='left',fontweight='bold');ax.legend(frameon=False,fontsize=9,loc='center right');fig.tight_layout();save(fig,'development_policies')
demo=json.loads((ROOT/'data/demo/trace.json').read_text());print('trace_schema',type(demo).__name__)
records=demo if isinstance(demo,list) else demo.get('trace',demo.get('samples',[]))
fig,ax=plt.subplots(figsize=(9,4.8));x=np.arange(len(records));masks=[v.get('events',v.get('mask',0)) if isinstance(v,dict) else v for v in records]
for c in range(8):
 yy=np.array([(m>>c)&1 for m in masks]);ax.step(x,(10-c)+.65*yy,where='post',color=TEAL if c<4 else BLUE,lw=1.5)
outs=json.loads((ROOT/'data/demo/expected.json').read_text())['outputs']
for c in range(2):
 yy=np.array([(m>>c)&1 for m in outs]);ax.step(x,(1-c)+.65*yy,where='post',color=TEAL if c==0 else BLUE,lw=2)
rst=[int(v.get('rst',False)) for v in records];ax.step(x,2+.65*np.array(rst),where='post',color=RED,lw=1.5)
ax.scatter([19],[1.3],marker='x',color=RED,s=65,zorder=5);ax.annotate('Deadline veto cancels group 1',(19,1.3),(21,4.3),fontsize=8,color=RED,arrowprops={'arrowstyle':'->','color':RED})
ax.set_yticks(np.arange(11)+.2,['Output 2','Output 1','Reset','Veto2','C2','B2','A2','Veto1','C1','B1','A1']);ax.set_xlabel('Logical ticks; physical calibration is outside this experiment');ax.set_title('Independent decisions remain cancellable until their deadlines',loc='left',fontweight='bold');ax.set_xlim(-.5,max(1,len(records)-.5));ax.grid(axis='x',alpha=.15);fig.tight_layout();save(fig,'event_trace')
fig,ax=plt.subplots(figsize=(9,4.0));ax.set_xlim(0,10);ax.set_ylim(0,4.6);ax.axis('off')
def box(x,y,w,h,t,color):
 ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=0.10,rounding_size=.10',fc=color,ec='none'));ax.text(x+w/2,y+h/2,t,ha='center',va='center',color='white',fontsize=10,fontweight='bold')
box(.2,2.8,2,1,'Specification\n+ explicit semantics',NAVY);box(3,2.8,2,1,'Executable kernel\n+ acceptance evidence',TEAL);box(5.8,2.8,2,1,'Useful design pack\n+ supported delivery',NAVY)
for a,b in [(2.25,2.9),(5.05,5.7)]:ax.add_patch(FancyArrowPatch((a,3.3),(b,3.3),arrowstyle='-|>',mutation_scale=14,color=TEAL,lw=2))
box(3,.4,2,1,'Composed successor\n+ new virtual events',TEAL);box(5.8,.4,2,1,'Complete-cost surplus\nNOT EARNED',RED)
ax.add_patch(FancyArrowPatch((6.8,2.65),(6.8,1.5),arrowstyle='-|>',mutation_scale=14,color=RED,lw=2));ax.add_patch(FancyArrowPatch((5.7,.9),(5.1,.9),arrowstyle='-|>',mutation_scale=14,color=RED,lw=2,linestyle='--'));ax.text(5.0,1.75,'Commercial reinvestment stops here',color=RED,ha='center',fontsize=9)
ax.add_patch(FancyArrowPatch((4,2.65),(4,1.5),arrowstyle='-|>',mutation_scale=14,color=TEAL,lw=2));ax.text(1.7,.9,'Separate research budget\nUSD4,100 charged once',ha='center',fontsize=9,color=NAVY);ax.set_title('Two loops connected by an earned funding condition',loc='left',fontweight='bold');save(fig,'two_flywheels')
fig,ax=plt.subplots(figsize=(9,2.7));ax.axis('off');ax.set_xlim(0,10);ax.set_ylim(0,3)
box(.25,.9,2.5,1.2,'Raw events\nherald / probe / veto',NAVY);box(3.7,.9,2.4,1.2,'Stage 1\naccepted decision',TEAL);box(7.1,.9,2.5,1.2,'Stage 2\ncalibration-trigger event',BLUE)
for a,b in [(2.9,3.6),(6.2,7)]:ax.add_patch(FancyArrowPatch((a,1.5),(b,1.5),arrowstyle='-|>',mutation_scale=16,color=NAVY,lw=2))
ax.text(6.65,2.45,'One logical tick',ha='center',fontsize=10,color=BLUE);ax.text(5,.25,'Original raw-only grammar rejects this mission; retained kernels remain unchanged.',ha='center',fontsize=10);save(fig,'successor_network')
print(json.dumps(derived,indent=2))
