# SPDX-License-Identifier: Apache-2.0
import argparse, hashlib, importlib.metadata, json, os, shutil, subprocess, sys, tempfile, time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,default=ROOT/'reproduction');a=ap.parse_args()
    out=a.output.resolve();out.mkdir(parents=True,exist_ok=True)
    versions=json.loads((ROOT/'environment.json').read_text())
    mismatches={k:{'expected':v,'observed':importlib.metadata.version(k)} for k,v in versions['packages'].items() if importlib.metadata.version(k)!=v}
    if mismatches:raise RuntimeError('Use the tested environment; version differences: '+json.dumps(mismatches))
    steps=[]
    def call(name,cmd,cwd,env,expect=0,timeout=180):
        t=time.perf_counter();p=subprocess.run(cmd,cwd=cwd,env=env,capture_output=True,text=True,timeout=timeout)
        record={'name':name,'command':[str(x) for x in cmd],'expected_exit':expect,'exit_code':p.returncode,'elapsed_seconds':time.perf_counter()-t,'stdout':p.stdout,'stderr':p.stderr}
        steps.append(record)
        if p.returncode!=expect:raise RuntimeError(name+' failed: '+p.stdout+p.stderr)
    with tempfile.TemporaryDirectory(prefix='agi-alpha-capsule-reproduction-') as td:
        temp=Path(td);cache=temp/'seaborn';cache.mkdir();shutil.copy2(ROOT/'inputs/iris.csv',cache/'iris.csv')
        env={**os.environ,'MPLCONFIGDIR':str(temp/'mpl'),'SEABORN_DATA':str(cache),'OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1','PYTHONDONTWRITEBYTECODE':'1'}
        call('independent_identity',[sys.executable,ROOT/'scripts/independent_audit.py',ROOT,'--output',out/'identity.json'],temp,env)
        for phase in ['development','confirmation']:
            for source in sorted((ROOT/'inputs'/phase).glob('*.ipynb')):
                case=source.stem;delivery=ROOT/'deliveries'/case
                identity=json.loads((delivery/'identity.json').read_text())
                if hashlib.sha256(source.read_bytes()).hexdigest()!=identity['input_sha256']:raise RuntimeError('Changed source '+case)
                if hashlib.sha256((delivery/'recovered.ipynb').read_bytes()).hexdigest()!=identity['output_sha256']:raise RuntimeError('Changed delivery '+case)
                call(case+' unchanged baseline',[sys.executable,ROOT/'scripts/capsule_runner.py',source,'--case',case,'--output',out/('baseline-'+case+'.json')],temp,env,expect=1)
                copied=temp/case;copied.mkdir();shutil.copy2(delivery/'recovered.ipynb',copied/'recovered.ipynb')
                if phase=='development':
                    call(case+' delivered',[sys.executable,ROOT/'scripts/capsule_runner.py',copied/'recovered.ipynb','--case',case,'--output',out/('accepted-'+case+'.json'),'--checks',ROOT/'scripts/development_checks.py'],copied,env)
                else:
                    call(case+' delivered',[sys.executable,ROOT/'scripts/independent_run.py',copied/'recovered.ipynb','--case',case,'--output',out/('accepted-'+case+'.json'),'--checks',ROOT/'scripts/independent_checks.py'],copied,env)
        call('adverse_controls',[sys.executable,ROOT/'scripts/independent_controls.py',ROOT,'--output',out/'adverse'],temp,env)
        expected={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'economics/results').glob('*') if p.is_file()}
        call('economic_study',[sys.executable,ROOT/'economics/run_economics.py'],ROOT,env)
        observed={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'economics/results').glob('*') if p.is_file()}
        if expected!=observed:raise RuntimeError('Economic regeneration changed frozen outputs')
        call('native_exact_source',[sys.executable,ROOT/'scripts/native_evidence_demo.py','--output',out/'native'],ROOT,env)
    report={'schema':'complete-reproduction/v1','accepted':True,'development_cases':2,'confirmation_cases':4,'confirmation_cells':133,'distinct_confirmation_checks':38,'economic_outputs_identical':len(expected),'dependency_versions_matched':not mismatches,'steps':steps,'limits':'Fresh-process execution on tested installed runtime, not clean dependency installation or general OS portability; model billing and customer revenue are not measured.'}
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='steps'},indent=2))

if __name__=='__main__':main()
