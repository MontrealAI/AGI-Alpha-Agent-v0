import json,argparse
from pathlib import Path

def run(spec,trace):
    patterns=spec['patterns'] if isinstance(spec,dict) else spec
    records=[]
    for row in trace:
        if isinstance(row,dict): records.append((row['events'],bool(row.get('rst',False))))
        else: records.append((row,False))
    result=[]; last_reset=-1
    for t,(events,reset) in enumerate(records):
        if reset: last_reset=t
        accepted=0
        for index,p in enumerate(patterns):
            anchor=t-p['deadline']
            if anchor<=last_reset or anchor<0: continue
            if not records[anchor][0]&(1<<p['a']): continue
            if any(records[v][0]&(1<<p['veto']) for v in range(anchor,t+1)): continue
            first=[b for b in range(anchor+p['l1'],anchor+p['u1']+1) if records[b][0]&(1<<p['b'])]
            second=[c for c in range(anchor+p['l1']+p['l2'],anchor+p['u1']+p['u2']+1) if records[c][0]&(1<<p['c'])]
            if any(p['l2']<=c-b<=p['u2'] for b in first for c in second): accepted|=1<<index
        result.append(accepted)
    return result

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--spec',required=True);ap.add_argument('--trace',required=True);ap.add_argument('--output',required=True);a=ap.parse_args()
    Path(a.output).write_text(json.dumps(run(json.loads(Path(a.spec).read_text()),json.loads(Path(a.trace).read_text())))+'\n')

if __name__=='__main__':main()
