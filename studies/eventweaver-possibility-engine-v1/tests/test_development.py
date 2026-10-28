import copy
import json
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from eventweaver import compile_spec, run, verilog

P = {'name':'test', 'a':0, 'b':1, 'c':2, 'veto':3, 'l1':1, 'u1':3, 'l2':1, 'u2':2, 'deadline':7}

class DevelopmentTests(unittest.TestCase):
    def test_overlap_and_duplicate_paths(self):
        trace = [1, 3, 2, 6, 4, 0, 0, 0, 0, 0]
        self.assertEqual(run([P], trace), [0,0,0,0,0,0,0,1,1,0])
    def test_endpoint_veto(self):
        for veto_tick in [0, 1, 4, 7]:
            trace = [1,2,4,0,0,0,0,0]
            trace[veto_tick] |= 8
            self.assertEqual(run([P], trace), [0]*8)
    def test_earliest_and_latest_lags(self):
        for b,c in [(1,2),(3,5)]:
            trace = [0]*8
            trace[0],trace[b],trace[c] = 1,2,4
            self.assertEqual(run([P], trace), [0]*7+[1])
        for b,c in [(0,1),(4,5),(1,1),(1,4)]:
            trace = [0]*8
            trace[0] |= 1
            trace[b] |= 2
            trace[c] |= 4
            self.assertEqual(run([P], trace), [0]*8)
    def test_reset_erases_pending(self):
        trace = [1,2,4,{'events':255,'rst':True},0,0,0,0,0,0]
        self.assertEqual(run([P], trace), [0]*10)
        trace = [{'events':255,'rst':True}]+[1,2,4,0,0,0,0,0]
        self.assertEqual(run([P], trace), [0]*8+[1])
    def test_independent_groups(self):
        q = dict(P, name='second', a=4, b=5, c=6, veto=7)
        self.assertEqual(run([P,q], [17,34,68,0,0,0,0,0]), [0]*7+[3])
        self.assertEqual(run([P,q], [17,34,68,8,0,0,0,0]), [0]*7+[2])
    def test_reject_invalid(self):
        bad = [[], [P]*2, [dict(P,a=True)], [dict(P,u1=0)], [dict(P,deadline=21)], [dict(P,deadline=4)], [dict(P,veto=2)], [dict(P,a=-1)], [dict(P,c=8)], [dict(P,l2=0)], [dict(P,extra=1)], [dict(P,name='')], {'channels':9,'patterns':[P]}]
        for spec in bad:
            with self.subTest(spec=spec), self.assertRaises(ValueError):
                compile_spec(spec)
        for trace in [[256],[-1],[True],[{'events':1,'rst':1}]]:
            with self.subTest(trace=trace), self.assertRaises(ValueError):
                run([P], trace)
    def test_hardware_shape(self):
        ir = compile_spec([P])
        self.assertEqual(len(ir['states']), 15)
        self.assertIn('module eventweaver', verilog([P]))

if __name__ == '__main__':
    unittest.main()
