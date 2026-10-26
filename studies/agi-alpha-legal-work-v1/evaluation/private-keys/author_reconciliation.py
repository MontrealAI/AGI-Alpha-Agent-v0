import datetime, hashlib, json, pathlib

ROOT=pathlib.Path('/workspace/scratch/9d2647fdda5a/legal-study')
records=[]
sha=lambda b:hashlib.sha256(b).hexdigest()
prefix='ORIGINAL SYNTHETIC RESEARCH TEXT — NOT FOR EXECUTION\nMutual information-exchange agreement between Research Company Cedar and Research Company Dune, fictional organizations.\n'

def emit(n,stratum,original,revised,amendments=None,edits=None):
    case=f'RECON-{n:02d}'
    data={'case_id':case,'source_class':'synthetic','original_text':original,'revised_text':revised,'amendments':amendments or []}
    h={'original':sha(original.encode()),'revised':sha(revised.encode())}
    h.update({f'amendment:{a["id"]}':sha(a['text'].encode()) for a in data['amendments']})
    key={'schema':'independent-reconciliation-key/v1','case_id':case,'stratum':stratum,'input_hashes':h,'required_amendment_ids':[a['id'] for a in data['amendments']],'legal_semantics_assessed':False,'codepoint_lengths':{'original':len(original),'revised':len(revised),**{f'amendment:{a["id"]}':len(a['text']) for a in data['amendments']}},'author_known_edits':edits or [],'edit_annotation_status':'Descriptive construction history only; no unique diff segmentation required.','acceptance':'Exact source identities, valid spans, complete original/revised reconstruction, separate complete amendment preservation, no legal-meaning or approval claims.','author':'/root/legal_scope'}
    ip=ROOT/'inputs/reconciliation'/f'{case}.json';kp=ROOT/'evaluation/private-keys/reconciliation'/f'{case}.json'
    for p,d in [(ip,data),(kp,key)]:
        assert not p.exists(),p
        p.write_text(json.dumps(d,indent=2,ensure_ascii=False)+'\n')
    records.append({'case_id':case,'stratum':stratum,'input_path':str(ip.relative_to(ROOT)),'input_sha256':sha(ip.read_bytes()),'key_path':str(kp.relative_to(ROOT)),'key_sha256':sha(kp.read_bytes())})

def replace(text,old,new):
    assert text.count(old)==1,(old,text.count(old))
    return text.replace(old,new)

old=prefix+'''Project: Harbour Connector.
1. Evaluation. The exchanged technical records may be used only to evaluate whether the companies should enter a software interoperability project. A demonstration supplied with those records remains part of the evaluation material.
2. Safeguarding. Each receiving company will limit copies to those reasonably needed for that evaluation and will maintain an inventory of copies supplied to its project staff.
3. Discussions. Neither company promises to purchase, supply or license any product merely by taking part in the discussions. Any later commercial arrangement will be recorded separately.
4. Records. Each company will identify the person responsible for its project records before the first demonstration session.
'''
new=replace(old,'only to evaluate whether the companies should enter a software interoperability project','to evaluate the software interoperability project and to build an internal proof-of-concept using the supplied records')
emit(1,'RC1-sentence-edit',old,new,edits=[{'operation':'single sentence fragment replacement','location':'Section 1','description':'Changed the stated activities involving technical records; no interpretation supplied.'}])

old=prefix+'''Project: Northern Signals.
A. Exchange window. Material may be shared during the 45 days following the project opening meeting. The meeting date must be entered in the project register.
B. Copies. A receiving company may maintain two working copies for the evaluation team. A third copy may be retained in the legal archive, separately from operational working files.
C. Review. If either company asks for a review meeting, the project coordinators will arrange one within ten days. This scheduling provision does not change any other obligation.
D. Notices. Project notices must identify Northern Signals in their subject line and include the applicable document version.
'''
new=replace(old,'45 days following the project opening meeting','12 days following the project opening meeting')
new=replace(new,'two working copies','four working copies')
emit(2,'RC1-sentence-edit',old,new,edits=[{'operation':'two nonadjacent replacements','location':'A and B','description':'Exchange-window quantity and working-copy quantity changed.'}])

old=prefix+'''1. Marking. The supplying company will mark the files listed in the delivery register as restricted project material. Oral presentations will be identified in the meeting record.
2. Access. Access is limited to personnel assigned to the proposed integration project. A personnel list will be updated at each scheduled review.
3. Technical inspection. The receiving company may inspect the sample output using the supplied test interface. Source code is not included in the sample output.
4. End of evaluation. The project coordinators will record the date on which evaluation access ends and identify the copies held by their respective teams.
'''
addition='2A. Public statements. Neither company may use the other company\'s project name in an external announcement without a separate written approval identifying that announcement.\n'
new=replace(old,'3. Technical inspection.',addition+'3. Technical inspection.')
emit(3,'RC2-insertion-deletion',old,new,edits=[{'operation':'clause insertion','location':'between Sections 2 and 3','inserted_text':addition}])

old=prefix+'''1. Identification. A delivery note accompanies each collection of evaluation records. It identifies the file set, the delivery date and the supplying company.
2. Evaluation team. The companies will maintain a list of authorized evaluation personnel and distribute updated lists to their project coordinators.
3. Backup handling. An automatically generated backup may be retained under the receiving company\'s ordinary retention process; it must remain inaccessible to the evaluation team and is not a source for new working copies.
4. Contact changes. A change to a project coordinator takes effect after the other company receives a written replacement contact notice.
5. Document register. Each version of this agreement will have a distinct entry in the document register.
'''
deleted='3. Backup handling. An automatically generated backup may be retained under the receiving company\'s ordinary retention process; it must remain inaccessible to the evaluation team and is not a source for new working copies.\n'
new=replace(old,deleted,'')
emit(4,'RC2-insertion-deletion',old,new,edits=[{'operation':'whole-clause deletion','location':'Section 3','deleted_text':deleted}])

parts=[
    'Purpose. The companies will examine a possible joint validation project using synthetic performance traces. The project specification is a separate document.\n',
    'Handling. The receiving company will keep evaluation traces in its designated project repository and record who can access that repository.\n',
    'Retention. Working copies will be listed in the closure register when the evaluation ends. Archived material will be identified separately.\n',
    'Required disclosures. A request from a public authority must be routed to the company\'s designated legal contact before the project team acts on it.\n']
old=prefix+''.join(f'{i+1}. {p}' for i,p in enumerate(parts))
new=prefix+''.join(f'{i+1}. {parts[j]}' for i,j in enumerate([3,0,1,2]))
emit(5,'RC3-reorder-renumber',old,new,edits=[{'operation':'reorder and renumber','original_order':[0,1,2,3],'revised_order':[3,0,1,2],'description':'Full clauses moved; new numbering reflects the supplied revised document.'}])

clauses=[
    'The companies will exchange sample configuration files through the named project repository. No other provision changed.\n',
    'Each delivered file set must identify its format and version in the delivery register. No other provision changed.\n',
    'Any supplemental explanation must identify the file set to which it relates. No other provision changed.\n']
schedule='Schedule R. The project repository identifier is RESEARCH-ROOM-7. It contains synthetic examples only.\n'
old=prefix+''.join(f'{(i+1)*10}. {c}' for i,c in enumerate(clauses))+schedule
new=prefix+schedule+''.join(f'{letter}. {clauses[j]}' for letter,j in zip('ABC',[1,2,0]))
emit(6,'RC3-reorder-renumber',old,new,edits=[{'operation':'move schedule and reorder repeated clause endings','original_labels':['10','20','30'],'revised_labels':['A','B','C'],'description':'Repeated unchanged sentence permits more than one valid diff alignment.'}])

old=prefix+'''1. File exchange. Material for the Delta evaluation will be supplied as plain-text logs and tabular synthetic test results.
2. Contact. The project coordination identifier is DELTA-DESK-OLD. This identifier refers to an internal research queue, not an external address.
3. Project register. The register will list supplied versions, review comments and the status of each document.
4. Closure. The two project coordinators will prepare a closure inventory 20 days after the evaluation ends.
'''
new=replace(old,'DELTA-DESK-OLD','DELTA-DESK-NEW')
amendments=[{'id':'AMEND-ONE','text':'SYNTHETIC SEPARATE AMENDMENT ONE\nDated 14 October 2026. Replace Section 4 of the supplied agreement with: "The project coordinators will prepare a closure inventory 12 days after the evaluation ends."\nThe supplied version of the underlying agreement has not been consolidated with this amendment.\n'}, {'id':'AMEND-TWO','text':'SYNTHETIC SEPARATE AMENDMENT TWO\nDated 20 October 2026. In Amendment One, replace "12 days" with "16 days". All other text in that amendment is unchanged.\nRetain this document separately in the research packet.\n'}]
emit(7,'RC4-separate-amendments',old,new,amendments,edits=[{'operation':'base document identifier replacement','description':'Two additional supplied amendment texts remain separate; no consolidated legal effect is computed.'}])

old=prefix+'''I. Delivery index. The supplying company will provide a delivery index naming each synthetic dataset and its schema version.
II. Review notes. The receiving company will keep observations in a separate review log. Entries must identify the source dataset and evaluation run.
III. Follow-up. Requests for clarification must cite the relevant delivery-index entry. A response will be linked to that request in the register.
IV. Attachments. The research packet lists Annex T and any separately supplied amendments. Their presence in the packet does not consolidate their text.
'''
new=replace(old,'Annex T and any separately supplied amendments','Annex T, Annex U and any separately supplied amendments')
amendments=[{'id':'ADDENDUM_A','text':'SYNTHETIC ADDENDUM A\n1. Supplemental index. Annex U lists validation outputs rather than input datasets.\n2. Identifier. The validation-output series is U-2026-ALPHA.\n3. Record. The reviewer must keep this addendum as a distinct document.\n'}, {'id':'CORRECTION_B','text':'SYNTHETIC CORRECTION B\nParagraph 2 of Addendum A contains the identifier U-2026-ALPHA. The supplied correction changes it to U-2026-BETA.\nA handwritten-signature field is intentionally blank; this synthetic document is not executed.\n'}]
emit(8,'RC4-separate-amendments',old,new,amendments,edits=[{'operation':'attachment-list insertion','description':'Two supplied documents contain a correction chain, preserved without interpretation.'}])

old=prefix+'''1. Project name. The research workspace is called "Cafe Atlas". Use that exact workspace name in the delivery index.
2. Units. Each sample run covers 1000 milliseconds and includes one 5-byte marker. The data are invented for document-comparison research.
3. Notation. A plus sign (+) identifies an appended sample; a hyphen (-) identifies a withdrawn sample in the index.
4. Reference. The accompanying description is version 1.0 and must be retained beside the sample register.
'''
new=replace(old,'"Cafe Atlas"','“Café Atlas”')
new=replace(new,'1000 milliseconds','1\u00a0000 milliseconds')
new=replace(new,'5-byte','5‑byte')
new=replace(new,'a hyphen (-)','a minus sign (−)')
emit(9,'RC5-unicode-formatting',old,new,edits=[{'operation':'Unicode text replacements','description':'Curly quotation marks, accented letter, nonbreaking space, nonbreaking hyphen and mathematical minus sign are intentional distinct codepoints.'}])

old=prefix+'''1. Schedule heading: Résumé of the evaluation.
2. The supplying company will provide the sample register before the opening meeting.
3. The receiving company will identify its review notes using the same register references.
4. Both companies will preserve each supplied version in the research archive.
'''
new=old.replace('\n','\r\n').replace('Résumé','Re\u0301sume\u0301').replace('2. The','2.\tThe').replace('3. The','3.  The')
emit(10,'RC5-unicode-formatting',old,new,edits=[{'operation':'formatting and Unicode-normalization variation','description':'CRLF replaces LF; one tab and one doubled space added; composed accents replaced by decomposed combining sequences. Raw codepoints must remain exact.'}])

old=prefix+'''Section 4 — Review procedure
4.1 The receiving company will record findings as follows:
    (a) identify the synthetic dataset;
    (b) identify the evaluation run;
    (c) reference the procedure in Section 7.2(b).
4.2 If a run is repeated, the reviewer will:
    (a) retain the earlier run identifier; and
    (b) explain the reason for repetition under Section 7.3.
Section 7 — Supporting records
7.2(b) The procedure record contains the sequence of test steps used in the run.
7.3 The repetition record identifies any changed test settings.
'''
new=replace(old,'reference the procedure in Section 7.2(b).','reference the procedure in Section 9.1(c) and the settings record in Section 9.2.')
new=replace(new,'under Section 7.3.','under Section 9.2.')
new=replace(new,'Section 7 — Supporting records\n7.2(b)','Section 9 — Supporting records\n9.1(c)')
new=replace(new,'7.3 The repetition record','9.2 The repetition record')
emit(11,'RC6-nested-references',old,new,edits=[{'operation':'nested cross-reference and target-label replacements','description':'Record text changed in both referring and referenced provisions. No conclusion about reference validity is required.'}])

old=prefix+'''Article A. Supplied material
A.1 The term "Sample Package" identifies the files listed in Attachment 1, item (ii).
A.2 A Sample Package may include:
    (i) synthetic input traces;
    (ii) mock output tables; and
    (iii) a description referring to §4.2(a) of the project note.
Article B. Questions
B.1 A clarification request must identify both the Sample Package and the item in Attachment 1.
B.2 The response must quote the relevant request identifier. The original question remains in the log.
Attachment 1
(ii) The files are identified by the inventory delivered with the project note.
'''
new=replace(old,'Attachment 1, item (ii)','Attachment 2, item (iv)')
new=replace(new,'(iii) a description referring to §4.2(a) of the project note.','(iii) a description referring to §5.1(c) of the project note; and\n    (iv) a manifest of intentionally omitted test cases.')
new=replace(new,'the item in Attachment 1.','the item in Attachment 2.')
new=replace(new,'Attachment 1\n(ii)','Attachment 2\n(iv)')
emit(12,'RC6-nested-references',old,new,edits=[{'operation':'nested item insertion plus cross-reference edits','description':'Added one list item and changed multiple textual references; no semantic certification.'}])

assert len(records)==12
assert len(list((ROOT/'inputs/reconciliation').glob('*.json')))==12
source=ROOT/'protocol/reconciliation-source-freeze.json'
assert sha(source.read_bytes())=='3f41122d1e89e8a42916816bd0aca90905b7b7edfd43ec552b6898c9531c09ae'
first=json.loads((ROOT/'protocol/corpus-freeze.json').read_text())
for r in first['cases']:
    assert sha((ROOT/r['input_path']).read_bytes())==r['input_sha256']
    assert sha((ROOT/r['key_path']).read_bytes())==r['key_sha256']
for r in records:
    case=json.loads((ROOT/r['input_path']).read_text());key=json.loads((ROOT/r['key_path']).read_text())
    texts={'original':case['original_text'],'revised':case['revised_text']}
    texts.update({f'amendment:{a["id"]}':a['text'] for a in case['amendments']})
    assert all(sha(texts[k].encode())==v for k,v in key['input_hashes'].items())
    assert all(len(texts[k])==v for k,v in key['codepoint_lengths'].items())
manifest={'schema':'independent-reconciliation-corpus-freeze/v1','author':'/root/legal_scope','created_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_freeze_sha256':sha(source.read_bytes()),'plan_sha256':sha((ROOT/'protocol/reconciliation-corpus-plan.json').read_bytes()),'case_count':12,'primary_history_unchanged':True,'author_exposure':'Second-offering scope, agreed mechanical key schema and source-freeze identity only; no second adapter/checker source or predictions inspected.','source_policy':'New original synthetic text; first-prototype cases not reused.','key_release':'WITHHELD until all24 predictions sealed.','annotation_scope':'Exact text and document identities only; no legal interpretation or preserved-meaning claim.','alignment_policy':'Construction edit descriptions do not prescribe a unique valid diff alignment.','authoring_file_sha256':sha(pathlib.Path(__file__).read_bytes()),'cases':records}
p=ROOT/'protocol/reconciliation-corpus-freeze.json';assert not p.exists();p.write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n')
print(json.dumps({'cases':12,'manifest_path':str(p),'manifest_sha256':sha(p.read_bytes()),'input_directory':'inputs/reconciliation','keys_directory':'evaluation/private-keys/reconciliation','first_corpus_and_keys_unchanged':True}))
