#!/usr/bin/env python3
"""Check only the allowed source packets. Optional SciPy REML uses 19 rows conditionally."""
from pathlib import Path
import shlex, json, math, hashlib
BASE=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
SOURCES=[
 "data/sources/metadat/data-raw/dat.bangertdrowns2004.r",
 "data/sources/metadat/data-raw/dat.bangertdrowns2004.txt",
 "data/sources/metadat/man/dat.bangertdrowns2004.Rd",
 "data/sources/metadat/data-raw/dat.raudenbush1985.r",
 "data/sources/metadat/data-raw/dat.raudenbush1985.txt",
 "data/sources/metadat/man/dat.raudenbush1985.Rd",
 "data/sources/crop_conflict/raw_data/readme",
 "data/sources/crop_conflict/network_meta_analysis.qmd"]
def table(rel):
    lines=(BASE/rel).read_text().splitlines()
    names=shlex.split(lines[0])
    return [dict(zip(names,shlex.split(line),strict=True)) for line in lines[1:] if line.strip()]
def reml(rows):
    try:
        from scipy.optimize import minimize_scalar
    except ImportError:
        return {"status":"not run: optional SciPy dependency unavailable"}
    y=[float(r['yi']) for r in rows]; v=[float(r['vi']) for r in rows]
    def evaluate(t):
        weights=[1/(a+t) for a in v]; sw=sum(weights)
        mu=sum(a*b for a,b in zip(weights,y))/sw
        q=sum(a*(b-mu)**2 for a,b in zip(weights,y))
        nll=.5*(sum(math.log(a+t) for a in v)+math.log(sw)+q)
        return nll,mu,1/math.sqrt(sw)
    bound=1.
    fit=minimize_scalar(lambda t:evaluate(t)[0],bounds=(0,bound),method='bounded',options={'xatol':1e-13})
    while fit.x>.95*bound:
        bound*=4
        fit=minimize_scalar(lambda t:evaluate(t)[0],bounds=(0,bound),method='bounded',options={'xatol':1e-13})
    assert fit.success
    tau2=min([0.,float(fit.x)],key=lambda t:evaluate(t)[0])
    _,mu,se=evaluate(tau2)
    return {"status":"computed; conditional on independent rows and supplied variances", "k":len(rows),"mu":mu,"tau2":tau2,"se_mu_conditional":se,"wald_95_ci":[mu-1.959963984540054*se,mu+1.959963984540054*se],"method":"scalar minimization of intercept-only restricted Gaussian likelihood; tau2 >= 0, boundary compared explicitly"}
teacher=table(SOURCES[4]); writing=table(SOURCES[1]); crop=(BASE/SOURCES[7]).read_text()
assert len(teacher)==19 and len(writing)==48
assert [int(r['study']) for r in teacher]==list(range(1,20))
required=['study','author','year','weeks','setting','tester','n1i','n2i','yi','sei','vi']
assert set(teacher[0])==set(required)
assert all(r[c]!='NA' for r in teacher for c in required)
assert all(math.isfinite(float(r[c])) for r in teacher for c in ['weeks','n1i','n2i','yi','sei','vi'])
assert all(float(r['vi'])>0 and float(r['sei'])>0 and int(r['n1i'])>1 and int(r['n2i'])>1 and int(r['weeks'])>=0 for r in teacher)
assert set(r['setting'] for r in teacher)=={'group','indiv'}
assert set(r['tester'] for r in teacher)=={'aware','blind'}
assert all(round(float(r['sei'])**2,4)==float(r['vi']) for r in teacher)
repeated={}
for r in teacher:
    repeated.setdefault((r['author'],r['year']),[]).append(int(r['study']))
repeated={f'{k[0]} ({k[1]})':v for k,v in repeated.items() if len(v)>1}
assert repeated=={'Pellegrini & Hicks (1972)':[4,5]}
assert int(teacher[3]['n1i'])==int(teacher[4]['n1i'])==11
assert int(teacher[3]['n2i'])==int(teacher[4]['n2i'])==22
writing_derived=[{'id':int(r['id']),'yi':round((1-3/(4*int(r['ni'])-9))*float(r['di']),2)} for r in writing]
for r,d in zip(writing,writing_derived):
    d['vi']=round((8+d['yi']**2)/(2*int(r['ni'])),3)
assert all(d['vi']>0 for d in writing_derived)
assert 'sm="SMD"' in crop
assert 'data/yield_data.RDS' in crop
assert 'method.tau' not in crop
assert '3733' in crop and '3939' in crop and '3938' in crop and '3732' in crop
results={
 'source_hashes':{rel:hashlib.sha256((BASE/rel).read_bytes()).hexdigest() for rel in SOURCES},
 'teacher':{'row_count':len(teacher),'missing_required':0,'all_variances_positive':True,'vi_equals_sei_squared_rounded_to_4_decimals':True,'max_abs_vi_minus_sei_squared':max(abs(float(r['vi'])-float(r['sei'])**2) for r in teacher),'weeks_range':[min(int(r['weeks']) for r in teacher),max(int(r['weeks']) for r in teacher)],'weeks_zero_count':sum(int(r['weeks'])==0 for r in teacher),'unequal_arm_size_count':sum(int(r['n1i'])!=int(r['n2i']) for r in teacher),'repeated_author_year':repeated,'nominal_reml':reml(teacher),'exploratory_keep_study4_drop5':reml([r for r in teacher if r['study']!='5']),'exploratory_keep_study5_drop4':reml([r for r in teacher if r['study']!='4'])},
 'writing':{'row_count':len(writing),'reconstruction_formula':'yi=round((1-3/(4*ni-9))*di,2); vi=round((8+yi^2)/(2*ni),3)','first_row_reconstructed':writing_derived[0],'precision_note':'Python round uses ties-to-even; reproduction should be checked against R for any exact decimal-half boundary if authoritative binary identity is required.'},
 'crop':{'claimed_kg_ha_outcome':True,'computed_measure_in_source':'SMD','input_RDS_referenced_but_not_in_permitted_inputs':True,'explicit_REML_setting_in_notebook':False,'conflicting_counts_in_text':[3733,3939,3938,3732],'notebook_executed':False},
 'checks_status':'passed; source semantics and unresolved independence need human/source authority',
 'dependencies':'Python standard library; SciPy only for conditional numerical REML calculations'}
(OUT/'checks_results.json').write_text(json.dumps(results,indent=2)+'\n')
print(json.dumps(results,indent=2))
