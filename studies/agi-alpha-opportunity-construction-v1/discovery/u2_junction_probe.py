"""Bounded constructive probe; no clinical validation or GA4GH compliance claim.
Public fixture: https://vrs.ga4gh.org/en/2.1/model/MolecularVariation/Adjacency.html
Synthetic sequence fixtures exhaust all pairs of 5-base A/C strings.
Only forward-oriented, exact, unlinked junctions, with full reference strings.
"""
import itertools,json
from pathlib import Path

def normalize(a,b,x,y):
    lo=hi=0
    while x+lo>0 and y+lo>0 and a[x+lo-1]==b[y+lo-1]: lo-=1
    while x+hi<len(a) and y+hi<len(b) and a[x+hi]==b[y+hi]: hi+=1
    return (x+lo,y+lo,x+hi,y+hi)

def sequence(a,b,x,y): return a[:x]+b[y:]

def order_public_pair(pair):
    # Restricted normative VRS case: one end and one start; no linker.
    assert sorted(k for p in pair for k in ('start','end') if k in p)==['end','start']
    return sorted(pair,key=lambda p:0 if 'end' in p else 1)

public_pair=[
 {'refgetAccession':'SQ.9KdcA9ZpY1Cpvxvg8bMSLYDUpsX6GDLO','id':'NC_000002.11','start':456},
 {'refgetAccession':'SQ.S_KjnFVz-FE7M0W6yoaUDgYxLPc1jyWU','id':'NC_000001.10','end':123}]
ordered=order_public_pair(public_pair)
assert ordered==order_public_pair(list(reversed(public_pair)))
seqs=[''.join(x) for x in itertools.product('AC',repeat=5)]
cases=classes=ambiguous=0
for a,b in itertools.product(seqs,repeat=2):
    by_output={}
    for x,y in itertools.product(range(6),repeat=2):
        result=sequence(a,b,x,y); cert=normalize(a,b,x,y)
        by_output.setdefault(result,set()).add(cert)
        for shift in range(cert[2]-cert[0]+1):
            xx,yy=cert[0]+shift,cert[1]+shift
            assert sequence(a,b,xx,yy)==result
            assert normalize(a,b,xx,yy)==cert
        cases+=1;ambiguous+=cert[0]!=cert[2]
    assert all(len(v)==1 for v in by_output.values())
    classes+=len(by_output)
a,b,x,y='CAGT','GAGC',1,1
cert=normalize(a,b,x,y)
real=[(cert[0]+k,cert[1]+k) for k in range(cert[2]-cert[0]+1)]
cart=list(itertools.product(range(cert[0],cert[2]+1),range(cert[1],cert[3]+1)))
false=[{'coordinates':p,'sequence':sequence(a,b,*p)} for p in cart if sequence(a,b,*p)!=sequence(a,b,x,y)]
result={
 'public_source_probe':{'source':'https://vrs.ga4gh.org/en/2.1/model/MolecularVariation/Adjacency.html','fixture':'Published two-location Adjacency JSON, transcribed directly','ordered_locations':ordered,'input_order_invariance':True,'limitation':'Tests coordinate parsing and normative orientation only; no reference bases or biological truth were available. The public page caption conflicts with its normative start/end explanation; code follows normative text.'},
 'synthetic_exhaustive_probe':{'alphabet':'AC','reference_length':5,'reference_pairs':len(seqs)**2,'junction_cases':cases,'unique_sequence_classes':classes,'ambiguous_cases':ambiguous,'false_merges':0,'false_splits':0,'sequence_preservation':True,'idempotence':True},
 'cartesian_range_counterexample':{'a':a,'b':b,'input':[x,y],'target_sequence':sequence(a,b,x,y),'coupled_equivalent_coordinates':real,'independent_coordinate_combinations':len(cart),'false_combinations':false},
 'limits':['Synthetic, bounded exact strings; no human structural-variant callset evaluated.','No reverse-complement sequence processing, linker sequences, circular molecules, uncertain instrument ranges, or complex derivative molecules implemented.','No VRS digest calculated; output is an experimental certificate, not a standard VRS identifier.','Demonstrates a feasible mathematical subroutine and concrete representation hazard; neither novelty nor clinical utility is established.']}
Path(__file__).with_name('u2_junction_probe_results.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
