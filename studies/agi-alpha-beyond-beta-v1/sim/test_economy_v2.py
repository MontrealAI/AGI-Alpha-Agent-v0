# SPDX-License-Identifier: Apache-2.0
import copy, json, pathlib, unittest
import numpy as np
from economy_v2 import (load_inputs, cost_table, simulate, initial_primitives, Belief,
    buyer_probabilities, coverage, Asset, dumps, alpha_assessment_inputs, current_table,
    beta_epoch, POLICIES)
C,R=load_inputs(pathlib.Path(__file__).with_name('config_v2.json'))

def context():
    c=copy.deepcopy(C);sc=c['scenarios']['favorable'];c['_stages']=R['stages'];c['_scenario']=sc;c['_private']=False
    c['_equiv']={n:np.zeros((12,6),dtype=bool) for n in ('R','V')};c['_partial']={n:np.zeros((12,6),dtype=bool) for n in ('R','V')};c['_known_coverage']={'R':0.,'V':0.}
    b=Belief(np.ones(9)/9,20,1);return c,sc,b,current_table(c,cost_table(R),2)

class EconomyV2Tests(unittest.TestCase):
    def test_tariffs_and_complete_campaigns(self):
        table=cost_table(R)
        self.assertAlmostEqual(sum(table[s['id']]['usd'] for s in R['stages']),263.46)
        for campaign in R['investment_campaigns'].values():self.assertAlmostEqual(sum(table[k]['usd']*n for k,n in campaign['counts'].items()),campaign['derived_budget_usd'])
        self.assertEqual(C['operations']['max_corrections'],2)
    def test_cash_resources_and_equal_compute_four_policies(self):
        shared=initial_primitives(C,C['scenarios']['central'],C['train_seed'],2);results=[simulate(C,R,'central',2,p,C['train_seed'],shared) for p in POLICIES]
        for r in results:
            self.assertEqual(r.metrics['setup_months'],1)
            for row in r.ledger:
                self.assertGreaterEqual(row['closing_cash'],0)
                self.assertAlmostEqual(row['opening_cash']+row['collections']-row['operating_outflow']-row['investment_outflow']-row['refund_outflow']-row['arrears_outflow'],row['closing_cash'],places=6)
                for suffix in ['tokens','workbench_minutes','container_minutes']:self.assertLessEqual(row['delivery_'+suffix]+row['research_'+suffix],row['capacity_'+suffix]+1e-5)
        for r in results[1:]:self.assertEqual([(x['capacity_tokens'],x['capacity_workbench_minutes']) for x in r.ledger],[(x['capacity_tokens'],x['capacity_workbench_minutes']) for x in results[0].ledger])
    def test_zero_effect_keeps_optimized_policies_identical(self):
        c=copy.deepcopy(C);c['network']['alpha_activity_effect_fraction']=0;c['network']['alpha_quality_effect_fraction']=0;shared=initial_primitives(c,c['scenarios']['favorable'],c['train_seed'],1)
        results=[simulate(c,R,'favorable',1,p,c['train_seed'],shared) for p in POLICIES[:3]]
        for r in results[1:]:self.assertEqual(r.metrics,results[0].metrics);self.assertEqual(r.ledger,results[0].ledger)
    def test_unobserved_future_transfer_does_not_enter_assessment(self):
        c,sc,b,table=context();a=Asset('R',1,True,.98,.7,np.zeros(12,dtype=bool),{},acquisition_done=set(),lifecycle_id='prior',creator=0,beta_version='beta-1')
        first=alpha_assessment_inputs(c,sc,table,b,{'R':a},['V'],{'V':True},C['train_seed'],1,2,'new',1000,'optimized_network')
        a.transfer[:]=True
        second=alpha_assessment_inputs(c,sc,table,b,{'R':a},['V'],{'V':True},C['train_seed'],1,2,'new',1000,'optimized_network')
        self.assertEqual(dumps(first),dumps(second))
    def test_component_assessment_never_claims_project_observations(self):
        c,sc,b,table=context();obs,costs,forecast,evidence,_,_=alpha_assessment_inputs(c,sc,table,b,{},['R'],{'R':True},C['train_seed'],1,2,'test',1000,'optimized_network')
        self.assertEqual(evidence['complete_project_test_executions'],0)
        self.assertTrue(all('candidate_accepted' not in o and o['acceptance_unit']=='component_test' and o['project_value_basis']=='MODEL_EXTRAPOLATION_FROM_COMPONENT_TESTS' for o in obs))
        self.assertGreater(costs['remaining_privacy'],0);self.assertGreater(costs['remaining_revalidation'],0)
    def test_all_equivalent_recipients_supply_no_eligible_alpha(self):
        c,sc,b,table=context()
        for n in ('R','V'):c['_equiv'][n][:]=True
        _,_,forecast,_,_,_=alpha_assessment_inputs(c,sc,table,b,{},['R'],{'R':True},C['train_seed'],1,2,'test',1000,'optimized_network')
        self.assertEqual(forecast['expected_uses'],0);self.assertEqual(forecast['recipients_missing_equivalent'],0)
    def test_beta_reduces_only_named_reconstruction_work(self):
        c,sc,b,table=context();base=cost_table(R);late=current_table(c,base,17)
        self.assertEqual(beta_epoch(c,17)['version'],'beta-3')
        self.assertLess(late['semantic_compiler_reconstruction']['usd'],base['semantic_compiler_reconstruction']['usd'])
        self.assertEqual(late['frontier_formulation']['usd'],base['frontier_formulation']['usd'])
    def test_false_passes_not_true_projects(self):
        c=copy.deepcopy(C);sc=c['scenarios']['central'];sc.update(semantic_correctness=0,shared_fault_probability=1,shared_fault_miss=1);c['operations']['postdelivery_discovery']=1;c['fixed_price_ablation']=.2;sc['asset_build_success']=0
        r=simulate(c,R,'central',3,'fixed_network',c['train_seed']);self.assertEqual(r.metrics['true_accepted_projects'],0);self.assertGreater(r.metrics['false_passes'],0);self.assertGreater(r.metrics['refunds'],0)
    def test_zero_authorization_and_same_month_settlement(self):
        c=copy.deepcopy(C);c['scenarios']['central']['collection_probability']=0;r=simulate(c,R,'central',1,'optimized_network',c['train_seed']);self.assertEqual(r.metrics['collections'],0);self.assertEqual(r.metrics['research_operating_funded'],0)
        c['scenarios']['central']['collection_probability']=1;c['scenarios']['central']['collection_lag']=0;r=simulate(c,R,'central',1,'optimized_beta',c['train_seed']);self.assertEqual(r.ledger[-1]['outstanding_receivables'],0);self.assertGreater(r.metrics['collections'],0)
    def test_only_purchase_updates_belief_and_delay_reduces_demand(self):
        a=Belief(np.ones(9)/9,2,.5);b=Belief(np.ones(9)/9,2,.5);a.update(C,.65,10,3,12);b.update(C,.65,10,3,12);np.testing.assert_array_equal(a.weights,b.weights)
        self.assertTrue(np.all(buyer_probabilities(C,[.65],queue_days=30)<buyer_probabilities(C,[.65])))
        self.assertIn(1.,C['price_fractions']);self.assertGreater(max(C['price_fractions']),1.)
    def test_export_scalars(self):
        self.assertEqual(json.loads(dumps({'guard':np.bool_(True),'amount':np.float64(2.5)})),{'guard':True,'amount':2.5})

if __name__=='__main__':unittest.main()
