import copy, json, math, unittest
from checker import check,inspect

BASE={'n':2,'edges':[[0,1,1.0]],'ground':[1.0,1.0],'rhs':[1.0,0.0]}
X=[2/3,1/3]

class EdgeBalanceChecks(unittest.TestCase):
 def test_hand_solution(self):
  r=check(BASE,X);self.assertTrue(r['valid']);self.assertLess(r['max_abs_residual'],1e-15)
 def test_bad_finite_solution(self):self.assertFalse(check(BASE,[.6,.4])['valid'])
 def test_energy_alone_not_sufficient(self):
  r=check(BASE,[0,0]);self.assertEqual(r['energy_error'],0);self.assertFalse(r['valid']);self.assertEqual(r['relative_residual'],1)
 def test_zero_rhs(self):
  t=copy.deepcopy(BASE);t['rhs']=[0,0];self.assertTrue(check(t,[0,0])['valid']);self.assertFalse(check(t,[1,1])['valid'])
 def test_duplicate_edges_add(self):
  t=copy.deepcopy(BASE);t['edges']=[[0,1,.4],[0,1,.6]];self.assertTrue(check(t,X)['valid'])
 def test_permuted_edge(self):
  t=copy.deepcopy(BASE);t['edges']=[[1,0,1.0]];self.assertTrue(check(t,X)['valid'])
 def test_isolated_grounded_nodes(self):
  t={'n':3,'edges':[],'ground':[.1,.2,.5],'rhs':[.1,-.4,1]};self.assertTrue(check(t,[1,-2,2])['valid'])
 def test_positive_update_handcase(self):
  t=copy.deepcopy(BASE);t['edges'].append([0,1,1.0]);self.assertTrue(check(t,[.6,.4])['valid']);self.assertFalse(check(t,X)['valid'])
 def test_ground_scope(self):
  for g in [0,-1,.099999,float('nan'),float('inf'),True,'1']:
   t=copy.deepcopy(BASE);t['ground'][0]=g;self.assertEqual(check(t,X)['reason'],'GROUND_SCOPE')
 def test_conductance_scope(self):
  for w in [0,-1,float('nan'),float('inf'),False,'1']:
   t=copy.deepcopy(BASE);t['edges'][0][2]=w;self.assertEqual(check(t,X)['reason'],'CONDUCTANCE_SCOPE')
 def test_solution_shape(self):
  for x in [None,[],[1],(1,2),'x',{},[1,2,3]]:self.assertEqual(check(BASE,x)['reason'],'SOLUTION_SHAPE')
 def test_solution_nonfinite(self):
  for v in [float('nan'),float('inf'),True,None,'1']:
   self.assertEqual(check(BASE,[v,0])['reason'],'SOLUTION_NONFINITE')
 def test_rhs_nonfinite(self):
  for v in [float('nan'),float('inf'),True,None,'1']:
   t=copy.deepcopy(BASE);t['rhs'][0]=v;self.assertEqual(check(t,X)['reason'],'RHS_NONFINITE')
 def test_invalid_endpoints(self):
  for uv in [[0,0],[-1,1],[0,2],[False,1],[.0,1]]:
   t=copy.deepcopy(BASE);t['edges']=[[uv[0],uv[1],1]];self.assertEqual(check(t,X)['reason'],'EDGE_ENDPOINT_SCOPE')
 def test_bad_n(self):
  for n in [0,-1,True,2.0,65537,None]:
   t=copy.deepcopy(BASE);t['n']=n;self.assertEqual(check(t,X)['reason'],'NODE_COUNT_SCOPE')
 def test_field_shapes(self):
  for field,reason in [('ground','GROUND_SHAPE'),('rhs','RHS_SHAPE'),('edges','EDGE_LIST_SCOPE')]:
   t=copy.deepcopy(BASE);t[field]=None;self.assertEqual(check(t,X)['reason'],reason)
  t=copy.deepcopy(BASE);t['edges']=[[0,1]];self.assertEqual(check(t,X)['reason'],'EDGE_SHAPE')
 def test_near_tolerance(self):
  self.assertTrue(check(BASE,[X[0]+1e-11,X[1]])['valid']);self.assertFalse(check(BASE,[X[0]+1e-7,X[1]])['valid'])
 def test_overflow_refused(self):
  t=copy.deepcopy(BASE);t['ground']=[1e308,1e308];self.assertEqual(check(t,[1e308,1e308])['reason'],'ARITHMETIC_NONFINITE')
 def test_scale_rhs(self):
  t=copy.deepcopy(BASE);t['rhs']=[1e6,0];self.assertTrue(check(t,[1e6*v for v in X])['valid'])
 def test_ground_shift_invalidates(self):
  t=copy.deepcopy(BASE);t['ground'][0]=2.;self.assertFalse(check(t,X)['valid'])

if __name__=='__main__':unittest.main(verbosity=2)
