# SPDX-License-Identifier: Apache-2.0
"""Package original grouped-change decisions and an actionable bilingual matrix."""
from __future__ import annotations

import datetime
import hashlib
import json
from pathlib import Path
import time
import zipfile

ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / 'production'
SOURCE = ROOT / 'vendor/useful-work-v2'
RUN = SOURCE / 'joint-study/run-001'


def main():
    started, wall, cpu = datetime.datetime.now(datetime.timezone.utc).isoformat(), time.perf_counter(), time.process_time()
    out = HERE / 'packets'
    out.mkdir(exist_ok=False)
    audit = json.loads((HERE / 'joint-results-audit.json').read_text())
    selection = json.loads((HERE / 'joint-selection.json').read_text())
    rows = []
    for target in selection['targets']:
        ident = target['mission_id']
        packet = RUN / 'results' / ident / 'retained/delivery/package'
        destination = out / ('AGI_ALPHA_' + ident.replace('-', '_') + '_Decision.zip')
        with zipfile.ZipFile(destination, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for path in sorted(packet.rglob('*')):
                if not path.is_file():
                    continue
                rel = str(path.relative_to(packet))
                info = zipfile.ZipInfo(rel, (2026, 10, 26, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o644 << 16
                archive.writestr(info, path.read_bytes())
        extraction = out / 'extraction-check' / ident
        with zipfile.ZipFile(destination) as archive:
            assert archive.testzip() is None
            for name in archive.namelist():
                assert not Path(name).is_absolute() and '..' not in Path(name).parts
            archive.extractall(extraction)
            files = archive.namelist()
        for name in files:
            assert (extraction / name).read_bytes() == (packet / name).read_bytes()
        decision = json.loads((packet / 'decision.json').read_text())
        rows.append({'mission_id': ident, 'target_versions': target['versions'],
                     'decision': decision['decision'], 'packet': destination.name,
                     'bytes': destination.stat().st_size, 'members': len(files),
                     'sha256': hashlib.sha256(destination.read_bytes()).hexdigest(),
                     'decision_sha256': hashlib.sha256((packet / 'decision.json').read_bytes()).hexdigest(),
                     'actual_extraction_verified': True, 'customer_acceptance_observed': False,
                     'authority': 'Component research evidence only; preserve native application lock pending full qualification.'})
    per_arm = []
    for original in audit['per_arm']:
        row = dict(original)
        row['mean_local_cpu_seconds'] = row['total_local_cpu_seconds'] / row['evaluations']
        per_arm.append(row)
    summary = {'schema': 'game-market-joint-summary/v1', 'unique_missions': 4, 'arm_evaluations': 12,
               'accepted_evaluations': sum(x['accepted'] for x in audit['per_arm']),
               'new_customer_jobs': 0, 'actual_collections_usd': 0,
               'per_arm': per_arm, 'per_mission': audit['per_mission'], 'packets': rows,
               'shared_setup_cpu_seconds': audit['setup_cpu_seconds'],
               'all_delivery_cpu_seconds': audit['delivery_cpu_seconds'],
               'shared_setup_wall_seconds': audit['setup_wall_seconds'],
               'complete_monetary_cost_usd': None,
               'unmeasured': audit['unmeasured'],
               'freeze_sha256': audit['freeze_sha256'], 'campaign_sha256': audit['campaign_sha256'],
               'source_freshness': 'Previously exposed dependency bodies in four new joint tuples; no prospective orders or independent defect-family claim.',
               'claim_boundary': 'Four new grouped component assessments; same retained productive asset. No new successor asset or economic admission.'}
    (HERE / 'joint-summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    lines = ['# Grouped dependency-refresh decision matrix / Matrice de décision', '',
             '**Measured:** four new combined dependency tuples, twelve A/B/C assessments, all accepted under the unchanged finite component contract. These are research-proposed maintenance options, not commissioned customer work.', '',
             '**Mesuré :** quatre nouvelles combinaisons de dépendances, douze évaluations A/B/C, toutes acceptées selon le contrat limité aux composants. Ce sont des options de maintenance proposées pour la recherche, et non des commandes clients.', '',
             'Baseline / Référence: Starlette 1.7.0, Pydantic 2.13.5, pydantic-core 2.46.5; original FastAPI 0.141.1 bridge and native consumer remain unchanged.', '',
             '| Option | Starlette | Pydantic | pydantic-core | A / B / C | Actual retained packet / Dossier retenu |',
             '|---|---:|---:|---:|---|---|']
    for row in rows:
        v = row['target_versions']
        lines.append('| ' + row['mission_id'] + ' | ' + v['starlette'] + ' | ' + v['pydantic'] + ' | '
                     + v['pydantic-core'] + ' | Scoped preservation / Préservation limitée | [' + row['packet']
                     + '](packets/' + row['packet'] + ') |')
    lines += ['', '## Practical action', '',
              'Each packet binds 61 required before/after checks, source and wheel identities, execution and independent-verification receipts, its decision and an exact proposed component-lock patch. Carry the preserved component evidence into full application and platform qualification. Keep the current native application lock until the existing owner and release gates pass. The finite pass does not establish authentication, persistence, production deployment, security or all possible behaviors.', '',
              'Unzip a packet and open its `report.html` or `README.md`. The complete companion supplies the unchanged execution sources, exact offline wheels and the frozen replay procedure; embedded historical absolute paths are custody records, not commands to alter those original locations.', '',
              '## Suite pratique', '',
              'Chaque dossier relie 61 contrôles requis avant et après, les identités du code source et des roues Python, les reçus d’exécution et de vérification indépendante, sa décision et un correctif exact du verrou des composants. Utiliser ces preuves pour poursuivre la qualification complète de l’application et des plateformes. Conserver le verrou natif actuel jusqu’à la réussite des contrôles des responsables et de publication. La conformité limitée ne démontre ni authentification, ni persistance, ni déploiement, ni sécurité, ni tous les comportements possibles.', '',
              'Décompresser un dossier et ouvrir `report.html` ou `README.md`. Le compagnon complet conserve les sources d’exécution, les roues exactes utilisables hors ligne et la procédure figée de reproduction. Les chemins absolus historiques sont des traces de provenance, pas des instructions pour modifier leurs emplacements d’origine.', '',
              '## Economic interpretation / Interprétation économique', '',
              'A required four explicit AI researcher dispositions; both B and conventional C required zero. This is automatic finalization within the tested scope, not measured human labor saved. Accepted quality ties C. Complete construction/delivery money, active attention and customer effort remain unknown; actual customer collections are zero. The 15-second body timeout runs concurrently before/after and cannot be counted twice to invent a caching benefit.', '',
              'A a nécessité quatre décisions explicites de l’agent de recherche IA ; B et la méthode conventionnelle C n’en ont nécessité aucune. Il s’agit d’une finalisation automatique dans le périmètre testé, non d’un gain mesuré de temps humain. La qualité acceptée égale C. Les coûts monétaires complets, le temps d’attention actif et l’effort client restent inconnus ; les encaissements clients observés sont nuls.', '',
              'The source/input freeze remained exact across all 144 files. Eight B/C native packs retained HOLD, empty authority and disconnected settlement. No new productive successor was built or admitted.', '']
    (HERE / 'GROUPED_DECISIONS_EN_FR.md').write_text('\n'.join(lines))
    receipt = {'schema': 'game-market-joint-packet-packaging/v1', 'started_at': started,
               'ended_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
               'wall_seconds': time.perf_counter() - wall, 'process_cpu_seconds': time.process_time() - cpu,
               'packets': rows, 'complete_cost_usd': None, 'new_primary_missions': 0,
               'scope': 'Packaging and actual extraction/hash checking of already completed outputs; no extra jobs.'}
    (HERE / 'joint-packaging-receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps({'packets': len(rows), 'total_bytes': sum(x['bytes'] for x in rows),
                      'wall_seconds': receipt['wall_seconds'], 'process_cpu_seconds': receipt['process_cpu_seconds']}))


if __name__ == '__main__':
    main()
