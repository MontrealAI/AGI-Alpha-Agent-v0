# SPDX-License-Identifier: Apache-2.0
import argparse, hashlib, importlib.metadata, json, re, resource, subprocess, sys, time, tomllib
from pathlib import Path
from packaging.markers import default_environment
from packaging.requirements import Requirement
from packaging.specifiers import SpecifierSet
from packaging.utils import canonicalize_name

p=argparse.ArgumentParser();p.add_argument('--job',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
t=time.perf_counter();c=time.process_time();rc=resource.getrusage(resource.RUSAGE_CHILDREN);a.out.mkdir(parents=True,exist_ok=False)
job=json.loads(a.job.read_text());base=a.job.resolve().parent;lock=(base/job['lock_path']).resolve();pyproject=(base/job['pyproject_path']).resolve();warehouse=(base/job['wheelhouse_path']).resolve()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
if sha(lock)!=job['lock_sha256'] or sha(pyproject)!=job['pyproject_sha256'] or job['target_environment']!=default_environment():raise ValueError('INPUT_IDENTITY')
project=tomllib.loads(pyproject.read_text())['project'];pins={canonicalize_name(n):v for n,v in re.findall(r'^([A-Za-z0-9_.-]+)==([^\s\\]+)',lock.read_text(),re.M)}
requirements=project['dependencies']+[r for x in job['project_extras'] for r in project['optional-dependencies'][x]]
root_conflicts=[];root_lines=[]
for text in requirements:
    r=Requirement(text)
    if r.marker and not any(r.marker.evaluate(dict(default_environment(),extra=x)) for x in ['']+job['project_extras']):continue
    name=canonicalize_name(r.name);version=pins.get(name)
    if r.url or version is None or not r.specifier.contains(version,prereleases=True):root_conflicts.append(text)
    if version:
        h=next(w['sha256'] for w in job['wheels'] if canonicalize_name(w['name'])==name)
        extras='['+','.join(sorted(r.extras))+']' if r.extras else ''
        root_lines.append(f'{name}{extras}=={version} --hash=sha256:{h}')
if not SpecifierSet(project['requires-python']).contains(default_environment()['python_full_version'],prereleases=True):root_conflicts.append('Requires-Python '+project['requires-python'])
(a.out/'root-requirements.lock').write_text('\n'.join(root_lines)+'\n')
command=[sys.executable,'-m','pip','--isolated','--disable-pip-version-check','install','--dry-run','--ignore-installed','--no-index','--find-links',str(warehouse),'--only-binary=:all:','--require-hashes','--report',str((a.out/'pip-report.json').resolve()),'-r',str(lock),'-r',str((a.out/'root-requirements.lock').resolve())]
with (a.out/'pip.stdout.txt').open('w') as so,(a.out/'pip.stderr.txt').open('w') as se:proc=subprocess.run(command,stdout=so,stderr=se,timeout=60,check=False)
report='pip-report.json' if (a.out/'pip-report.json').is_file() else None
decision='CONFLICT' if root_conflicts else 'CONSISTENT' if proc.returncode==0 and report else 'CONFLICT' if 'ResolutionImpossible' in (a.out/'pip.stderr.txt').read_text() else 'INCOMPLETE'
end=resource.getrusage(resource.RUSAGE_CHILDREN)
result={'schema':'agialpha-lock-result/v1','job_sha256':sha(a.job),'job_id':job['id'],'decision':decision,'pip_exit_code':proc.returncode,'files':{'stdout':'pip.stdout.txt','stderr':'pip.stderr.txt','report':report},'tool_versions':{'python':sys.version.split()[0],'pip':importlib.metadata.version('pip'),'packaging':importlib.metadata.version('packaging')},'elapsed_wall_seconds':time.perf_counter()-t,'cpu_seconds':time.process_time()-c+end.ru_utime+end.ru_stime-rc.ru_utime-rc.ru_stime,'application_qualified':False,'authority':[],'financial_action':False,'commands':[command],'root_conflicts':root_conflicts,'method':'direct standard pip workflow; generic measurement wrapper','new_retained_enterprise_capability':False,'human_finalization_minutes':None}
(a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
