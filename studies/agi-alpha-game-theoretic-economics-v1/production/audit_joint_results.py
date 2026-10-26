# SPDX-License-Identifier: Apache-2.0
"""Independent post-run accounting/identity checks for the fixed joint-profile extension."""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
from pathlib import Path
import statistics

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'vendor/useful-work-v2'
RUN = SOURCE / 'joint-study/run-001'


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, help='New audit receipt path; never overwrite an earlier receipt.')
    args = parser.parse_args()
    freeze = read(ROOT / 'production/joint-freeze.json')
    checked = 0
    for entry in freeze['files']:
        assert sha(ROOT / entry['path']) == entry['sha256'], entry['path']
        checked += 1
    sequence = read(ROOT / 'production/joint-protocol.json')['sequence']
    campaign = read(RUN / 'campaign.json')
    assert campaign.get('complete') is True and campaign['pending'] is None
    assert len(campaign['results']) == len(sequence) == 12
    selection = read(ROOT / 'production/joint-selection.json')
    expected = {row['mission_id']: row['versions'] for row in selection['targets']}
    assert len(expected) == 4
    setup = read(RUN / 'setup.json')
    assert len(setup['environments']) == 5
    assert setup['complete'] is True
    for env in setup['environments']:
        preparation = read(RUN / 'environments' / env['id'] / 'preparation.json')
        assert env['complete'] is True and preparation['network_requests'] == 0
        assert sha(RUN / 'environments' / env['id'] / 'preparation.json') == env['preparation_sha256']
        assert len(preparation['wheels']) == 10
        for wheel in preparation['wheels']:
            assert sha(RUN / 'environments' / env['id'] / 'wheels' / wheel['filename']) == wheel['sha256']
    rows = []
    audited_payloads = 0
    for row, fixed in zip(campaign['results'], sequence, strict=True):
        assert row['mission'] == fixed['mission'] and row['arm'] == fixed['arm']
        folder = RUN / 'results' / row['mission'] / row['arm']
        base = folder if row['arm'] == 'manual' else folder / 'delivery'
        packet = base / 'package'
        decision = read(packet / 'decision.json')
        assert sha(packet / 'decision.json') == row['decision_sha256']
        assert decision['before_versions'] == selection['baseline']
        assert decision['after_versions'] == expected[row['mission']]
        assert decision['decision'] == row['decision']
        assert row['accepted'] == (row['decision'] in ['SCOPED_COMPONENT_PRESERVED', 'COMPONENT_REGRESSION'])
        manifest = read(packet / 'artifact-manifest.json')
        names = set()
        for entry in manifest['files']:
            assert entry['path'] not in names
            names.add(entry['path'])
            path = packet / entry['path']
            assert path.resolve().is_relative_to(packet.resolve())
            assert path.stat().st_size == entry['bytes'] and sha(path) == entry['sha256']
            audited_payloads += 1
        pair = base / 'pair'
        p = read(pair / 'pair.json')
        assert p['custody_complete'] is True
        counts = {}
        for side in ['before', 'after']:
            ver = read(pair / (side + '-verification.json'))
            obs = pair / (side + '-observations.json')
            assert sha(obs) == ver['observations_sha256']
            assert ver['native_import_route'] is True
            assert ver['contract_sha256'] == selection['contract']['sha256']
            assert sum(ver['counts'].values()) == 61
            counts[side] = ver['counts']
        if row['arm'] != 'manual':
            pack = read(folder / 'pack.json')
            assert pack['evaluation']['admission'] == 'HOLD'
            assert pack['evaluation']['authority'] == []
            assert pack['evaluation']['settlement'] == 'NOT_CONNECTED'
            inspection = read(folder / 'inspection.json')
            assert inspection['activeProof'] == [] and inspection['activeAuthority'] == []
            receipt = row['receipt']
            wall = receipt['wall_seconds']
            cpu = receipt['child_cpu_seconds'] + receipt['meter_cpu_seconds']
        else:
            receipts = [row['pair_receipt'], row['finalization_receipt']]
            wall = sum(x['wall_seconds'] for x in receipts)
            cpu = sum(x['child_cpu_seconds'] + x['meter_cpu_seconds'] for x in receipts)
            assert row['explicit_finalizations'] == 1
            assert decision['manual_disposition']['supplied'] == decision['decision']
        rows.append({'mission_id': row['mission'], 'arm': row['arm'], 'accepted': row['accepted'],
                     'decision': row['decision'], 'counts': counts, 'mechanical_wall_seconds': wall,
                     'local_cpu_seconds': cpu, 'explicit_finalizations': row['explicit_finalizations'],
                     'decision_sha256': row['decision_sha256'],
                     'complete_money_usd': None, 'active_human_minutes': None})
    summary = []
    for arm in ['manual', 'retained', 'conventional']:
        selected = [r for r in rows if r['arm'] == arm]
        summary.append({'arm': arm, 'evaluations': len(selected), 'accepted': sum(r['accepted'] for r in selected),
                        'median_mechanical_wall_seconds': statistics.median(r['mechanical_wall_seconds'] for r in selected),
                        'mean_mechanical_wall_seconds': statistics.mean(r['mechanical_wall_seconds'] for r in selected),
                        'total_local_cpu_seconds': sum(r['local_cpu_seconds'] for r in selected),
                        'median_local_cpu_seconds': statistics.median(r['local_cpu_seconds'] for r in selected),
                        'explicit_finalizations': sum(r['explicit_finalizations'] for r in selected),
                        'complete_money_usd': None, 'active_human_minutes': None})
    measured_setup_cpu = sum(x['receipt']['child_cpu_seconds'] + x['receipt']['meter_cpu_seconds'] for x in setup['environments'])
    result = {'schema': 'game-market-joint-results-audit/v1', 'audited_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'freeze_sha256': sha(ROOT / 'production/joint-freeze.json'), 'frozen_files_unchanged': checked,
              'campaign_sha256': sha(RUN / 'campaign.json'), 'public_preregistration':
                  'https://github.com/MontrealAI/AGI-Alpha-Agent-v0/issues/4850#issuecomment-6421473941',
              'checks': {'sequence_complete': True, 'four_unique_research_missions': True,
                         'all_package_payloads_checked': audited_payloads, 'five_offline_environments': True,
                         'all_native_packs_hold_no_authority': True},
              'per_mission': rows, 'per_arm': summary, 'setup_cpu_seconds': measured_setup_cpu,
              'delivery_cpu_seconds': sum(x['local_cpu_seconds'] for x in rows),
              'setup_wall_seconds': sum(x['receipt']['wall_seconds'] for x in setup['environments']),
              'modeled_or_observed_customer_jobs': 0, 'actual_collections_usd': 0,
              'complete_cost_usd': None, 'unmeasured': ['Source acquisition/copy and discovery compute',
                  'All assistant authoring inference and applicable billing', 'All active human attention and customer effort',
                  'Packaging/audit/publication not yet complete at this receipt', 'Complete inherited construction and maintenance'],
              'interpretation': 'Four grouped tuples with seen dependency bodies; not four independent defects. Twelve arm evaluations are four research missions. Timing descriptive only. Canonical same-asset investment remains unknown; no new productive successor constructed.'}
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    output = args.out if args.out is not None else ROOT / 'production/audit-runs' / (stamp + '.json')
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x') as stream:
        stream.write(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'per_arm': summary, 'frozen_files_unchanged': checked, 'package_payloads': audited_payloads,
                      'setup_cpu_seconds': measured_setup_cpu, 'delivery_cpu_seconds': result['delivery_cpu_seconds'],
                      'new_audit_receipt': str(output)}))


if __name__ == '__main__':
    main()
