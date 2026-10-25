#!/usr/bin/env python3
"""Read-only audit of saved outputs: no producing job, model, or external tool runs."""
import argparse
import collections
import csv
import io
import json
import math
import sys
import zipfile
from pathlib import Path
sys.dont_write_bytecode = True
from common import DEFAULT_ROOT, EXPECTED_FREEZE, child, read_json, sha, verify_freeze

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=DEFAULT_ROOT)
    parser.add_argument('--freeze-only', action='store_true', help='Verify the original freeze and all frozen source files only.')
    parser.add_argument('--hashes-only', action='store_true', help='Check saved evidence/archives without the independent semantic oracle.')
    args = parser.parse_args()
    root = args.root.resolve()
    issues, checks = [], 0
    def check(label, condition, detail=None):
        nonlocal checks
        checks += 1
        if not condition:
            issues.append({'check': label, 'detail': detail})
    freeze = verify_freeze(root)
    checks += len(freeze['files']) + 1
    if args.freeze_only:
        print(json.dumps({'status': 'PASS', 'scope': 'Read-only freeze/source identity audit only', 'checks': checks, 'freeze_sha256': EXPECTED_FREEZE}, indent=2))
        return 0
    oracle = None
    if not args.hashes_only:
        path = root / 'src/reference_reconciliation.py'
        namespace = {'__name__': 'saved_output_oracle', '__file__': str(path)}
        exec(compile(path.read_text(), str(path), 'exec'), namespace)
        oracle = namespace['verify_all']
    packets = [root / 'raw/showcase'] + sorted(p.parent for p in (root / 'raw/primary').glob('*/receipt.json')) + sorted(p.parent for p in (root / 'raw/scale').glob('*/*/receipt.json'))
    check('145 saved reconciliation attempts', len(packets) == 145, len(packets))
    oracle_checks, leaves, accepted = 0, 0, 0
    parent_hash = sha(root / 'raw/showcase/output/successor-tool.mjs')
    public_input = read_json(root / 'raw/showcase/input.json')
    for side, stem in [('left', 'c352bad0'), ('right', 'f836f06e')]:
        inventory = read_json(root / ('protocol/public_inventory_' + stem + '.json'))
        expected_inventory = [{key: str(value) for key, value in entry.items()} for entry in inventory['entries']]
        actual_inventory = list(csv.DictReader(io.StringIO(public_input[side + 'Csv'])))
        check('public input binds frozen inventory: ' + side, actual_inventory == expected_inventory)
    for packet in packets:
        label = str(packet.relative_to(root))
        try:
            receipt, inp = read_json(packet / 'receipt.json'), read_json(packet / 'input.json')
            accepted += receipt.get('accepted') is True
            manifest = read_json(packet / 'OUTPUT_MANIFEST.json')
            recorded_names = {entry['path'] for entry in manifest}
            actual_names = {str(p.relative_to(packet / 'output')) for p in (packet / 'output').rglob('*') if p.is_file()}
            check(label + ': exact file set', recorded_names == actual_names)
            for entry in manifest:
                p = child(packet / 'output', entry['path'])
                check(label + ': ' + entry['path'], p.stat().st_size == entry['bytes'] and sha(p) == entry['sha256'])
                leaves += 1
            for side in ['left', 'right']:
                check(label + ': exact ' + side + ' input', (packet / (side + '.csv')).read_bytes() == inp[side + 'Csv'].encode())
            if packet != root / 'raw/showcase':
                check(label + ': retained bytes', receipt['retained_tool_sha256'] == parent_hash)
            check(label + ': unknown complete cost preserved', receipt.get('fully_allocated_cost') is None and receipt.get('human_active_minutes') is None and receipt.get('human_review_minutes') is None)
            with zipfile.ZipFile(packet / 'delivery.zip') as archive:
                names = archive.namelist()
                check(label + ': archive members', len(names) == len(set(names)) and set(names) == recorded_names | {'acceptance.json', 'OUTPUT_MANIFEST.json'})
                for name in names:
                    disk = packet / name if name in ['acceptance.json', 'OUTPUT_MANIFEST.json'] else child(packet / 'output', name)
                    check(label + ': archived bytes ' + name, archive.read(name) == disk.read_bytes())
            if oracle:
                result = oracle(inp, packet / 'output')
                oracle_checks += result['checks']
                check(label + ': independent semantic oracle', result['accepted'], result['failures'])
        except Exception as exc:
            check(label + ': readable complete evidence', False, type(exc).__name__ + ': ' + str(exc))
    primary, scale = read_json(root / 'raw/primary/results.json'), read_json(root / 'raw/scale/results.json')
    check('36 primary instances', len(primary['records']) == 36)
    check('108 scale attempts in nine batches', len(scale['records']) == 108 and len(scale['batches']) == 9)
    for entry in primary['records']:
        check('primary receipt ' + entry['job_id'], entry == read_json(root / 'raw/primary' / entry['job_id'] / 'receipt.json'))
    for entry in scale['records']:
        check('scale receipt ' + entry['batch'] + '/' + entry['job_id'], entry == read_json(root / 'raw/scale' / entry['batch'] / entry['job_id'] / 'receipt.json'))
    for batch in scale['batches']:
        check('batch throughput ' + batch['batch'], math.isclose(batch['accepted_per_minute'], 60 * batch['accepted'] / batch['wall_seconds'], rel_tol=1e-12))
    controls = read_json(root / 'raw/controls/controls.json')
    check('eight separate controls', controls['controlCaseDenominator'] == 8 and len(controls['cases']) == 8 and controls['businessDeliverablesCounted'] == 0)
    for entry in read_json(root / 'raw/controls/evidence-manifest.json')['files']:
        path = child(root / 'raw/controls', entry['path'])
        check('control hash ' + entry['path'], path.stat().st_size == entry['bytes'] and sha(path) == entry['sha256'])
    for entry in controls['cases']:
        check('control ' + entry['id'], entry['status'] == 'PASS' and all(c['passed'] for c in entry['checks']))
    parents = {read_json(p / 'receipt.json')['job_id']: p for p in packets if 'scale' not in p.relative_to(root).parts}
    groups = collections.defaultdict(list)
    lineage = read_json(root / 'raw/successor-report/lineage.json')
    check('37 successor parents', len(lineage) == 37)
    for entry in lineage:
        path = parents[entry['job_id']] / 'output/guide-result.json'
        value = read_json(path)['metrics']['fieldDifferences']
        check('successor lineage ' + entry['job_id'], entry['guide_sha256'] == sha(path) and entry['field_differences'] == value)
        groups[entry['context']].append(value)
    expected = [{'group': key, 'count': len(values), 'total': sum(values), 'min': min(values), 'max': max(values)} for key, values in sorted(groups.items())]
    aggregate = read_json(root / 'raw/successor-report/output/analysis.json')
    check('successor exact groups', aggregate['groups'] == expected)
    check('successor exact total', aggregate['total'] == sum(sum(values) for values in groups.values()))
    report = {'status': 'PASS' if not issues else 'FINDINGS', 'scope': 'Read-only saved evidence audit; no producing job rerun, no files written.',
              'freeze_sha256': EXPECTED_FREEZE, 'outer_checks': checks, 'independent_oracle_checks': oracle_checks,
              'packets': len(packets), 'receipt_accepted': accepted, 'output_manifest_files': leaves, 'issues': issues}
    print(json.dumps(report, indent=2))
    return 0 if not issues else 1

if __name__ == '__main__':
    raise SystemExit(main())
