#!/usr/bin/env python3
"""Rebuild the recorded edition in a NEW directory; never alter original evidence."""
import argparse
import shutil
import subprocess
import sys
from pathlib import Path
sys.dont_write_bytecode = True
from common import DEFAULT_ROOT, copy_files, new_destination, verify_freeze, write_json

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=DEFAULT_ROOT)
    parser.add_argument('--destination', type=Path, required=True)
    parser.add_argument('--prepare-only', action='store_true', help='Copy build inputs but execute no figure, browser, or TeX build.')
    parser.add_argument('--browser-only', action='store_true', help='Build the standalone browser file without figures or TeX.')
    args = parser.parse_args()
    source = args.source.resolve()
    freeze = verify_freeze(source)
    destination = new_destination(source, args.destination)
    names = [entry['path'] for entry in freeze['files']] + ['protocol/FREEZE.json', 'protocol/FREEZE.sha256']
    if (source / 'verification/verify_clean_build.py').is_file():
        names.append('verification/verify_clean_build.py')
    for folder in ['paper', 'figures', 'economics_post', 'browser']:
        for path in (source / folder).iterdir():
            if path.is_file() and path.suffix.lower() in {'.py', '.tex', '.bib', '.json', '.md', '.html'} or path.is_file() and path.name == 'LICENSE':
                names.append(str(path.relative_to(source)))
    # Recorded data used by the browser and figure builders; no original file is modified.
    names += ['raw/ANALYSIS.json', 'raw/ENVIRONMENT.json', 'raw/primary/results.json', 'raw/scale/results.json',
              'raw/controls/controls.json', 'raw/controls/source-identity.json', 'raw/controls/evidence-manifest.json',
              'raw/showcase/brief.json', 'raw/showcase/input.json', 'raw/showcase/receipt.json', 'raw/showcase/acceptance.json',
              'raw/showcase/OUTPUT_MANIFEST.json', 'raw/showcase/output/summary.json', 'raw/showcase/delivery.zip',
              'raw/showcase/output/successor-tool.mjs', 'raw/successor-report/receipt.json', 'raw/successor-report/acceptance.json',
              'raw/successor-report/lineage.json', 'raw/successor-report/output/analysis.json']
    copied = copy_files(source, destination, names)
    report = {'status': 'PREPARED', 'scope': 'Rebuild original recorded edition, not a new experiment or new paper claims.', 'copied_files': copied, 'steps': []}
    write_json(destination / 'PUBLICATION_REBUILD.json', report)
    if args.prepare_only:
        print('PREPARED_ONLY: ' + str(destination))
        return 0
    def command(label, argv, cwd):
        result = subprocess.run(argv, cwd=cwd, capture_output=True, text=True)
        (destination / (label + '.stdout.txt')).write_text(result.stdout)
        (destination / (label + '.stderr.txt')).write_text(result.stderr)
        report['steps'].append({'step': label, 'argv': argv, 'exit_code': result.returncode})
        write_json(destination / 'PUBLICATION_REBUILD.json', report)
        if result.returncode:
            raise RuntimeError(label + ' failed; new-directory logs retained.')
    if not args.browser_only:
        if not shutil.which('latexmk'):
            raise RuntimeError('latexmk must already be installed. No package installation is performed.')
        command('figures', [sys.executable, 'figures/make_figures.py'], destination)
        # Preserve the proven table macro structure; refresh its contents after economics-row regeneration.
        # Use the macro names actually committed in the recorded source.
        current = (source / 'paper/table-data.tex').read_text()
        import re
        defined = re.findall(r'\\newcommand\{\\([^}]+)\}', current)
        if len(defined) != 3:
            raise ValueError('Unexpected committed table macro structure; inspect before rebuilding.')
        table = []
        for stem, macro in zip(['complexity', 'scale', 'economics'], defined):
            table.append('\\newcommand{\\' + macro + '}{%\n' + (destination / 'paper' / (stem + '-rows.tex')).read_text().rstrip() + '\n}\n')
        (destination / 'paper/table-data.tex').write_text('\n'.join(table))
        command('paper', ['latexmk', '-pdf', '-interaction=nonstopmode', '-halt-on-error', 'main.tex'], destination / 'paper')
    command('browser', [sys.executable, 'browser/build_demo.py'], destination)
    report['status'] = 'BUILT_REQUIRES_RENDERED_VISUAL_REVIEW'
    report['note'] = 'Generated timestamps and host TeX/font versions may change bytes. Recheck every PDF page; no visual certification is inherited.'
    write_json(destination / 'PUBLICATION_REBUILD.json', report)
    print('BUILT in isolated directory: ' + str(destination))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
