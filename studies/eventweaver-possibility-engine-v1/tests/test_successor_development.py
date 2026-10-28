import copy
import json
import pathlib
import sys
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
import eventweaver
import successor

SPEC=json.loads((ROOT/'protocol/successor_v1.json').read_text())['development_demo']

def trace():
    result=[{'events':0,'rst':False} for _ in range(17)]
    result[0]['rst']=True
    for tick,channel in [(1,0),(2,1),(3,2),(10,4),(11,5)]:result[tick]['events']|=1<<channel
    return result

class SuccessorDevelopmentTests(unittest.TestCase):
    def test_new_mission(self):
        expected=[0]*17
        expected[8]=1
        expected[14]=2
        self.assertEqual(successor.run(SPEC,trace()),expected)
    def test_mandatory_interface_tick(self):
        rows=trace()
        rows[10]['events']=1<<5
        rows[11]['events']=0
        rows[9]['events']=1<<4
        expected=[0]*17
        expected[8]=1
        self.assertEqual(successor.run(SPEC,rows),expected)
    def test_endpoint_veto(self):
        rows=trace()
        rows[14]['events']=1<<6
        expected=[0]*17
        expected[8]=1
        self.assertEqual(successor.run(SPEC,rows),expected)
    def test_reset_erases_virtual(self):
        rows=trace()
        rows[9]['rst']=True
        expected=[0]*17
        expected[8]=1
        self.assertEqual(successor.run(SPEC,rows),expected)
    def test_unordered_stage_list(self):
        spec=copy.deepcopy(SPEC)
        spec['stages'].reverse()
        expected=[0]*17
        expected[8]=2
        expected[14]=1
        self.assertEqual(successor.run(spec,trace()),expected)
    def test_reject_invalid_graph(self):
        cases=[]
        bad=copy.deepcopy(SPEC);bad['stages'][1]['a']='stage:missing';cases.append(bad)
        bad=copy.deepcopy(SPEC);bad['stages'][0]['a']='stage:conditioned_calibration';cases.append(bad)
        bad=copy.deepcopy(SPEC);bad['stages'][1]['a']='stage:conditioned_calibration';cases.append(bad)
        bad=copy.deepcopy(SPEC);bad['stages'][1]['b']='raw:8';cases.append(bad)
        bad=copy.deepcopy(SPEC);bad['stages'][1]['b']='raw:04';cases.append(bad)
        bad=copy.deepcopy(SPEC);bad['stages'][1]['b']=4;cases.append(bad)
        bad=copy.deepcopy(SPEC);bad['stages'][1]['b']=bad['stages'][1]['c'];cases.append(bad)
        for bad in cases:
            with self.subTest(spec=bad),self.assertRaises(ValueError):successor.validate(bad)
    def test_parent_rejects_new_grammar(self):
        with self.assertRaises(ValueError):eventweaver.compile_spec(SPEC['stages'])
        self.assertEqual(successor.verify_parent(),successor.PARENT_SHA256)

if __name__=='__main__':unittest.main()
