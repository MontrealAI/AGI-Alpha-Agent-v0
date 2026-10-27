import argparse,collections,gzip,hashlib,itertools,json,math,pathlib,time

def encode(word, edges, parity=False):
    rank={x:i for i,x in enumerate(word)}
    bits=tuple(int(rank[a]<rank[b]) for a,b in edges)
    return bits+(sum(bits)%2,) if parity else bits

def precedence_oracle(observation,edges,names,parity):
    predecessors={x:set() for x in names}
    for i,(a,b) in enumerate(edges):
        if observation[i] is None: continue
        if observation[i]: predecessors[b].add(a)
        else: predecessors[a].add(b)
    survivors=[]
    def visit(prefix,remaining):
        if not remaining:
            if parity and observation[-1] is not None:
                inversions=sum(prefix[i]>prefix[j] for i in range(len(prefix)) for j in range(i+1,len(prefix)))
                if (len(edges)-inversions)%2!=observation[-1]: return
            survivors.append(''.join(prefix));return
        for x in sorted(remaining):
            if not (predecessors[x]&remaining):visit(prefix+(x,),remaining-{x})
    visit((),set(names))
    return survivors

def ordinary_library_repair(observation,edges,names):
    repaired=list(observation)
    missing=[i for i,b in enumerate(repaired) if b is None]
    if len(missing)>1:return None
    if missing:repaired[missing[0]]=sum(x for x in repaired if x is not None)%2
    elif sum(repaired)%2:return None
    return precedence_oracle(repaired,edges,names,True)

def evaluate(n,case_sink):
    names=tuple(chr(65+i) for i in range(n));edges=tuple(itertools.combinations(names,2));m=len(edges)
    summary={'n':n,'histories':math.factorial(n),'pairwise_bits':m,'xor_bits':m+1,'pairwise_duplication_lower_bound_bits':2*m,'schemes':{}}
    for has_parity in (False,True):
        label='pairwise_plus_xor' if has_parity else 'pairwise'
        counts={1:collections.Counter(),2:collections.Counter()};bad_histories={1:set(),2:set()};examples={};detected=0;flips=0;ties=0
        for word in itertools.permutations(names):
            key=''.join(word);code=encode(word,edges,has_parity)
            for n_erasures in (1,2):
                for erased in itertools.combinations(range(len(code)),n_erasures):
                    observation=list(code)
                    for i in erased:observation[i]=None
                    survivors=precedence_oracle(observation,edges,names,has_parity)
                    assert key in survivors
                    outcome='unique' if len(survivors)==1 else 'ambiguous'
                    counts[n_erasures][outcome]+=1
                    if outcome=='ambiguous':bad_histories[n_erasures].add(key);examples.setdefault(str(n_erasures),{'history':key,'erased':erased,'recovery_set':survivors})
                    if has_parity and n_erasures==1:
                        library=ordinary_library_repair(observation,edges,names)
                        assert library==survivors;ties+=1
                    case_sink({'n':n,'scheme':label,'history':key,'erased':erased,'recovery_set':survivors})
            if has_parity:
                for i in range(len(code)):
                    corrupted=list(code);corrupted[i]^=1;flips+=1
                    detected+=sum(corrupted)%2==1
        row={'erasures':{str(k):{'cases':sum(v.values()),'unique':v['unique'],'ambiguous':v['ambiguous'],'histories_with_adversarial_ambiguity':len(bad_histories[k]),'example':examples.get(str(k))} for k,v in counts.items()}}
        if has_parity:
            x=names;y=(names[1],names[0])+names[2:];cx=encode(x,edges,True);cy=encode(y,edges,True)
            observation=list(cx);observation[0]^=1
            dx=sum(a!=b for a,b in zip(observation,cx));dy=sum(a!=b for a,b in zip(observation,cy))
            assert dx==dy==1
            row.update({'ordinary_identical_information_library_ties':ties,'single_bit_substitutions_tested':flips,'single_bit_substitutions_detected':detected,'single_substitution_not_correctable_witness':{'history_1':''.join(x),'history_2':''.join(y),'received':observation,'distance_to_history_1':dx,'distance_to_history_2':dy},'physical_implementation':False})
            assert row['erasures']['1']['unique']==math.factorial(n)*(m+1)
            assert row['erasures']['2']['ambiguous']>0
            assert detected==flips
        else:assert row['erasures']['1']['ambiguous']==math.factorial(n)*(n-1)
        summary['schemes'][label]=row
    return summary

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--config',required=True);parser.add_argument('--output-dir',required=True);a=parser.parse_args()
    config_path=pathlib.Path(a.config);config=json.loads(config_path.read_text());out=pathlib.Path(a.output_dir);out.mkdir(parents=True,exist_ok=True)
    code_hash=hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest();config_hash=hashlib.sha256(config_path.read_bytes()).hexdigest()
    assert code_hash==config['frozen_source_sha256']
    started=time.time();digest=hashlib.sha256();rows=[]
    with gzip.GzipFile(filename=str(out/'transfer_cases.jsonl.gz'),mode='wb',mtime=0) as case_file:
        def sink(row):
            line=(json.dumps(row,sort_keys=True,separators=(',',':'))+'\n').encode();digest.update(line);case_file.write(line)
        for n in config['new_validation_sizes']:rows.append(evaluate(n,sink))
    result={'label':'fresh-size exhaustive mathematical validation; not blind discovery, physical performance, human comparison or earned revenue','configuration_sha256':config_hash,'source_sha256':code_hash,'case_stream_sha256':digest.hexdigest(),'wall_seconds_measured':time.time()-started,'results':rows,'interpretation':{'operational_alpha':'unmeasured; no ordinary-user versus expert frontier-model trial was run','retained_alpha':'technical reuse succeeds on new event counts but an ordinary library with identical information ties on every one-erasure recovery; no superiority or financial net Alpha established','novelty':'standard parity construction; no discovery beyond coding prior art','physical_transfer':'unmeasured; bits, couplings and fabrication are different resources'}}
    (out/'transfer_results.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
