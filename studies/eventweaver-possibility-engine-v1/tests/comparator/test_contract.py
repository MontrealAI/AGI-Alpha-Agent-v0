import json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
import conventional,reference_oracle,eventweaver

class ContractTests(unittest.TestCase):
    def setUp(self):self.spec=json.loads((ROOT/'protocol/technical_v1.json').read_text())['first_demo']
    def check(self,events,expected,resets=(0,),spec=None):
        rows=[{'events':events.get(t,0),'rst':t in resets} for t in range(30)]
        want=[expected.get(t,0) for t in range(30)]
        for method in [reference_oracle.run,conventional.run,eventweaver.run]:self.assertEqual(method(spec or self.spec,rows),want,method.__module__)
    def test_deadline_is_inclusive(self):self.check({2:1,3:2,4:4},{9:1})
    def test_upper_lag_bounds_inclusive(self):self.check({2:1,5:2,7:4},{9:1})
    def test_same_tick_is_not_positive_lag(self):self.check({2:7},{})
    def test_deadline_veto_cancels(self):self.check({2:1,3:2,4:4,9:8},{})
    def test_anchor_veto_cancels(self):self.check({2:9,3:2,4:4},{})
    def test_postdeadline_veto_does_not_change_past(self):self.check({2:1,3:2,4:4,10:8},{9:1})
    def test_reset_cancels_old_anchor(self):self.check({2:1,3:2,4:4},{},resets=(0,5))
    def test_reset_dominates_events(self):self.check({2:1,3:2,4:4},{},resets=(0,2))
    def test_postreset_new_anchor(self):self.check({2:1,3:2,4:4,8:1,9:2,10:4},{15:1},resets=(0,5))
    def test_group_isolation(self):self.check({2:1,3:32,4:4},{})
    def test_second_group(self):self.check({2:16,3:32,5:64},{10:2})
    def test_multiple_paths_one_output(self):self.check({2:1,3:2,4:6,5:6,6:4},{9:1})
    def test_overlapping_anchor_outputs(self):self.check({2:1,3:3,4:6,5:4},{9:1,10:1})
    def test_irrelevant_channel_does_not_block_first_group(self):self.check({2:129,3:130,4:132},{9:1})

if __name__=='__main__':unittest.main()
