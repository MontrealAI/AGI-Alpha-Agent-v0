# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations
import argparse, hashlib, importlib.metadata, json, os, re, resource, subprocess, sys, time, tomllib
from pathlib import Path
from packaging.markers import default_environment
from packaging.requirements import Requirement
from packaging.specifiers import SpecifierSet
from packaging.utils import canonicalize_name, parse_wheel_filename

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def write(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False)+'\n')

def build(job_path, out):
    started=time.perf_counter(); cpu0=time.process_time(); child0=resource.getrusage(resource.RUSAGE_CHILDREN)
    job_path=job_path.resolve(); out.mkdir(parents=True, exist_ok=False)
    job=json.loads(job_path.read_text()); base=job_path.parent
    result={'schema':'agialpha-lock-result/v1','job_sha256':digest(job_path),'job_id':job['id'],
            'decision':'INCOMPLETE','pip_exit_code':-1,'files':{'stdout':'pip.stdout.txt','stderr':'pip.stderr.txt','report':None},
            'tool_versions':{'python':sys.version.split()[0],'pip':importlib.metadata.version('pip'),'packaging':importlib.metadata.version('packaging')},
            'application_qualified':False,'authority':[],'financial_action':False,'commands':[],
            'method':'retained ordinary-pip full-lock preflight','preflight_findings':[]}
    (out/'pip.stdout.txt').write_text(''); (out/'pip.stderr.txt').write_text('')
    try:
        if job['schema']!='agialpha-lock-job/v1': raise ValueError('JOB_SCHEMA')
        if job['target_environment']!=default_environment(): raise ValueError('TARGET_ENVIRONMENT_NOT_CURRENT')
        lock=(base/job['lock_path']).resolve(); project=(base/job['pyproject_path']).resolve(); wheels=(base/job['wheelhouse_path']).resolve()
        if digest(lock)!=job['lock_sha256'] or digest(project)!=job['pyproject_sha256']: raise ValueError('INPUT_IDENTITY')
        lock_text=lock.read_text(); blocks=re.split(r'\n(?=[A-Za-z0-9_.-]+==)', '\n'+lock_text)
        pins={}
        for block in blocks:
            m=re.match(r'\s*([A-Za-z0-9_.-]+)==([^\s\\]+)',block)
            if m:
                name=canonicalize_name(m[1]); hashes=re.findall(r'--hash=sha256:([a-f0-9]{64})',block)
                if name in pins or not hashes: raise ValueError('LOCK_PIN_OR_HASH')
                pins[name]=(m[2],hashes)
        if not pins: raise ValueError('EMPTY_LOCK')
        selected=out/'selected-wheels'; selected.mkdir()
        declared={}
        for entry in job['wheels']:
            name=canonicalize_name(entry['name']); filename=entry['filename']
            if Path(filename).name!=filename or name in declared: raise ValueError('WHEEL_MANIFEST')
            source=wheels/filename; wn,wv,_,_=parse_wheel_filename(filename)
            if str(wn)!=name or str(wv)!=entry['version'] or name not in pins or pins[name][0]!=entry['version']: raise ValueError('WHEEL_PIN_IDENTITY')
            if entry['sha256'] not in pins[name][1] or digest(source)!=entry['sha256']: raise ValueError('WHEEL_DIGEST')
            os.link(source,selected/filename); declared[name]=entry
        if set(declared)!=set(pins): raise ValueError('COMPLETE_WHEEL_SET_REQUIRED')
        project_data=tomllib.loads(project.read_text())['project']; target=job['target_environment']
        if not SpecifierSet(project_data.get('requires-python','')).contains(target['python_full_version'],prereleases=True):
            result['preflight_findings'].append({'kind':'ROOT_PYTHON_CONFLICT','requirement':project_data['requires-python'],'observed':target['python_full_version']})
        roots=list(project_data.get('dependencies',[]))
        for extra in job['project_extras']:
            if extra not in project_data.get('optional-dependencies',{}): raise ValueError('UNKNOWN_PROJECT_EXTRA')
            roots.extend(project_data['optional-dependencies'][extra])
        root_rows=[]
        for text in roots:
            req=Requirement(text)
            if req.url: raise ValueError('DIRECT_REFERENCE_UNSUPPORTED')
            contexts=['']+job['project_extras']
            if req.marker and not any(req.marker.evaluate(dict(target,extra=x)) for x in contexts): continue
            name=canonicalize_name(req.name)
            if name not in pins: raise ValueError('MISSING_ROOT_WHEEL')
            version,hashes=pins[name]
            if not req.specifier.contains(version,prereleases=True):
                result['preflight_findings'].append({'kind':'ROOT_VERSION_CONFLICT','requirement':text,'observed':version})
            extras='['+','.join(sorted(req.extras))+']' if req.extras else ''
            root_rows.append(name+extras+'=='+version+' '+' '.join('--hash=sha256:'+h for h in hashes))
        (out/'root-requirements.lock').write_text('\n'.join(root_rows)+'\n')
        command=[sys.executable,'-m','pip','--isolated','--disable-pip-version-check','install','--dry-run','--ignore-installed',
                 '--no-index','--find-links',str(selected.resolve()),'--only-binary=:all:','--require-hashes','--report',
                 str((out/'pip-report.json').resolve()),'-r',str(lock),'-r',str((out/'root-requirements.lock').resolve())]
        result['commands'].append(command)
        with (out/'pip.stdout.txt').open('w') as so,(out/'pip.stderr.txt').open('w') as se:
            proc=subprocess.run(command,stdout=so,stderr=se,timeout=60,check=False)
        result['pip_exit_code']=proc.returncode
        if digest(lock)!=job['lock_sha256'] or digest(project)!=job['pyproject_sha256'] or any(digest(selected/e['filename'])!=e['sha256'] for e in declared.values()):
            raise ValueError('INPUT_CHANGED_DURING_OPERATION')
        if (out/'pip-report.json').is_file(): result['files']['report']='pip-report.json'
        if result['preflight_findings']: result['decision']='CONFLICT'
        elif proc.returncode==0 and result['files']['report']: result['decision']='CONSISTENT'
        elif 'ResolutionImpossible' in (out/'pip.stderr.txt').read_text(): result['decision']='CONFLICT'
        else: result['decision']='INCOMPLETE'
    except (ValueError,KeyError,OSError,subprocess.TimeoutExpired) as exc:
        result['decision']='INCOMPLETE'; result['preflight_findings'].append({'kind':'INCOMPLETE_EVIDENCE','detail':str(exc)})
    child1=resource.getrusage(resource.RUSAGE_CHILDREN)
    result['elapsed_wall_seconds']=time.perf_counter()-started
    result['cpu_seconds']=time.process_time()-cpu0+child1.ru_utime+child1.ru_stime-child0.ru_utime-child0.ru_stime
    result['artifacts_sha256']={n:digest(out/n) for n in ['pip.stdout.txt','pip.stderr.txt']+(['pip-report.json'] if result['files']['report'] else [])}
    result['limits']=['Wheel metadata consistency only; application behavior, vulnerabilities and release qualification remain separate.','Research-proposed lock; no customer order, installation, authority or financial transaction.']
    write(out/'result.json',result); return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--job',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    print(json.dumps(build(a.job,a.out)))
