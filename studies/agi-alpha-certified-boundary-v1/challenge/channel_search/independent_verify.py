import itertools,json,hashlib
from pathlib import Path

ROOT=Path(__file__).resolve().parent
def audit(path):
    raw=path.read_bytes();data=json.loads(raw);points=data.get('points',data.get('best_points',[]));q=data.get('q',15);dimension=data.get('dimension',3)
    valid_shape=bool(points) and all(isinstance(p,list) and len(p)==dimension and all(type(x)==int and 0<=x<q for x in p) for p in points)
    if not valid_shape:return {'file':path.name,'accepted':False,'reason':'shape or range'}
    unique=len({tuple(p) for p in points})==len(points)
    collision=[]
    for i,p in enumerate(points):
        for j in range(i):
            if not any(min(abs(x-y),q-abs(x-y))>=2 for x,y in zip(p,points[j])):collision.append([i,j])
    inverse={};overlaps=[]
    for i,p in enumerate(points):
        for noise in itertools.product((0,1),repeat=dimension):
            output=tuple((x+z)%q for x,z in zip(p,noise))
            if output in inverse and inverse[output]!=i:overlaps.append([i,inverse[output]])
            inverse[output]=i
    roundtrips=sum(inverse[tuple((x+z)%q for x,z in zip(p,noise))]==i for i,p in enumerate(points) for noise in itertools.product((0,1),repeat=dimension))
    refusals=sum(tuple(out) not in inverse for out in itertools.product(range(q),repeat=dimension))
    return {'file':path.name,'sha256':hashlib.sha256(raw).hexdigest(),'accepted':unique and not collision and not overlaps,'messages':len(points),'pairs_checked':len(points)*(len(points)-1)//2,'confusable_pairs':collision,'channel_output_collisions':overlaps,'accepted_output_words':len(inverse),'roundtrips':roundtrips,'refused_output_words':refusals,'channel_model':'Each coordinate outputs input or input+1 modulo q; no stronger error model is certified'}

if __name__=='__main__':
    paths=[ROOT/'c15_3_published383.json',ROOT/'global_milp.json']+sorted(ROOT.glob('local_search_seed*.json'))+sorted(ROOT.glob('c15_3_best_seed*.json'))
    reports=[audit(p) for p in paths if p.exists()]
    controls=[]
    base=json.loads((ROOT/'c15_3_published383.json').read_text())
    for name,points in [('duplicate',base['points']+[base['points'][0]]),('out_of_range',[[15,0,0]]),('confusable',[[0,0,0],[1,1,1]])]:
        p=ROOT/f'negative_{name}.json';p.write_text(json.dumps({'q':15,'dimension':3,'points':points}));r=audit(p);controls.append({'case':name,'correct_refusal':not r['accepted']})
    result={'positive_reports':reports,'negative_controls':controls,'all_pass':all(r['accepted'] for r in reports) and all(x['correct_refusal'] for x in controls)}
    (ROOT/'independent_verification.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
