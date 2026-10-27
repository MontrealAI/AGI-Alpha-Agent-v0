# SPDX-License-Identifier: Apache-2.0
"""Transparent analytic screens from frozen paid-work inputs; no retuning."""
import copy
import csv
import json
import math
import pathlib
import sys
from build import ROOT, esc, money, number, pct, table, write
sys.path.insert(0,str(ROOT/'sim'))
from economy_v3 import cost_table, current_table, expected_delivery, resource_sum, scaled


def main():
    out=ROOT/'results/paid_work_final'
    c=json.loads((out/'frozen_config.json').read_text())
    w=json.loads((out/'frozen_workflow_costs.json').read_text())
    metrics=json.loads((ROOT/'paper/generated/paper_metrics.json').read_text())
    c['_stages']=w['stages'];base=cost_table(w);t=current_table(c,base,1);o=c['operations']
    setup=resource_sum(scaled(base[k],v) for k,v in c['discovery_budget_counts'].items())
    fixed=o['monthly_control_cost']+o['monthly_business_automation_cost']
    setup_months=math.ceil(max(setup['minutes']/o['monthly_workbench_minutes'],setup['tokens']/o['monthly_token_quota']))
    startup=setup['usd']+setup_months*fixed+o.get('setup_cost',0)
    settlement_overhead=c['runoff_months']*fixed
    records={};grid=[]
    validation_ids=['independent_semantic_validation','certificate_checker_reconstruction','adversarial_harness_reconstruction','fresh_stress_and_holdout_execution','revalidation']
    for name,sc in c['scenarios'].items():
        # Initial heterogeneous Beta includes existing and partial equivalents.
        # Average scope difficulty is an analytic approximation; confirmation
        # samples individual domains, histories and faults explicitly.
        local_sc=copy.deepcopy(sc)
        local_sc['semantic_correctness']=max(0,sc['semantic_correctness']-sum(
            weight*penalty for weight,penalty in zip(c['scope']['domain_weights'],c['scope']['domain_semantic_penalties'])))
        overlap=c['scope']['partial_equivalent_probability']*c['scope']['partial_reconstruction_saving']
        coverage={n:c['scope'][f'existing_equivalent_{n}']+(1-c['scope'][f'existing_equivalent_{n}'])*overlap for n in ('R','V')}
        d=expected_delivery(c,local_sc,t,coverage['R'],coverage['V'])
        no_val=copy.deepcopy(t)
        for k in validation_ids:no_val[k]['usd']=0.
        dv=expected_delivery(c,local_sc,no_val,coverage['R'],coverage['V'])
        abst=o.get('admission_abstention_probability',o.get('admission_abstention',.06))
        tp=(1-abst)*d['true_pass'];fp=(1-abst)*d['false_pass'];quantity=sc['activity_quantity_multiplier']
        attempt_usd=(1-abst)*d['usd']+abst*t['intake_clarification']['usd']*quantity
        validation_usd=(1-abst)*(d['usd']-dv['usd'])
        direct=attempt_usd/tp
        storage=o['storage_per_delivery']*(tp+fp)/tp
        recovery=fp/tp*t['recovery']['usd']*quantity
        lead_counts=o['qualification_units_per_opportunity']+(1-c['scope']['supported_domain_fraction'])
        qualification=sc['arrivals_month']*lead_counts*t['intake_clarification']['usd']*quantity
        monthly=fixed+qualification+(startup+settlement_overhead)/c['months']
        mix=c['scope']['base_share']+(1-c['scope']['base_share'])*c['scope']['rich_human_reference_multiplier']
        selected=metrics['scenarios'][name]['policies']['optimized_beta']['price_fraction']
        def screen(fraction):
            offer=fraction*sc['human_reference']*mix
            received=sc['collection_probability']*(offer*(1-o['payment_fraction'])-o['payment_fixed'])
            false_fees=fp/tp*sc['collection_probability']*(offer*o['payment_fraction']+o['payment_fixed'])
            ancillary=storage+recovery+false_fees
            margin=received-direct-ancillary
            minimum=monthly/margin if margin>0 else None
            return {'scenario':name,'price_fraction':fraction,'scope_mix_offer':offer,
                    'net_receipt_per_true_project':received,'expected_direct_cost_per_true_project':direct,
                    'validation_cost_per_true_project':validation_usd/tp,'ancillary_per_true_project':ancillary,
                    'fixed_qualification_startup_monthly':monthly,'settlement_overhead_allocated_monthly':settlement_overhead/c['months'],'contribution_per_true_project':margin,
                    'minimum_true_projects_monthly':minimum,
                    'required_purchase_share':minimum/(sc['arrivals_month']*c['scope']['supported_domain_fraction']*tp) if minimum is not None else None,
                    'max_total_direct_cost_at_one_true_project_month':received-ancillary-monthly,
                    'max_validation_cost_at_one_true_project_month':received-ancillary-monthly-(direct-validation_usd/tp)}
        result=screen(selected)
        expected_resources={k:(1-abst)*d[k]+abst*t['intake_clarification'][k]*quantity for k in ['minutes','tokens','container_minutes']}
        qualification_resources={k:sc['arrivals_month']*lead_counts*t['intake_clarification'][k]*quantity for k in expected_resources}
        caps={'minutes':o['monthly_workbench_minutes'],'tokens':o['monthly_token_quota'],'container_minutes':4*o['monthly_workbench_minutes']}
        result['project_capacity_monthly_before_bursts_queues_or_retention']=min(max(0,caps[k]-qualification_resources[k])/expected_resources[k] for k in caps)
        result['assumed_true_pass_per_purchased_attempt']=tp
        result['initial_beta_equivalent_coverage']=coverage
        result['semantic_correctness_scope_average']=local_sc['semantic_correctness']
        result['capacity_by_resource']={k:max(0,caps[k]-qualification_resources[k])/expected_resources[k] for k in caps}
        records[name]=result
        grid.extend(screen(float(p)) for p in c['price_fractions'])
    retention=[]
    for name,cost in w['incremental_retention_options'].items():
        components=['R','V'] if name=='bundle' else [name]
        benefit=sum(w['totals'][f'{x}_avoidable_reconstruction_usd'] for x in components)
        retention.append({'candidate':name,'additional_upfront_cost':cost['derived_budget_usd'],
                          'maximum_named_cost_saving_per_compatible_use':benefit,
                          'ideal_direct_savings_reuses':cost['derived_budget_usd']/benefit,
                          'source_job_cost_charged_again':0.0})
    obj={'status':'Analytic screening from frozen assumptions, not observed demand or a full cash-risk simulation',
         'price_basis':'Actual confirmation mean monthly posted base-scope fraction; not a sales-weighted price or a newly optimized policy.',
         'limits':['Initial no-new-capsule workflow includes expected existing/partial equivalents and average supported-domain semantic difficulty. It is an analytic approximation, not the realized evolving Beta mixture.',
                   'All false passes are refunded and recovery/processing charged in this analytic screen; the main simulation models detection and timing.',
                   'Startup and fixed settlement-runoff overhead are amortized over the operating horizon; cash still has to exist before any expenditure. Qualification and required purchase share use the initial scenario opportunity rate, not a forecast of actual demand growth.',
                   'Capacity screen excludes common bursts, queues, maintenance and retention, and is an upper operating envelope, not a throughput guarantee.',
                   'Maximum validation cost holds performance fixed; spending up to a ceiling does not establish the same accuracy.',
                   'Simple reuse ratios omit future access, transfer, maintenance, erosion, failure and opportunity costs.'],
         'scenarios':records,'retention_lower_bounds':retention}
    (out/'analytic_thresholds.json').write_text(json.dumps(obj,indent=2)+'\n')
    with (out/'price_threshold_grid.csv').open('w') as f:
        writer=csv.DictWriter(f,fieldnames=list(grid[0]));writer.writeheader();writer.writerows(grid)
    rows=[]
    for name,r in records.items():
        rows.append([esc(name.title()),number(r['minimum_true_projects_monthly'],3) if r['minimum_true_projects_monthly'] else 'No positive margin',pct(r['required_purchase_share']) if r['required_purchase_share'] is not None else '--',money(r['max_validation_cost_at_one_true_project_month']),number(r['project_capacity_monthly_before_bursts_queues_or_retention'],1)])
    text=r'\subsection{Conditional break-even screens}\begin{table}[htbp]\centering\small'+table(['Condition','Useful / month','Required purchase','Validation ceiling*','Capacity upper*'],rows)+r'\caption{Analytic screens at the confirmation mean posted price. *Validation ceiling is per useful outcome at one useful project/month; capacity is purchased project attempts/month before bursts, queues, retention and maintenance. Complete setup, settlement-runoff overhead and qualification are included; all false passes are refunded in this screen. These are conditional thresholds, not demand evidence or service guarantees.}\end{table}'
    text+='\nThe primary retention options cost '+', '.join(money(r['additional_upfront_cost'],2)+' for '+esc(r['candidate']) for r in retention)+'. Their optimistic reconstruction-only reuse requirements are '+', '.join(number(r['ideal_direct_savings_reuses'],1)+' for '+esc(r['candidate']) for r in retention)+'. The source job is not charged again. Actual repayment requires enough compatible first encounters with recipients after overlap, transfer, access, upkeep, erosion and the capacity consumed by retention.'
    text+='\n\nFor an additional retention bill $K$, maximum affordable expenditure at a decision is cleared cash minus protected liabilities, reserves and headroom. The full ledger determines this ceiling before spending. For constant compatible reuse $u$ and per-use incremental value $b_t$, the prospective screen is $\\sum_{t=1}^{H}\\delta^t(ub_t-m_t)>K$, where $m_t$ includes remaining maintenance and revalidation. Advancing Beta changes $b_t$; a shorter useful lifetime or lower adoption can make waiting optimal even after a profitable source job.'
    write('thresholds.tex',text)
    print(json.dumps(obj,indent=2))


if __name__=='__main__':main()
