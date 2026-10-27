from pathlib import Path
import csv, hashlib, importlib.util, io, json, math, shlex, sys
sys.dont_write_bytecode = True
import numpy as np
from scipy.optimize import brentq
BASE = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent

def module(name):
    path=OUT/'inherited'/f'{name}.py'
    spec=importlib.util.spec_from_file_location(name,path)
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    return mod

continuity=module('continuity'); validator=module('mapping_validator')

def parse(rel):
    raw=(BASE/rel).read_bytes()
    lines=raw.decode().splitlines(); headers=shlex.split(lines[0]); records=[]
    for number,line in enumerate(lines[1:],2):
        if not line.strip(): continue
        cells=shlex.split(line)
        assert len(cells)==len(headers),(number,len(cells),len(headers))
        records.append(dict(zip(headers,cells)))
    stream=io.StringIO(newline='');w=csv.DictWriter(stream,fieldnames=headers,delimiter='\t',lineterminator='\n');w.writeheader();w.writerows(records)
    return raw,records,stream.getvalue().encode()

raw,records,normalized=parse('data/sources/metadat/data-raw/dat.raudenbush1985.txt')
(OUT/'teacher_source.tsv').write_bytes(normalized)
mapping={
 'purpose':'Conditional descriptive reproduction of average standardized IQ difference between expectancy-designated pupils and controls across the 19 supplied rows; no causal or practice verdict.',
 'effect_measure':'SMD','promised_units':'standard-deviation units',
 'effect_input':'Supplied yi from dat.raudenbush1985.txt; retain values without a second bias correction.',
 'variance_input':'Supplied vi from the same row, not sei and not an equal-arm recomputation.',
 'variance_derivation':'supplied_vi','equal_arms_supported':False,
 'time_meaning':'weeks = teacher-student contact before expectancy induction, not treatment or follow-up duration; year = publication year.',
 'dependence_limit':'Independent row errors are conditional, not demonstrated. Rows 4 and 5 share author/year/arm sizes but differ in tester; resolve cohort and covariance before unrestricted inference.',
 'authority_limit':'Current task authorizes local source inspection and checks; it does not confer deployment, publication, editorial or practice authority.',
 'retraction_decision_automatic':False,
 'original_source':'data/sources/metadat/data-raw/dat.raudenbush1985.txt',
 'original_source_sha256':hashlib.sha256(raw).hexdigest(),
 'normalization':'shlex preserves quoted authors; lossless cell strings written as UTF-8 TSV with header and unchanged row order; original row number = normalized row number.',
 'source_sha256':hashlib.sha256(normalized).hexdigest(),'delimiter':'\t','id_column':'study',
 'derivation':'supplied_yi_vi','yi_column':'yi','vi_column':'vi','expected_rows':19
}
(OUT/'fresh_mapping.json').write_text(json.dumps(mapping,indent=2)+'\n')
issues=validator.validate(mapping);assert issues==[],issues
rows=continuity.load_packet(normalized,mapping)
assert len(rows)==19 and [r['id'] for r in rows]==[str(i) for i in range(1,20)]
assert all(r['yi']==float(src['yi']) and r['vi']==float(src['vi']) for r,src in zip(rows,records))
sei_checks=[{'id':r['study'],'supplied_vi':float(r['vi']),'squared_sei':float(r['sei'])**2,'rounded_squared_sei':round(float(r['sei'])**2,4)} for r in records]
assert all(abs(x['rounded_squared_sei']-x['supplied_vi'])<1e-12 for x in sei_checks)
unequal=[r['study'] for r in records if int(r['n1i'])!=int(r['n2i'])]
fit=continuity.reml(rows)
y=np.array([r['yi'] for r in rows]);v=np.array([r['vi'] for r in rows])
def reml_score(t):
    w=1/(v+t);mu=float(np.dot(w,y)/w.sum())
    return .5*(w.sum()-(w*w).sum()/w.sum()-np.dot(w*w,(y-mu)**2))
upper=1.
while reml_score(upper)<0: upper*=2
reference_tau2=0. if reml_score(0.)>=0 else float(brentq(reml_score,0.,upper,xtol=1e-14))
weights=[1/(r['vi']+reference_tau2) for r in rows]
reference_estimate=math.fsum(w*r['yi'] for w,r in zip(weights,rows))/math.fsum(weights)
reference_se=math.sqrt(1/math.fsum(weights))
differences={'tau2':abs(fit['tau2']-reference_tau2),'estimate':abs(fit['estimate']-reference_estimate),'se':abs(fit['se']-reference_se)}
assert max(differences.values())<1e-7,differences
negative_units=validator.validate({**mapping,'promised_units':'kg/ha'})
assert 'standardized_effect_cannot_be_relabelled_as_physical_units' in negative_units
negative_arms=validator.validate({**mapping,'variance_derivation':'equal_arms_from_total_n'})
assert 'unsupported_equal_arm_assumption' in negative_arms
negative_hash=None
try: continuity.load_packet(normalized+b'\n',mapping)
except ValueError as exc: negative_hash=str(exc)
assert negative_hash=='Source identity changed; qualify a new packet'
old_raw,old_records,old_normalized=parse('data/sources/metadat/data-raw/dat.bangertdrowns2004.txt')
old_mapping={'source_sha256':hashlib.sha256(old_normalized).hexdigest(),'delimiter':'\t','id_column':'id','derivation':'bangert_secondary_equal_arms','expected_rows':48}
old_rows=continuity.load_packet(old_normalized,old_mapping)
assert len(old_rows)==48
for src,row in zip(old_records,old_rows):
    n=float(src['ni']);yy=round((1-3/(4*n-9))*float(src['di']),2);vv=round((8+yy*yy)/(2*n),3)
    assert row['yi']==yy and row['vi']==vv
results={
 'status':'passed','artifact_archive_sha256':hashlib.sha256((BASE/'integration/results/capability-v1/received-v2.zip').read_bytes()).hexdigest(),
 'actual_inherited_file_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (OUT/'inherited').iterdir() if p.is_file()},
 'fresh_mapping_validator_issues':issues,'teacher_rows':len(rows),'unique_ids':len({r['id'] for r in rows}),
 'direct_inputs_preserved':True,'positive_finite_variances':True,'sei_squared_round4_matches_supplied_vi':len(sei_checks),
 'max_abs_vi_minus_sei_squared':max(abs(x['supplied_vi']-x['squared_sei']) for x in sei_checks),
 'unequal_arm_ids':unequal,'unequal_arm_count':len(unequal),'weeks_range':[min(float(r['weeks']) for r in records),max(float(r['weeks']) for r in records)],
 'same_author_year_arm_sizes_ambiguity':{'ids':['4','5'],'author':'Pellegrini & Hicks','year':1972,'n1i':11,'n2i':22,'tester':['aware','blind'],'conclusion':'Neither independence nor duplication can be inferred from labels.'},
 'conditional_inherited_reml':fit,'independent_score_reference':{'tau2':reference_tau2,'estimate':reference_estimate,'se':reference_se,'absolute_differences':differences,'tolerance':1e-7},
 'negative_controls':{'smd_as_kg_ha':negative_units,'unsupported_equal_arms':negative_arms,'changed_source_hash':negative_hash},
 'writing_origin_requalification':{'rows':len(old_rows),'matches_supplied_R_formula_in_Python':True,'original_source_sha256':hashlib.sha256(old_raw).hexdigest(),'limitation':'Not a cross-runtime R rounding test; equal-arm assumption remains source-specific.'},
 'limitations':['The mapping validator checks selected fields and constraints; passing it does not establish provenance, semantic validity, independence, rights or scientific truth.','The independent analytic REML score check confirms numerical agreement, not validity of row independence.','No original primary-study reports, arm outcome SDs, cohort ledger, crop RDS, package lockfile or independent R/metafor execution were supplied or used.']
}
(OUT/'check_results.json').write_text(json.dumps(results,indent=2,allow_nan=False)+'\n')
print(json.dumps(results,indent=2,allow_nan=False))
