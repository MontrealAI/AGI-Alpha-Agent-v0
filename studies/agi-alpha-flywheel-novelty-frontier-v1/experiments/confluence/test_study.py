import hashlib,itertools,json,unittest
import study

class AcceptanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.cfg=json.loads((study.ROOT/'config.json').read_text())
    def test_frozen_config(self):
        freeze=json.loads((study.ROOT/'freeze.json').read_text())
        self.assertEqual(hashlib.sha256((study.ROOT/'config.json').read_bytes()).hexdigest(),freeze['config_sha256'])
    def test_order_survives_reset_to_reference(self):
        model=study.make_model(4,self.cfg); tab=study.table(model)
        self.assertEqual(study.run_word(tab,4,'AB'),(((1,1,1,0),),False))
        self.assertEqual(study.run_word(tab,4,'BA'),(((1,1,0,1),),False))
        self.assertEqual(study.run_word(tab,4,'ABR'),(((0,0,0,0),),False))
    def test_actual_internal_race_converges(self):
        model=study.make_model(3,self.cfg)
        r=study.all_orders(model,(1,0,0),model['fields']['B'])
        self.assertEqual(r['terminals'],((1,1,1),)); self.assertEqual(r['paths'],2)
        self.assertGreater(r['race_states'],0); self.assertFalse(r['cycle'])
    def test_recurrence_and_coincidence_cannot_be_claimed_distinguishable(self):
        tab=study.table(study.make_model(4,self.cfg))
        self.assertEqual(study.run_word(tab,4,'C'),study.run_word(tab,4,'ABA'))
        self.assertEqual(study.run_word(tab,4,'C'),study.run_word(tab,4,'BAB'))
    def test_complete_nominal_state_space_matches_independent_semantics(self):
        for n in self.cfg['dimensions']:
            model=study.make_model(n,self.cfg)
            for s in study.bits(n):
                for event in self.cfg['full_word_alphabet']:
                    end,cycle=study.pulse(model,s,event)
                    self.assertFalse(cycle); self.assertEqual(end,(study.oracle(s,event),))
                    self.assertEqual(end,(study.monotone_control(model,s,event),))
    def test_checker_does_not_hide_multiple_terminal_states(self):
        model={'n':2,'C':[[0,-120],[-120,0]],'up':[100,100],'down':[-80,-80]}
        r=study.all_orders(model,(0,0),(110,110))
        self.assertEqual(set(r['terminals']),{(1,0),(0,1)}); self.assertFalse(r['cycle'])
    def test_checker_does_not_hide_nontermination(self):
        model={'n':2,'C':[[0,-200],[200,0]],'up':[100,100],'down':[0,0]}
        r=study.all_orders(model,(0,0),(110,-10))
        self.assertTrue(r['cycle']); self.assertEqual(r['terminals'],())
    def test_coupling_is_necessary_and_mutation_fails(self):
        for c in [0,35]:
            tab=study.table(study.make_model(4,self.cfg,coupling=c))
            self.assertEqual(study.run_word(tab,4,'AB'),study.run_word(tab,4,'BA'))

if __name__=='__main__': unittest.main()
