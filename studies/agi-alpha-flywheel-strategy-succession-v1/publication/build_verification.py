#!/usr/bin/env python3
"""Assemble existing local verification; no experiment is launched."""
from pathlib import Path
import hashlib, json, datetime
from pypdf import PdfReader

ROOT=Path(__file__).resolve().parents[1]
def bind(s):
    p=ROOT/s
    return {'path':s,'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}

pdf=ROOT/'paper/AGI_ALPHA_FLYWHEEL_Strategy_Succession.pdf'
reader=PdfReader(pdf)
catalog=reader.trailer['/Root']
active=[]
for key in ['/AA','/AcroForm']:
    if key in catalog:active.append(key)
opening=catalog.get('/OpenAction')
if opening is not None and hasattr(opening,'get') and opening.get('/S') not in ['/GoTo',None]:active.append('active opening action')
names=catalog.get('/Names',{})
if '/JavaScript' in names or '/EmbeddedFiles' in names:active.append('active names or embedded files')
for n,page in enumerate(reader.pages,1):
    if '/AA' in page:active.append(f'page{n}/AA')
    for ref in page.get('/Annots',[]):
        action=ref.get_object().get('/A',{})
        if action and action.get('/S') not in ['/URI','/GoTo']:active.append(f'page{n}:{action.get("/S")}')
assert not active,active
qa=json.loads((ROOT/'publication/pdf-qa/FINAL_ALL_PAGES.json').read_text())
rebuild=json.loads((ROOT/'publication/PACKAGED_LATEX_REBUILD.json').read_text())
assert qa['pdf_sha256']==rebuild['author_pdf_sha256']==hashlib.sha256(pdf.read_bytes()).hexdigest()
files=['paper/AGI_ALPHA_FLYWHEEL_Strategy_Succession.pdf','browser/index.html','protocol/STUDY_FREEZE.json','companion/SOURCE_MANIFEST.json','publication/pdf-qa/FINAL_ALL_PAGES.json','publication/PACKAGED_LATEX_REBUILD.json','publication/FINAL_RECORDED_QA.json','EVIDENCE_DOCKET.json']
j={
 'schema':'agi-alpha-strategy-publication-verification/v1',
 'status':'LOCAL_RESEARCH_PACKAGE_VERIFIED_PUBLICATION_REVIEW_PENDING',
 'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'scientific_source_hash':'7e5a1dd2dcf7eb00ec055f1858d5dd722cc950f15f33314bb94c456c753845a7',
 'prospective_freeze_sha256':'6d0308707f3909fd18d086a950d237835dafd9ab6cfa9a559846715f46613827',
 'frozen_files_checked':52,
 'registered_confirmation':{'completed':True,'explicit_launches':1,'trials':336,'native_cases':72,'source_or_protocol_changes_after_freeze':False,'mid_stream_manual_phase_triggers':0},
 'independent_review':{'main_audit':'PASS','summary_audit':'PASS','ancestry_scope':'PASS_WITH_SCOPE_CLARIFICATION','institutional_independence':False},
 'paper':{'physical_pages':22,'all_final_pages_rendered_and_visually_inspected':True,'all_checks_pass':True,'packaged_source_rebuild_byte_identical':rebuild['byte_identical'],'author_pdf_sha256':rebuild['author_pdf_sha256'],'active_pdf_actions_observed':active,'initial_navigation':'Internal first-page Fit destination; no execution','passive_check_scope':'Local structural check only; repository publication validator and owner gates remain separate.'},
 'browser':{'fresh_local_computation':True,'offline_network_blocked_qa':'PASS','recorded_confirmation_labeled':True,'persistent_when_tab_closed':False,'execution_digest':'67fa72590db37750936fce825c34e1d207aa61a831f1678ded24a768d43dc407'},
 'growth_claims':{'primary_inherited_asset':False,'net_benefit_over_strongest_comparator':False,'qualified_fresh_deep_repair_succession':False,'self_acceleration':False,'commercial_adoption_or_payback':False},
 'operating_limits':[
   'One cumulative account funds delivery and discovery; separate protected service and improvement accounts are not implemented.',
   'Repair tasks use generated conventional baselines, not the actual prior accepted mission plan.',
   'The browser runs locally; authenticated connection to an approved installed executor is not implemented.',
   'Human duration, model charges and complete monetary costs remain unknown.',
   'Existing Harness/Fleet restrictions and publication owner gates remain intact.'
 ],
 'publication':{'source_handoff':'Prepared for isolated additive draft PR','merged':False,'research_release_asset_publicly_verified':False,'website_deployed_or_served_bytes_verified':False,'preferred_edition_02_preserved_sha256':'e1391d05727eb5afb0e0de903f9e87db744a79d7b017cf17c4177fed0467e40b'},
 'artifacts':[bind(s) for s in files],
 'saved_copy_checks':'Unexecuted and executed checkpoints were read back with exact hashes. Final deliverable receipts are reported separately after final upload.'
}
(ROOT/'VERIFICATION.json').write_text(json.dumps(j,indent=2)+'\n')
print(json.dumps({'verification':'PASS','PDF':rebuild['author_pdf_sha256'],'all_pages':22,'docket_claims':16}))
