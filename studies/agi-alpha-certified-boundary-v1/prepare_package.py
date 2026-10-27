# SPDX-License-Identifier: Apache-2.0
"""Assemble the publication package without unrelated caches or copyrighted papers."""
from pathlib import Path
import hashlib
import json
import shutil
import zipfile

ROOT=Path(__file__).resolve().parent
DEST=ROOT/'deliverables'/'agi_alpha_certified_boundary_v1'
TOP=['README.md','NOTICE.md','LICENSE','LinkedIn_draft.txt','certificate_service.py',
     'final_certificate.py','reproduce.py','requirements-search.txt','requirements-native.txt','requirements-publication.txt','prepare_package.py']
DIRS=['certificate','scout','study','fresh_conventional','challenge','lineage','economics','evidence','confirmation']


def excluded(relative):
    parts=relative.parts
    if str(relative) in {'lineage/capacity_prior_art/LATEST_PRIOR_ART.md','lineage/capacity_prior_art/tandon_arithmetic_reproduction.txt'}:return False
    if any(part in {'.git','__pycache__','sources','capacity_prior_art'} or part.startswith('replay_') for part in parts):return True
    if relative.suffix in {'.pyc','.pdf','.html'}:return True
    if 'emanuel' in relative.name.lower() and relative.suffix=='.txt':return True
    if relative.name in {'mo_answers.json','thesis_metadata.json'}:return True
    return False


def copy(path, relative=None):
    destination=DEST/(relative or path.relative_to(ROOT))
    destination.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(path,destination)


def main():
    if DEST.exists():
        raise ValueError('Package destination already exists; preserve earlier builds and choose a new edition.')
    DEST.mkdir(parents=True)
    for name in TOP:copy(ROOT/name)
    omitted=[]
    for directory in DIRS:
        for path in sorted((ROOT/directory).rglob('*')):
            if not path.is_file():continue
            relative=path.relative_to(ROOT)
            if excluded(relative):omitted.append(str(relative));continue
            copy(path)
    pub_files=['paper.md','paper.tex','paper.pdf','paper.html','PAPER.md','executive_brief.md',
               'executive_brief.tex','executive_brief.pdf','executive_brief.html','EXECUTIVE_BRIEF.md',
               'references.bib','paper_template.tex','html_template.html','style.css','layout.lua',
               'make_figures.py','build_publication.py','check_browser.py','build_manifest.json',
               'conclusion_consistency.json','visual_qa_summary.json','final_proof_fragment.md','mathematical_review_notes.md']
    for name in pub_files:copy(ROOT/'publication'/name)
    for path in (ROOT/'publication/figures').iterdir():
        if path.is_file():copy(path)
    for directory in ['qa_review','qa_final','qa_approved','qa_browser']:
        for path in (ROOT/'publication'/directory).glob('*.json'):copy(path)
    # Final browser screenshots are small, useful visual evidence.
    for path in (ROOT/'publication/qa_browser').glob('*.png'):copy(path)
    # The superseded manuscript is preserved explicitly as history.
    old=ROOT/'publication/paper_polynomial_checkpoint.md'
    copy(old,Path('publication/history/paper_polynomial_checkpoint.md'))
    (DEST/'publication/history/README.md').write_text(
        '# Historical internal checkpoint\n\nThis is the earlier polynomial-only manuscript checkpoint, '
        'preserved before the stronger conventional result and final economic comparator correction. '
        'It is superseded by publication/paper.md and is not the final research-review edition.\n')
    (DEST/'EXCLUDED_WORKING_SOURCES.json').write_text(json.dumps({
        'reason':'Full third-party paper working copies, unrelated source checkouts, caches and raw source-history collections are excluded. Authored audits, exact new evidence and citations remain.',
        'paths':omitted},indent=2)+'\n')
    files=[p for p in DEST.rglob('*') if p.is_file()]
    manifest={'edition':'AGI-ALPHA-CERTIFIED-BOUNDARY-20261027-v1',
              'files':[{'path':str(p.relative_to(DEST)),'bytes':p.stat().st_size,
                        'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(files)]}
    (DEST/'MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (DEST/'SHA256SUMS').write_text(''.join(r['sha256']+'  '+r['path']+'\n' for r in manifest['files']))
    archive=DEST.parent/'AGI_ALPHA_Certified_Boundary_v1.zip'
    with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for path in sorted(DEST.rglob('*')):
            if path.is_file():z.write(path,arcname=str(Path(DEST.name)/path.relative_to(DEST)))
    with zipfile.ZipFile(archive) as z:
        if z.testzip() is not None:raise ValueError('ZIP integrity check failed')
    aliases={'paper.pdf':'AGI_ALPHA_FLYWHEEL_Certified_Boundary_v1.pdf',
             'paper.html':'AGI_ALPHA_FLYWHEEL_Certified_Boundary_v1.html',
             'executive_brief.pdf':'AGI_ALPHA_Executive_Brief_v1.pdf'}
    for source,name in aliases.items():shutil.copyfile(DEST/'publication'/source,DEST.parent/name)
    shutil.copyfile(DEST/'LinkedIn_draft.txt',DEST.parent/'AGI_ALPHA_LinkedIn_Draft_v1.txt')
    print(json.dumps({'package_root':str(DEST),'file_count':len(manifest['files']),
                      'archive':str(archive),'archive_bytes':archive.stat().st_size,
                      'archive_sha256':hashlib.sha256(archive.read_bytes()).hexdigest()},indent=2))


if __name__=='__main__':main()
