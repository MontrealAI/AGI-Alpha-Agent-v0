"""Build study-specific metadata for the unchanged offline native bridge."""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
WITNESS=ROOT/'scout/revised_polynomial.json'
FROZEN='c92bc1977bbb6804af862d52c82507793ff57e2355c501477f609e7a1dd22633'
assert hashlib.sha256(WITNESS.read_bytes()).hexdigest()==FROZEN
artifacts=[
 'scout/revised_polynomial.json','scout/certify_bernstein.py','scout/bernstein_results.json',
 'lineage/myerson_independent_bivariate.py','lineage/myerson_independent_bivariate.json',
 'lineage/myerson_independent_bounds.py','lineage/myerson_revised_independent_bounds.json',
 'study/midpoint_uniform.py','study/midpoint_uniform_result.json',
 'lineage/myerson_independent_uniform.py','lineage/myerson_independent_uniform.json',
 'lineage/myerson_original_counterexample.json',
]
metadata={
 'candidate':{
  'id':'myerson-heft-certificate-v1',
  'title':'A universal heft barrier for finite residue partitions',
  'sector':'Computer-assisted mathematics and reusable proof certificates',
  'thesis':'An exact rational polynomial certificate replaces unbounded enumeration with a universal lower bound, independently recomputed in two implementations. This is a mathematical research result; priority, external review, commercial demand and model superiority are separate questions.',
  'goal':'Verify h > 1891871140656049/1929687500000000 for every finite exact residue-class partition with at least two points per class.',
  'successMetric':'Two independently derived exact certificate implementations agree; all 78 short-class patches, the infinite-length tail and every finite n pass; the known invalid grid witness is refused. No external peer review or production qualification is asserted.',
 },
 'sources':[
  {'id':'myerson-author-question','title':'Gerry Myerson: finite residue covers and heft question',
   'url':'https://mathoverflow.net/questions/462981/open-problems-which-might-benefit-from-computational-experiments/499017',
   'excerpt':'The author defines distinct-modulus residue classes that partition 1 through n, each containing at least two interval elements, and asks whether any has total reciprocal modulus below 0.98. August 2026 updates address other directions. This paraphrase records the inspected question, not an ownership claim.',
   'kind':'public-excerpt'},
  {'id':'myerson-poon-simpson-2009','title':'Incongruent restricted disjoint covering systems',
   'url':'https://doi.org/10.1016/j.disc.2009.02.002',
   'excerpt':'Myerson, Poon and Simpson introduced this finite covering-system setting and reported structural and computational results. The inspected primary search extract gives heft bounds in terms of interval length and number of classes; the full CORE PDF was unavailable to this audit.',
   'kind':'public-excerpt'},
  {'id':'lyman-morris-toomey-2012','title':'Incongruent Restricted Disjoint Covering Systems',
   'url':'https://www.laura-lyman.com/uploads/3/9/7/4/39745896/correctirdcspaper.pdf',
   'excerpt':'The authors define incongruent restricted disjoint covering systems with at least two interval elements per congruence class and describe structural families and finite computations. The study preserves the original partition requirement.',
   'kind':'public-excerpt'},
 ],
 'witness':{
  'theorem':'For every n>=2, every partition of {1,...,n} into complete truncated residue classes, each containing at least two points, has h=sum(1/m)>1891871140656049/1929687500000000>49/50. Distinct moduli are not required by the proof.',
  'bound_exact':'1891871140656049/1929687500000000',
  'witness_sha256':FROZEN,
  'evidence_class':'Executed exact computer-assisted proof; independently recomputed by a same-session workstream; no proof-assistant formalization or external peer review.',
  'proof_obligations':{
   'short_classes':'78 exact tensor-Bernstein patches for lengths2..40; independent generic Horner checker passes with95 leaves,maxdepth6.',
   'long_classes':'Exact bound I+abs(f0)/40+TV(gprime)/(8*40^2)<1 covers all lengths>=41.',
   'all_interval_lengths':'Independent telescoping centered-moment recurrence matches Euler-Maclaurin coefficients;16 rational Bernstein intervals and exactn2,3 prove midpoint average>I for alln>=2.',
   'refusal':'Original coarse-grid witness has exact finite-class violation n26,m15,r11, with normalized left side1.0464113181398584>1.',
  },
  'artifacts':[{'path':p,'sha256':hashlib.sha256((ROOT/p).read_bytes()).hexdigest(),'bytes':(ROOT/p).stat().st_size} for p in artifacts],
 },
 'rights':{
  'new_material':'Original mathematical calculations and certificate implementations produced in this study; no claim to ownership of the underlying open problem.',
  'public_sources':'Primary sources are cited and briefly paraphrased. No unlicensed external implementation is copied into the mathematical certificate.',
  'native_reuse':'Unchanged Apache-2.0 source closure at47c17f6aca6b1bb8779dd3e47d5ba5f8af3329f4; LICENSE and per-file notices preserved. Adapter is unchanged from979f50024ddbf3d6eff6c49d3271898c64b240f8.',
  'permissions':'Local research execution and reviewable artifacts only. No external contact, publication, minting, trading, spending, permission change, live ENS authentication or MARK activation.',
 },
 'uncertainty':{
  'priority':'Scoped primary-source search found an author-posted open question; universal novelty is not established by that search.',
  'verification':'Two same-session independent computational derivations and analytic review; external mathematician review remains desirable. Integrity hashes do not establish mathematical truth by themselves.',
  'models':'No separately metered live frontier-model benchmark, ordinary-versus-expert controlled trial, or superhuman-specialist claim.',
  'economics':'Actual authoring cost and demand are not measured here. Zero receipts; no profitable business claim follows from this mathematical result.',
  'capsule':'Production scope is not qualified; the adapter must preserve the unsupported scientific capsule refusal.',
 },
 'milestones':[
  {'id':'freeze-and-check','goal':'Recompute the frozen rational witness and both exact finite-class certificates.',
   'successMetric':'Witness digest matches;78/78 patches pass in both implementations;alln and infinite-tail obligations pass.',
   'depends_on':[],'budget':{'cpu_seconds_ceiling':60,'memory_mib_ceiling':512,'external_spend_usd':0},
   'permissions':['local read-only source verification','local new artifact writes'],
   'falsifiers':['Any exact negative class-constraint witness','Any uncovered parameter domain','Any input digest mismatch'],
   'duration_seconds':600},
  {'id':'fresh-adverse-review','goal':'Confirm frozen proof on fresh exact cases and refuse malformed or inflated claims.',
   'successMetric':'Fresh direct checks agree and designed invalid artifacts fail;universal proof is never inferred from finite sampling.',
   'depends_on':['freeze-and-check'],'budget':{'cpu_seconds_ceiling':120,'memory_mib_ceiling':512,'external_spend_usd':0},
   'permissions':['local executable research','no external actions'],
   'falsifiers':['Verifier accepts known invalid grid witness','Verifier accepts changed bound or coefficients without new proof'],
   'duration_seconds':600},
  {'id':'research-review-edition','goal':'Assemble the proof, failed evidence, sources and independent audit for research review.',
   'successMetric':'PDF and browser edition agree on theorem and scope;external-review and canonical-release statuses remain explicit.',
   'depends_on':['fresh-adverse-review'],'budget':{'editorial_minutes_ceiling':30,'external_spend_usd':0},
   'permissions':['local publication package','existing review process only'],
   'falsifiers':['An unproven economic or model-superiority claim is presented as measured','A local draft is reported as a canonical merged release'],
   'duration_seconds':1800},
 ],
}
target=ROOT/'lineage/native/myerson_metadata.json'
target.write_text(json.dumps(metadata,indent=2)+'\n')
print(target)
