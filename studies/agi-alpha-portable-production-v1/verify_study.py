# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations
import argparse, copy, csv, hashlib, importlib.util, json, shutil, tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parent
FIXED={
 'data/public/SOURCE_MANIFEST.json':'641f7cb5293d0d919c6b1b2e39dd072d4be184e4f0d1a103458d3af61477475f',
 'protocol/FRESH_CONFIRMATION.json':'df7002de8eb4f66446aa9e23d7875b213140d91fd39e65275d105c116c03321e',
 'verify_confirmation.py':'38f49c711fe0d03e74972d6e85ae2adfc40a705f3d3ef8d84500082fee24674c',
 'src/produce.py':'5c2be43b6e014a34465eb249d6f30e5e278c9a0975f0d8fc59a6ccc8cf4b058e',
 'src/feature_program.json':'0beb58c9cb2890afa653cb64dc33b87f5dd154986de83fa76352f6eded2174c8',
 'evidence/HISTORICAL_SEAL.json':'6f923a2ebf82ad525f4a166b03da0075f328aa53e1157d70129e2ec9d6be2984'
}
FRESH_CHECKS={'one_valid_solid','nominal_bbox','independent_analytic_volume','independent_native_geometry','step_roundtrip','feature_probes'}
HISTORICAL_CHECKS={'one_valid_solid','nominal_bbox','analytic_volume','reference_volume','reference_symmetric_difference','step_roundtrip'}
ARTIFACTS={'part.step','part.stl','part.svg','feature_program.json','features.csv'}
CSV_FIELDS=['id','kind','x','y','diameter','counterbore_diameter','counterbore_depth','countersink_diameter','included_angle_deg','source_units','physical_tolerance','material','machine_release']

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def read_json(path):
    return json.loads(Path(path).read_text())

def frozen_errors(root):
    errors=[]
    for rel,expected in FIXED.items():
        p=root/rel
        if not p.is_file() or p.is_symlink() or sha(p)!=expected:
            errors.append('Changed frozen or post-execution-sealed file: '+rel)
    if errors:return errors
    expected_declaration={rel:FIXED[rel] for rel in ['protocol/FRESH_CONFIRMATION.json','verify_confirmation.py','src/produce.py']}
    p=root/'protocol/FRESH_FREEZE.json'
    if not p.is_file() or p.is_symlink() or read_json(p)!=expected_declaration:
        errors.append('Changed freeze declaration')
    for item in read_json(root/'data/public/SOURCE_MANIFEST.json')['files']:
        p=root/'data/public'/item['path']
        if not p.is_file() or p.is_symlink() or sha(p)!=item['sha256'] or p.stat().st_size!=item['size']:
            errors.append('Changed public input: '+item['path'])
    for item in read_json(root/'evidence/HISTORICAL_SEAL.json')['files']:
        p=root/item['path']
        if not p.is_file() or p.is_symlink() or sha(p)!=item['sha256'] or p.stat().st_size!=item['bytes']:
            errors.append('Changed post-execution historical archive: '+item['path'])
    return errors

def exact_rows(value,key,expected,label,errors):
    if type(value) is not list or any(type(row) is not dict for row in value):
        errors.append(label+': expected row list');return {}
    ids=[row.get(key) for row in value]
    if len(ids)!=len(expected) or any(type(x) is not str for x in ids) or len(set(ids))!=len(ids) or set(ids)!=set(expected):
        errors.append(label+': missing, duplicate or unexpected IDs');return {}
    return {row[key]:row for row in value}

def all_required_checks(checks,required):
    return type(checks) is dict and set(checks)==required and all(type(v) is bool and v for v in checks.values())

def report_errors(report,protocol):
    errors=[]
    if type(report) is not dict:return ['Fresh report: expected object']
    cases=exact_rows(report.get('cases'),'id',[x['id'] for x in protocol['cases']],'Fresh cases',errors)
    negative=exact_rows(report.get('negative_cases'),'case',protocol['negative_cases'],'Fresh negative cases',errors)
    exploratory=exact_rows(report.get('exploratory_schema_cases'),'case',protocol['exploratory_adversarial_cases'],'Exploratory schema cases',errors)
    for name,row in cases.items():
        if row.get('accepted') is not True or not all_required_checks(row.get('checks'),FRESH_CHECKS):errors.append('Fresh case failed/incomplete: '+name)
    for name,row in negative.items():
        if row.get('refused') is not True:errors.append('Fresh negative not refused: '+name)
    for name,row in exploratory.items():
        if row.get('refused') is not False:errors.append('Preserved schema failure changed: '+name)
    accepted=sum(row.get('accepted') is True and all_required_checks(row.get('checks'),FRESH_CHECKS) for row in cases.values())
    refused=sum(row.get('refused') is True for row in negative.values())
    if type(report.get('accepted_cases')) is not int or report['accepted_cases']!=accepted or accepted!=len(protocol['cases']):errors.append('Fresh accepted summary mismatch')
    if type(report.get('refused_negative_cases')) is not int or report['refused_negative_cases']!=refused or refused!=len(protocol['negative_cases']):errors.append('Fresh negative summary mismatch')
    for key,rel in [('protocol_sha256','protocol/FRESH_CONFIRMATION.json'),('checker_sha256','verify_confirmation.py'),('constructor_sha256','src/produce.py')]:
        if report.get(key)!=FIXED[rel]:errors.append('Fresh report identity mismatch: '+key)
    if report.get('origin')!=protocol['case_origin']:errors.append('Fresh report origin mismatch')
    if report.get('status')!='PASS_GEOMETRY_ONLY':errors.append('Fresh report status failed')
    return errors

def report_status(report,protocol=None):
    return not report_errors(report,protocol if protocol is not None else read_json(ROOT/'protocol/FRESH_CONFIRMATION.json'))

def historical_report_errors(report,cases,root):
    errors=[]
    rows=exact_rows(report.get('cases'),'id',[x['id'] for x in cases],'Historical cases',errors)
    for key,rel in [('constructor_sha256','src/produce.py'),('program_sha256','src/feature_program.json'),('source_manifest_sha256','data/public/SOURCE_MANIFEST.json')]:
        if report.get(key)!=FIXED[rel]:errors.append('Historical identity mismatch: '+key)
    accepted=0
    for case in cases:
        row=rows.get(case['id'])
        if row is None:continue
        good=row.get('accepted') is True and all_required_checks(row.get('checks'),HISTORICAL_CHECKS)
        accepted+=good
        if not good:errors.append('Historical case failed/incomplete: '+case['id'])
        if row.get('source')!=case['source_file']:errors.append('Historical source mismatch: '+case['id'])
        artifacts=row.get('artifacts')
        if type(artifacts) is not dict or set(artifacts)!=ARTIFACTS:
            errors.append('Historical artifact inventory mismatch: '+case['id']);continue
        for name,item in artifacts.items():
            p=root/'results/construction_v1_2'/case['id']/name
            if type(item) is not dict or not p.is_file() or p.is_symlink() or item.get('sha256')!=sha(p) or item.get('bytes')!=p.stat().st_size:
                errors.append('Historical artifact receipt mismatch: '+case['id']+'/'+name)
    if type(report.get('case_count')) is not int or report['case_count']!=len(cases):errors.append('Historical case count mismatch')
    if type(report.get('accepted_cases')) is not int or report['accepted_cases']!=accepted or accepted!=len(cases):errors.append('Historical accepted summary mismatch')
    return errors

def csv_errors(path,case):
    with path.open(newline='') as f:
        reader=csv.DictReader(f);actual=list(reader);fields=reader.fieldnames
    expected=[]
    for hole in case['holes']:
        values={**hole,'source_units':case['source_units'],'physical_tolerance':'UNSPECIFIED','material':'UNSPECIFIED','machine_release':'NO'}
        expected.append({key:str(values[key]) if key in values else '' for key in CSV_FIELDS})
    return [] if fields==CSV_FIELDS and actual==expected else ['Feature CSV differs from frozen nominal recipe: '+case['id']]

def load_producer(root):
    spec=importlib.util.spec_from_file_location('accepted_producer',root/'src/produce.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

def validate_package(root,geometry=True):
    errors=frozen_errors(root)
    result={'errors':errors,'step_geometry_roundtrips':[],'recipe_and_csv_cases':0}
    if errors:return result
    protocol=read_json(root/'protocol/FRESH_CONFIRMATION.json')
    historical=read_json(root/'src/feature_program.json')['cases']
    errors.extend(report_errors(read_json(root/'results/fresh_confirmation/acceptance.json'),protocol))
    errors.extend(historical_report_errors(read_json(root/'results/construction_v1_2/acceptance.json'),historical,root))
    for folder,cases in [('construction_v1_2',historical),('fresh_confirmation',protocol['cases'])]:
        base=root/'results'/folder
        dirs=[p.name for p in base.iterdir() if p.is_dir()]
        if len(dirs)!=len(cases) or set(dirs)!={x['id'] for x in cases}:
            errors.append('Result directory set differs from frozen case set: '+folder)
        for case in cases:
            directory=base/case['id']
            if not directory.is_dir() or directory.is_symlink():errors.append('Missing or linked case directory: '+str(directory));continue
            files=list(directory.iterdir())
            if {p.name for p in files}!=ARTIFACTS or any(not p.is_file() or p.is_symlink() for p in files):errors.append('Case artifact inventory mismatch: '+folder+'/'+case['id']);continue
            if read_json(directory/'feature_program.json')!=case:errors.append('Case recipe differs from frozen request: '+folder+'/'+case['id']);continue
            csv_problem=csv_errors(directory/'features.csv',case);errors.extend(csv_problem)
            if not csv_problem:result['recipe_and_csv_cases']+=1
    if errors or not geometry:return result
    import cadquery as cq
    if cq.__version__!='2.7.0':errors.append('CadQuery differs from frozen 2.7.0 environment');return result
    producer=load_producer(root)
    for folder,cases in [('construction_v1_2',historical),('fresh_confirmation',protocol['cases'])]:
        for case in cases:
            original=producer.build(case)
            reloaded=cq.importers.importStep(str(root/'results'/folder/case['id']/'part.step')).val()
            delta=original.cut(reloaded).Volume()+reloaded.cut(original).Volume()
            tolerance=max(1e-6,abs(original.Volume())*1e-8)
            m=producer.metrics(reloaded)
            accepted=m['valid'] and m['solids']==1 and abs(delta)<=tolerance and all(abs(x-y)<1e-7 for x,y in zip(m['bbox'],case['stock']))
            result['step_geometry_roundtrips'].append({'case':case['id'],'origin':folder,'symmetric_difference_volume':delta,'volume_tolerance':tolerance,'valid_single_solid':m['valid'] and m['solids']==1,'accepted':accepted})
            if not accepted:errors.append('STEP geometry mismatch: '+folder+'/'+case['id'])
    return result

def copy_fixture(root,temp):
    for rel in list(FIXED)+['protocol/FRESH_FREEZE.json']:
        dest=temp/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(root/rel,dest)
    for rel in ['data/public','evidence/history','results/construction_v1_2','results/fresh_confirmation']:
        shutil.copytree(root/rel,temp/rel,dirs_exist_ok=True)

def mutation_probes(root):
    protocol=read_json(root/'protocol/FRESH_CONFIRMATION.json');report=read_json(root/'results/fresh_confirmation/acceptance.json')
    empty=copy.deepcopy(report);empty['cases']=[];empty['negative_cases']=[]
    failed=copy.deepcopy(report);failed['status']='FAIL_FROZEN_CONFIRMATION'
    probes=[{'case':'empty detailed evidence with unchanged claimed totals','rejected':not report_status(empty,protocol)},
            {'case':'explicit failed confirmation report','rejected':not report_status(failed,protocol)}]
    with tempfile.TemporaryDirectory(prefix='agi-alpha-wrapper-audit-') as td:
        temp=Path(td)/'study';temp.mkdir();copy_fixture(root,temp)
        for rel in ['protocol/FRESH_CONFIRMATION.json','src/produce.py']:
            p=temp/rel;original=p.read_bytes();p.write_bytes(original+b'\n')
            probes.append({'case':'changed '+rel,'rejected':bool(frozen_errors(temp))});p.write_bytes(original)
        missing=temp/'results/fresh_confirmation'/protocol['cases'][0]['id'];held=temp/'held-case';missing.rename(held)
        probes.append({'case':'missing expected confirmation case directory','rejected':bool(validate_package(temp,False)['errors'])});held.rename(missing)
        p=missing/'feature_program.json';original=p.read_bytes();changed=read_json(p);changed['holes'][0]['diameter']+=0.01;p.write_text(json.dumps(changed))
        probes.append({'case':'changed output recipe under unchanged frozen request','rejected':bool(validate_package(temp,False)['errors'])});p.write_bytes(original)
    return probes

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=ROOT);p.add_argument('--output',type=Path,default=ROOT/'evidence/final_verification.json');a=p.parse_args()
    validation=validate_package(a.root)
    probes=mutation_probes(a.root) if not validation['errors'] else []
    accepted=not validation['errors'] and len(validation['step_geometry_roundtrips'])==6 and validation['recipe_and_csv_cases']==6 and len(probes)==6 and all(x['rejected'] for x in probes)
    result={'schema':'supplementary-verification-v2','status':'PASS' if accepted else 'FAIL',
      'scope':'Retrospective integrity and six known-case STEP checks. No new prospective scientific confirmation or physical qualification.',
      'verifier_sha256':sha(Path(__file__)),'historical_seal_phase':'POST_EXECUTION',
      'frozen_and_sealed_files_verified':not frozen_errors(a.root),
      'fresh_report_accepted':not report_errors(read_json(a.root/'results/fresh_confirmation/acceptance.json'),read_json(a.root/'protocol/FRESH_CONFIRMATION.json')),
      **validation,'mutation_probes':probes,
      'unresolved':['duplicate or missing feature identifiers admitted by frozen constructor','original parametric dependencies are not preserved','trusted frozen inputs only; not a hardened external-input service','no customer acceptance or physical qualification','shared OpenCascade kernel','no matched model comparison or economically enabling distinction over ordinary CadQuery']}
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
    if not accepted:raise SystemExit(1)

if __name__=='__main__':main()
