import argparse,json,subprocess,time
from pathlib import Path

PINS={'alpha':'0385df4c9728db19c396e039cd04678eebfddb9e','manager':'c5958eae872458c2f3cac48fea0b4bbfadc6ac6c','jobs':'9983478d42c32fe399f28dd9b0e0173f904b8a11'}
REPOS={'alpha':'AGI-Alpha-Agent-v0','manager':'AGIJobManager','jobs':'AGIJobsv0'}
PATTERNS={'alpha':['examples/successor-capability','examples/successor-workbench/mission-store.mjs','docs/assets/successor/engine.mjs','scripts/generate_successor_capability.py','scripts/templates/successor-capability','docs/successor/capabilities/sources.json'],'manager':['scripts/integrations/discovery-lab-native-test.mjs','scripts/integrations/discovery-lab-contract.mjs','scripts/integrations/discovery-lab-work-request.mjs','config/discovery-lab-alpha-source.json'],'jobs':['integrations/alpha-agent/discovery-lab-native-test.mjs','integrations/alpha-agent/discovery-lab-contract.mjs','integrations/alpha-agent/discovery-lab-work-request.mjs','config/discovery-lab-alpha-source.json']}

def run(args,cwd=None):
    return subprocess.run(args,cwd=cwd,check=True,text=True,capture_output=True).stdout

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--work',required=True);args=parser.parse_args();root=Path(args.work).resolve();root.mkdir(parents=True,exist_ok=False)
    for key,repo in REPOS.items():
        target=root/key;run(['git','clone','--filter=blob:none','--no-checkout','--depth','1',f'https://github.com/MontrealAI/{repo}.git',str(target)])
        run(['git','fetch','--depth','1','origin',PINS[key]],target);run(['git','sparse-checkout','set','--no-cone',*PATTERNS[key]],target);run(['git','checkout','--detach','FETCH_HEAD'],target)
        assert run(['git','rev-parse','HEAD'],target).strip()==PINS[key]
    outcomes={}
    for key,script in [('manager','scripts/integrations/discovery-lab-native-test.mjs'),('jobs','integrations/alpha-agent/discovery-lab-native-test.mjs')]:
        command=['node',str(root/key/script),str(root/'alpha')]
        if key=='jobs':command.append(str(root/'shared-workspace.json'))
        started=time.perf_counter();raw=run(command);elapsed=time.perf_counter()-started;(root/f'{key}-native.json').write_text(raw);value=json.loads(raw)
        if key=='manager':(root/'shared-workspace.json').write_text(json.dumps(value['retainedWorkspace']))
        outcomes[key]={'elapsedSeconds':elapsed,'route':value['route'],'workspaceDigest':value['workspaceDigest'],'states':[(item['case'],item['receipt']['state']) for item in value['outcomes']],'authority':value['authority'],'capBaseUnits':value['currencyCapBaseUnits']}
    assert outcomes['manager']['workspaceDigest']==outcomes['jobs']['workspaceDigest'];(root/'summary.json').write_text(json.dumps(outcomes,indent=2)+'\n');print(json.dumps(outcomes,indent=2))

if __name__=='__main__':main()
