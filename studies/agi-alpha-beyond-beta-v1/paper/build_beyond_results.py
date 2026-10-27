# SPDX-License-Identifier: Apache-2.0
"""Publication tables for the independently confirmed Beyond Beta edition."""
from __future__ import annotations
import argparse
import csv
import json
import pathlib
import numpy as np
from build import ROOT, GEN, esc, money, pct, number, table, write, plt

POLICIES = ['optimized_beta', 'optimized_private', 'optimized_network', 'fixed_network']
LABELS = ['Beta', 'Private Alpha', 'Network Alpha', 'Fixed network']


def describe(x):
    a = np.asarray(x, dtype=float)
    return {'mean':float(a.mean()), 'median':float(np.median(a)),
            'p05':float(np.quantile(a,.05)), 'p95':float(np.quantile(a,.95)),
            'positive':float(np.mean(a>0)), 'n':len(a)}


def main(results):
    summary = json.loads((results/'summary.json').read_text())
    if 'confirmation' not in summary['status'].lower():
        raise RuntimeError('Publication requires the new frozen confirmation, not development results')
    config = json.loads((results/'frozen_config.json').read_text())
    freeze = json.loads((results/'freeze.json').read_text())
    count = summary['worlds_per_scenario']
    data = {}
    for name, scenario in summary['scenarios'].items():
        rows = list(csv.DictReader((results/f'{name}_worlds.csv').open()))
        groups = {p:[r for r in rows if r['policy']==p] for p in POLICIES}
        if any(len(g)!=count for g in groups.values()):
            raise RuntimeError('Missing matched confirmation histories: '+name)
        # Preserve world alignment explicitly, independent of CSV output order.
        for p in POLICIES:
            groups[p].sort(key=lambda r:int(r['world']))
        ids = [[r['world'] for r in groups[p]] for p in POLICIES]
        if any(x!=ids[0] for x in ids):raise RuntimeError('Unmatched world identifiers')
        metrics = {}
        for p,rr in groups.items():
            def total(k):return sum(float(r.get(k,0) or 0) for r in rr)
            accepted=total('true_accepted_projects');passed=total('validated_deliveries')
            metrics[p]={'profit':describe([r['net_profit'] for r in rr]),
                'quality_adjusted':describe([r['quality_adjusted_profit'] for r in rr]),
                'useful':total('true_accepted_projects')/count,
                'rich':total('rich_true_projects')/count,
                'cost':total('fully_allocated_cost_total')/accepted if accepted else None,
                'direct':total('direct_cost_total')/accepted if accepted else None,
                'false_pass_rate':total('false_passes')/passed if passed else None,
                'research':sum(float(r['investment_cost'])>0 for r in rr)/count,
                'insolvency':sum(str(r.get('insolvent',r.get('insolvency',0))).lower() in ('true','1','1.0') for r in rr)/count,
                'price_fraction':np.mean([float(r['mean_price_fraction']) for r in rr]),
                'opportunities':total('qualified_opportunities')/count,
                'adoption':total('orders')/max(1,total('qualified_opportunities')),
                'research_cost':total('investment_cost')/count,
                'admissions':total('research_admissions')/count}
            if p in scenario['policies']:
                metrics[p]['insolvency']=scenario['policies'][p]['probability_insolvency']
        b=groups['optimized_beta'];pr=groups['optimized_private'];n=groups['optimized_network'];f=groups['fixed_network']
        def delta(x,y,k='net_profit'):return [float(a[k])-float(bb[k]) for a,bb in zip(x,y)]
        gain=delta(n,b);qgain=delta(n,b,'quality_adjusted_profit')
        used=[float(r['investment_cost'])>0 and float(r.get('research_admissions',0))>0 and float(r.get('R_uses',0))+float(r.get('V_uses',0))>0 for r in n]
        repaid=[bool(u and g>0) for u,g in zip(used,gain)]
        op=[float(r['investment_cost'])>0 and float(r['research_seed_funded'])<1e-7 for r in n]
        paired={'network':describe(gain),'private':describe(delta(pr,b)),
                'sharing':describe(delta(n,pr)),'pricing':describe(delta(n,f)),
                'quality_network':describe(qgain),
                'useful':describe(delta(n,b,'true_accepted_projects')),
                'rich':describe(delta(n,b,'rich_true_projects')),
                'repaid':float(np.mean(repaid)),
                'quality_repaid':float(np.mean([u and g>0 for u,g in zip(used,qgain)])),
                'operating_funded':float(np.mean(op)),
                'operating_funded_repaid':float(np.mean([a and r for a,r in zip(op,repaid)]))}
        data[name]={'policies':metrics,'paired':paired}

    c=data['central'];fav=data['favorable'];cn=c['policies']['optimized_network'];cb=c['policies']['optimized_beta']
    fn=fav['policies']['optimized_network']
    write('abstract_results.tex',f"Across {count:,} independent enterprise worlds per primary condition, mean central Beta profit was {money(cb['profit']['mean'])} over 24 operating months. Network Alpha changed that mean by {money(c['paired']['network']['mean'])}; its extra mean effect over private retention was {money(c['paired']['sharing']['mean'])}. Favorable network Alpha added {money(fav['paired']['network']['mean'])} relative to Beta, with used research and positive paired terminal value in {pct(fav['paired']['repaid'])} of worlds. Central pooled complete cost was {money(cn['cost'])} per truly accepted project and the material false-pass fraction was {pct(cn['false_pass_rate'])}. These conditional model results do not establish real demand, operational Alpha or self-accelerating invention.")
    write('headline.tex',r'\resultbox{\textbf{Two economic answers.} '+f"Competent Beta generated central mean pre-tax profit of {money(cb['profit']['mean'])}. Optional network Alpha added {money(c['paired']['network']['mean'])} centrally and {money(fav['paired']['network']['mean'])} favorably. Sharing's extra mean effect over private retention was {money(c['paired']['sharing']['mean'])} centrally. Central network pricing averaged {pct(cn['price_fraction'])} of the human reference. Its residual material false-pass rate was {pct(cn['false_pass_rate'])}; no external buyer tolerance for that rate is established. All figures are simulated and conditional on the declared assumptions."+'}')
    protocol=f"Code, decision rules, costs and the stress design were frozen before confirmation at {esc(freeze['frozen_at_utc'])}. Confirmation uses {count:,} independent enterprise worlds per condition and four matched policies: {3*count:,} independent worlds and {12*count:,} complete policy histories. The confirmation seed is {config['test_seed']}, distinct from development seed {config['train_seed']}. Each history includes paid discovery/setup, 24 operating months and settlement runoff. Every world is preserved. The experimental unit is the enterprise campaign; internal solver calls and descendant jobs are not additional independent inventions."
    protocol+='\n\n'+r'Configuration SHA-256: \nolinkurl{'+summary['config_sha256']+'}. Monetary tariffs are held at their evidence-date values. Future Beta changes are assumed capability epochs, not forecasts of named releases. Intervals summarize the specified simulated population; they are not confidence intervals for real adoption or frontier performance.'
    write('protocol.tex',protocol)

    rows=[]
    for name,d in data.items():
        m=d['policies']['optimized_network'];p=m['profit']
        rows.append([esc(name.title()),money(d['policies']['optimized_beta']['profit']['mean']),money(p['mean']),money(p['p05']),money(p['p95']),money(m['cost'])])
    result=r'\begin{table}[htbp]\centering\small'+table(['Condition','Beta mean','Network mean','Network 5th','Network 95th','Cost / useful'],rows)+r'\caption{Complete pre-tax enterprise profit and pooled network cost per truly accepted project, USD. All failed and zero-output enterprises remain in the totals. Research, graph work, discovery and setup are included.}\end{table}'
    rows=[]
    for name,d in data.items():
        m=d['policies']['optimized_network'];p=d['paired']
        rows.append([esc(name.title()),money(p['network']['mean']),money(p['sharing']['mean']),pct(m['research']),pct(p['repaid']),pct(m['false_pass_rate'])])
    result+='\n'+r'\begin{table}[htbp]\centering\small'+table(['Condition','Network $-$ Beta','Network $-$ private','Research','Repaid*','Wrong passes'],rows)+r'\caption{Paired mean effects and all-world frequencies. *Paid research, an admitted asset used on fresh work, and positive paired terminal profit after complete costs. This does not require two investments. Wrong passes are pooled material errors divided by validator-approved deliveries.}\end{table}'
    for name,d in data.items():
        m=d['policies']['optimized_network'];p=d['paired'];ref=config['scenarios'][name]['human_reference']
        result+='\n\n'+r'\textbf{'+esc(name.title())+'.} '+f"Network operation produced {number(m['useful'],1)} truly accepted projects on average from {number(m['opportunities'],1)} paid qualified opportunities. The mean monthly posted base-scope fraction was {pct(m['price_fraction'])} of the {money(ref)} reference, approximately {money(m['price_fraction']*ref)}; this is not the sales-weighted price or cleared collection per project. The pooled observed-in-simulation purchase share was {pct(m['adoption'])}. Complete cost per useful outcome was {money(m['cost'])}, versus direct delivery cost of {money(m['direct'])}. Profitable worlds were {pct(m['profit']['positive'])}; cash-shortfall shutdowns were {pct(m['insolvency'])}."
        result+=' '+f"Network Alpha's paired effect had a 5th--95th percentile range of {money(p['network']['p05'])} to {money(p['network']['p95'])}. Its mean effect on useful projects was {number(p['useful']['mean'],2)} and on richer supported projects {number(p['rich']['mean'],2)}. Research occurred in {pct(m['research'])} of worlds; {pct(p['operating_funded'])} undertook it exclusively from operating-generated funds under the stated source rule, and {pct(p['operating_funded_repaid'])} combined that funding with used assets and positive paired value. Mean paid campaign cost was {money(m['research_cost'])} over all worlds, including those that rationally chose no campaign."
        result+=' '+f"Private Alpha's mean effect over Beta was {money(p['private']['mean'])}. Sharing's additional effect was {money(p['sharing']['mean'])}, with a 5th--95th percentile range of {money(p['sharing']['p05'])} to {money(p['sharing']['p95'])}. Endogenous network pricing changed mean profit by {money(p['pricing']['mean'])} against the fixed 65\% diagnostic. This last effect includes induced research choices and is not a pure elasticity estimate."
    result+='\n\n'+f"Removing every otherwise undetected paid false-pass receipt as a terminal valuation stress leaves central network mean adjusted profit of {money(cn['quality_adjusted']['mean'])} and favorable mean adjusted profit of {money(fn['quality_adjusted']['mean'])}. This is a valuation sensitivity, not a new cash-timing trajectory or full liability model. It does not show that the residual semantic error rate is commercially acceptable."
    result+='\n\nAn admission is a simulated expected-value judgment. It is neither equivalent to positive realized Alpha nor empirical certification of the retained software. The no-asset control can profit while declining research because Beta already supplies strong capability. New assets compete with existing equivalents, shared capacity, copying and a limited useful lifetime.'
    result+='\n'+r'\begin{figure}[htbp]\centering\includegraphics[width=\linewidth]{generated/results_overview.pdf}\caption{Left: median complete profit and 5th--95th percentile ranges. Right: mean causal increments from private retention and network availability, at matched aggregate resources. All values are conditional simulation outcomes.}\end{figure}'
    write('results.tex',result)

    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9,'axes.spines.top':False,'axes.spines.right':False,'pdf.fonttype':42})
    names=list(data);xx=np.arange(len(names));fig,ax=plt.subplots(1,2,figsize=(10,3.6))
    for offset,policy,label,color in [(-.24,'optimized_beta','Beta','#a3b0ba'),(0,'optimized_private','Private Alpha','#b59658'),(.24,'optimized_network','Network Alpha','#183f59')]:
        mm=[data[x]['policies'][policy]['profit'] for x in names];y=np.array([v['median']/1000 for v in mm]);low=np.array([v['p05']/1000 for v in mm]);hi=np.array([v['p95']/1000 for v in mm])
        ax[0].bar(xx+offset,y,.23,label=label,color=color);ax[0].errorbar(xx+offset,y,yerr=[y-low,hi-y],fmt='none',ecolor='#222',capsize=2)
    ax[0].set_ylabel('Pre-tax net profit (USD thousands)');ax[0].legend(frameon=False,fontsize=8);ax[0].set_title('Beta economics and retained Alpha')
    for offset,k,label,color in [(-.18,'private','Private − Beta','#b59658'),(.18,'sharing','Network − private','#183f59')]:
        ax[1].bar(xx+offset,[data[x]['paired'][k]['mean']/1000 for x in names],.34,label=label,color=color)
    ax[1].set_ylabel('Mean paired increment (USD thousands)');ax[1].legend(frameon=False,fontsize=8);ax[1].set_title('Keep the incremental questions distinct')
    for a in ax:a.axhline(0,color='#888',lw=.7);a.set_xticks(xx,[x.title() for x in names])
    fig.tight_layout();fig.savefig(GEN/'results_overview.pdf');fig.savefig(GEN/'results_overview.png',dpi=170);plt.close(fig)

    write('conclusion.tex',f"The model separates a potentially profitable frontier service from the harder claim that retained and shared capabilities add net value. Central Beta mean pre-tax profit was {money(cb['profit']['mean'])}; optional network Alpha's additional mean effect was {money(c['paired']['network']['mean'])}. In favorable conditions the increment was {money(fav['paired']['network']['mean'])}, with used research and positive paired value in {pct(fav['paired']['repaid'])} of worlds. These results support only the mechanisms and conditions actually tested. They do not establish actual sales, operational Alpha, a permanent moat, universal optimality or self-accelerating invention. A network invents economic possibilities only when useful changes survive competent Beta comparisons, complete costs, finite cash and subsequent erosion; preserving cash is a legitimate outcome when they do not.")
    write('reproduction.tex',r'''From the package root, run the bounded mechanism with \texttt{python3 experiment/foundry.py}. Run the new lifecycle and economic tests using the README's exact commands. The Beyond Beta simulator is \texttt{sim/economy\_v2.py}; read its frozen protocol and hash manifest before changing behavior. A changed artifact requires a new output directory and independent seed. Every world's monthly ledger and events are preserved in compressed JSONL; CSVs support independent analysis. The paper is generated from \texttt{paper/build\_beyond\_results.py}, the threshold/stress builders and \texttt{paper/build.py}. The bilingual HTML opens locally without a model or server. The earlier simulation files remain development history and are not the active confirmation protocol.''')
    (GEN/'paper_metrics.json').write_text(json.dumps({'worlds_per_scenario':count,'config_sha256':summary['config_sha256'],'scenarios':data},indent=2)+'\n')
    print(json.dumps({'worlds_per_scenario':count,'scenarios':data},indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--results',type=pathlib.Path,default=ROOT/'results/beyond_beta_final');a=p.parse_args();main(a.results)
