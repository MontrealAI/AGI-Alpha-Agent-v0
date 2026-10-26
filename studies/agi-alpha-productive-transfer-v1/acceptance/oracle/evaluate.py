from pathlib import Path
import argparse,hashlib,json
ROOT=Path(__file__).resolve().parents[1]
def canonical(x): return json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()
def key(r): return r.get('line'),r.get('column'),r.get('callee')
def evaluate(task,oracle,response):
 expected={key(r):r for r in oracle['calls']};seen={};errors=[];conservative=[];target_rows=[]
 if response.get('schema')!='alpha-transfer-extraction/v1':errors.append({'kind':'SCHEMA'})
 if response.get('inputSha256')!=hashlib.sha256(canonical(task)).hexdigest():errors.append({'kind':'INPUT_IDENTITY'})
 for category in ['claims','unresolved']:
  rows=response.get(category)
  if not isinstance(rows,list):errors.append({'kind':'INVALID_LIST','category':category});continue
  for row in rows:
   if not isinstance(row,dict):errors.append({'kind':'INVALID_ROW','category':category});continue
   k=key(row)
   if k in seen:errors.append({'kind':'DUPLICATE_CALL','call':list(k)});continue
   seen[k]=category
   if k not in expected:errors.append({'kind':'EXTRANEOUS_CALL','call':list(k)});continue
   truth=expected[k]
   if category=='claims':
    for side in ['before','after']:
     target=row.get(side,{})
     if not isinstance(target,dict) or {k:target.get(k) for k in ['source','symbol']}!={k:truth['targets'][side][k] for k in ['source','symbol']}:
      errors.append({'kind':'WRONG_TARGET','call':list(k),'side':side})
    if not isinstance(row.get('explanation'),str) or len(row['explanation'].strip())<12:errors.append({'kind':'MISSING_MAPPING_RATIONALE','call':list(k)})
    target_rows.append({'call':list(k),'expected_core_scope_outcome':truth['expected_core_scope_outcome']})
   else:
    reason=row.get('reason')
    if not isinstance(reason,str) or len(reason.strip())<12:errors.append({'kind':'UNJUSTIFIED_REFUSAL','call':list(k)})
    if truth['expected_core_scope_outcome']!='UNRESOLVED':conservative.append(list(k))
 for k in expected.keys()-seen.keys():errors.append({'kind':'OMITTED_DEPENDENCY_CALL','call':list(k)})
 return {'schema':'alpha-transfer-independent-extraction-review/v1','task':task['id'],'inputSha256':hashlib.sha256(canonical(task)).hexdigest(),'responseSha256':hashlib.sha256(canonical(response)).hexdigest(),'complete_truthful_inventory':not errors,'required_calls':len(expected),'submitted_claims':sum(v=='claims' for v in seen.values()),'submitted_unresolved':sum(v=='unresolved' for v in seen.values()),'material_errors':errors,'conservative_unresolved_on_bindable_source':conservative,'claim_oracle_expectations':target_rows,'limits':['Long refusal text alone does not substantiate its semantics. Same-session reviewer must inspect unresolved reasons and any stronger downstream prose claim.','Complete truthful scope includes explicit unresolved work, not compatibility acceptance.','Counts are calls within a job, not independent maintenance jobs or customers.']}
def main():
 p=argparse.ArgumentParser();p.add_argument('--task',required=True);p.add_argument('--response',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 if a.out.exists():raise ValueError('output exists')
 task=json.loads((ROOT/'tasks'/f'{a.task}.json').read_text());oracle=json.loads((ROOT/'oracle'/f'{a.task}.json').read_text());response=json.loads(a.response.read_text());result=evaluate(task,oracle,response)
 a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'task':a.task,'accepted':result['complete_truthful_inventory'],'errors':len(result['material_errors'])}))
if __name__=='__main__':main()
