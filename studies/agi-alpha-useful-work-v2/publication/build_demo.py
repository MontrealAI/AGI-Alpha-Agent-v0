# SPDX-License-Identifier: Apache-2.0
"""Build a self-contained bilingual decision demo from sealed actual artifacts."""
from __future__ import annotations
import base64
import datetime
import hashlib
import io
import json
from pathlib import Path
import time
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PUB = ROOT / 'publication'


def read(path):
    return json.loads(path.read_text())


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def bundle(directory):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(directory.rglob('*')):
            if path.is_file():
                info = zipfile.ZipInfo(str(path.relative_to(directory)), (2026, 10, 26, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o100644 << 16
                archive.writestr(info, path.read_bytes())
        supporting = ['data/consumer/api.py', 'data/consumer/models.py', 'src/manual_probe.py',
                      'src/verify_component.py', 'src/measured_run.py', 'native/LICENSE.Alpha']
        index = []
        for relative in supporting:
            raw = (ROOT / relative).read_bytes()
            name = 'supporting-source/' + relative
            info = zipfile.ZipInfo(name, (2026, 10, 26, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, raw)
            index.append({'path': name, 'sha256': sha(raw), 'bytes': len(raw)})
        archive.writestr('SUPPORTING_SOURCE.json', json.dumps({
            'schema': 'decision-download-supporting-source/v1', 'original_packet_files_unchanged': True,
            'files': index, 'source': 'AGI-Alpha-Agent-v0 consumer eb07086ac42799ff45f7b1c946a2f7c514bd3bbc; study source freeze f417768b69a6729000d5ce9d10393bfac7eec45b7ce448a0d61c711a6662530c',
            'reuse': 'Apache-2.0 license copy retained. Original notices remain in copied source.',
            'reproduction': 'This is the inspectable decision packet with supporting source. Use the complete companion for dependency wheels, the full execution closure and relocated offline replay.'
        }, indent=2) + '\n')
    raw = buffer.getvalue()
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        if archive.testzip() is not None:
            raise ValueError('EMBEDDED_DOWNLOAD_CRC')
    return {'base64': base64.b64encode(raw).decode(), 'sha256': sha(raw), 'bytes': len(raw)}


def main():
    wall, cpu = time.perf_counter(), time.process_time()
    summary = read(ROOT / 'results/economic-analysis-01/summary.json')
    campaign = read(ROOT / 'results/confirmation/campaign.json')
    packets = []
    paths = [('development', ROOT / 'results/development/first-delivery-corrected')]
    paths += [(row['mission'], ROOT / 'results/confirmation' / row['mission'] / 'retained/delivery/package')
              for row in read(ROOT / 'protocol/primary-protocol.json')['mission_order']]
    for mission, directory in paths:
        decision_raw = (directory / 'decision.json').read_bytes()
        decision = json.loads(decision_raw)
        patch = (directory / 'proposed-component-lock.patch').read_text()
        changes = [{'package': key, 'before': value, 'after': decision['after_versions'][key]}
                   for key, value in decision['before_versions'].items() if value != decision['after_versions'][key]]
        packets.append({'id': mission, 'decision': decision, 'decision_sha256': sha(decision_raw),
                        'decision_text': decision_raw.decode(), 'patch': patch, 'changes': changes,
                        'download': bundle(directory), 'path': str(directory.relative_to(ROOT))})
    data = {'packets': packets, 'by_arm': summary['by_arm'],
            'runs': [{key: row[key] for key in ['mission_id', 'arm', 'accepted', 'decision',
                'request_to_package_wall_seconds', 'mechanical_wall_seconds', 'measured_local_cpu_seconds',
                'actual_manual_finalizations', 'evidence_sha256']} for row in summary['runs']],
            'freeze_sha256': sha((ROOT / 'protocol/source-freeze.json').read_bytes()),
            'campaign_sha256': sha((ROOT / 'results/confirmation/campaign.json').read_bytes()),
            'primary_started_at': campaign['started_at'], 'primary_ended_at': campaign['ended_at'],
            'economics': {'marginal_money_usd': None, 'recurring_money_usd': None, 'fully_loaded_money_usd': None,
                          'customer_price_usd': None, 'customer_savings_usd': None, 'actual_collections_usd': 0,
                          'available_cash_usd': None, 'investment_repaid': None}}
    (PUB / 'demo-data.json').write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n')
    template = (PUB / 'demo-template.html').read_text()
    html = template.replace('__SEALED_DATA__', json.dumps(data, ensure_ascii=False).replace('</', '<\\/'))
    output = PUB / 'AGIALPHA_Useful_Work_Demo.html'
    output.write_text(html)
    record = {'schema': 'bilingual-demo-construction/v1', 'created_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'html_sha256': sha(output.read_bytes()), 'bytes': output.stat().st_size,
              'packets': [{'mission': row['id'], 'zip_sha256': row['download']['sha256'], 'zip_bytes': row['download']['bytes'],
                           'decision_sha256': row['decision_sha256']} for row in packets],
              'wall_seconds': time.perf_counter() - wall, 'process_cpu_seconds': time.process_time() - cpu,
              'money_usd': None, 'new_missions': 0, 'note': 'Presentation and exact embedded downloads; no new experiment or price assumption.'}
    (PUB / 'demo-construction.json').write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps({key: record[key] for key in ['html_sha256', 'bytes', 'wall_seconds']}))


if __name__ == '__main__':
    main()
