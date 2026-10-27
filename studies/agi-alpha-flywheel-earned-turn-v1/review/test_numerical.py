import copy, hashlib, json, sys, tempfile, unittest
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'companion'))
from numerical import Factor,Update,make_task,with_load,operator_id,matrix,direct,choose_changes,change_task,digest
from checker import check

class NumericalScopeChecks(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(prefix='earned-numeric-review-');self.p=Path(self.tmp.name);self.task=make_task(27101,4);self.x,self.factor=direct(self.task);self.receipt=digest({'accepted-development-B':True})
 def tearDown(self):self.tmp.cleanup()
 def factor_file(self):
  p=self.p/'factor.npz';return p,self.factor.save(p)
 def child(self):return Update(self.factor,self.task,choose_changes(self.task,self.x,2),self.receipt)
 def update_file(self):
  c=self.child();p=self.p/'update.npz';return c,p,c.save(p)
 def mutated(self,path,fn):
  with np.load(path,allow_pickle=False) as z:data={k:z[k].copy() for k in z.files}
  fn(data);new=self.p/'mutated.npz';np.savez(new,**data);return new,{'sha256':hashlib.sha256(new.read_bytes()).hexdigest()}
 def meta_mutated(self,path,fn):
  def apply(data):
   m=json.loads(str(data['meta']));fn(m);data['meta']=np.array(json.dumps(m))
  return self.mutated(path,apply)
 def test_integer_ground_float_edges(self):
  t={'n':2,'edges':[[0,1,1.5]],'ground':[1,1],'rhs':[1,0]};x,f=direct(t);self.assertTrue(check(t,x.tolist())['valid']);np.testing.assert_allclose(x,[.625,.375],atol=1e-14)
 def test_invalid_changes_never_call_parent(self):
  invalid=[[],[[True,1]],[[0,0]],[[0,-.1]],[[1000,.1]],[[0,float('nan')]],[[0,float('inf')]],[[0,.2],[0,.3]],[[0,True]],[[0,'1']],[[0.0,1]],None]
  for changes in invalid:
   calls=self.factor.calls
   with self.assertRaisesRegex(ValueError,'UPDATE_SCOPE'):Update(self.factor,self.task,changes,self.receipt)
   self.assertEqual(self.factor.calls,calls)
 def test_invalid_receipt_before_parent(self):
  calls=self.factor.calls
  with self.assertRaisesRegex(ValueError,'PRECEDING_RECEIPT_SCOPE'):Update(self.factor,self.task,[[0,1]],'B')
  self.assertEqual(self.factor.calls,calls)
 def test_change_copy_and_identity(self):
  changes=[[0,.5]];c=Update(self.factor,self.task,changes,self.receipt);changes[0][1]=9.;self.assertEqual(c.changes,[[0,.5]]);self.assertEqual(c.oid,operator_id(change_task(self.task,[[0,.5]])))
 def test_trusted_ids_same_math_and_identity(self):
  changes=[[0,.5]];new=change_task(self.task,changes);normal=Update(self.factor,self.task,changes,self.receipt);trusted=Update(self.factor,self.task,changes,self.receipt,validated_ids=(operator_id(self.task),operator_id(new)))
  self.assertEqual(normal.identity,trusted.identity);self.assertTrue(check(new,trusted.solve(new['rhs']).tolist())['valid']);np.testing.assert_allclose(normal.W,trusted.W,atol=1e-14)
 def test_trusted_ids_structural_and_parent_binding(self):
  for ids in [(operator_id(self.task),operator_id(self.task)),('0'*64,'1'*64),('bad','bad'),['0'*64,'1'*64]]:
   calls=self.factor.calls
   with self.assertRaises(ValueError):Update(self.factor,self.task,[[0,.5]],self.receipt,validated_ids=ids)
   self.assertEqual(self.factor.calls,calls)
 def test_factor_roundtrip(self):
  p,r=self.factor_file();f=Factor.load(p,r,operator_id(self.task));self.assertTrue(check(self.task,f.solve(self.task['rhs']).tolist())['valid'])
 def test_factor_byte_tamper(self):
  p,r=self.factor_file();p.write_bytes(p.read_bytes()+b'x')
  with self.assertRaisesRegex(ValueError,'FACTOR_BYTES_CHANGED'):Factor.load(p,r,operator_id(self.task))
 def test_factor_bad_recipe_with_new_checksum(self):
  p,r=self.factor_file();p,r=self.meta_mutated(p,lambda m:m.update(identity='forged-not-recomputed'))
  with self.assertRaisesRegex(ValueError,'FACTOR_IDENTITY_MISMATCH'):Factor.load(p,r,operator_id(self.task))
 def test_factor_dependency_change(self):
  p,r=self.factor_file();p,r=self.meta_mutated(p,lambda m:m.update(dependencies={'numpy':'changed','scipy':'changed'}))
  with self.assertRaisesRegex(ValueError,'DEPENDENCY_CHANGED'):Factor.load(p,r,operator_id(self.task))
 def test_factor_schema_change(self):
  p,r=self.factor_file();p,r=self.meta_mutated(p,lambda m:m.update(schema='unknown'))
  with self.assertRaisesRegex(ValueError,'FACTOR_METADATA_SCHEMA'):Factor.load(p,r,operator_id(self.task))
 def test_factor_permutation_corruption(self):
  p,r=self.factor_file();p,r=self.mutated(p,lambda d:d['pr'].__setitem__(0,d['pr'][1]))
  with self.assertRaisesRegex(ValueError,'FACTOR_PERMUTATION'):Factor.load(p,r,operator_id(self.task))
 def test_factor_nonfinite(self):
  p,r=self.factor_file();p,r=self.mutated(p,lambda d:d['Udata'].__setitem__(0,np.nan))
  with self.assertRaisesRegex(ValueError,'FACTOR_ARRAY_SCHEMA'):Factor.load(p,r,operator_id(self.task))
 def test_factor_bad_indices(self):
  p,r=self.factor_file();p,r=self.mutated(p,lambda d:d['Lindices'].__setitem__(0,self.task['n']))
  with self.assertRaisesRegex(ValueError,'FACTOR_ARRAY_SCHEMA'):Factor.load(p,r,operator_id(self.task))
 def test_factor_stale_operator(self):
  p,r=self.factor_file()
  with self.assertRaisesRegex(ValueError,'STALE_OPERATOR'):Factor.load(p,r,'0'*64)
 def test_update_roundtrip(self):
  c,p,r=self.update_file();u=Update.load(p,r,self.factor,expected_oid=c.oid);t=change_task(self.task,c.changes);self.assertTrue(check(t,u.solve(t['rhs']).tolist())['valid'])
 def test_update_base_binding(self):
  c,p,r=self.update_file();p,r=self.meta_mutated(p,lambda m:m.update(base_operator='0'*64))
  with self.assertRaisesRegex(ValueError,'STALE_UPDATE_OPERATOR'):Update.load(p,r,self.factor)
 def test_update_current_world_binding(self):
  c,p,r=self.update_file()
  with self.assertRaisesRegex(ValueError,'STALE_UPDATE_OPERATOR'):Update.load(p,r,self.factor,expected_oid='0'*64)
 def test_update_recipe_corruption(self):
  c,p,r=self.update_file();p,r=self.meta_mutated(p,lambda m:m.update(identity='0'*64))
  with self.assertRaisesRegex(ValueError,'UPDATE_IDENTITY_MISMATCH'):Update.load(p,r,self.factor)
 def test_update_array_shape(self):
  c,p,r=self.update_file();p,r=self.mutated(p,lambda d:d.update(W=d['W'][:-1]))
  with self.assertRaisesRegex(ValueError,'UPDATE_ARRAY_SCHEMA'):Update.load(p,r,self.factor)
 def test_update_direction_corruption(self):
  c,p,r=self.update_file();p,r=self.mutated(p,lambda d:d['U'].__setitem__((0,0),123.))
  with self.assertRaisesRegex(ValueError,'UPDATE_DIRECTION_SCHEMA'):Update.load(p,r,self.factor)
 def test_update_schur_corruption(self):
  c,p,r=self.update_file();p,r=self.mutated(p,lambda d:d['S'].__setitem__((0,0),-1.))
  with self.assertRaisesRegex(ValueError,'UPDATE_SCHUR_SCHEMA'):Update.load(p,r,self.factor)
 def test_update_nonfinite(self):
  c,p,r=self.update_file();p,r=self.mutated(p,lambda d:d['W'].__setitem__((0,0),np.inf))
  with self.assertRaisesRegex(ValueError,'UPDATE_ARRAY_SCHEMA'):Update.load(p,r,self.factor)

def math_review():
 rows=[]
 for seed in [27101,27102,27103,27104]:
  for side in [4,24,40]:
   t=make_task(seed,side);b=with_load(t,seed+100);A=matrix(t)
   for ordering in ['MMD_AT_PLUS_A','COLAMD','NATURAL']:
    with tempfile.TemporaryDirectory(prefix='earned-roundtrip-review-') as directory:
     p=Path(directory);f=Factor(A,operator_id(t),ordering);x=f.solve(t['rhs']);rec=f.save(p/'factor.npz');loaded=Factor.load(p/'factor.npz',rec,operator_id(t));x2=loaded.solve(t['rhs']);rb=loaded.solve(b['rhs']);changes=choose_changes(b,rb,4);receipt=digest({'task':b,'solution':rb.tolist(),'accepted':True});child=Update(loaded,b,changes,receipt);changed=change_task(b,changes);y=child.solve(changed['rhs']);ur=child.save(p/'update.npz');child2=Update.load(p/'update.npz',ur,loaded,expected_oid=operator_id(changed));y2=child2.solve(changed['rhs']);nativechild=Update(f,b,changes,receipt);yn=nativechild.solve(changed['rhs']);strong,_=direct(changed)
     rows.append({'seed':seed,'side':side,'ordering':ordering,'factor_native':check(t,x.tolist()),'factor_portable':check(t,x2.tolist()),'B_portable':check(b,rb.tolist()),'child_portable':check(changed,y.tolist()),'child_restored':check(changed,y2.tolist()),'child_native':check(changed,yn.tolist()),'max_native_portable_difference':float(np.max(np.abs(x-x2))),'max_child_vs_direct_difference':float(np.max(np.abs(y-strong))),'construction_parent_block_calls':child.construction_parent_calls,'rhs_columns_in_block':4,'factor_file_sha256':rec['sha256'],'update_file_sha256':ur['sha256']})
 assert len(rows)==36 and all(all(r[k]['valid'] for k in ['factor_native','factor_portable','B_portable','child_portable','child_restored','child_native']) for r in rows)
 report={'status':'PASS_DEVELOPMENT_ONLY','not_candidate_selection':True,'scope':'Four declared development seeds, three standard ordering variants, plus small analytic-size smoke cases; no confirmation input generated.','source_sha256':hashlib.sha256((ROOT/'companion/numerical.py').read_bytes()).hexdigest(),'checker_sha256':hashlib.sha256((ROOT/'review/checker.py').read_bytes()).hexdigest(),'rows':rows}
 (ROOT/'review'/'NUMERICAL_MATH_REVIEW_FIXED.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps({'cases':len(rows),'checked_outputs':len(rows)*6,'all_valid':True,'max_relative_residual':max(r[k]['relative_residual'] for r in rows for k in ['factor_native','factor_portable','B_portable','child_portable','child_restored','child_native']),'max_child_vs_direct_difference':max(r['max_child_vs_direct_difference'] for r in rows)}))

if __name__=='__main__':
 if '--math-review' in sys.argv:math_review()
 else:unittest.main(verbosity=2)
