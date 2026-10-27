"""Create additive final-result metadata without replacing the polynomial record."""
import copy
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
metadata=copy.deepcopy(json.loads((ROOT/'lineage/native/myerson_metadata.json').read_text()))
raw=(ROOT/'certificate/weight.json').read_bytes()
weight=json.loads(raw)
assert weight['bound']=='17902560/18258529' and weight['relation']=='>='
metadata['candidate']={
 'id':'myerson-heft-final-weight-v1',
 'title':'A finite exact certificate for the universal 0.98 heft barrier',
 'sector':'Computer-assisted mathematics and reusable proof certificates',
 'thesis':'A conventional challenge produced a simpler piecewise-linear certificate; exact audit normalization strengthens it beyond the first polynomial construction. Two exact implementations and a cell-average argument prove a universal bound. No exclusive AI, discovery or commercial advantage is inferred.',
 'goal':'Verify h >= 17902560/18258529 >49/50 for every finite one-dimensional exact residue partition with at least two interval points per class.',
 'successMetric':'Both exact verifiers agree for all lengths2..20; an analytic tail covers all longer classes; cell averages cover every n. Frozen final scope and input controls pass, including refusal of uncertified strictness at the bound. External expert review remains pending.',
}
metadata['sources'].append({
 'id':'emanuel-thesis-2011','title':'Paul Robert Emanuel, Covering systems, 2011 dissertation',
 'url':'https://doi.org/10.25949/19441907',
 'excerpt':'Appendix C, Theorem C.1, printed page215 gives the strongest inspected prior general bound h>sqrt(8)-2. The thesis defines one-dimensional finite residue partitions; its separate two-dimensional examples do not contradict this theorem. Full copyrighted source copies are excluded from the distributable.',
 'kind':'public-excerpt',
})
artifact_paths=[
 'certificate/weight.json','final_certificate.py','study/final_confirmation_protocol.json',
 'study/final_request.json','fresh_conventional/verify_weight.py',
 'lineage/audit_conventional_weight.py','lineage/CONVENTIONAL_WEIGHT_AUDIT.md',
 'confirmation/conventional_independent/INDEPENDENT_WEIGHT_AUDIT.json',
 'lineage/FINAL_WEIGHT_CONFIRMATION_PLAN_V2.json','lineage/run_final_weight_exact_cases.py',
 'confirmation/final_weight_exact_cases.json',
]
final_audit=ROOT/'confirmation/final_independent/ADVERSE_AUDIT.json'
if not final_audit.exists():
    raise ValueError('Wait for the final corrected wrapper independent refusal audit before binding final metadata')
artifact_paths.extend(['confirmation/final_independent/ADVERSE_AUDIT.json',
                       'lineage/run_final_weight_wrapper_audit.py'])
metadata['witness']={
 'theorem':'For every n>=2, every one-dimensional exact partition of{1,...,n} into full restricted residue classes, each hitting at least twice, has h=sum(1/m)>=17902560/18258529>49/50. Distinctness is unnecessary; strictness at this exact final constant is not asserted.',
 'bound_exact':'17902560/18258529','relation':'>=',
 'mathematical_witness':weight,
 'witness_sha256':hashlib.sha256(raw).hexdigest(),
 'evidence_class':'Executed exact computer-assisted theorem, independently recomputed in the same session; no external peer review or proof-assistant formalization.',
 'discovery_attribution':'Fresh-context conventional workstream produced the piecewise-linear construction. Independent audit normalized by the already-computed exact maximum. This stronger conventional result replaces the earlier polynomial constant as the headline.',
 'proof_obligations':{
  'short_classes':'Exact line-arrangement boundary maxima for all lengths2..20; independent polygon-edge clipping and direct interpolation agree.',
  'interior_maxima':'Every arrangement cell has S=A*a*d+B*d^2+C*d; nonzeroA gives an indefinite Hessian, and A=0 lets a maximum move horizontally to a boundary.',
  'long_classes':'Zero-extension quadrature gives integral(W)+TV(Wprime)/(8*20^2)=7905/8<18258529/18240 for every length>=21.',
  'all_interval_lengths':'Exact cell-average dual weights transfer the continuous class inequality to every finite n, with no finite cutoff or asymptotic exception.',
  'fresh_confirmation':'512 seeded exact phase/cell-integral cases, including256 short and256 tail classes, pass; modified normalization and middle-height controls fail.',
  'interface':'Final corrected wrapper independently recomputes the complete proof, rejects altered/missing proof inputs and unsupported scopes, and refuses strictness at the exact final constant.',
 },
 'artifacts':[{'path':p,'sha256':hashlib.sha256((ROOT/p).read_bytes()).hexdigest(),'bytes':(ROOT/p).stat().st_size} for p in artifact_paths],
}
metadata['rights']['public_sources']+=' Full Emanuel thesis/article working copies are not redistributed; the package retains source citations, hashes and newly authored mathematical evidence.'
metadata['uncertainty']['comparison']='The strongest conventional construction exceeds the first polynomial constant after exact normalization. No exclusive discovery advantage, operational Alpha or specialist economic gain is established.'
metadata['uncertainty']['interface_correction']='The first final CLI mistakenly treated an explicitly supplied JSON null request as omitted; the failure is preserved and a corrected prospective freeze is used. This interface bug did not invalidate the mathematical certificate.'
metadata['milestones'][0].update({
 'goal':'Recompute the final piecewise-linear witness in both exact implementations.',
 'successMetric':'Frozen inputs match; all short-class maxima agree; the infinite tail is bounded; cell averages preserve every n.',
 'falsifiers':['Any exact class inequality exceeds the normalizer','Any omitted boundary or interior maximum','Any input digest mismatch'],
})
metadata['milestones'][1].update({
 'goal':'Confirm fresh exact cell weights and refuse malformed inputs or stronger unsupported claims.',
 'successMetric':'512 exact fresh classes pass; altered weights/normalizers fail; final wrapper refuses null/malformed requests, unsupported scopes and strictness at the exact bound.',
})
metadata['supersedes_for_headline']={
 'prior_metadata':'lineage/native/myerson_metadata.json',
 'prior_results':'lineage/native/results_myerson',
 'status':'Preserved valid earlier polynomial theorem; not deleted or relabeled.',
}
target=ROOT/'lineage/native/final_weight_metadata.json'
if target.exists():raise ValueError('Final metadata already exists; preserve it and make an additive revision if needed')
target.write_text(json.dumps(metadata,indent=2)+'\n')
print(target)
