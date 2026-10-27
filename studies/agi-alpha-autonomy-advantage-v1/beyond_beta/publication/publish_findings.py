#!/usr/bin/env python3
"""Mechanical publication synthesis of completed frozen results; no new worlds."""
from pathlib import Path
import json,statistics,hashlib,os
ROOT=Path(__file__).resolve().parents[1]; PUB=ROOT/'publication'
s=json.loads((ROOT/'results/primary/summary.json').read_text());assert s['status']=='COMPLETE'
a=json.loads((ROOT/'analysis/analysis.json').read_text())
c=json.loads((ROOT/'analysis/commercial-core.json').read_text())
p=c['commercialCore']['referenceProfiles']['reference']
col=p['totalsUSD']['collected']/p['counts']['usefulAccepted'];unit=p['pooledUnitCostsUSD']['fullAllocated'];profitunit=col-unit
fixed=sum(p['costBucketsUSD'][k] for k in ['C','shared_setup','shared_recurring_operations'])/p['worlds']
var=(p['costBucketsUSD']['A']+p['costBucketsUSD']['FINANCIAL'])/p['counts']['usefulAccepted']
threshold=fixed/(col-var)
headline=r'''\par\textbf{Primary finding.} The best tested ordinary-service policy charged \usd{10,000} and made no retained-capability investment. In the reference profile, 14 fresh histories produced a pooled full cost of \usd{1,058} per useful outcome against a \usd{23,714} cost-derived human reference; mean complete profit was \usd{151,024} and available operating funds \usd{122,040} over 72 business weeks plus runoff. All 14 were profitable. The same price produced no orders and cash closure in all 13 burdensome-profile histories. Optional retention reduced reference-condition mean profit by \usd{65}. Three network-admitted assets in the high-repeat/slow-Beta condition did not recover their direct retention costs. The supported positive result is conditional profitable Beta service; capability compounding and realized commercial success are not established.'''
(PUB/'headline.tex').write_text(headline+'\n')
results=r'''\subsection{Optional retention: paid learning does not require retention}

The independently selected overall winner is the \usd{10,000} Beta-only policy. The best tested optional policy uses the same price, a risk-adjusted positive-value rule and operating-generated funds. It remains profitable in the favorable service environments but does not improve the reference result. Across all 19 confirmation conditions, its mean complete-profit increment is nonpositive; the high-repeat interval includes zero, while the no-demand contrast is identically zero. This is evidence about these specified capability families and decision rules, not a limit on frontier intelligence or a theorem that retaining skills can never pay.

In the 40 reference-condition network histories, 199 paid-job candidates and 222 optional-research proposals produced no admission. Of these, 335 were declined for nonpositive incremental value and 86 were deferred while a relevant evaluation already existed. The additional cost is primarily bounded assessment, not a compulsory separate invention project. Creator-private and network availability have the same result here because no asset becomes available; that inactive contrast cannot establish general sharing or graph superiority.

\textbf{The prespecified paid-job trace.} In reference/seed1001, the first paid-job candidate arises from a stateful component delivered at week16 after one repair. Its contract price is \usd{10,000}, against a \usd{36,404} estimated human-service reference. The origin record contains \usd{358.91} of direct delivery-A cost, including the work that generated the candidate; shared company costs are allocated separately in the service results. A further \usd{11.79} assessment is charged only to B at week17, from earlier operating funds. The origin invoice is collected at week19, so that later receipt does not finance the earlier decision.

The candidate forecasts 13.33 relevant uses and \usd{35.80} gross savings, against \usd{500.46} of additional fixed retention/qualification, \usd{70.14} maintenance and \usd{121.37} distribution. The forecast net is negative \usd{656.17}, before further risk adjustment. The policy declines it. The originating A cost is not charged again, and the proposed retention costs are not falsely recorded as spent. The useful paid job survives; the weak retention option does not.

\subsection{Fresh reuse, sharing and a moving frontier}

Under sixfold repeat opportunities and slower Beta improvement, the primary network arm admits three paid-job assets and records 25 uses. All three are technically valid in the simulated hidden-truth process, yet each loses direct retention value: \usd{436}, \usd{471} and \usd{563}, respectively. No separate-research asset is admitted there. The whole retention/research program includes every rejected attempt and averages negative \usd{230} of direct net resources per enterprise. Complete enterprise profit falls by \usd{3,117} relative to matched Beta (conditional 95\% interval: negative \usd{6,299} to negative \usd{648}); accepted useful volume is3,118 versus3,129. Complete policy value includes altered delivery timing, acceptance and collections in addition to asset resource savings.

Network availability versus creator-private availability is also negative in that condition: \usd{2,974} less mean profit. Equal agent counts and budgets exclude ``more compute'' as its explanation, but this is an availability-policy contrast including the resulting retention decisions, not a pure graph-versus-registry experiment. Across primary network conditions only three assets are admitted. The frozen-Beta counterfactual admits five across its conditions; branches descended from related simulated jobs are not independent discoveries. No graph-size, download or agreement count is substituted for economic value.

The moving-Beta and frozen-Beta ablations do not establish positive accumulation or faster worthwhile invention. Some admitted methods are invoked on fresh work, but the tested program fails its complete economic comparison. New offerings unlocked by retained Alpha and improved efficiency of successive invention campaigns are not demonstrated. Continued profitable ordinary delivery and cash retention are the supported choices within the searched policy family.

\begin{figure}[ht]\centering
\includegraphics[width=\linewidth]{figures/commercial-core-profile.pdf}
\caption{Commercial core in the reference profile, all values modeled. Left: matched human reference, contract price and fully allocated cost on the same251 useful outcomes. Right: mean company collections, complete costs, pre-tax-reserve profit and spendable operating funds over72 business weeks plus runoff. The right panel is per enterprise, not per job.}
\end{figure}

\subsection{Economic and capacity conditions}

The reference profile collects an average of COLLECTED per useful outcome after defaults and cancellations, rather than treating every quoted \usd{10,000} as collected. Subtracting the full UNIT cost leaves PROFITUNIT of complete pre-tax-reserve profit per useful outcome. Holding the observed mix and program fixed, the accounting break-even diagnostic is THRESHOLD accepted outcomes over the operating horizon, so two such outcomes would clear that static cost threshold. This is not a demand forecast or a survival guarantee: collection timing, lost capacity, quality, reserves and early cash closure still matter.

The cash upper bound and the investment-value bound differ. An average \usd{122,040} is available after modeled costs and reserves in the reference profile, but the existence of funds does not justify an uneconomic candidate. With no demand, all40 histories close and lose an average \usd{10,148}; preserving the reserve prevents insolvency rather than making the enterprise viable. A different price could change the burdensome profile, but its profitability has not been confirmed under a separately optimized profile-specific policy.

The target configuration uses six workers, each with24 model-hours and240 proof-container-hours per week, plus stated aggregate token/request quotas. Mean useful turnaround in the reference profile is19.16 days and its 95th percentile is28 days; initial queue delay is small, but per-worker proof capacity reaches its reservation limit. The weekly fluid schedule cannot establish minute-by-minute burst compliance, arbitrary concurrency or a production service-level guarantee. Reference useful throughput is0.249 outcomes per enterprise-week; the high-repeat panel tests greater offered demand, not observed customers. Enterprise expansion is outside the optimized control set.

\begin{figure}[ht]\centering
\includegraphics[width=0.93\linewidth]{figures/alpha-conditions.pdf}
\caption{Optional network retention minus matched Beta across every prespecified condition. Intervals are paired-seed bootstrap intervals conditional on the model, not confidence about real-world demand or capability. Negative enhancement value does not erase the separately reported profitable service core.}
\end{figure}
'''
for key,val in [('PROFITUNIT',profitunit),('COLLECTED',col),('UNIT',unit)]:results=results.replace(key,r'\usd{'+f'{val:,.2f}'+'}')
results=results.replace('THRESHOLD',f'{threshold:.2f}')
assert 'PROFIT\\' not in results and 'PROFITUNIT' not in results and 'COLLECTED' not in results and 'THRESHOLD' not in results
(PUB/'results.tex').write_text(results+'\n')
reproduction=r'''The protocol was frozen on26October2026 before outcome inspection (full SHA-256 in the frozen protocol record); all52 files in the source closure remain unchanged. A shared-filesystem capacity failure interrupted the original run. Its original compressed bytes were preserved, and a separate recovery retained all1,289 complete ordered records plus an803,265-byte unfinished tail and per-record hashes. The remaining fixed histories were completed in a copied workspace; training selection was committed before confirmation. Four local processes accelerated independent simulation histories without adding workers inside the modeled enterprise. The original interruption and incomplete computation are not erased, and complete actual research cost is unknown.

The original independent auditor passed all4,560 confirmation histories but flagged51 training histories. A separately preserved diagnostic showed that the auditor omitted Beta/policy changes when reconstructing comparison epochs. The graph correctly counted one Beta advance plus one admission as epoch2 where the auditor inferred1. The corrected diagnostic replay passed all6,288 histories with13,267,486 checks and746 historical reuse receipts; eight focused anti-bypass controls passed. Original failures and the frozen auditor remain intact. No primary source, history, financial number or selected policy changed.

The native adapter reconciled24 prespecified histories through48 existing \code{planMission} calls and264 fixture-authority checks. The maximum rounding discrepancy was0.914 cents against a2.01-cent tolerance. No historical study admission routine or live authority/settlement action was called. Two separately recorded verification replays, including the first admitted-asset history, reproduced all ten checked economic sections exactly despite regenerated cryptographic keys; no cases were added to the primary sample. The standalone graph lifecycle passed60 adversarial controls and the engine passed four explicitly fictional economic controls. These tests establish research-code and accounting consistency, not truthful real customer outcomes.

The English/French demonstration embeds all4,560 confirmation summaries and retains the fixed reference/1001 example. Its first paid-job candidate is shown even though retention is declined. Static checks15/15 and minimal-DOM interaction checks20/20 passed. Normal Chromium rendering was blocked by the environment; no visual-browser success is claimed. The final paper is compiled and rendered separately for page inspection.

A clean numerical rerun should use the unchanged runner with an adequate operational envelope, for example \code{python3 beyond_beta/run_experiment.py --run --max-seconds 7200 --output beyond_beta/results/reproduction}. The original1,800-second envelope and the storage recovery are retained for provenance rather than imposed as scientific parameters. Exact dependency versions and non-executing inspection commands appear in the runbook.'''
(PUB/'reproduction.tex').write_text(reproduction+'\n')
# Exact chart data come from the final reconciled commercial report.
os.environ['MPLCONFIGDIR']=str(PUB/'.mpl-cache')
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams.update({'font.size':9,'axes.spines.top':False,'axes.spines.right':False,'font.family':'DejaVu Sans','text.color':'#163044','axes.labelcolor':'#163044'})
fig,axs=plt.subplots(1,2,figsize=(9.2,3.6),gridspec_kw={'width_ratios':[1,1.28]})
vals=[p['priceAndHumanComparison']['matchedHumanReferenceMeanUSD'],10000,unit]
for ax,labels,values,colors,title in [
 (axs[0],['Human reference','Contract price','Complete cost'],vals,['#8194A3','#087F8C','#AA742D'],'Per useful accepted outcome'),
 (axs[1],['Collections','Complete costs','Operating profit','Available funds'],[p['perEnterpriseMeansUSD'][k] for k in ['collected','accrued','completePreTaxReserveProfit','availableOperating']],['#8194A3','#AA742D','#087F8C','#58A7A6'],'Mean enterprise over the horizon')]:
 bars=ax.barh(labels,values,color=colors,height=.56);ax.invert_yaxis();ax.set_title(title,loc='left',fontweight='bold',fontsize=10)
 ax.set_xlim(0,max(values)*1.30);ax.set_xlabel('Modeled USD');ax.grid(axis='x',alpha=.15);ax.set_axisbelow(True)
 for b,v in zip(bars,values):ax.text(v+max(values)*.025,b.get_y()+b.get_height()/2,f'${v:,.0f}',va='center',fontsize=9)
 ax.ticklabel_format(axis='x',style='plain');ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda x,pos:f'{x/1000:g}k'))
fig.tight_layout(w_pad=2.2);(PUB/'figures').mkdir(exist_ok=True)
fig.savefig(PUB/'figures/commercial-core-profile.pdf');fig.savefig(PUB/'figures/commercial-core-profile.png',dpi=160);plt.close(fig)
(ROOT/'analysis/publication-synthesis.json').write_text(json.dumps({'basis':'MECHANICAL_REPORTING_OF_COMPLETE_FROZEN_RESULTS','economicWorldsExecuted':0,'referenceCollectedPerUsefulUSD':col,'referenceCompleteCostPerUsefulUSD':unit,'referenceCompleteProfitPerUsefulUSD':profitunit,'staticBreakEvenUsefulAtObservedMix':threshold,'fullActualResearchCostUSD':None,'inputs':{'summary':hashlib.sha256((ROOT/'results/primary/summary.json').read_bytes()).hexdigest(),'commercial':hashlib.sha256((ROOT/'analysis/commercial-core.json').read_bytes()).hexdigest()}},indent=2)+'\n')
print(json.dumps({'publicationGenerated':True,'referenceProfitPerUsefulUSD':profitunit,'staticBreakEvenUsefulAtObservedMix':threshold}))

# Typography-only cleanup; preserve exact code/hash spans.
import re
for name in ('headline.tex','results.tex','reproduction.tex'):
 path=PUB/name; parts=re.split(r'(\\code\{[^}]*\})',path.read_text())
 for i in range(0,len(parts),2):
  parts[i]=re.sub(r'(?<=[A-Za-z])(?=[0-9])|(?<=[0-9])(?=[A-Za-z])',' ',parts[i])
 path.write_text(''.join(parts))
