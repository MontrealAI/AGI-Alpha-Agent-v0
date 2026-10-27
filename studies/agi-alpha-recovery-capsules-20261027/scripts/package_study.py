# SPDX-License-Identifier: Apache-2.0
"""Make deterministic study/LaTeX archives and verify the content manifest."""
import argparse
import hashlib
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OMIT_SUFFIXES = {'.pyc', '.aux', '.log', '.blg', '.out', '.toc'}
MANIFEST_EXCLUSIONS = {'MANIFEST.json', 'PUBLICATION_RECEIPT.json'}


def selected_files():
    return [p for p in sorted(ROOT.rglob('*')) if p.is_file()
            and '__pycache__' not in p.parts and p.suffix not in OMIT_SUFFIXES
            and p.relative_to(ROOT).parts[0] != 'reproduction']


def identity(path):
    content = path.read_bytes()
    return {'path': path.relative_to(ROOT).as_posix(), 'bytes': len(content),
            'sha256': hashlib.sha256(content).hexdigest(),
            'git_blob_sha1': hashlib.sha1(b'blob ' + str(len(content)).encode() + b'\0' + content).hexdigest()}


def archive(path, entries):
    with zipfile.ZipFile(path, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for name, content in sorted(entries):
            info = zipfile.ZipInfo(name, date_time=(2026, 10, 27, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            z.writestr(info, content)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=ROOT.parent / 'deliverables')
    parser.add_argument('--verify', action='store_true')
    args = parser.parse_args()
    if args.verify:
        manifest = json.loads((ROOT / 'MANIFEST.json').read_text())
        failures = [r['path'] for r in manifest['files'] if not (ROOT / r['path']).is_file()
                    or identity(ROOT / r['path']) != r]
        if failures:
            raise SystemExit('Content mismatch: ' + ', '.join(failures))
        print(json.dumps({'manifest_verified': True, 'files': len(manifest['files']),
                          'exclusions': sorted(MANIFEST_EXCLUSIONS)}))
        return
    files = [p for p in selected_files() if p.relative_to(ROOT).as_posix() not in MANIFEST_EXCLUSIONS]
    manifest = {'schema': 'recovery-capsules-content-manifest/v1',
                'edition': 'Recovery Capsules: Making Stranded Analysis Usable',
                'exclusions': sorted(MANIFEST_EXCLUSIONS),
                'exclusion_reason': 'The manifest cannot hash itself. The publication receipt is added after the immutable Git content commit exists; it does not amend scientific content.',
                'intermediate_exclusions': 'Python caches, TeX build intermediates/logs and new reproduction/ outputs; preserved scientific failure evidence remains included.',
                'files': [identity(p) for p in files]}
    (ROOT / 'MANIFEST.json').write_text(json.dumps(manifest, indent=2) + '\n')
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    prefix = 'AGI_ALPHA_Recovery_Capsules'
    full = out / 'AGI_ALPHA_Recovery_Capsules_Complete_Study.zip'
    archive(full, [(prefix + '/' + p.relative_to(ROOT).as_posix(), p.read_bytes()) for p in selected_files()])
    latex_files = [ROOT / 'publication' / n for n in ['paper.tex', 'body.tex', 'references.bib', 'paper.bbl', 'executive-brief.tex']]
    latex_files += sorted((ROOT / 'figures').glob('*.pdf'))
    instructions = ('AGI ALPHA FLYWHEEL — When Capability Creates Opportunity\n'
                    'Recovery Capsules: Making Stranded Analysis Usable\n'
                    'Vincent Boucher — President of MONTREAL.AI\n\n'
                    'In publication/, run pdflatex -interaction=nonstopmode -halt-on-error paper.tex; '
                    'bibtex paper; then pdflatex twice. Compile executive-brief.tex with pdflatex.\n'
                    'The supplied PDF figures are the exact publication figures. Standard TeX Live packages are required.\n'
                    'The complete study archive provides executable figures, economic inputs, delivery cases and evidence.\n')
    source = out / 'AGI_ALPHA_FLYWHEEL_LaTeX_Source.zip'
    entries = [(prefix + '/' + p.relative_to(ROOT).as_posix(), p.read_bytes()) for p in latex_files]
    entries.append((prefix + '/README_compile.txt', instructions.encode()))
    entries.append((prefix + '/LICENSE', (ROOT / 'LICENSE').read_bytes()))
    archive(source, entries)
    result = {'manifest_files': len(files), 'archives': [
        {'path': str(p), 'bytes': p.stat().st_size, 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}
        for p in [full, source]]}
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
