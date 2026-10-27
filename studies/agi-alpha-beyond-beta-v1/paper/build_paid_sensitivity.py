# SPDX-License-Identifier: Apache-2.0
"""Render every prespecified sensitivity; no selection or parameter changes."""
import csv
import json
import math
from build import ROOT, esc, money, pct, number, table, write

LABELS={
'lower_reference_4900':'Human reference USD 4,900',
'demand_downturn_one_arrival':'One opportunity per month',
'zero_job_candidate_emergence':'No job-born candidates',
'optional_research_disabled':'No separate C research',
'zero_alpha_mapping':'Zero incremental Alpha effects',
'cost_only_alpha':'Nominal cost-only effects (qualified)',
'all_recipients_already_equivalent':'All recipients already equivalent',
'free_ordinary_reuse_across_agents':'Ordinary cross-agent reuse is free',
'static_beta':'Static Beta',
'rapid_beta_erosion':'Faster Beta erosion',
'fortyeight_recipients_same_compute':'48 recipients; same compute',
'specialized_routing_same_compute':'Specialist routing; same compute',
'concentrated_compatible_scope':'Concentrated supported schema',
'validation_activity_double':'Double validation activities',
'retention_activity_double':'Double retention activities',
'strong_shared_errors':'Stronger correlated errors',
'authorization80_lag2':'80% authorization, two-month lag',
'loose_capacity_cost_only':'Looser capacity; quality effects retained',
'compound_static_beta_large_pool_recurrence':'Joint static-Beta / larger-pool case',
}

def main():
    path=ROOT/'results/paid_work_sensitivity'
    manifest=json.loads((path/'design_freeze.json').read_text())
    actual=json.loads((path/'run_manifest.json').read_text())
    if any(actual.get(k)!=v for k,v in manifest.items()):
        raise RuntimeError('Sensitivity run does not match frozen design')
    rows=list(csv.DictReader((path/'results.csv').open()))
    byname={r['name']:r for r in rows}
    if len(byname)!=len(manifest['cases']) or set(byname)!={c['name'] for c in manifest['cases']}:
        raise RuntimeError('Missing or extra prespecified sensitivity cases')
    records=[]
    for case in manifest['cases']:
        name=case['name'];row=byname[name]
        summary=json.loads((path/f'{name}_summary.json').read_text())
        if summary['config_sha256']!=case['configuration_sha256'] or summary['workflow_costs_sha256']!=case['workflow_costs_sha256']:
            raise RuntimeError('Unmatched stress inputs: '+name)
        record={'name':name,'label':LABELS[name],'scenario':case['scenario'],'compound':case['compound']}
        for k,v in row.items():
            if k in ('name','scenario','compound'):continue
            record[k]=float(v) if v not in ('','None') else None
        records.append(record)
    body=r'\subsection{Prespecified sensitivity and ablation results}'
    body+=f"\nThe {len(records)} frozen conditions each use {manifest['worlds_per_case']} independent world IDs and four matched policies. The common stress seed is {manifest['seed']}, separate from the primary confirmation seed. Conditions reuse keyed random streams: there are {len(records)*manifest['worlds_per_case']:,} case--world evaluations, not that many mutually independent draws. Every condition and all scalar world outcomes are preserved. Compound changes are explicitly exploratory scenarios, declared before confirmation; they are not isolated causal estimates or calibrated demand forecasts."
    display=[]
    for r in records:
        label=esc(r['label'])+(' (C)' if r['scenario']=='central' else '')+('*' if r['compound'] else '')
        display.append([label,money(r['beta_profit_mean']),money(r['network_incremental_profit_mean']),pct(r['probability_retention']),pct(r['probability_retention_admission'])])
    body+='\n'+r'\begin{table}[htbp]\centering\scriptsize'+table(
        ['Condition','Beta profit','Network $-$ Beta','Retention','Admission'],display,
        r'p{.37\linewidth}rrrr')+r'\caption{All prespecified stresses, USD means and all-world frequencies. (C) changes the central condition; other rows change the favorable condition. *Compound scenario. Retention is any additional B purchase; admission is any paid-job capsule admitted within the simulation. No frozen sensitivity produces actual capsule reuse or operating-funded useful feedback. These capability results are qualified by the recipient decision bottleneck described below.}\end{table}'
    named={r['name']:r for r in records}
    zero=named['zero_alpha_mapping'];ordinary=named['free_ordinary_reuse_across_agents'];equiv=named['all_recipients_already_equivalent'];cost=named['cost_only_alpha'];rapid=named['rapid_beta_erosion'];static=named['static_beta'];pool=named['fortyeight_recipients_same_compute'];joint=named['compound_static_beta_large_pool_recurrence']
    body+='\n\n'+r'\textbf{Redundancy and attribution.} '+f"Removing the modeled Alpha effects changes network profit relative to Beta by {money(zero['network_incremental_profit_mean'])}; making every recipient equivalent yields {money(equiv['network_incremental_profit_mean'])}. When ordinary cross-agent reuse is itself free and equivalent, the increment is {money(ordinary['network_incremental_profit_mean'])}. These controls test whether the formal sharing layer adds anything beyond capabilities already available. The nominal cost-only case produces {money(cost['network_incremental_profit_mean'])}, but a recipient-valuation defect prevents interpreting it as a clean quality-free ablation. Reliability-linked dollar value must not be inferred solely from avoided token costs."
    body+='\n\n'+r'\textbf{The moving frontier and the recipient pool.} '+f"Static Beta produces a mean increment of {money(static['network_incremental_profit_mean'])}, versus {money(rapid['network_incremental_profit_mean'])} under faster erosion. Forty-eight heterogeneous recipients at unchanged aggregate compute produce {money(pool['network_incremental_profit_mean'])}; this isolates recipient-pool structure from simply buying more compute. The joint scenario produces {money(joint['network_incremental_profit_mean'])}, with useful operating-funded feedback in {pct(joint['probability_operating_funded_paid_job_feedback'])} of worlds. It jointly holds Beta static, expands the recipient pool, increases paid-contract arrivals and pays for fourfold reserved capacity/control resources. Its result cannot be attributed to any one of those changes."
    bad=named['strong_shared_errors'];cheap=named['lower_reference_4900'];low=named['demand_downturn_one_arrival']
    body+='\n\n'+r'\textbf{Commercial failure conditions.} '+f"At the USD 4,900 human reference, mean Beta profit is {money(cheap['beta_profit_mean'])}; with one monthly opportunity it is {money(low['beta_profit_mean'])}. Stronger correlated errors leave {pct(bad['pooled_material_error_fraction'])} material errors among approved deliveries and mean Beta profit of {money(bad['beta_profit_mean'])}. Positive accounting profit alone does not establish an acceptable error rate, buyer trust or product fitness."
    body+='\n\nThe frozen identifier \\texttt{loose\\_capacity\\_cost\\_only} changes reserved capacity but retains quality effects; it is therefore labeled accordingly in the table. The distinct \\texttt{cost\\_only\\_alpha} case removes the quality increment. No frozen parameters were changed to repair that naming ambiguity. The primary candidate-scan frequency and one-campaign forecast are bounded heuristics; a policy that stops unproductive searching may do better. No global optimum is claimed.'
    body+='\n\n'+r'\textbf{What the frozen Alpha result cannot establish.} '+f"The 48-recipient, same-compute case purchases retention in {pct(pool['probability_retention'])} of worlds and admits it in {pct(pool['probability_retention_admission'])}; the compound case purchases in {pct(joint['probability_retention'])} and admits in {pct(joint['probability_retention_admission'])}. Neither produces a capsule use. A post-confirmation independent review found that recipient beliefs and admission forecasts are not harmonized. The candidate posterior mean $(2+s)/(4+n)$ has a ceiling of $26/28=0.92857$ after 24 perfect cases, or $18/20=0.90$ after a 16-case reassessment. It is compared with a known favorable Beta component correctness of at least $0.97$. Even at the lowest permitted price and greatest reconstruction saving, the resulting favorable per-use valuation is negative before acquisition costs. Zero uptake is therefore structurally imposed by this conservative trust rule, rather than evidence that every underlying capability lacks incremental value. Admission and capital forecasts can still expect deployment, creating a controller mismatch."
    body+='\n\nThe frozen cost-only ablation also omits the quality-effect multiplier from recipient valuation, so it can charge a perceived quality penalty although the deployed capability has no modeled quality effect. All frozen outcomes and hashes are preserved; this limitation does not alter Beta-only delivery, cash or profit. The positive USD24.78 increment in the concentrated-schema case has no retention purchase or reuse and is an incidental whole-policy resource/cash effect, not evidence of Alpha.'
    body+='\n\nA deterministic replay of the lowest-ID admitted compound world matches all 95 saved scalar and paired fields. It spends USD232.04 on an admitted package, uses it zero times, and loses USD843.61 relative to Beta. This is an admitted-but-unused mechanism diagnostic, not a new trial. The separate directed QA transfer fixture exercises a useful fresh-recipient branch but loses USD450.05 over the whole paired trajectory; its forced action is never commercial-selection evidence. One fresh-sample posterior-coherence diagnostic is declared separately; it changes beliefs, not actual model capability, and cannot replace the frozen primary or stress findings.'
    write('sensitivity.tex',body)
    (path/'paper_sensitivity_metrics.json').write_text(json.dumps({'worlds_per_case':manifest['worlds_per_case'],'records':records},indent=2)+'\n')
    print(json.dumps({'cases':len(records),'worlds_per_case':manifest['worlds_per_case'],'all_frozen_cases_rendered':True}))

if __name__=='__main__':
    main()
