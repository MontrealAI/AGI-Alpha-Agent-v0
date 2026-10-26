# SPDX-License-Identifier: Apache-2.0
"""Register customer-supplied public snapshots without importing their source."""
from __future__ import annotations
import argparse,json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from pipeline import source_tree,sha,encoded

def main():
 p=argparse.ArgumentParser();p.add_argument('--id',required=True);p.add_argument('--repository',required=True);p.add_argument('--before-ref',required=True);p.add_argument('--after-ref',required=True);p.add_argument('--before-dir',required=True);p.add_argument('--after-dir',required=True);p.add_argument('--consumer-dir',action='append',required=True);a=p.parse_args()
 if not re.fullmatch(r'[a-z0-9][a-z0-9-]{1,63}',a.id):raise ValueError('MISSION_ID')
 if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',a.repository):raise ValueError('PUBLIC_REPOSITORY_NAME')
 if not all(re.fullmatch(r'[0-9a-f]{40}',x) for x in [a.before_ref,a.after_ref]):raise ValueError('EXACT_COMMIT_REQUIRED')
 def read(relative):
  path=(ROOT/relative).resolve()
  if not path.is_relative_to(ROOT/'data'):raise ValueError('INPUT_MUST_BE_UNDER_DATA')
  return source_tree(path)
 item={'repository':a.repository,'before_ref':a.before_ref,'after_ref':a.after_ref,'before_dir':a.before_dir,'after_dir':a.after_dir,'consumers':a.consumer_dir,'role':'customer-supplied-local-assessment','source_identity_qualification':'Byte hashes verified locally; supplier must provide independently verified Git source custody.'}
 for key in ['before_dir','after_dir']:item[key+'_inventory_sha256']=sha(encoded({k:sha(v.encode()) for k,v in read(item[key]).items()}))
 item['consumer_inventory_sha256']=sha(encoded({p+'/'+k:sha(v.encode()) for p in a.consumer_dir for k,v in read(p).items()}))
 registry=ROOT/'data/missions.json';value=json.loads(registry.read_text())
 if a.id in value['missions']:raise ValueError('MISSION_ALREADY_REGISTERED')
 value['missions'][a.id]=item;registry.write_bytes(encoded(value)+b'\n');print(json.dumps({'registered':a.id,'next_command':f'node src/workbench.mjs {a.id} conventional results/{a.id}','qualification':item['source_identity_qualification']}))
if __name__=='__main__':main()
