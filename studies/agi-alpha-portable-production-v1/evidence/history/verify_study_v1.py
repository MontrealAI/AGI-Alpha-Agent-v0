# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations
import argparse, hashlib, importlib.util, json, shutil, tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parent
FIXED={
 'data/public/SOURCE_MANIFEST.json':'641f7cb5293d0d919c6b1b2e39dd072d4be184e4f0d1a103458d3af61477475f',
 'protocol/FRESH_CONFIRMATION.json':'df7002de8eb4f66446aa9e23d7875b213140d91fd39e65275d105c116c03321e',
 'verify_confirmation.py':'38f49c711fe0d03e74972d6e85ae2adfc40a705f3d3ef8d84500082fee24674c',
 'src/produce.py':'5c2be43b6e014a34465eb249d6f30e5e278c9a0975f0d8fc59a6ccc8cf4b058e',
 'src/feature_program.json':'0beb58c9cb2890afa653cb64dc33b87f5dd154986de83fa76352f6eded2174c8'
}

def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def frozen_errors(root: Path) -> list[str]:
    errors=[]
    for rel,expected in FIXED.items():
        p=root/rel
        if not p.is_file() or p.is_symlink() or sha(p)!=expected:
            errors.append('Changed frozen file: '+rel)
    listed=json.loads((root/'protocol/FRESH_FREEZE.json').read_text())
    for rel in ['protocol/FRESH_CONFIRMATION.json','verify_confirmation.py','src/produce.py']:
        if listed.get(rel)!=FIXED[rel]:errors.append('Changed freeze declaration: '+rel)
    public=root/'data/public'
    source=json.loads((public/'SOURCE_MANIFEST.json').read_text())
    for item in source['files']:
        p=public/item['path']
        if not p.is_file() or p.is_symlink() or sha(p)!=item['sha256']:
            errors.append('Changed public input: '+item['path'])
    return errors

def load_producer(root: Path):
    spec=importlib.util.spec_from_file_location('accepted_producer',root/'src/produce.py')
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    return m

def report_status(report: dict) -> bool:
    return report.get('status')=='PASS_GEOMETRY_ONLY' and report.get('accepted_cases')==3 and report.get('refused_negative_cases')==6 and all(all(c['checks'].values()) for c in report['cases']) and all(x['refused'] for x in report['negative_cases'])

def main() -> None:
    ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,default=ROOT)
    ap.add_argument('--output',type=Path,default=ROOT/'evidence/final_verification.json')
    a=ap.parse_args();errors=frozen_errors(a.root)
    if errors:raise SystemExit('REFUSED under old freeze: '+'; '.join(errors))
    import cadquery as cq
    producer=load_producer(a.root)
    report=json.loads((a.root/'results/fresh_confirmation/acceptance.json').read_text())
    statuses=report_status(report)
    roundtrip=[]
    for folder in ['construction_v1_2','fresh_confirmation']:
        for case_dir in sorted((a.root/'results'/folder).iterdir()):
            if not case_dir.is_dir():continue
            case=json.loads((case_dir/'feature_program.json').read_text())
            original=producer.build(case);reloaded=cq.importers.importStep(str(case_dir/'part.step')).val()
            delta=original.cut(reloaded).Volume()+reloaded.cut(original).Volume()
            tolerance=max(1e-6,abs(original.Volume())*1e-8)
            roundtrip.append({'case':case['id'],'symmetric_difference_volume':delta,'accepted':abs(delta)<=tolerance})
    mutation_results=[]
    with tempfile.TemporaryDirectory(prefix='agi-alpha-freeze-') as td:
        temp=Path(td)/'study';temp.mkdir()
        for rel in list(FIXED)+['protocol/FRESH_FREEZE.json']:
            dest=temp/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(a.root/rel,dest)
        shutil.copytree(a.root/'data/public',temp/'data/public',dirs_exist_ok=True)
        for rel in ['protocol/FRESH_CONFIRMATION.json','src/produce.py']:
            target=temp/rel;original=target.read_bytes();target.write_bytes(original+b'\n')
            rejected=bool(frozen_errors(temp));target.write_bytes(original)
            mutation_results.append({'changed_file':rel,'rejected':rejected})
    failed=dict(report);failed['status']='FAIL_FROZEN_CONFIRMATION'
    false_status_rejected=not report_status(failed)
    result={'status':'PASS' if statuses and all(x['accepted'] for x in roundtrip) and all(x['rejected'] for x in mutation_results) and false_status_rejected else 'FAIL',
      'scope':'Retrospective supplementary integrity and STEP checks; not new independent scientific confirmation.',
      'frozen_inputs_verified':True,'fresh_report_accepted':statuses,
      'step_geometry_roundtrips':roundtrip,'changed_input_refusals':mutation_results,
      'failed_report_causes_failure':false_status_rejected,
      'unresolved':['duplicate or missing feature identifiers admitted by constructor validation','no customer acceptance','no physical qualification','same OpenCascade kernel in both geometry paths','no matched frontier-model operating comparison','no economically enabling distinction over ordinary CadQuery']}
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))
    if result['status']!='PASS':raise SystemExit(1)

if __name__=='__main__':main()
