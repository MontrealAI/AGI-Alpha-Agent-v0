# SPDX-License-Identifier: Apache-2.0
"""Analytic initial-state screening; never a substitute for cash simulation."""
import json
import math
import pathlib
import sys
import numpy as np

ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'sim'))
from economy import Belief, cost_table, price_plan, resource_sum, scaled


def main():
    c=json.loads((ROOT/'results/final/frozen_config.json').read_text())
    w=json.loads((ROOT/'results/final/frozen_workflow_costs.json').read_text())
    c['_stages']=w['stages'];table=cost_table(w);o=c['operations'];records={}
    setup=resource_sum(scaled(table[k],v) for k,v in c['discovery_budget_counts'].items())
    setup_months=math.ceil(max(setup['minutes']/o['monthly_workbench_minutes'],setup['tokens']/o['monthly_token_quota']))
    fixed=o['monthly_control_cost']+o['monthly_business_automation_cost']
    for name,sc in c['scenarios'].items():
        b=Belief(np.asarray(c['market']['prior_weights'],float)/sum(c['market']['prior_weights']),c['market']['arrival_prior_shape'],c['market']['arrival_prior_rate'])
        plan=price_plan(c,sc,table,b,{},1,'optimized_optional');d=plan['delivery'];mix=c['scope']['base_share']+(1-c['scope']['base_share'])*c['scope']['rich_human_reference_multiplier']
        price=plan['fraction']*sc['human_reference']*mix
        receipt=price*sc['collection_probability']*(1-o['payment_fraction'])-o['payment_fixed']*sc['collection_probability']
        false_fee=d['false_pass']/d['true_pass']*sc['collection_probability']*(price*o['payment_fraction']+o['payment_fixed'])
        direct=d['usd']/d['true_pass']+o['storage_per_delivery']*(d['true_pass']+d['false_pass'])/d['true_pass']
        qualification=sc['arrivals_month']*o['qualification_units_per_opportunity']*table['intake_clarification']['usd']*sc['activity_quantity_multiplier']
        sunk_amort=(setup['usd']+setup_months*fixed)/c['months']
        contribution=receipt-false_fee-direct
        n=(fixed+qualification+sunk_amort)/contribution if contribution>0 else None
        records[name]={'initial_model_selected_price_fraction':plan['fraction'],
          'scope_mix_mean_offer_usd':price,'net_receipt_per_true_project_usd':receipt,
          'forecast_direct_cost_per_true_project_usd':direct,'refunded_false_pass_processing_fee_per_true_usd':false_fee,
          'fixed_plus_qualification_plus_amortized_setup_per_month':fixed+qualification+sunk_amort,
          'minimum_true_projects_per_month_screen':n,
          'required_purchase_share_of_supported_opportunities_screen':n/(sc['arrivals_month']*c['scope']['supported_domain_fraction']*d['true_pass']) if n is not None else None,
          'maximum_direct_cost_per_true_at_one_true_project_month':receipt-false_fee-(fixed+qualification+sunk_amort),
          'maximum_direct_cost_per_true_at_five_true_projects_month':receipt-false_fee-(fixed+qualification+sunk_amort)/5,
          'forecast_no_research_project_capacity_month':min(o['monthly_workbench_minutes']/d['minutes'],o['monthly_token_quota']/d['tokens'],4*o['monthly_workbench_minutes']/d['container_minutes']),
          'expected_true_pass_probability':d['true_pass'],'expected_validator_false_pass_probability':d['false_pass']}
    out={'status':'Analytic initial-state screening from frozen inputs, not empirical demand or guaranteed simulation break-even',
         'limitations':['Uses the controller approximate expected-delivery model and its initial posterior price.',
                        'Refunds all false passes in expected contribution; actual simulation records discovery/collection timing separately.',
                        'Amortizes charged discovery/setup over24 operating months; no candidate investment is forced.',
                        'Omits correlated burst and queue transitions and is not a cash-shortfall probability calculation.',
                        'Reported capacity uses the assumed internal allocation, not an account entitlement.'],
         'scenarios':records}
    (ROOT/'results/final/analytic_thresholds.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps(out,indent=2))


if __name__=='__main__':main()
