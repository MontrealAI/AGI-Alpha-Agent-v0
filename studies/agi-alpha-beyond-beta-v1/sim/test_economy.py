# SPDX-License-Identifier: Apache-2.0
import copy, json, pathlib, unittest
import numpy as np
from economy import load_inputs, cost_table, unit, simulate, initial_primitives, Belief, buyer_probabilities, coverage, Asset, dumps
from graph_admission import make_simulated_record

C,R=load_inputs(pathlib.Path(__file__).with_name('config.json'))

class EconomyTests(unittest.TestCase):
    def test_numpy_event_scalars_are_serialized_without_type_change(self):
        self.assertEqual(json.loads(dumps({'guard':np.bool_(True),'count':np.int64(4),'amount':np.float64(1.5)})),{'guard':True,'count':4,'amount':1.5})
    def test_tariffs_and_complete_activity_counts(self):
        table=cost_table(R)
        self.assertAlmostEqual(sum(table[s['id']]['usd'] for s in R['stages']),263.46)
        for name,campaign in R['investment_campaigns'].items():self.assertAlmostEqual(sum(table[k]['usd']*n for k,n in campaign['counts'].items()),campaign['derived_budget_usd'])
        self.assertEqual(C['operations']['max_corrections'],2)
    def test_discovery_prepays_real_setup_time(self):
        result=simulate(C,R,'central',2,'optimized_no_assets',C['train_seed'])
        self.assertEqual(result.metrics['setup_months'],1)
        self.assertGreater(result.metrics['setup_tokens'],0)
        self.assertAlmostEqual(result.metrics['discovery_cost'],C['discovery_cost'])
    def test_cash_and_resource_conservation(self):
        for policy in ['optimized_no_assets','optimized_optional']:
            r=simulate(C,R,'favorable',2,policy,C['train_seed'])
            for row in r.ledger:
                self.assertGreaterEqual(row['closing_cash'],0)
                self.assertAlmostEqual(row['opening_cash']+row['collections']-row['operating_outflow']-row['investment_outflow']-row['refund_outflow']-row['arrears_outflow'],row['closing_cash'],places=6)
                for suffix in ['tokens','workbench_minutes','container_minutes']:self.assertLessEqual(row['delivery_'+suffix]+row['research_'+suffix],row['capacity_'+suffix]+1e-5)
    def test_future_transfer_draws_do_not_enter_policy(self):
        g=make_simulated_record('R',0,1,18,[0,1,2,3,4],True)
        a=Asset('R',1,True,.95,.7,np.zeros(12,dtype=bool),g)
        first=coverage(C,{'R':a},2)
        a.transfer[:]=True
        self.assertEqual(first,coverage(C,{'R':a},2))
    def test_only_purchase_nonpurchase_updates_belief(self):
        m=C['market'];b1=Belief(np.ones(9)/9,2,.5);b2=Belief(np.ones(9)/9,2,.5)
        b1.update(C,.65,10,3,12);b2.update(C,.65,10,3,12)
        np.testing.assert_array_equal(b1.weights,b2.weights)
        self.assertAlmostEqual(b1.weights.sum(),1)
    def test_no_profitable_asset_value_means_identical_paired_histories(self):
        c=copy.deepcopy(C);c['scenarios']['central']['asset_build_success']=0
        shared=initial_primitives(c,c['scenarios']['central'],c['train_seed'],1)
        a=simulate(c,R,'central',1,'optimized_no_assets',c['train_seed'],shared);b=simulate(c,R,'central',1,'optimized_optional',c['train_seed'],shared)
        self.assertEqual(a.metrics,b.metrics);self.assertEqual(a.ledger,b.ledger)
    def test_false_passes_never_count_as_true_projects(self):
        c=copy.deepcopy(C);sc=c['scenarios']['central'];sc.update(semantic_correctness=0,shared_fault_probability=1,shared_fault_miss=1);c['operations']['postdelivery_discovery']=1;c['fixed_price_ablation']=.2;sc['asset_build_success']=0
        r=simulate(c,R,'central',3,'fixed_optional',c['train_seed'])
        self.assertEqual(r.metrics['true_accepted_projects'],0)
        self.assertGreater(r.metrics['false_passes'],0)
        self.assertGreater(r.metrics['refunds'],0)
    def test_zero_authorization_has_no_collections(self):
        c=copy.deepcopy(C);c['scenarios']['central']['collection_probability']=0
        r=simulate(c,R,'central',1,'optimized_optional',c['train_seed'])
        self.assertEqual(r.metrics['collections'],0)
        self.assertEqual(r.metrics['research_operating_funded'],0)
    def test_same_month_settlement_is_not_lost(self):
        c=copy.deepcopy(C);c['scenarios']['central']['collection_lag']=0
        r=simulate(c,R,'central',1,'optimized_no_assets',c['train_seed'])
        self.assertEqual(r.ledger[-1]['outstanding_receivables'],0)
        self.assertGreater(r.metrics['collections'],0)
    def test_price_grid_has_parity_and_premium(self):
        self.assertIn(1.,C['price_fractions']);self.assertGreater(max(C['price_fractions']),1.)
        p=buyer_probabilities(C,[.2,1.2]);self.assertTrue(np.all(p[:,0]>p[:,1]))
    def test_queue_delay_reduces_purchase_likelihood(self):
        p=buyer_probabilities(C,[.65]);q=buyer_probabilities(C,[.65],queue_days=30)
        self.assertTrue(np.all(q<p))
    def test_no_human_review_hidden_in_activity_register(self):
        self.assertTrue(all(s['provider_human_minutes']==0 for s in R['stages']))
        self.assertEqual(C['operations']['routine_provider_human_minutes'],0)

if __name__=='__main__':unittest.main()
