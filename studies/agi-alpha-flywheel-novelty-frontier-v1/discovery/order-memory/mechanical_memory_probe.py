import argparse,collections,hashlib,itertools,json,pathlib

def encode(word, edges):
    rank={x:i for i,x in enumerate(word)}
    return tuple(int(rank[a]<rank[b]) for a,b in edges)

def recover(observation, edges, names, parity=False):
    survivors=[]
    for word in itertools.permutations(names):
        valid=True
        for k,(a,b) in enumerate(edges):
            if observation[k] is None: continue
            before=next(x for x in word if x in (a,b))
            if (before==a)!=bool(observation[k]): valid=False;break
        if not valid: continue
        if parity and observation[-1] is not None:
            inversions=sum(word[i]>word[j] for i in range(len(word)) for j in range(i+1,len(word)))
            if (len(edges)-inversions)%2!=observation[-1]: continue
        survivors.append(''.join(word))
    return survivors

def run():
    names=tuple('ABCD'); cycle=(('A','B'),('B','C'),('C','D'),('D','A')); complete=tuple(itertools.combinations(names,2))
    words=list(itertools.permutations(names)); groups=collections.defaultdict(list)
    for word in words: groups[str(encode(word,cycle))].append(''.join(word))
    rows=[]; paired={}; coded={}
    for word in words:
        key=''.join(word); bits=encode(word,complete); paired[key]=bits; coded[key]=bits+(sum(bits)%2,)
        for scheme,code,has_parity in [('pairwise',bits,False),('pairwise_plus_xor',coded[key],True)]:
            for erased in range(len(code)):
                observation=list(code);observation[erased]=None
                survivors=recover(observation,complete,names,has_parity)
                assert key in survivors
                rows.append({'scheme':scheme,'history':key,'erased_index':erased,'recovery_set':survivors,'unique':len(survivors)==1})
    summary={}
    for scheme in ('pairwise','pairwise_plus_xor'):
        rs=[r for r in rows if r['scheme']==scheme]
        summary[scheme]={'cases':len(rs),'unique_recoveries':sum(r['unique'] for r in rs),'ambiguous_recoveries':sum(not r['unique'] for r in rs),'fraction_unique':sum(r['unique'] for r in rs)/len(rs),'histories_with_some_ambiguous_erasure':len({r['history'] for r in rs if not r['unique']})}
    assert len(groups)==14
    assert summary['pairwise']['ambiguous_recoveries']==72
    assert summary['pairwise_plus_xor']['ambiguous_recoveries']==0
    result={'evidence_label':'exhaustive_abstract_discrete_computation; no material built; ordinary coding repair not discovery','parameters':{'events':list(names),'cycle_edges':cycle,'complete_edges':complete,'seed':None,'randomness':'none; all permutations and erasure locations enumerated'},'cycle_readout_classes':dict(groups),'cycle_distinct_readouts':len(groups),'full_pairwise_distinct_readouts':len(set(paired.values())),'minimum_hamming_distance_pairwise':min(sum(x!=y for x,y in zip(a,b)) for a,b in itertools.combinations(paired.values(),2)),'minimum_hamming_distance_with_parity':min(sum(x!=y for x,y in zip(a,b)) for a,b in itertools.combinations(coded.values(),2)),'single_erasure_results':summary,'pairwise_only_lower_bound_bits_for_single_erasure':12,'parity_code_bits':7,'lower_bound_argument':'Every unordered event pair can be adjacent in some history. Exchanging adjacent events changes only that pairwise relation. If that pair has fewer than two independent stored copies, erasing it makes those two histories indistinguishable. Hence every one of the six pairs must be stored twice in the pairwise-only class.','parity_repair_boundary':'XOR is a conventional one-erasure-correcting code. Seven abstract stored bits are not seven proven physical devices. Mechanical realizability, couplers, ancillas, readout burden, fabrication tolerances, timing, wear and manufacturing cost are unmeasured. This code is not a substantive discovery beyond coding prior art.','oracle':'Independent enumerator uses explicit precedence constraints and permutation inversion parity, not the encoder function.','assumptions':['Each of four labeled events occurs exactly once.','Each binary pairwise recorder faithfully reports which endpoint occurred first.','One known erasure; no unmarked substitutions or two erasures.','All six recorder outputs and optional parity are available after the sequence.','No physical material dynamics or fabrication model is claimed.'],'code_sha256':hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest(),'cases':rows}
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',default=str(pathlib.Path(__file__).with_name('mechanical_memory_probe.json')));a=p.parse_args();r=run();pathlib.Path(a.output).write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items() if k not in ('cases','cycle_readout_classes')},indent=2))
