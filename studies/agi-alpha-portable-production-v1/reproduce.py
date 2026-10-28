# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations
import argparse, hashlib, json, shutil, subprocess, sys
from pathlib import Path
from verify_study import frozen_errors

ROOT=Path(__file__).resolve().parent

def main() -> None:
    p=argparse.ArgumentParser(description='Reproduce known study cases in a new directory; preserves original evidence.')
    p.add_argument('destination',type=Path);a=p.parse_args()
    if a.destination.exists():raise SystemExit('Refusing an existing destination; choose a new directory.')
    errors=frozen_errors(ROOT)
    if errors:raise SystemExit('REFUSED: '+'; '.join(errors))
    work=a.destination.resolve()/'study';work.mkdir(parents=True)
    for name in ['src','protocol','data']:
        shutil.copytree(ROOT/name,work/name)
    for name in ['verify_confirmation.py','verify_study.py']:
        shutil.copy2(ROOT/name,work/name)
    shutil.copytree(ROOT/'evidence/history',work/'evidence/history')
    shutil.copy2(ROOT/'evidence/HISTORICAL_SEAL.json',work/'evidence/HISTORICAL_SEAL.json')
    commands=[
      [sys.executable,str(work/'src/produce.py'),'--source-dir',str(work/'data/public'),'--output',str(work/'results/construction_v1_2')],
      [sys.executable,str(work/'verify_confirmation.py')],
      [sys.executable,str(work/'verify_study.py'),'--output',str(work/'evidence/final_verification.json')]
    ]
    for command in commands:subprocess.run(command,check=True)
    result={'status':'PASS','destination':str(work),'verifier_sha256':hashlib.sha256((work/'verify_study.py').read_bytes()).hexdigest(),'reproducer_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'historical_archive':'Preserved records sealed after original execution; no preregistration claim.','interpretation':'Reproduction of known public and disclosed fresh cases, not a new prospective trial. STEP headers and elapsed times may vary; semantic checks are the reproducibility target.'}
    (a.destination/'REPRODUCTION.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))

if __name__=='__main__':main()
