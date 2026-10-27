import argparse,collections,functools,hashlib,itertools,json,pathlib,random,time
ROOT=pathlib.Path(__file__).resolve().parent

def bits(n): return list(itertools.product((0,1),repeat=n))
def project(state,n): return tuple(state[i] for i in ({2:[0,2],3:[0,1,2],4:[0,1,2,3]}[n]))
def expand(state):
    if len(state)==2: return (state[0],0,state[1],0)
    if len(state)==3: return (*state,0)
    return tuple(state)

def make_model(n,cfg,rng=None,coupling=None):
    idx={2:[0,2],3:[0,1,2],4:[0,1,2,3]}[n]
    d=cfg['tolerance_half_width']
    def draw(v): return v if rng is None else v+rng.randint(-d,d)
    C=[[0]*n for _ in range(n)]
    for i,j in [(0,2),(1,3)]:
        if i in idx and j in idx:
            v=draw(cfg['coupling'] if coupling is None else coupling)
            C[idx.index(i)][idx.index(j)]=C[idx.index(j)][idx.index(i)]=v
    A=[cfg['high_drive'],0,0,cfg['low_drive']]
    B=[0,cfg['high_drive'],cfg['low_drive'],0]
    A=[draw(A[i]) if A[i] else 0 for i in idx]
    B=[draw(B[i]) if B[i] else 0 for i in idx]
    return {'n':n,'C':C,'up':[draw(cfg['up_threshold']) for _ in idx],'down':[draw(cfg['down_threshold']) for _ in idx],
        'fields':{'A':A,'B':B,'C':[a+b for a,b in zip(A,B)],'R':[draw(cfg['reset_drive']) for _ in idx],'0':[0]*n}}

def unstable(model,state,field):
    out=[]
    for i in range(model['n']):
        force=field[i]+sum(c*s for c,s in zip(model['C'][i],state))
        if (state[i]==0 and force>=model['up'][i]) or (state[i]==1 and force<=model['down'][i]): out.append(i)
    return out

def all_orders(model,start,field):
    graph={}; stack=[start]
    while stack:
        s=stack.pop()
        if s in graph: continue
        nxt=[]
        for i in unstable(model,s,field):
            t=tuple(1-v if k==i else v for k,v in enumerate(s)); nxt.append(t)
            if t not in graph: stack.append(t)
        graph[s]=nxt
    colors={}; cycle=False
    def visit(s):
        nonlocal cycle
        if colors.get(s)==1: cycle=True; return
        if colors.get(s)==2: return
        colors[s]=1
        for t in graph[s]: visit(t)
        colors[s]=2
    visit(start)
    terminal=tuple(sorted(s for s,nxt in graph.items() if not nxt))
    @functools.lru_cache(None)
    def paths(s): return 1 if not graph[s] else sum(paths(t) for t in graph[s])
    min_drop=None
    for s,nxt in graph.items():
        for t in nxt:
            delta=energy(model,t,field)-energy(model,s,field)
            min_drop=-delta if min_drop is None else min(min_drop,-delta)
    return {'terminals':terminal,'cycle':cycle,'states':len(graph),'edges':sum(map(len,graph.values())),
        'race_states':sum(len(v)>1 for v in graph.values()),'paths':None if cycle else paths(start),'min_energy_drop':min_drop}

def energy(model,state,field):
    return -sum(h*s for h,s in zip(field,state))-sum(model['C'][i][j]*state[i]*state[j] for i in range(model['n']) for j in range(i+1,model['n']))

def pulse(model,state,event):
    first=all_orders(model,state,model['fields'][event]); terminal=set(); cycle=first['cycle']
    for s in first['terminals']:
        second=all_orders(model,s,model['fields']['0']); terminal.update(second['terminals']); cycle|=second['cycle']
    return tuple(sorted(terminal)),cycle

def oracle(state,event):
    x,y,z,w=expand(state)
    if event=='R': return (0,)*len(state)
    a=event in ('A','C'); b=event in ('B','C')
    new=(int(x or a),int(y or b),int(z or (b and (x or a))),int(w or (a and (y or b))))
    return project(new,len(state))

def monotone_control(model,state,event):
    s=state
    for label in [event,'0']:
        for _ in range(2**model['n']+1):
            flips=unstable(model,s,model['fields'][label])
            if not flips: break
            s=tuple(1-v if i in flips else v for i,v in enumerate(s))
        else: raise ValueError('parallel closure did not terminate')
    return s

def table(model): return {(s,e):pulse(model,s,e) for s in bits(model['n']) for e in ['A','B','C','R']}
def run_word(tab,n,word):
    states={(0,)*n}
    for e in word:
        out=set()
        for s in states:
            terminal,cycle=tab[s,e]
            if cycle: return (),True
            out.update(terminal)
        states=out
    return tuple(sorted(states)),False

def expected_word(n,word):
    state=(0,)*n
    for e in word: state=oracle(state,e)
    return state

def audit(model):
    reports=[all_orders(model,s,h) for s in bits(model['n']) for h in model['fields'].values()]
    tab=table(model)
    return {'state_field_cases':len(reports),'nonconfluent':sum(len(r['terminals'])!=1 or r['cycle'] for r in reports),
        'race_cases':sum(r['race_states']>0 for r in reports),'max_update_paths':max((r['paths'] or 0) for r in reports),
        'min_energy_drop':min(r['min_energy_drop'] for r in reports if r['min_energy_drop'] is not None),
        'oracle_mismatch':sum(cycle or end!=(oracle(s,e),) for (s,e),(end,cycle) in tab.items()),
        'monotone_control_mismatch':sum(cycle or end!=(monotone_control(model,s,e),) for (s,e),(end,cycle) in tab.items())},tab

def run():
    cfg=json.loads((ROOT/'config.json').read_text()); freeze=json.loads((ROOT/'freeze.json').read_text())
    config_hash=hashlib.sha256((ROOT/'config.json').read_bytes()).hexdigest()
    if config_hash!=freeze['config_sha256']: raise RuntimeError('frozen configuration changed')
    start=time.perf_counter(); rng=random.Random(cfg['confirmation_seed']); summaries=[]; models=[]; traces={}
    random_words=[''.join(rng.choice(cfg['full_word_alphabet']) for _ in range(rng.randint(1,cfg['confirmation_max_length']))) for _ in range(cfg['confirmation_random_words'])]
    for n in cfg['dimensions']:
        m=make_model(n,cfg); models.append(m); a,tab=audit(m)
        counts={'words':0,'oracle_mismatch':0,'nonconfluent':0}
        for length in range(cfg['full_word_max_length']+1):
            for seq in itertools.product(cfg['full_word_alphabet'],repeat=length):
                end,cycle=run_word(tab,n,seq); counts['words']+=1
                counts['nonconfluent']+=int(cycle or len(end)!=1)
                counts['oracle_mismatch']+=int(end!=(expected_word(n,seq),))
        fresh_bad=sum(run_word(tab,n,w)!=( (expected_word(n,w),),False) for w in random_words)
        indep=make_model(n,cfg,coupling=0); itab=table(indep)
        mutation=make_model(n,cfg,coupling=35); mtab=table(mutation)
        traces[str(n)]={w:{'states':[''.join(map(str,s)) for s in run_word(tab,n,w)[0]],'cycle':run_word(tab,n,w)[1]} for w in ['','A','B','AB','BA','C','ABA','BAB','ABR','BAR','RAB','RBA']}
        summaries.append({'n':n,'audit':a,'exhaustive_words':counts,'fresh_random_words':len(random_words),'fresh_failures':fresh_bad,
            'independent_control':{'AB':run_word(itab,n,'AB')[0],'BA':run_word(itab,n,'BA')[0],'distinguishes_order':run_word(itab,n,'AB')!=run_word(itab,n,'BA')},
            'weak_coupling_falsifier':{'coupling':35,'AB':run_word(mtab,n,'AB')[0],'BA':run_word(mtab,n,'BA')[0],'distinguishes_order':run_word(mtab,n,'AB')!=run_word(mtab,n,'BA')}})
    tolerance={'draws':cfg['tolerance_draws'],'state_field_cases':0,'nonconfluent':0,'oracle_mismatch':0,'monotone_control_mismatch':0,'min_energy_drop':None}
    for _ in range(cfg['tolerance_draws']):
        for n in cfg['dimensions']:
            m=make_model(n,cfg,rng); a,_=audit(m)
            for k in ['state_field_cases','nonconfluent','oracle_mismatch','monotone_control_mismatch']: tolerance[k]+=a[k]
            tolerance['min_energy_drop']=a['min_energy_drop'] if tolerance['min_energy_drop'] is None else min(tolerance['min_energy_drop'],a['min_energy_drop'])
    bad={'n':2,'C':[[0,-120],[-120,0]],'up':[100,100],'down':[-80,-80]}
    race=all_orders(bad,(0,0),(110,110))
    cyc={'n':2,'C':[[0,-200],[200,0]],'up':[100,100],'down':[0,0]}
    cycle=all_orders(cyc,(0,0),(110,-10))
    d=cfg['tolerance_half_width']; margins={'high_switch':cfg['high_drive']-d-(cfg['up_threshold']+d),
        'gated_switch':cfg['coupling']-d+cfg['low_drive']-d-(cfg['up_threshold']+d),
        'single_input_stays_off':cfg['up_threshold']-d-max(cfg['coupling']+d,cfg['low_drive']+d),
        'retention':0-(cfg['down_threshold']+d),
        'reset':cfg['down_threshold']-d-(cfg['reset_drive']+d+cfg['coupling']+d)}
    result={'study':cfg['study'],'config_sha256':config_hash,'script_sha256':hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest(),
        'freeze':freeze,'evidence_class':cfg['evidence_class'],'units':'integer units / 100 dimensionless field',
        'models':summaries,'witnesses':traces,'tolerance':tolerance,'analytic_box_margins':margins,
        'negative_controls':{'antiferromagnetic_race':race,'asymmetric_cycle':cycle},
        'novelty_verdict':'REJECT AS FLAGSHIP: known ferromagnetic monotone closure exactly matches; sequential/vectorial memory and event recorders pre-exist; no demonstrated substantive advance',
        'elapsed_seconds':time.perf_counter()-start}
    (ROOT/'models.json').write_text(json.dumps(models,indent=2)+'\n')
    (ROOT/'results.json').write_text(json.dumps(result,indent=2)+'\n')
    (ROOT/'confirmation_words.json').write_text(json.dumps(random_words,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ['models','tolerance','analytic_box_margins','negative_controls','novelty_verdict','elapsed_seconds']},indent=2))
    return result

if __name__=='__main__': run()
