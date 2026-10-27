# SPDX-License-Identifier: Apache-2.0
import copy
import unittest
from economy_v3 import HERE, load_inputs
from economy_v3_posterior import recipient_component_estimate

class RecipientPriorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.c,_=load_inputs(HERE/'config_v3.json');cls.sc=cls.c['scenarios']['favorable']
    def test_paid_source_declared_prior(self):
        pi=.97*.85;q0=pi*.995+(1-pi)*.65
        self.assertAlmostEqual(recipient_component_estimate(self.c,self.sc,24,24,{'kind':'paid_job'}),(4*q0+24)/28)
    def test_dedicated_research_prior(self):
        q0=.9*.995+.1*.65
        self.assertAlmostEqual(recipient_component_estimate(self.c,self.sc,12,24,{'kind':'separate_research'}),(4*q0+12)/28)
    def test_origin_latent_fields_do_not_change_prior(self):
        a=recipient_component_estimate(self.c,self.sc,23,24,{'kind':'paid_job','latent_correctness':False,'future_paid':False})
        b=recipient_component_estimate(self.c,self.sc,23,24,{'kind':'paid_job','latent_correctness':True,'future_paid':True})
        self.assertEqual(a,b)
    def test_evidence_can_support_or_reject_candidate(self):
        self.assertGreater(recipient_component_estimate(self.c,self.sc,24,24,{'kind':'paid_job'}),.97)
        self.assertLess(recipient_component_estimate(self.c,self.sc,23,24,{'kind':'paid_job'}),.97)
        self.assertGreaterEqual(recipient_component_estimate(self.c,self.sc,0,24,{'kind':'paid_job'}),0)

if __name__=='__main__':unittest.main()
