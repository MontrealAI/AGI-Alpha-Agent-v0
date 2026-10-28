#!/usr/bin/env python3
"""Close the distributable research edition with deterministic ZIP metadata.

Run after document/browser QA. Does not modify experimental source or results.
The archive cannot contain itself; its external receipt binds the final ZIP.
"""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import zipfile

ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT / 'release'
STAMP = (2026, 10, 28, 12, 0, 0)
TOP = 'AGI_Alpha_Possibility_Engine'
TRANSIENT_DIRS = {'.deps', '.cache', '.review_transport', '__pycache__', '.pytest_cache', '.git', 'node_modules', 'replay'}
ROOT_FILES = {'README.txt', 'Developer_Handoff.txt', 'LinkedIn_Draft.txt', 'THIRD_PARTY_NOTICES.txt',
              'LICENSE', 'requirements.txt', 'requirements-edition.txt', 'requirements-verification.txt'}
DIRECTORIES = {'src', 'tests', 'data', 'results', 'protocol', 'paper', 'web', 'audit', 'research'}
EXCLUDE_EXACT = {'research/source_editions/issue4850_snapshot.json', 'audit/publication_receipt.json',
                 'audit/publication_preflight.json', 'audit/publication_upload_progress.json'}


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def record(path):
    return {'path': path.relative_to(ROOT).as_posix(), 'bytes': path.stat().st_size, 'sha256': digest(path)}


def add_file(z, path, name):
    info = zipfile.ZipInfo(name, STAMP)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o100644 << 16
    z.writestr(info, path.read_bytes(), compresslevel=6)


def include(path):
    rel = path.relative_to(ROOT)
    if not path.is_file() or any(p in TRANSIENT_DIRS for p in rel.parts):
        return False
    if rel.as_posix() in EXCLUDE_EXACT or path.suffix in {'.pyc', '.pyo'}:
        return False
    if len(rel.parts) == 1:
        return rel.name in ROOT_FILES
    if rel.parts[0] not in DIRECTORIES:
        return False
    if rel.parts[0] == 'paper' and path.suffix in {'.aux', '.log', '.out', '.toc', '.fls', '.fdb_latexmk', '.synctex'}:
        return False
    with path.open('rb') as f:
        if f.read(4) == b'\x7fELF':
            return False
    return True


def main():
    RELEASE.mkdir(exist_ok=True)
    required = ['paper/AGI_Alpha_Possibility_Engine.pdf', 'paper/Executive_Brief.pdf', 'web/index.html',
                'results/browser_qa.json', 'audit/edition_integrity.json', 'audit/handoff_checks.json',
                'research/claims.json', 'README.txt', 'Developer_Handoff.txt',
                'results/business_confirmation_journals.jsonl.gz']
    for p in required:
        if not (ROOT / p).is_file():
            raise SystemExit('Required artifact missing: ' + p)
    source_files = sorted((ROOT / 'paper').glob('*.tex')) + sorted((ROOT / 'paper/figures').glob('*.pdf')) + [ROOT/'paper/BUILD.txt']
    source_zip = RELEASE / 'AGI_Alpha_Possibility_Engine_LaTeX.zip'
    with zipfile.ZipFile(source_zip, 'w') as z:
        for p in source_files:
            add_file(z, p, 'AGI_Alpha_LaTeX/' + p.relative_to(ROOT / 'paper').as_posix())
    policy = {
        'schema': 'possibility_engine.packaging_policy.v1',
        'included': 'Complete research source, protocols, summaries, detailed traces, full journal, failures, paper, brief, browser and dependencies necessary as source.',
        'excluded': ['Dependency downloads and caches', 'Native ELF build products that can be rebuilt from included sources',
                     'LaTeX transient build files', '717-comment issue working snapshot; eight relevant exact receipts retained instead',
                     'Publication transport/receipt generated after archive closure', 'The companion archive itself'],
        'issue_custody': 'research/coordination_evidence.json retains eight relevant receipt bodies, dates, source URLs and SHA256 identities. Full working issue snapshot remains locally preserved.',
        'source_zip': record(source_zip),
        'internal_manifest_self_exclusion': 'files_manifest.json does not hash itself; the external release receipt hashes that manifest and the complete ZIP.',
        'browser_downloads': 'Use the extracted folder for document links. The complete companion ZIP is distributed alongside the edition; its internal reader links to the bundle manifest, avoiding a nonexistent self-contained ZIP.'
    }
    (RELEASE/'packaging_policy.json').write_text(json.dumps(policy, indent=2)+'\n')
    files = sorted(p for p in ROOT.rglob('*') if include(p))
    files += [source_zip, RELEASE/'packaging_policy.json']
    manifest = {'schema': 'possibility_engine.files_manifest.v1', 'edition': '2026-10-28-v1',
                'decision': 'STOP standalone expansion; NO FLAGSHIP EARNED',
                'root_in_archive': TOP, 'file_count_excluding_manifest': len(files),
                'total_uncompressed_bytes_excluding_manifest': sum(p.stat().st_size for p in files),
                'files': [record(p) for p in files]}
    manifest_path = RELEASE/'files_manifest.json'
    manifest_path.write_text(json.dumps(manifest, indent=2)+'\n')
    archive = RELEASE/'AGI_Alpha_Possibility_Engine_Companion.zip'
    with zipfile.ZipFile(archive, 'w') as z:
        for p in files+[manifest_path]:
            add_file(z, p, TOP+'/'+p.relative_to(ROOT).as_posix())
    errors=[]
    with zipfile.ZipFile(archive) as z:
        bad = z.testzip()
        if bad: errors.append('CRC mismatch: '+bad)
        for entry in manifest['files']:
            data=z.read(TOP+'/'+entry['path'])
            if len(data)!=entry['bytes'] or hashlib.sha256(data).hexdigest()!=entry['sha256']:
                errors.append('Byte/hash mismatch: '+entry['path'])
        if len(z.infolist()) != len(files)+1: errors.append('Unexpected archive member count')
    receipt={'schema':'possibility_engine.release_receipt.v1',
             'created_at_utc':datetime.now(timezone.utc).isoformat(),
             'archive':record(archive), 'latex_source':record(source_zip), 'manifest':record(manifest_path),
             'paper':record(ROOT/'paper/AGI_Alpha_Possibility_Engine.pdf'),
             'brief':record(ROOT/'paper/Executive_Brief.pdf'), 'browser':record(ROOT/'web/index.html'),
             'archive_entries':len(files)+1, 'verified_against_manifest':True,
             'errors':errors, 'passed':not errors,
             'publication':'Local artifact closure; remote publication has a separate verified receipt.'}
    (RELEASE/'release_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt,indent=2))
    if errors:raise SystemExit(1)


if __name__=='__main__':
    main()
