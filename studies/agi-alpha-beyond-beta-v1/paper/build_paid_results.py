# SPDX-License-Identifier: Apache-2.0
"""Commercial core first; optional Alpha separately. Frozen inputs unchanged."""
from __future__ import annotations
import argparse
import csv
import json
import pathlib
import numpy as np
from build import ROOT, GEN, esc, money, pct, number, table, write, plt

POLICIES=['optimized_beta','optimized_private','optimized_network','fixed_network']

def describe(values):
    a=np.asarray(values,dtype=float)
    se=float(a.std(ddof=1)/np.sqrt(len(a))) if len(a)>1 else 0.
    return {'mean':float(a.mean()),'median':float(np.median(a)),
            'p05':float(np.quantile(a,.05)),'p95':float(np.quantile(a,.95)),
            'positive':float(np.mean(a>0)),'n':len(a),'mc_standard_error':se,
            'mc_mean_interval_95':[float(a.mean()-1.96*se),float(a.mean()+1.96*se)]}

def main(results):
    summary=json.loads((results/'summary.json').read_text())
    if 'confirmation' not in summary['status'].lower():
        raise RuntimeError('Final publication requires frozen confirmation')
    config=json.loads((results/'frozen_config.json').read_text())
    freeze=json.loads((results/'freeze.json').read_text())
    cash=json.loads((results/'commercial_cash_summary.json').read_text())
    count=summary['worlds_per_scenario'];data={}
    for name,scenario in summary['scenarios'].items():
        rows=list(csv.DictReader((results/f'{name}_worlds.csv').open()))
        groups={p:sorted([r for r in rows if r['policy']==p],key=lambda r:int(r['world'])) for p in POLICIES}
        if any(len(rr)!=count for rr in groups.values()):raise RuntimeError('Incomplete histories')
        ids=[[r['world'] for r in groups[p]] for p in POLICIES]
        if any(x!=ids[0] for x in ids):raise RuntimeError('Worlds are not matched')
        metrics={}
        for p,rr in groups.items():
            def total(k):return sum(float(r.get(k,0) or 0) for r in rr)
            accepted=total('true_accepted_projects');passed=total('validated_deliveries')
            cp=cash['scenarios'][name]['policies'][p]
            m={'profit':describe([r['net_profit'] for r in rr]),
               'quality_adjusted':describe([r['quality_adjusted_profit'] for r in rr]),
               'useful':accepted/count,'rich':total('rich_true_projects')/count,
               'cost':total('fully_allocated_cost_total')/accepted if accepted else None,
               'direct':total('direct_cost_total')/accepted if accepted else None,
               'false_pass_rate':total('false_passes')/passed if passed else None,
               'retention_spending':sum(float(r['retention_cost'])>0 for r in rr)/count,
               'insolvency':scenario['policies'][p]['probability_insolvency'],
               'price_fraction':float(np.mean([float(r['mean_price_fraction']) for r in rr])),
               'opportunities':total('qualified_opportunities')/count,
               'adoption':total('orders')/max(1,total('qualified_opportunities')),
               'upfront_retention_cost':total('retention_cost')/count,
               'optional_research_cost':total('investment_cost')/count,
               'ledger_A':total('ledger_A_delivery_total')/count,
               'ledger_B':total('ledger_B_retention_total')/count,
               'ledger_C':total('ledger_C_optional_research_total')/count,
               'admissions':total('retention_admissions')/count,
               'collections':total('collections')/count,'refunds':total('refunds')/count,
               'unpaid_refunds':total('refund_obligations_unpaid')/count,
               'complete_cost':total('fully_allocated_cost_total')/count,
               'startup_discovery':total('discovery_cost')/count,
               'scans':total('emergence_scans')/count,'candidates':total('emergent_candidates')/count,
               'uses':total('retention_uses')/count,
               'useful_fresh_uses':total('retention_useful_fresh_projects')/count,
               'paid_useful_source_recipient_pairs':total('source_true_collected_useful_recipient_projects')/count,
               'local_uses':total('source_local_artifact_reuses')/count,
               'capacity_blocked':total('capacity_blocked')/count,
               'cash_blocked':total('cash_blocked')/count,
               'expired_orders':total('expired_orders')/count,
               'pooled_offered_price':total('offered_price_total')/max(1,total('offered_projects')),
               'pooled_delivered_invoice':total('delivered_price_total')/max(1,passed),
               'cash_endpoints':cp['endpoints'],
               'matched_paid_cohort':cp['true_useful_collected_price_reference']}
            metrics[p]=m
        b=groups['optimized_beta'];pr=groups['optimized_private'];n=groups['optimized_network'];f=groups['fixed_network']
        def delta(x,y,key='net_profit'):return [float(a[key])-float(bb[key]) for a,bb in zip(x,y)]
        gain=delta(n,b);qgain=delta(n,b,'quality_adjusted_profit')
        used=[float(r['retention_cost'])>0 and float(r['retention_admissions'])>0 and float(r['retention_uses'])>0 for r in n]
        paired={'network':describe(gain),'private':describe(delta(pr,b)),
                'sharing':describe(delta(n,pr)),'pricing':describe(delta(n,f)),
                'quality_network':describe(qgain),
                'useful':describe(delta(n,b,'true_accepted_projects')),
                'rich':describe(delta(n,b,'rich_true_projects')),
                'repaid':float(np.mean([u and g>0 for u,g in zip(used,gain)])),
                'operating_funded_repaid':float(np.mean([
                    float(r['operating_funded_true_paid_source_useful_projects'])>0
                    and float(r['investment_cost'])==0 and g>0 and q>0
                    for r,g,q in zip(n,gain,qgain)]))}
        data[name]={'policies':metrics,'paired':paired,
                    'best_tested_mean_policy':max(POLICIES,key=lambda p:metrics[p]['profit']['mean'])}
    central=data['central'];fav=data['favorable'];cons=data['conservative']
    cb=central['policies']['optimized_beta'];fb=fav['policies']['optimized_beta'];lb=cons['policies']['optimized_beta']
    cprice=cb['matched_paid_cohort']['per_project']
    c24=cb['cash_endpoints']['operating_horizon']['metrics']
    no_primary_retention=all(d['policies']['optimized_network']['retention_spending']==0 for d in data.values())
    abstract=f"Across {count:,} independent worlds per condition, central Beta-only delivery produced mean complete pre-tax profit of {money(cb['profit']['mean'])}, {number(cb['useful'],1)} truly accepted projects, and {money(c24['retained_operating_cash_above_seed']['mean'])} available at month 24 after protecting reserves, known obligations and the original seed. Mean gross charge in the useful, collected cohort was {money(cprice['gross_offered_price']['mean'])} against a scope-matched human reference of {money(cprice['modeled_human_service_reference']['mean'])}; pooled complete cost was {money(cb['cost'])} per truly accepted outcome. Favorable Beta profit was {money(fb['profit']['mean'])}; the conservative mean was {money(lb['profit']['mean'])}. Residual material false-pass rates were {pct(cb['false_pass_rate'])} centrally and {pct(fb['false_pass_rate'])} favorably. "
    abstract+=("No primary world purchased additional retention or separate capability construction. Paid candidate scanning reduced network-policy profit slightly; that result does not negate profitable Beta operation. A separately frozen exploratory belief diagnostic enabled useful reuse but remained less profitable than Beta after complete costs. " if no_primary_retention else "Optional Alpha and capital decisions are evaluated separately from this commercial result. ")
    abstract+="These are conditional modeled economics, not observed sales, operational certification or demonstrated recursive improvement."
    write('abstract_results.tex',abstract)
    headline=r'\resultbox{\textbf{Profitable work is the primary result.} '+f"Central Beta-only operation earned mean complete pre-tax profit of {money(cb['profit']['mean'])} and retained {money(c24['retained_operating_cash_above_seed']['mean'])} at month 24 above the original seed, reserves and known obligations. Favorable mean profit was {money(fb['profit']['mean'])}. The conservative condition lost {money(abs(lb['profit']['mean']))} on average. Optional Alpha is a separate economic question: the primary network policy changed central profit by {money(central['paired']['network']['mean'])}. A profitable Beta-only enterprise is a valid positive commercial result; profitable delivery is not evidence of capability compounding."+'}'
    write('headline.tex',headline)
    protocol=f"The behavioral protocol, costs and stress design were frozen before confirmation on 26 October 2026 at 23:55 UTC (full timestamp in the freeze manifest). There are {count:,} independent world IDs per primary condition and four matched policies: {3*count:,} condition--world evaluations and {12*count:,} complete policy histories. Conditions reuse keyed random streams; the condition ensembles are not mutually independent. Confirmation seed {config['test_seed']} is distinct from development seed {config['train_seed']}. Each history includes paid discovery/setup, 24 operating months and three settlement-runoff months. Every world is preserved. The enterprise campaign is the experimental unit; descendant jobs are not additional independent inventions."
    protocol+='\n\n'+r'Configuration SHA-256: \nolinkurl{'+summary['config_sha256']+'}. The commercial-core-first presentation requested on 27 October changes no frozen parameter, policy, hypothesis, seed or outcome. Monetary tariffs retain their 26 October evidence cutoff. Future Beta epochs are assumptions, not forecasts of named releases. Reported distributions describe these specified simulated populations, not empirical probabilities of commercial success.'
    write('protocol.tex',protocol)

    body=r'\subsection{Beta-only useful delivery and complete profit}'
    body+='\nCompetent Beta includes the current frontier workflow, ordinary tools, existing equivalents and useful source-agent local artifacts. It requires no newly admitted graph skill and no optional capability campaign. The following commercial results stand independently of the optional Alpha findings.'
    rows=[]
    for name,d in data.items():
        m=d['policies']['optimized_beta'];p=m['matched_paid_cohort']['per_project']
        rows.append([esc(name.title()),number(m['useful'],1),money(p['modeled_human_service_reference']['mean']),money(p['gross_offered_price']['mean']),money(m['cost']),money(m['profit']['mean'])])
    body+='\n'+r'\begin{table}[htbp]\centering\small'+table(['Condition','Useful jobs','Human ref.*','Charge*','Cost/useful','Net profit'],rows)+r'\caption{Beta-only commercial core. Project counts and complete profit are enterprise means. *Human reference and gross charge use the same truly useful, collected cohort, including richer scopes. Complete cost pools all paid and failed work, overhead, setup and discovery over all truly accepted outcomes, including valid outcomes whose payment was not authorized. The columns are not an algebraic per-job profit calculation. USD; simulated.}\end{table}'
    rows=[]
    for name,d in data.items():
        m=d['policies']['optimized_beta'];p=m['profit']
        rows.append([esc(name.title()),money(m['collections']),money(m['refunds']),money(m['complete_cost']),money(p['p05']),money(p['p95'])])
    body+='\n'+r'\begin{table}[htbp]\centering\small'+table(['Condition','Collections','Refunds','All costs','Profit 5th','Profit 95th'],rows)+r'\caption{Mean settled gross receipts, paid refunds and complete costs; profit distribution across all worlds. Fees are already in costs. Unpaid refund liabilities also reduce profit. Seed capital is not revenue.}\end{table}'
    for name,d in data.items():
        m=d['policies']['optimized_beta'];co=m['matched_paid_cohort'];p=co['per_project'];price=config['scenarios'][name]['human_reference']*m['price_fraction']
        body+='\n\n'+r'\textbf{'+esc(name.title())+'.} '+f"Beta delivered {number(m['useful'],1)} truly useful projects ({number(m['useful']/24,2)} per operating month), of which {number(co['per_world']['true_useful_collected_projects']['mean'],1)} were useful and collected. The gross charge in that paid cohort averaged {money(p['gross_offered_price']['mean'])}; its matched human reference averaged {money(p['modeled_human_service_reference']['mean'])}. Their arithmetic reference-price difference was {money(p['reference_price_difference']['mean'])}, or a mean {pct(p['reference_price_difference_fraction']['mean'])} discount across those projects. This is not observed buyer savings or proof that every buyer would otherwise purchase the human service. The mean monthly posted base-scope price was {money(price)} ({pct(m['price_fraction'])} of the base reference), distinct from the sold scope mix. The modeled purchase share was {pct(m['adoption'])} across {number(m['opportunities'],1)} qualified opportunities. Profit was positive in {pct(m['profit']['positive'])} of simulated worlds; cash-shortfall shutdown occurred in {pct(m['insolvency'])}. These are scenario frequencies, not calibrated real-world success probabilities."
    body+='\n\n'+r'\textbf{Quality is a separate condition.} '+f"Material errors among approved Beta deliveries were {pct(lb['false_pass_rate'])}, {pct(cb['false_pass_rate'])} and {pct(fb['false_pass_rate'])} in conservative, central and favorable conditions. Removing all otherwise undetected paid false-pass receipts as a terminal valuation stress leaves central profit of {money(cb['quality_adjusted']['mean'])} and favorable profit of {money(fb['quality_adjusted']['mean'])}. This supports the modeled useful-work margin without treating erroneous receipts as indispensable. It does not create a new refund-timing trajectory, establish a full liability ceiling, or prove that buyers accept the residual error rate. A required error budget tighter than a scenario's residual rate would require a stronger validator or narrower offering."
    body+='\n\n'+r'\subsection{Available surplus, seed and throughput}'
    rows=[]
    for name,d in data.items():
        m=d['policies']['optimized_beta'];a=m['cash_endpoints']['operating_horizon']['metrics'];z=m['cash_endpoints']['terminal_runoff']['metrics']
        rows.append([esc(name.title()),money(a['closing_cash']['mean']),money(a['reserve']['mean']),money(a['outstanding_receivables']['mean']),money(a['retained_operating_cash_above_seed']['mean']),money(z['retained_operating_cash_above_seed']['mean'])])
    body+='\n'+r'\begin{table}[htbp]\centering\scriptsize'+table(['Condition','Cash, m24','Reserve, m24','Receivable, m24','Excess*, m24','Excess*, m27'],rows)+r'\caption{Beta cash stocks, USD means. *Nonnegative cash available after protecting known obligations, the declared reserve and the entire original USD20,000 seed. Receivables cannot fund current spending. Known refunds/recovery are not subtracted twice when already inside reserve. The settled endpoint retains the operating reserve policy; it is not liquidation value. Nonnegative world-level stocks are averaged, so a positive mean excess does not negate conservative losses.}\end{table}'
    body+='\n'+f"Central month-24 uncommitted cash was {money(c24['available_uncommitted_cash']['mean'])}, including possible seed, while {money(c24['retained_operating_cash_above_seed']['mean'])} remained after preserving the entire seed. Its 5th--95th percentile range above seed was {money(c24['retained_operating_cash_above_seed']['p05'])} to {money(c24['retained_operating_cash_above_seed']['p95'])}. The conservative median excess above seed was zero even though many enterprises retained some original capital. These stocks differ from accrual-like complete profit and are never summed across months."
    body+='\nThe primary runs show no capacity-deferred orders. Their achieved throughput therefore demonstrates conditional operation at the tested demand, not a measured saturation point or an Alpha-driven capacity expansion. The resource screens and scale stresses locate conditional bottlenecks; actual provider quotas, latency and validator capacity require later measurement. Increased volume by itself is not self-acceleration.'
    body+='\n'+r'\begin{figure}[htbp]\centering\includegraphics[width=\linewidth]{generated/results_overview.pdf}\caption{Commercial core first. Left: Beta complete-profit medians and 5th--95th percentile ranges. Right: paired mean policy increments from optional private capability decisions and network availability. The scales differ deliberately: large service economics and small enhancement effects are distinct questions.}\end{figure}'

    body+='\n'+r'\subsection{Optional retained Alpha, sharing and investment}'
    rows=[]
    for name,d in data.items():
        m=d['policies']['optimized_network'];p=d['paired']
        rows.append([esc(name.title()),money(p['network']['mean']),money(p['sharing']['mean']),pct(m['retention_spending']),number(m['admissions'],2),pct(p['operating_funded_repaid'])])
    body+='\n'+r'\begin{table}[htbp]\centering\small'+table(['Condition','Network $-$ Beta','Network $-$ private','Retain','Admit','Feedback'],rows)+r'\caption{Optional-policy mean increments and all-world frequencies, kept separate from Beta commercial success. Retain is an additional B-package purchase. Feedback requires an operating-funded package linking useful collected source work to useful fresh recipient work, positive total and quality-adjusted paired value, and no separate C construction campaign. It is descriptive, not a mandatory investment count.}\end{table}'
    if no_primary_retention:
        body+='\nNo primary world purchased portable retention or optional separate capability construction. Ordinary source-agent artifacts remain available under Beta; paid candidate scans and nominated candidates do not establish additional Alpha. The tested policy declined the incremental expenditures. Its small negative network effects reflect the cost and incidental resource consequences of searching, not destruction of the profitable commercial core. This is evidence of the tested policy choosing restraint, not proof that every possible retained capability is worthless or that global optimality has been established.'
    for name,d in data.items():
        m=d['policies']['optimized_network'];p=d['paired']
        body+='\n\n'+f"{esc(name.title())}: network availability changed mean profit by {money(p['network']['mean'])} (Monte Carlo standard error {money(p['network']['mc_standard_error'],2)}; 5th--95th percentile {money(p['network']['p05'])} to {money(p['network']['p95'])}). Private optional decisions changed profit by {money(p['private']['mean'])}. Paid scans averaged {number(m['scans'],1)}, nominated candidates {number(m['candidates'],1)}, and upfront B purchases {money(m['upfront_retention_cost'])}. There were {number(m['useful_fresh_uses'],2)} useful capability--project reuse pairs; separate capsules can create multiple pairs for one project. The paired policy effect on distinct useful projects was {number(p['useful']['mean'],2)}. Endogenous network pricing changed mean profit by {money(p['pricing']['mean'])} relative to the fixed 65\\% diagnostic; this comparison includes any induced resource decisions."
    rows=[]
    for name,d in data.items():
        b=d['policies']['optimized_beta'];n=d['policies']['optimized_network']
        rows.append([esc(name.title()),money(b['ledger_A']),money(b['ledger_B']),money(b['ledger_C']),money(n['ledger_B']),money(n['optional_research_cost'])])
    body+='\n'+r'\begin{table}[htbp]\centering\small'+table(['Condition','Beta A','Beta B','Beta C*','Network B','Later C'],rows)+r'\caption{Disjoint complete-cost records, USD means. A includes delivery, within-job learning, qualification, fees and allocated overhead. B includes extra scans, failed candidates, retention and reuse. *C includes initial bounded venture discovery; later optional C campaigns are identified separately. Refunds reverse revenue, and no source-job construction is charged again to B.}\end{table}'
    body+='\nThe primary confirmation does not supply a population of funded admissions from which to estimate admission precision or realized skill repayment. Directed funded and recovery fixtures verify software/accounting branches only; their forced capital action is not economic-selection evidence. Any actual funded sensitivity path is separately labeled and retains its all-world frequency. Profitable delivery, useful retained Alpha, productive reinvestment and self-acceleration remain different claims.'
    write('results.tex',body)

    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9,'axes.spines.top':False,'axes.spines.right':False,'pdf.fonttype':42})
    names=list(data);x=np.arange(len(names));fig,ax=plt.subplots(1,2,figsize=(10,3.5))
    mm=[data[n]['policies']['optimized_beta']['profit'] for n in names]
    y=np.array([v['median']/1000 for v in mm]);lo=np.array([v['p05']/1000 for v in mm]);hi=np.array([v['p95']/1000 for v in mm])
    ax[0].bar(x,y,color=['#9b6152','#183f59','#6a8b7a'],width=.55)
    ax[0].errorbar(x,y,yerr=[y-lo,hi-y],fmt='none',ecolor='#222',capsize=3)
    ax[0].set_ylabel('Beta net profit (USD thousands)');ax[0].set_title('Useful delivery: complete economics')
    for offset,k,label,color in [(-.17,'private','Private optional − Beta','#b59658'),(.17,'sharing','Network optional − private','#183f59')]:
        ax[1].bar(x+offset,[data[n]['paired'][k]['mean'] for n in names],.32,label=label,color=color)
    ax[1].set_ylabel('Mean paired policy increment (USD)');ax[1].set_title('Optional enhancements: separate value');ax[1].legend(frameon=False,fontsize=8)
    for a in ax:a.axhline(0,color='#888',lw=.7);a.set_xticks(x,[n.title() for n in names])
    fig.tight_layout();fig.savefig(GEN/'results_overview.pdf');fig.savefig(GEN/'results_overview.png',dpi=160);plt.close(fig)
    conclusion=f"Expertly used frontier Beta supports a positive modeled commercial result in the central and favorable conditions: mean complete pre-tax profits of {money(cb['profit']['mean'])} and {money(fb['profit']['mean'])}, respectively. Central operation leaves {money(c24['retained_operating_cash_above_seed']['mean'])} available at month 24 after protecting known obligations, reserves and original seed. These results do not require newly admitted Alpha, sharing superiority or a reinvestment sequence. The conservative loss identifies a meaningful boundary. "
    conclusion+="The primary policy made no additional retention or capability purchases. That preserves the commercial interpretation: decline an unconvincing enhancement and keep serving useful demand. The separate sensitivities expose an admission/reuse belief mismatch, so their zero-use result is a limit of the tested controller rather than proof that retained capabilities cannot add value. Any posterior-coherence diagnostic is separately labeled exploratory and does not replace the frozen commercial result. None of these simulated results proves actual demand, acceptable operational error, a permanent moat or recursive improvement. The shortest next step is to measure matched buyer willingness, complete frontier delivery costs and residual semantic error, then evaluate fresh recipients only where retention has a defensible incremental case."
    write('conclusion.tex',conclusion)
    write('reproduction.tex',r'''The README gives exact reproduction commands. The frozen primary wrapper is \texttt{sim/confirm\_v3.py}; the sensitivity wrapper is \texttt{sim/run\_stress\_v3.py}. Both preserve independent seeds and check frozen inputs. Every primary history, monthly ledger and activity receipt is retained in compressed JSONL, with all-world CSVs for analysis. Stress outputs preserve every scalar world and policy contrast. Post hoc deterministic reporting of cash and matched prices is \texttt{analysis/commercial\_cash\_summary.py}; it changes no decision. Publication tables come from \texttt{paper/build\_paid\_results.py}, the threshold/sensitivity/lifecycle renderers and \texttt{paper/build.py}. The bilingual HTML opens offline. Historical protocols and negative development findings are preserved with their status; they are not substituted for this confirmation.''')
    output={'worlds_per_scenario':count,'config_sha256':summary['config_sha256'],'scenarios':data}
    (GEN/'paper_metrics.json').write_text(json.dumps(output,indent=2)+'\n')
    print(json.dumps({'worlds_per_scenario':count,'commercial_core_first':True,'all_primary_retention_declined':no_primary_retention,'central_beta_profit':cb['profit']['mean'],'central_beta_available_above_seed_month24':c24['retained_operating_cash_above_seed']['mean']},indent=2))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--results',type=pathlib.Path,default=ROOT/'results/paid_work_final')
    main(parser.parse_args().results)
