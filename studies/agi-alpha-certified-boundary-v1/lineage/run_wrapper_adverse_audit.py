"""Independent confirmation/refusal audit of the frozen certificate interface."""
import copy
import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import time
from fractions import Fraction as Q
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT/'confirmation/independent'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run():
    if DEST.exists():
        raise ValueError('Preserve earlier evidence; choose another audit destination')
    DEST.mkdir(parents=True)
    protocol=json.loads((ROOT/'study/confirmation_protocol.json').read_text())
    assert digest(ROOT/'certificate_service.py')==protocol['wrapper_sha256']
    spec=importlib.util.spec_from_file_location('audited_certificate_service',ROOT/'certificate_service.py')
    service=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(service)
    guarded=[ROOT/'certificate_service.py',ROOT/'study/confirmation_protocol.json']+[ROOT/p for p in service.SOURCES]
    before={str(p.relative_to(ROOT)):digest(p) for p in guarded}
    started=time.monotonic()
    request={'dimension':1,'coverage':'exactly_once','class_type':'full_residue',
             'minimum_hits':2,'interval_length':'all','interval_start':-37,
             'distinct_moduli':False,'lower_bound':str(service.BOUND)}
    request_path=DEST/'valid_translated_request.json'
    request_path.write_text(json.dumps(request,indent=2)+'\n')
    command=[sys.executable,'certificate_service.py','--request',str(request_path),
             '--output',str(DEST/'full_recomputation')]
    full=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,timeout=60)
    (DEST/'full_cli_stdout.json').write_text(full.stdout)
    (DEST/'full_cli_stderr.txt').write_text(full.stderr)
    assert full.returncode==0,full.stderr
    accepted=json.loads(full.stdout)
    assert accepted['status']=='PASS: exact research certificate recomputed'
    assert accepted['request_decision']['status']=='ACCEPTED_WITHIN_STATED_ASSUMPTIONS'
    cases=[]

    def scope_case(name,changes,expected):
        q=copy.deepcopy(request)
        q.update(changes)
        try:
            result=service.assess_scope(q)
            actual=True
            assert result['status']=='SCOPE_ADMISSIBLE; proof recomputation still required'
        except service.Refusal as exc:
            actual=False
            result={'reason':str(exc)}
        assert actual==expected,(name,result)
        cases.append({'name':name,'request':q,'expected_scope_admissible':expected,
                      'scope_admissible':actual,'result':result})

    scope_case('original one-dimensional universal request',{'distinct_moduli':True,'interval_start':1},True)
    scope_case('weaker exact bound on finite translated interval',{'interval_length':257,'interval_start':-1000,'lower_bound':'49/50'},True)
    scope_case('at least three hits is a valid subset',{'minimum_hits':3,'interval_length':601},True)
    scope_case('zero lower bound is a valid weaker claim',{'lower_bound':'0'},True)
    scope_case('one-dimensional finite interval need not assert existence',{'interval_length':2},True)
    scope_case('bound above the certified integral',{'lower_bound':str(service.BOUND+Q(1,10**12))},False)
    scope_case('unsupported singletons',{'minimum_hits':1},False)
    scope_case('arbitrary arithmetic progression',{'class_type':'arbitrary_arithmetic_progression'},False)
    scope_case('two dimensions',{'dimension':2},False)
    scope_case('overlapping covering',{'coverage':'at_least_once'},False)
    scope_case('incomplete packing',{'coverage':'at_most_once'},False)
    scope_case('float is not an exact bound string',{'lower_bound':0.98},False)
    scope_case('zero-denominator rational',{'lower_bound':'1/0'},False)
    scope_case('nonrational text',{'lower_bound':'NaN'},False)
    scope_case('noninteger translation',{'interval_start':Q(1,2).__str__()},False)
    scope_case('boolean dimension',{'dimension':True},False)
    scope_case('boolean minimum hits',{'minimum_hits':True},False)
    scope_case('unknown schema field',{'claim_is_approved':True},False)
    scope_case('length one not supported',{'interval_length':1},False)
    malformed=[]
    for name,obj in [('nonobject',[]),('missing fields',{'dimension':1})]:
        try: service.assess_scope(obj)
        except service.Refusal as exc: malformed.append({'name':name,'refused':True,'reason':str(exc)})
        else: raise AssertionError(name+' unexpectedly accepted')
    for name,raw in [('extra witness newline',(ROOT/service.SOURCES[0]).read_bytes()+b'\n'),
                     ('malformed witness bytes',b'{not valid json')]:
        try: service.validate_witness(raw)
        except service.Refusal as exc: malformed.append({'name':name,'refused':True,'reason':str(exc)})
        else: raise AssertionError(name+' unexpectedly accepted')

    # Every file mutation is made in a newly created disposable source copy.
    mutations=[]
    for label in ['forged_witness','missing_witness','modified_checker','malformed_rational_witness',
                  'missing_checker','missing_protocol','malformed_request_json','optimized_python','existing_output']:
        with tempfile.TemporaryDirectory(prefix='adverse_',dir=DEST) as directory:
            work=Path(directory)
            for source in guarded:
                target=work/source.relative_to(ROOT)
                target.parent.mkdir(parents=True,exist_ok=True)
                shutil.copyfile(source,target)
            req=work/'request.json'
            req.write_text(json.dumps(request))
            output=work/'result'
            witness=work/service.SOURCES[0]
            if label=='forged_witness': witness.write_bytes(witness.read_bytes()+b'\n')
            elif label=='missing_witness': witness.unlink()
            elif label=='modified_checker':
                path=work/service.SOURCES[1]
                path.write_text(path.read_text()+'\n# altered in disposable audit copy\n')
            elif label=='malformed_rational_witness':
                obj=json.loads(witness.read_text());obj['coefficients'][0]='1/0';witness.write_text(json.dumps(obj))
            elif label=='missing_checker': (work/service.SOURCES[1]).unlink()
            elif label=='missing_protocol': (work/'study/confirmation_protocol.json').unlink()
            elif label=='malformed_request_json': req.write_text('{')
            elif label=='existing_output': output.mkdir()
            cmd=[sys.executable]+(['-O'] if label=='optimized_python' else [])+['certificate_service.py',
                 '--request',str(req),'--output',str(output)]
            result=subprocess.run(cmd,cwd=work,capture_output=True,text=True,timeout=10)
            assert result.returncode==2,(label,result.stdout,result.stderr)
            refusal=json.loads(result.stderr)
            assert refusal['status']=='REFUSED'
            assert not (output/'acceptance.json').exists()
            mutations.append({'case':label,'return_code':result.returncode,'refusal':refusal,
                              'acceptance_file_created':False})
    after={str(p.relative_to(ROOT)):digest(p) for p in guarded}
    assert before==after
    elapsed=time.monotonic()-started
    assert elapsed<=120
    report={'status':'PASS: frozen full proof and all specified adverse controls',
            'wrapper_sha256':protocol['wrapper_sha256'],'witness_sha256':protocol['witness_sha256'],
            'elapsed_seconds':elapsed,'full_recomputation_seconds':accepted['elapsed_seconds'],
            'full_recomputation_passed':True,'fresh_exact_cases_file':'lineage/FRESH_EXACT_CONFIRMATION.json',
            'scope_cases':cases,'malformed_direct_controls':malformed,'disposable_copy_controls':mutations,
            'source_hashes_before':before,'source_hashes_after':after,'original_sources_unchanged':True,
            'limitations':'Same-session executable confirmation; no external peer review, model A/B or economic gain measured.'}
    (DEST/'ADVERSE_AUDIT.json').write_text(json.dumps(report,indent=2)+'\n')
    print({'status':report['status'],'full_recomputation_seconds':accepted['elapsed_seconds'],
           'scope_cases':len(cases),'direct_malformed_controls':len(malformed),
           'disposable_copy_controls':len(mutations),'elapsed_seconds':elapsed,
           'original_sources_unchanged':True})


if __name__=='__main__':
    run()
