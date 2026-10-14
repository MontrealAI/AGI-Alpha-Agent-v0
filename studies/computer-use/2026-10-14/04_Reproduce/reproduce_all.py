from pathlib import Path
import argparse,shutil,subprocess,sys,json,hashlib
source=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--output',required=True);args=p.parse_args();dest=Path(args.output).resolve()
if dest.exists() or dest.is_relative_to(source):raise SystemExit('Use a new destination outside the source package.')
shutil.copytree(source,dest,ignore=shutil.ignore_patterns('__pycache__','.venv'))
commands=[['browser_acceptance.py','--tasks','A','B','--variants','before','after'],['browser_acceptance.py','--tasks','B','--variants','without-portability-fix'],['recovery_tests.py'],['owner_effort.py']]
for cmd in commands:subprocess.run([sys.executable,str(dest/'04_Reproduce'/cmd[0]),*cmd[1:]],check=True)
files={p.relative_to(dest).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()for p in sorted(dest.rglob('*'))if p.is_file() and '__pycache__' not in p.parts and p.name!='MANIFEST.json'}
(dest/'MANIFEST.json').write_text(json.dumps({'schema':'study-package-manifest/v1','notice':'Replay manifest. Included narrative is the original report; inspect refreshed raw results.','files':files},indent=2)+'\n')
print('Replay complete:',dest)
