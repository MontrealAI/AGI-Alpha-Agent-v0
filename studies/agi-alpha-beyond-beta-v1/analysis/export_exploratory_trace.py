# SPDX-License-Identifier: Apache-2.0
"""Normalize the preselected saved diagnostic trajectory; never run another world."""
import json,hashlib
from pathlib import Path
from export_paid_work_trace import build_export,qualifying_paths,markdown
ROOT=Path(__file__).resolve().parents[1]

def main():
    path=ROOT/'results/paid_work_prior_diagnostic';selected=path/'selected_useful_nonpayback'
    read=lambda p:json.loads(p.read_text())
    manifest=read(selected/'selection_manifest.json');summary=read(path/'summary.json');chain=read(selected/'chain.json')
    if not manifest['all_three_saved_arms_matched'] or manifest['strict_paid_job_feedback'] or manifest['network_vs_beta_profit']>=0:
        raise ValueError('Selected trace no longer matches its disclosed nonpayback criterion.')
    if hashlib.sha256((path/'run_manifest.json').read_bytes()).hexdigest()!=manifest['source_completed_run_manifest_sha256']:
        raise ValueError('Selected trace belongs to another completed diagnostic.')
    network=read(selected/'posterior_coherent_network.json');beta=read(selected/'frozen_beta.json')
    route=next(x for x in qualifying_paths(network) if x[0]['id']==chain['capability_id'])
    assert route[3][0]['job_id']==chain['recipient_job_id']
    selection={'basis':'SELECTED_EXPLORATORY_USEFUL_REUSE_WITHOUT_COMPLETE_NETWORK_PAYBACK','rule':manifest['selection_rule'],
               'qualifying_worlds_in_selected_scenario':None,'scenario_worlds':summary['worlds'],
               'network_population_median_profit':summary['arms']['posterior_coherent_network']['net_profit']['median'],
               'population_feedback_frequency':summary['paired']['probability_operating_funded_paid_job_feedback'],
               'illustration_is_not_frequency_estimate':True,'latent_truth_used_only_for_retrospective_illustration_selection':True}
    mapped={'config_sha256':summary['configuration_sha256'],'workflow_costs_sha256':summary['workflow_costs_sha256']}
    data=build_export(path,mapped,(network,beta,route,selection))
    data['source_record_file']=str((selected/'posterior_coherent_network.json').relative_to(ROOT))
    data['matched_beta_record_file']=str((selected/'frozen_beta.json').relative_to(ROOT))
    data['diagnostic_arm']='posterior_coherent_network';data['seed']=summary['seed'];data['selection_manifest']=manifest
    data['primary_confirmation_config_sha256']=read(ROOT/'results/paid_work_final/summary.json')['config_sha256']
    data['primary_has_qualifying_path']=False
    data['limitations'].insert(0,'This is the lowest-ID selected saved world of the single exploratory prior-alignment diagnostic. It shows useful reuse and negative total network value, not profitable feedback; no new world was run.')
    out=ROOT/'results/paid_work_exploratory_trace.json';out.write_text(json.dumps(data,indent=2,ensure_ascii=False));out.with_suffix('.md').write_text(markdown(data).replace('Qualifying worlds in this scenario: None/100.','The selection exporter did not enumerate the qualifying subset; aggregate useful-reuse frequency is reported separately.'))
    print(json.dumps({'output':str(out),'world':data['world'],'basis':data['basis'],'network_minus_beta':data['paired_network_minus_beta']['net_profit']}))

if __name__=='__main__':main()
