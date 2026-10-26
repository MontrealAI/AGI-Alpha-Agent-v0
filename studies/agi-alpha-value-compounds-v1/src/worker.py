# SPDX-License-Identifier: Apache-2.0
"""Fixed local assessment worker; accepts registered mission identifiers only."""
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
from pipeline import ROOT,assess,load_mission,encoded,sha

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True);parser.add_argument('--cache',type=Path,required=True)
    args=parser.parse_args();args.out.mkdir(parents=True,exist_ok=True)
    sequence=0
    for line in sys.stdin:
        if len(line)>2048: raise ValueError('REQUEST_BOUND')
        request=json.loads(line)
        if set(request)!={'mission','arm','reuse'} or not isinstance(request['reuse'],bool): raise ValueError('REQUEST_SCHEMA')
        item,before,after,consumers=load_mission(request['mission'])
        report=assess(before,after,repository=item['repository'],before_ref=item['before_ref'],after_ref=item['after_ref'],consumer_files=consumers,arm=request['arm'],cache_dir=args.cache if request['reuse'] else None)
        sequence+=1;path=args.out/f'{sequence:04d}-{request["mission"]}-{request["arm"]}.json';raw=encoded(report)+b'\n';path.write_bytes(raw)
        print(json.dumps({'path':str(path.resolve()),'sha256':sha(raw),'bytes':len(raw),'status':report['status']}),flush=True)
if __name__=='__main__':main()
