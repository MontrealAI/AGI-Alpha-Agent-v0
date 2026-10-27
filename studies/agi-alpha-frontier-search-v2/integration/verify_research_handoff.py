"""Verify preserved negative research evidence; does not execute a new physics experiment."""
import argparse,json,math
from pathlib import Path
p=argparse.ArgumentParser()
p.add_argument('--stage',choices=['known-result','next-gate'],required=True)
a=p.parse_args();r=Path(__file__).resolve().parent
if a.stage=='known-result':
 d=json.loads((r/'rejected_quantum_record.json').read_text());q=d['executed_local_result_from_independent_confirmation']
 assert d['new_discovery'] is False and d['qualified_venture'] is False
 assert q['channels']==4 and q['kraus_tuples']==256
 assert math.isclose(q['herald_probability'],7/16,abs_tol=1e-12)
 assert math.isclose(q['conditional_fidelity_formula'],5/7,abs_tol=1e-12)
 assert math.isclose(q['choi_partial_transpose_min'],-1/14,abs_tol=1e-12)
 print(json.dumps({'stage':a.stage,'status':'known-result-preserved','new_discovery':False,'scope':'Verification of archived independent result, not a new physics run'}))
else:
 d=json.loads((r/'next_experiment_gate.json').read_text())
 unmet=[x['id'] for x in d['required_conditions'] if not x['met']]
 assert unmet and d['execution_authority'] is False
 assert d['disposition']=='research-proposal-not-ready'
 print(json.dumps({'stage':a.stage,'status':'blocked-pending-distinct-construction','unmet_conditions':unmet,'execution_authority':False}))
