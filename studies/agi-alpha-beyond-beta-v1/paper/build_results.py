# SPDX-License-Identifier: Apache-2.0
"""Generate numeric paper sections from completed economic runs, not pilot claims."""
from __future__ import annotations
import argparse, csv, json, pathlib
import numpy as np
from build import ROOT, GEN, esc, money, pct, number, table, write, plt


def main(results):
    summary=json.loads((results/'summary.json').read_text())
    if 'confirmation' not in summary['status'].lower():
        raise RuntimeError('Publication requires independent confirmation, not a pilot')
    config=json.loads((results/'frozen_config.json').read_text())
    freeze=json.loads((results/'freeze.json').read_text())
    scenarios=summary['scenarios'];n=summary['worlds_per_scenario'];pooled={};raw={}
    for name,s in scenarios.items():
        rr=list(csv.DictReader((results/f'{name}_worlds.csv').open()))
        raw[name]=[r for r in rr if r['policy']=='optimized_optional']
        def total(k):return sum(float(r[k]) for r in raw[name])
        passed=total('validated_deliveries');accepted=total('true_accepted_projects')
        pooled[name]={'error':total('false_passes')/passed if passed else None,
            'cost':total('fully_allocated_cost_total')/accepted if accepted else None,
            'direct':total('direct_cost_total')/accepted if accepted else None,
            'adoption':total('orders')/max(1,total('qualified_opportunities')),
            'research_campaigns':total('research_campaigns'),
            'research_admissions':total('research_admissions'),
            'orders_mean':total('orders')/n,'opportunities_mean':total('qualified_opportunities')/n}
    C=scenarios['central'];F=scenarios['favorable'];cm=C['policies']['optimized_optional'];fm=F['policies']['optimized_optional']
    abstract=f"In {n:,} independent simulated enterprise campaigns per condition, central mean pre-tax profit was {money(cm['net_profit']['mean'])} over 24 operating months; its pooled complete cost was {money(pooled['central']['cost'])} per useful accepted project. The central optional-investment policy undertook research in {pct(cm['probability_research'])} of worlds. Favorable mean paired incremental profit from optional investment was {money(F['paired']['optional_incremental_profit']['mean'])}; an admitted, used investment with positive paired terminal value occurred in {pct(F['paired']['probability_research_repaid'])} of all favorable worlds. Pooled materially incorrect validator passes were {pct(pooled['central']['error'])} centrally and {pct(pooled['favorable']['error'])} favorably. These are conditional model results, not frequencies established for real customers or frontier models."
    write('abstract_results.tex',abstract)
    headline=r'\resultbox{\textbf{Modeled commercial result.} '+f"The central price policy posted an average base-scope fraction of {pct(cm['mean_price_fraction']['mean'])} of the human reference and generated mean pre-tax profit of {money(cm['net_profit']['mean'])}. Optional capability development changed mean favorable profit by {money(F['paired']['optional_incremental_profit']['mean'])} relative to matched no-asset operation. Profit, investment and trustworthy output remain separate: the central residual material false-pass rate is {pct(pooled['central']['error'])}. All demand, construction and frontier-performance probabilities remain unmeasured scenario inputs."+'}'
    write('headline.tex',headline)
    protocol=f"The final campaign froze the executable behavioral closure and calibration before confirmation at {esc(freeze['frozen_at_utc'])}. It ran {n:,} independent enterprise worlds for each of three primary conditions, with three matched policies per world ({3*n:,} worlds; {9*n:,} complete policy histories). Each history contains 24 operating months plus settlement runoff; bounded discovery/setup precedes operation and is charged. The base seed is {config['test_seed']}, distinct from the development seed {config['train_seed']}. Every history, not only successful illustrations, is preserved. The experimental unit is the enterprise campaign. Each commercial opportunity is a full new-project contract; internal solver instances are not additional sales."
    protocol+='\n\n'+r'Configuration identity: \nolinkurl{'+summary['config_sha256']+'}. Model and tool tariffs are held at their evidence-date values; future provider changes are not forecast. Numerical intervals summarize the declared simulated population. They are not confidence intervals for real adoption or autonomous invention.'
    write('protocol.tex',protocol)
    rows=[]
    for name,s in scenarios.items():
        m=s['policies']['optimized_optional'];rows.append([esc(name.title()),money(m['net_profit']['mean']),money(m['net_profit']['p05']),money(m['net_profit']['p95']),money(pooled[name]['cost']),pct(pooled[name]['error'])])
    result=r'\begin{table}[htbp]\centering\small'+table(['Condition','Mean profit','5th pct.','95th pct.','Cost / useful','Wrong passes'],rows)+r'\caption{Endogenous price with optional investment. Complete cost includes discovery, setup, all failures and paid research. Material-error fraction is pooled over validator-approved deliveries. No-output enterprises remain in costs and profits. All outcomes simulated, USD pre-tax.}\end{table}'
    rows=[]
    for name,s in scenarios.items():
        m=s['policies']['optimized_optional'];p=s['paired'];rows.append([esc(name.title()),number(m['true_accepted_projects']['mean'],1),pct(m['mean_price_fraction']['mean']),pct(m['probability_research']),pct(p['probability_research_repaid']),money(p['optional_incremental_profit']['mean'])])
    result+='\n'+r'\begin{table}[htbp]\centering\small'+table(['Condition','Useful projects','Price / reference','Research','Repaid*','Mean paired gain'],rows)+r'\caption{All-world frequencies and averages. *Repaid means research was paid, an admitted asset was used, and paired terminal net profit exceeded no-asset operation after all costs; it does not require two investments. No-research worlds are retained in these frequencies.}\end{table}'
    for name,s in scenarios.items():
        m=s['policies']['optimized_optional'];p=s['paired'];p0=s['policies']['optimized_no_assets'];fixed=s['policies']['fixed_optional'];ref=config['scenarios'][name]['human_reference']
        result+='\n\n'+r'\textbf{'+esc(name.title())+'.} '+f"Mean pre-tax profit was {money(m['net_profit']['mean'])}; {pct(m['probability_profit'])} of worlds were profitable and {pct(m['probability_insolvency'])} hit the model's cash-shortfall shutdown. Mean useful accepted projects were {number(m['true_accepted_projects']['mean'],1)} from {number(pooled[name]['opportunities_mean'],1)} paid qualified opportunities over the horizon. Average monthly posted base-scope price was {pct(m['mean_price_fraction']['mean'])} of the {money(ref)} reference (approximately {money(m['mean_price_fraction']['mean']*ref)}); this is not a sales-weighted collection price. Pooled direct delivery cost was {money(pooled[name]['direct'])}, while complete allocated cost was {money(pooled[name]['cost'])} per useful outcome."
        result+=' '+f"Research occurred in {pct(m['probability_research'])} of campaigns; {pct(p['probability_operating_only_research'])} of all worlds undertook research using operating-generated funds alone under the stated attribution rule. Paired incremental profit averaged {money(p['optional_incremental_profit']['mean'])}, with a 5th--95th percentile range of {money(p['optional_incremental_profit']['p05'])} to {money(p['optional_incremental_profit']['p95'])}. The fixed 65\% diagnostic produced mean profit of {money(fixed['net_profit']['mean'])}; the endogenous price/optional-investment policy's mean total advantage over that diagnostic was {money(p['price_policy_total_effect']['mean'])}. That comparison includes investment decisions induced by the pricing policy; it is not a pure elasticity estimate."
    result+='\n\n'+f"Refunding every otherwise undetected paid false pass as a terminal valuation stress leaves central mean adjusted profit of {money(cm['quality_adjusted_profit']['mean'])} and favorable mean adjusted profit of {money(fm['quality_adjusted_profit']['mean'])}. This subtracts the specified hidden false-pass revenue; it is not a fresh cash-timing simulation, a full liability model, or evidence that the residual errors are commercially acceptable. A formal checker cannot repair a wrongly elicited objective. No external buyer quality tolerance is established by these results."
    result+='\n\nThe no-investment control remains a competent frontier workflow able to reconstruct the same components. The policy can profitably preserve its cash because substantial baseline capability is already available. Candidate assets compete with that strong starting point, incoming equivalent capabilities, useful lifetime and the cost of diverting production capacity. Positive ordinary operating economics do not automatically justify a new research campaign.'
    result+='\n'+r'\begin{figure}[htbp]\centering\includegraphics[width=\linewidth]{generated/results_overview.pdf}\caption{Profitability, optional research and residual validation errors are different outcomes. Left: median and 5th--95th percentiles. Right: all-world investment/repayment frequencies and pooled material-error rates. All quantities are conditional simulation results.}\end{figure}'
    write('results.tex',result)
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9,'axes.spines.top':False,'axes.spines.right':False,'pdf.fonttype':42})
    names=list(scenarios);xx=np.arange(len(names));fig,ax=plt.subplots(1,2,figsize=(10,3.6))
    for offset,policy,label,color in [(-.18,'optimized_no_assets','No new assets','#9ca9b5'),(.18,'optimized_optional','Optional investment','#183f59')]:
        m=[scenarios[x]['policies'][policy]['net_profit'] for x in names];y=np.array([v['median']/1000 for v in m]);low=np.array([v['p05']/1000 for v in m]);high=np.array([v['p95']/1000 for v in m]);ax[0].bar(xx+offset,y,.34,label=label,color=color);ax[0].errorbar(xx+offset,y,yerr=[y-low,high-y],fmt='none',ecolor='#222',capsize=2)
    ax[0].axhline(0,color='#888',lw=.7);ax[0].set_xticks(xx,[x.title() for x in names]);ax[0].set_ylabel('Pre-tax net profit (USD thousands)');ax[0].legend(frameon=False,fontsize=8);ax[0].set_title('Complete enterprise economics')
    for off,typ,label,color in [(-.25,'research','Research undertaken','#a27a37'),(0,'repaid','Used research with positive paired value','#183f59'),(.25,'errors','Materially wrong validator passes','#b37f73')]:
        y=[100*(scenarios[x]['policies']['optimized_optional']['probability_research'] if typ=='research' else scenarios[x]['paired']['probability_research_repaid'] if typ=='repaid' else pooled[x]['error']) for x in names]
        ax[1].bar(xx+off,y,.24,label=label,color=color)
    ax[1].set_xticks(xx,[x.title() for x in names]);ax[1].set_ylabel('Percent (distinct denominators)');ax[1].set_ylim(0,max(100,ax[1].get_ylim()[1]));ax[1].legend(frameon=False,fontsize=7,loc='upper left');ax[1].set_title('Keep outcomes separate')
    fig.tight_layout();fig.savefig(GEN/'results_overview.pdf');fig.savefig(GEN/'results_overview.png',dpi=170);plt.close(fig)
    conclusion=f"The executed model supports profitable automated operation under its central and favorable commercial assumptions, while exposing a materially weaker conservative region. The central mean result is {money(cm['net_profit']['mean'])}, with {pct(cm['probability_research'])} research participation; favorable mean incremental value from optional investment is {money(F['paired']['optional_incremental_profit']['mean'])}. The useful conclusion is conditional: a human-referenced offering can retain surplus, and that surplus may fund worthwhile capabilities where reuse, quality effects, demand and lifetime justify them. Neither a fixed discount nor a prescribed sequence of investments is needed. These figures do not establish realized customer success, a universally optimal policy, zero residual error or self-accelerating invention."
    write('conclusion.tex',conclusion)
    write('reproduction.tex',r'''From the extracted package root, run the mechanism with \texttt{python3 experiment/foundry.py}. Run economic controls with \texttt{python3 -m unittest discover -s sim}. The simulation entry point is \texttt{python3 sim/economy.py}; use its \texttt{--help} output and the README's exact freeze/confirmation commands. Read \texttt{results/final/freeze.json} before editing a behavioral file. A changed artifact requires a new output directory and freeze. Complete compressed JSONL records contain every world's ledger and events; CSV summaries facilitate independent analysis. The paper uses \texttt{paper/build\_results.py} then \texttt{paper/build.py}. The HTML demonstration is self-contained and opens locally without a live model or server. See the evidence companion and QA receipts for the exact verification scope.''')
    write('sensitivity.tex','The complete preregistered stress and mechanism-ablation results are supplied in the research package. The final sensitivity table is generated from the completed stress run.')
    (GEN/'paper_metrics.json').write_text(json.dumps({'worlds_per_scenario':n,'pooled':pooled,'config_sha256':summary['config_sha256']},indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--results',type=pathlib.Path,default=ROOT/'results/final');args=parser.parse_args();main(args.results)
