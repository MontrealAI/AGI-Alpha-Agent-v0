"""Fresh refusal and recomputation audit of the corrected final interface."""
from fractions import Fraction as Q
from pathlib import Path
import copy
import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import time

ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT/'confirmation/final_independent'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def run():
    assert not DEST.exists(), 'Preserve previous audit evidence'
    DEST.mkdir(parents=True)
    freeze=json.loads((ROOT/'study/final_confirmation_protocol.json').read_text())
    assert freeze['version']==2
    expected='a326acba5f745b3410e58b6a2ab59b446e563bad0bd4236106e3f4f0852bfb48'
    assert sha(ROOT/'final_certificate.py')==expected==freeze['source_hashes']['final_certificate.py']
    files=list(freeze['source_hashes'])+['study/final_confirmation_protocol.json']
    before={p:sha(ROOT/p) for p in files}
    sys.path.insert(0,str(ROOT))
    spec=importlib.util.spec_from_file_location('audited_final_certificate',ROOT/'final_certificate.py')
    service=importlib.util.module_from_spec(spec);spec.loader.exec_module(service)
    request={'dimension':1,'coverage':'exactly_once','class_type':'full_residue',
             'minimum_hits':2,'interval_length':'all','interval_start':-1207,
             'distinct_moduli':False,'lower_bound':str(service.BOUND),'bound_relation':'>='}
    plan={'kind':'Prospective corrected-interface audit before execution','final_wrapper_sha256':expected,
          'protocol_sha256':sha(ROOT/'study/final_confirmation_protocol.json'),
          'valid_request':request,'scope_cases':'Threshold, strictness, translation and original assumptions',
          'invalid_cli_inputs':['null','list','scalar','string','boolean','malformed JSON','missing fields',
           'strictness at final constant','above-bound claim','altered/missing witness or checker',
           'missing protocol','optimized Python','existing output'],
          'budget_seconds':120,'source_mutations':'Disposable copies only; original hashes must remain identical'}
    (DEST/'PROSPECTIVE_PLAN.json').write_text(json.dumps(plan,indent=2)+'\n')
    started=time.monotonic()
    req=DEST/'valid_request.json';req.write_text(json.dumps(request,indent=2)+'\n')
    result=subprocess.run([sys.executable,'final_certificate.py','--request',str(req),
                           '--output',str(DEST/'full_recomputation')],cwd=ROOT,
                          capture_output=True,text=True,timeout=60)
    (DEST/'full_cli_stdout.json').write_text(result.stdout)
    (DEST/'full_cli_stderr.txt').write_text(result.stderr)
    assert result.returncode==0,result.stderr
    receipt=json.loads(result.stdout)
    assert receipt['bound']==str(service.BOUND) and receipt['relation']=='>='
    assert receipt['request_decision']['status']=='ACCEPTED_WITHIN_STATED_ASSUMPTIONS'
    cases=[]
    definitions=[
      ('original threshold strict',{'lower_bound':'49/50','bound_relation':'>'},True),
      ('exact final constant non-strict',{},True),
      ('translated finite interval',{'interval_length':509,'interval_start':-4000},True),
      ('positive translated interval',{'interval_length':251,'interval_start':10**9},True),
      ('at least three hits subset',{'minimum_hits':3,'distinct_moduli':True},True),
      ('old polynomial bound strict',{'lower_bound':'1891871140656049/1929687500000000','bound_relation':'>'},True),
      ('uncertified strictness at final constant',{'bound_relation':'>'},False),
      ('above final constant',{'lower_bound':str(service.BOUND+Q(1,10**12))},False),
      ('singletons',{'minimum_hits':1},False),
      ('two dimensions',{'dimension':2},False),
      ('arbitrary arithmetic progressions',{'class_type':'arbitrary_ap'},False),
      ('overlapping covering',{'coverage':'at_least_once'},False),
      ('incomplete packing',{'coverage':'at_most_once'},False),
      ('float threshold',{'lower_bound':0.98},False),
      ('zero-denominator rational',{'lower_bound':'1/0'},False),
      ('nonnumeric rational',{'lower_bound':'NaN'},False),
      ('invalid relation',{'bound_relation':'='},False),
      ('boolean dimension',{'dimension':True},False),
      ('boolean hits',{'minimum_hits':True},False),
      ('fractional translation',{'interval_start':'1/2'},False),
      ('length one',{'interval_length':1},False),
      ('unknown schema field',{'special_approval':True},False),
    ]
    for name,changes,wanted in definitions:
        q=copy.deepcopy(request);q.update(changes)
        try:
            answer=service.assess_scope(q);allowed=True
            assert answer['status']=='SCOPE_ADMISSIBLE; proof recomputation still required'
        except service.Refusal as exc:
            answer={'reason':str(exc)};allowed=False
        assert allowed==wanted,(name,answer)
        cases.append({'case':name,'request':q,'expected_scope_admissible':wanted,
                      'actual_scope_admissible':allowed,'answer':answer})
    mutations=[]
    labels=['null_request','list_request','scalar_request','string_request','boolean_request',
            'malformed_json_request','missing_fields','strict_at_bound','above_bound',
            'forged_witness','missing_witness','changed_middle_height','changed_normalizer',
            'malformed_rational_witness','changed_checker','missing_checker','changed_common_helper',
            'missing_common_helper','missing_protocol','optimized_python','existing_output']
    for label in labels:
        with tempfile.TemporaryDirectory(prefix='final_adverse_',dir=DEST) as directory:
            work=Path(directory)
            for p in files:
                target=work/p;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/p,target)
            req=work/'request.json';req.write_text(json.dumps(request));output=work/'out'
            witness=work/'certificate/weight.json'
            if label=='null_request':req.write_text('null')
            elif label=='list_request':req.write_text('[]')
            elif label=='scalar_request':req.write_text('7')
            elif label=='string_request':req.write_text('"all"')
            elif label=='boolean_request':req.write_text('true')
            elif label=='malformed_json_request':req.write_text('{')
            elif label=='missing_fields':req.write_text('{}')
            elif label in ['strict_at_bound','above_bound']:
                q=copy.deepcopy(request)
                if label=='strict_at_bound':q['bound_relation']='>'
                else:q['lower_bound']=str(service.BOUND+Q(1,10**12))
                req.write_text(json.dumps(q))
            elif label=='forged_witness':witness.write_bytes(witness.read_bytes()+b'\n')
            elif label=='missing_witness':witness.unlink()
            elif label in ['changed_middle_height','changed_normalizer','malformed_rational_witness']:
                w=json.loads(witness.read_text())
                if label=='changed_middle_height':w['heights'][10]+=100
                elif label=='changed_normalizer':w['maximum']=str(service.MAXIMUM-Q(1,1000000))
                else:w['maximum']='1/0'
                witness.write_text(json.dumps(w))
            elif label=='changed_checker':
                p=work/service.SOURCES[1];p.write_text(p.read_text()+'\n# disposable mutation\n')
            elif label=='missing_checker':(work/service.SOURCES[0]).unlink()
            elif label=='changed_common_helper':
                p=work/'certificate_service.py';p.write_text(p.read_text()+'\n# disposable mutation\n')
            elif label=='missing_common_helper':(work/'certificate_service.py').unlink()
            elif label=='missing_protocol':(work/'study/final_confirmation_protocol.json').unlink()
            elif label=='existing_output':output.mkdir()
            command=[sys.executable]+(['-O'] if label=='optimized_python' else [])+[
                'final_certificate.py','--request',str(req),'--output',str(output)]
            answer=subprocess.run(command,cwd=work,capture_output=True,text=True,timeout=10)
            assert answer.returncode!=0 and not (output/'acceptance.json').exists(),(label,answer.stdout)
            structured=False
            try:
                error=json.loads(answer.stderr);structured=error.get('status')=='REFUSED'
            except json.JSONDecodeError:error={'exception_stderr':answer.stderr}
            if label!='missing_common_helper':assert answer.returncode==2 and structured,(label,error)
            mutations.append({'case':label,'return_code':answer.returncode,'structured_refusal':structured,
                              'error':error,'acceptance_created':False})
    after={p:sha(ROOT/p) for p in files};assert before==after
    elapsed=time.monotonic()-started;assert elapsed<120
    out={'status':'PASS: corrected final proof recomputed and all scope/input controls fail closed',
         'wrapper_sha256':expected,'protocol_version':2,'protocol_sha256':plan['protocol_sha256'],
         'witness_sha256':freeze['source_hashes']['certificate/weight.json'],
         'full_recomputation_seconds':receipt['elapsed_seconds'],'elapsed_seconds':elapsed,
         'scope_cases':cases,'disposable_cli_controls':mutations,'original_sources_unchanged':True,
         'source_hashes_before':before,'source_hashes_after':after,
         'fresh_mathematical_confirmation':'confirmation/final_weight_exact_cases.json',
         'preserved_interface_failure':'confirmation/final_null_request_probe_record.json',
         'minor_behavior_note':'Removing the Python helper module causes an import error with exit1, before CLI handlers load. This fails closed with no acceptance, while all supplied malformed requests and other tested proof-input failures return structured refusal exit2.',
         'comparison_scope':'Descriptive agreement with explicit same-asset theorem assumptions; no blinded model A/B, operational advantage or skill Alpha is inferred.'}
    (DEST/'ADVERSE_AUDIT.json').write_text(json.dumps(out,indent=2)+'\n')
    print({'status':out['status'],'full_recomputation_seconds':receipt['elapsed_seconds'],
           'scope_cases':len(cases),'cli_controls':len(mutations),'elapsed_seconds':elapsed,
           'unchanged_sources':True})


if __name__=='__main__':run()
