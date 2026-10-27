# SPDX-License-Identifier: Apache-2.0
"""Create a complete, content-verified research archive and delivery copies."""
import hashlib
import json
import pathlib
import zipfile
import argparse

ROOT = pathlib.Path(__file__).resolve().parent
DEST = ROOT.parent / 'paid-work-alpha-deliverables'
SKIP_DIRS = {'__pycache__', 'pdf_qa', 'browser_screenshots', '.pytest_cache', 'qa_views', '.publication_stage'}
SKIP_SUFFIXES = {'.pyc', '.aux', '.log', '.out', '.toc', '.synctex.gz'}
SKIP_NAMES = {'main.pdf', 'evidence.pdf', 'package_manifest.json', 'internal_preview.html'}
SKIP_RELATIVE = {'baseline/goalos_v93_ascension_lab.html', 'baseline/goalos_validated_skill_graph_diagram.webp', 'evidence/foundations/Gym_Specialist_ASI_Successor_Omega_v2_1_0_Print.pdf', 'evidence/foundations/Gym_Specialist_ASI_Successor_Omega_v2_1_0_Print.txt'}


def include(p):
    return p.is_file() and str(p.relative_to(ROOT)) not in SKIP_RELATIVE and not any(x in SKIP_DIRS for x in p.relative_to(ROOT).parts) and p.suffix not in SKIP_SUFFIXES and p.name not in SKIP_NAMES


def main(compact_scratch=False):
    DEST.mkdir(exist_ok=True)
    for p in ['paper/AGI_ALPHA_Flywheel_Profitable_Work_First.pdf', 'paper/AGI_ALPHA_Flywheel_Evidence_Companion.pdf', 'demo/index.html', 'results/paid_work_final/summary.json', 'results/paid_work_final/freeze.json', 'qa/paid_job_independent_review.md', 'qa/graph_lifecycle_v3_audit.json', 'qa/canonical_reconciliation_v3.json', 'qa/posterior_diagnostic_reconciliation.json', 'qa/recipient_prior_final_review.json', 'qa/pdf_verification.json', 'demo/qa_report.json', 'results/paid_work_sensitivity/run_manifest.json', 'results/paid_work_prior_diagnostic/run_manifest.json', 'README.md']:
        if not (ROOT / p).is_file():
            raise RuntimeError('Missing final artifact: ' + p)
    files = sorted(p for p in ROOT.rglob('*') if include(p))
    manifest = {'study': 'PAID-WORK-ALPHA-2026-10-26-v3', 'basis': 'Executed local network simulation, lifecycle tests and bounded mechanism; no observed commercial activity or frontier job calls.',
                'files': [{'path': str(p.relative_to(ROOT)), 'bytes': p.stat().st_size, 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()} for p in files],
                'exclusions': 'Build caches/intermediates and internal browser/PDF screenshots. Inspected raw website references without a repository license and the all-rights-reserved Gym manuscript are represented by source URLs and hashes rather than redistributed. Failed or superseded scientific runs are retained with their labels.', 'source_reference_exclusions':sorted(SKIP_RELATIVE)}
    mp = ROOT / 'package_manifest.json'
    mp.write_text(json.dumps(manifest, indent=2) + '\n')
    files.append(mp)
    archive = DEST / 'AGI_ALPHA_Flywheel_Research_Package.zip'
    large = [p for p in files if compact_scratch and p.name.endswith('_complete_records.jsonl.gz') and p.stat().st_size > 8_000_000]
    regular = [p for p in files if p not in large]
    def add_file(z, p):
            info = zipfile.ZipInfo('agi-alpha-beyond-beta-v1/' + str(p.relative_to(ROOT)), date_time=(2026, 10, 26, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            z.writestr(info, p.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9):
        pass
    relocated=[]
    # Largest first leaves the maximal available headroom for each transfer.
    for p in sorted(large,key=lambda p:p.stat().st_size,reverse=True):
        expected = hashlib.sha256(p.read_bytes()).hexdigest()
        member = 'agi-alpha-beyond-beta-v1/' + str(p.relative_to(ROOT))
        # Close the central directory and verify the member before removing its
        # redundant scratch copy. The evidence remains byte-for-byte in ZIP.
        with zipfile.ZipFile(archive, 'a', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
            add_file(z,p)
        with zipfile.ZipFile(archive) as z:
            assert hashlib.sha256(z.read(member)).hexdigest()==expected
        relocated.append({'path':str(p.relative_to(ROOT)),'archive_member':member,'sha256':expected})
        p.unlink()
    with zipfile.ZipFile(archive, 'a', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for p in sorted(regular):
            add_file(z, p)
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        for f in manifest['files']:
            assert hashlib.sha256(z.read('agi-alpha-beyond-beta-v1/' + f['path'])).hexdigest() == f['sha256']
    outputs = []
    for source, name in [('paper/AGI_ALPHA_Flywheel_Profitable_Work_First.pdf', 'AGI_ALPHA_Flywheel_Profitable_Work_First.pdf'),
                         ('paper/AGI_ALPHA_Flywheel_Evidence_Companion.pdf', 'AGI_ALPHA_Flywheel_Evidence_Companion.pdf'),
                         ('demo/index.html', 'AGI_ALPHA_Flywheel_EN_FR_Demo.html')]:
        p = DEST / name
        p.write_bytes((ROOT / source).read_bytes())
        outputs.append(p)
    outputs.append(archive)
    receipt = {'archive_members': len(files), 'verified_records_relocated_to_archive':relocated, 'files': [{'path': str(p), 'bytes': p.stat().st_size, 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()} for p in outputs]}
    (DEST / 'delivery_manifest.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--compact-scratch',action='store_true',help='Move large complete-record files into the verified archive, preserving all evidence bytes while avoiding duplicate storage.')
    main(parser.parse_args().compact_scratch)
