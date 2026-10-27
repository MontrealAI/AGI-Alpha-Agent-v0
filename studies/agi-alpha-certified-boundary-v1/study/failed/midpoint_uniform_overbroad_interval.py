import json,math,sys
from fractions import Fraction as F
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'lineage'))
from myerson_independent_bounds import polynomial,bernstein,midpoint_objective

root=Path(__file__).resolve().parents[1]
c=[F(x) for x in json.loads((root/'scout/revised_polynomial.json').read_text())['coefficients']]
p=polynomial(c);I=sum(v/F(i+1) for i,v in enumerate(p))
B=[F(1)]
for n in range(1,21):B.append(-sum(F(math.comb(n+1,k))*B[k] for k in range(n))/F(n+1))
delta=[]
for r in range(1,11):
 k=2*r;order=k-1
 deriv1=sum(p[j]*F(math.factorial(j),math.factorial(j-order)) for j in range(order,len(p)))
 deriv0=p[order]*math.factorial(order)
 half=(F(2)**(1-k)-1)*B[k]
 delta.append(half*(deriv1-deriv0)/math.factorial(k))
checks=[]
for n in list(range(2,25))+[101,997]:
 exact=I+sum(a/F(n**(2*r)) for r,a in enumerate(delta,1))
 assert exact==midpoint_objective(p,n)
 checks.append(n)
stack=[(F(0),F(1,4),0)];leaves=[]
while stack:
 lo,hi,depth=stack.pop();bs=bernstein(delta,lo,hi)
 if min(bs)>0:
  leaves.append({'lo':str(lo),'hi':str(hi),'min_coefficient':str(min(bs)),'depth':depth});continue
 if depth>=30:raise ValueError(('uncertified',lo,hi,bs))
 mid=(lo+hi)/2;stack.extend([(lo,mid,depth+1),(mid,hi,depth+1)])
out={'claim':'For every integer n>=2, the midpoint average is strictly greater than the integral I. Exact Euler-Maclaurin polynomial and positive Bernstein coefficients on t=1/n^2 in (0,1/4] certify this.','integral':str(I),'integral_decimal':float(I),'coefficients_Qn_minus_I_div_t':[str(x) for x in delta],'exact_identity_checks_n':checks,'positive_intervals':leaves,'uniform_implies':'heft > I, conditional on all residue-class dual inequalities','uses_existing_polynomial_conversion':'lineage/myerson_independent_bounds.py','independent_audit_required':True}
(root/'study/midpoint_uniform_result.json').write_text(json.dumps(out,indent=2)+'\n')
print({'integral':str(I),'decimal':float(I),'positive_intervals':len(leaves),'maxdepth':max(v['depth'] for v in leaves)})
