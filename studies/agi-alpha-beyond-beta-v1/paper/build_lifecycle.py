# SPDX-License-Identifier: Apache-2.0
"""Render executed lifecycle receipts; never generate evidence from UI scores."""
import hashlib
import json
from build import ROOT, esc, table, write


def main():
    audit=json.loads((ROOT/'qa/graph_lifecycle_v3_audit.json').read_text())
    traces=json.loads((ROOT/'results/graph_lifecycle_v3_cases.json').read_text())
    if not audit['passed'] or any(not c['passed'] for c in traces['cases']):
        raise RuntimeError('Lifecycle tests did not pass')
    source=hashlib.sha256((ROOT/'sim/graph_lifecycle_v3.py').read_bytes()).hexdigest()
    if source!=audit['source_sha256'] or source!=traces['source_sha256']:
        raise RuntimeError('Lifecycle evidence does not match the source')
    tests=hashlib.sha256((ROOT/'sim/test_graph_lifecycle_v3.py').read_bytes()).hexdigest()
    if tests!=audit['test_sha256']:raise RuntimeError('Test receipt source mismatch')
    steps=[s for c in traces['cases'] for s in c['steps']]
    verified=0
    for s in steps:
        if 'event_hash' not in s:continue
        body={k:v for k,v in s.items() if k!='event_hash'}
        actual=hashlib.sha256(json.dumps(body,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode()).hexdigest()
        if actual!=s['event_hash']:raise RuntimeError('Changed trace event')
        verified+=1
    rejected=sum(s.get('allowed') is False for s in steps)
    content=(f"All {audit['tests_run']} adversarial lifecycle cases passed. The replay contains {len(steps)} recorded steps, including {rejected} rejected operations; these are software test actions, not independent invention campaigns or commercial projects. The publication builder independently verifies {verified} event commitments and the exact implementation/test hashes before presenting them. ")
    content+=r'The implementation SHA-256 is \nolinkurl{'+source+'}.'
    rows=[['Admission and value','Prospective incremental Alpha; source-job receipts are not charged twice; duplicate and negative-value candidates rejected.'],
          ['Authority and freshness','Exact direct names; distinct roles; stale evidence, Beta/policy/registry changes and immutable public views.'],
          ['History and composition','Canonical bypass blocked; revocation and retirement survive old history; dependencies checked transitively.'],
          ['Privacy and actions','AES-GCM tampering, trusted executors, explicit action permission, export controls and protected evaluation/scorer exclusion.'],
          ['History and learning','Separate failure memory cannot enter positive discovery; origin records bind observable delivery and receipt provenance.']]
    content+='\n'+r'\begin{table}[htbp]\centering\small'+table(['Test family','Executed boundary'],[[esc(a),esc(b)] for a,b in rows],'p{.25\\linewidth}p{.68\\linewidth}')+r'\caption{Research implementation tests. Synthetic identities and economic assessments are not real validators or operational capability evidence.}\end{table}'
    content+='\nThe export test deliberately retains previously authorized plaintext after revocation. This is an expected privacy limit, not an implementation success at erasing copies. The process owner, trusted executor installation, real ENS ownership, wallet signatures, production key custody, Ethereum and zero-knowledge proofs are outside the tested boundary.'
    write('lifecycle_results.tex',content)
    receipt={'source_sha256':source,'test_sha256':tests,'cases':audit['tests_run'],'steps':len(steps),'rejected_operations':rejected,'independently_verified_event_hashes':verified,'passed':True,'scope':'Receipt integrity and exact code/test identity; not semantic or economic truth.'}
    (ROOT/'qa/lifecycle_v3_receipt_verification.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt,indent=2))


if __name__=='__main__':main()
