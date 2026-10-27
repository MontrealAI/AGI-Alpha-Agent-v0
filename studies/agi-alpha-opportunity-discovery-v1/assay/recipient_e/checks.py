import json, shlex, hashlib, math, shutil, subprocess, sys
from pathlib import Path
from datetime import datetime, timezone
import numpy as np
import scipy
from scipy.optimize import minimize_scalar, brentq
from scipy.stats import norm, chi2
BASE=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
SOURCE_PATHS=["assay/expert_method.txt", "data/sources/metadat/data-raw/dat.bangertdrowns2004.r", "data/sources/metadat/data-raw/dat.bangertdrowns2004.txt", "data/sources/metadat/man/dat.bangertdrowns2004.Rd", "data/sources/metadat/data-raw/dat.raudenbush1985.r", "data/sources/metadat/data-raw/dat.raudenbush1985.txt", "data/sources/metadat/man/dat.raudenbush1985.Rd", "data/sources/crop_conflict/raw_data/readme", "data/sources/crop_conflict/network_meta_analysis.qmd"]
def read_table(rel):
    lines=(BASE/rel).read_text().splitlines()
    names=shlex.split(lines[0])
    return [dict(zip(names,shlex.split(line))) for line in lines[1:] if line.strip()]
t=read_table("data/sources/metadat/data-raw/dat.raudenbush1985.txt")
b=read_table("data/sources/metadat/data-raw/dat.bangertdrowns2004.txt")
y=np.array([float(row['yi']) for row in t]); v=np.array([float(row['vi']) for row in t]); se=np.array([float(row['sei']) for row in t])
assert len(t)==19 and len(b)==48
assert len(set(row['study'] for row in t))==19
assert all(len(row)==11 for row in t)
assert np.isfinite(y).all() and np.isfinite(v).all() and (v>0).all()
assert all(int(row['n1i'])>0 and int(row['n2i'])>0 for row in t)
assert all(round(float(row['sei'])**2,4)==float(row['vi']) for row in t)
assert min(int(row['weeks']) for row in t)==0 and max(int(row['weeks']) for row in t)==24
assert {row['setting'] for row in t}=={'group','indiv'}
assert {row['tester'] for row in t}=={'aware','blind'}

def nll(a):
    w=1/(v+a); mu=np.dot(w,y)/w.sum()
    return float(.5*(np.log(v+a).sum()+np.log(w.sum())+np.dot(w,(y-mu)**2)))
def score(a):
    w=1/(v+a); mu=np.dot(w,y)/w.sum()
    return float(np.dot(w*w,(y-mu)**2)-w.sum()+np.dot(w,w)/w.sum())
hi=1.0
while score(hi)>0: hi*=2
root=0.0 if score(0)<=0 else float(brentq(score,0,hi,xtol=1e-14))
fit=minimize_scalar(nll,bounds=(0,hi),method='bounded',options={'xatol':1e-14})
candidates=[(0.0,nll(0)),(float(fit.x),float(fit.fun))]
tau2=min(candidates,key=lambda z:z[1])[0]
assert abs(root-tau2)<1e-7
w=1/(v+tau2); mu=float(np.dot(w,y)/w.sum()); semu=float(math.sqrt(1/w.sum())); z=mu/semu; crit=float(norm.ppf(.975))
w0=1/v; m0=np.dot(w0,y)/w0.sum(); Q=float(np.dot(w0,(y-m0)**2))
dup={}
for row in t: dup.setdefault((row['author'],row['year']),[]).append(int(row['study']))
repeated=[{'author':key[0],'year':int(key[1]),'studies':ids} for key,ids in dup.items() if len(ids)>1]
checks={'checked_at_utc':datetime.now(timezone.utc).isoformat(),'source_sha256':{rel:hashlib.sha256((BASE/rel).read_bytes()).hexdigest() for rel in SOURCE_PATHS},'runtime':{'python':sys.version.split()[0],'numpy':np.__version__,'scipy':scipy.__version__},'input_checks':{'teacher_rows':len(t),'writing_rows':len(b),'teacher_unique_ids':19,'teacher_missing_effect_or_variance':0,'teacher_all_variances_positive':True,'teacher_vi_equals_sei_squared_rounded_4dp':True,'max_absolute_vi_minus_sei_squared':float(np.max(np.abs(v-se**2))),'teacher_unequal_arm_rows':sum(row['n1i']!=row['n2i'] for row in t),'teacher_weeks_range':[0,24],'teacher_weeks_over_three':sum(int(row['weeks'])>3 for row in t),'repeated_author_year':repeated},'conditional_teacher_intercept_only_REML':{'k':19,'method':'Independent Python restricted-likelihood minimization, checked against analytic REML score root','tau2':tau2,'tau2_score_root':root,'mu':mu,'se_mu':semu,'z':z,'two_sided_p_normal':float(2*norm.sf(abs(z))),'ci95_normal':[mu-crit*semu,mu+crit*semu],'Q':Q,'Q_df':18,'Q_p':float(chi2.sf(Q,18)),'all_rows_retained':True,'independence_verified':False,'interpretation':'Numerical reference conditional on the supplied variances and independent rows; not a confirmed causal or editorial conclusion.'},'nontransferable_formula_example':{'teacher_study':1,'n1i':77,'n2i':339,'supplied_yi':.03,'supplied_vi':.0156,'writing_variance_rule_if_wrongly_reused':round((8+.03**2)/(2*(77+339)),3)}}
rscript=shutil.which('Rscript')
if rscript:
    run=subprocess.run([rscript,str(OUT/'reference.R'),str(BASE)],capture_output=True,text=True,timeout=50)
    checks['R_metafor_reference']={'Rscript':rscript,'exit_code':run.returncode,'stdout':run.stdout,'stderr':run.stderr}
else:
    checks['R_metafor_reference']={'status':'Not executed: Rscript is unavailable in PATH. No packages installed or network accessed.'}
(OUT/'checks.json').write_text(json.dumps(checks,indent=2)+'\n')
print(json.dumps(checks,indent=2))
