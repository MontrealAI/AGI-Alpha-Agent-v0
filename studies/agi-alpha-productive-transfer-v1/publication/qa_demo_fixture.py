# SPDX-License-Identifier: Apache-2.0
"""Generate explicit UI controls only. Never read experiment inputs or outcomes."""
from __future__ import annotations

import argparse
import hashlib
import json
from copy import deepcopy
from pathlib import Path

from build_demo import build


def digest(value: str) -> str:
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


def bilingual(en: str, fr: str) -> dict[str, str]:
    return {'en': en, 'fr': fr}


def fixture() -> dict:
    text = ('# SYNTHETIC UI CONTROL — aucune preuve d’étude\r\n'
            'from qa_dependency import decide\r\n'
            'def consumer(value):\r\n'
            '    return decide(value, removed=True)\r\n'
            '# </script><script>globalThis.QA_INJECTION_EXECUTED=true</script>\r\n'
            '# Literal source tokens: __ENGINE_BUNDLE__ __STUDY_DATA__\r\n')
    sources = {
        'consumer': {'repository': 'synthetic-ui-control/consumer', 'commit': '1' * 40,
                     'path': 'src/fixture_consumer.py', 'sha256': digest(text), 'text': text},
        'before': {'repository': 'synthetic-ui-control/dependency', 'commit': '2' * 40,
                   'path': 'qa_dependency.py', 'text': 'def decide(value, removed=False):\n    return value\n'},
        'after': {'repository': 'synthetic-ui-control/dependency', 'commit': '3' * 40,
                  'path': 'qa_dependency.py', 'text': 'def decide(value):\n    return value\n'},
    }
    for source in sources.values():
        source['sha256'] = digest(source['text'])
    raw = {'schema': 'alpha-transfer-raw-task/v1', 'id': 'UI-CONTROL-01',
           'title': 'SYNTHETIC UI CONTROL', 'purpose': 'UI presentation only; not a production mission.',
           'dependency': {'package': 'qa_dependency', 'importRoots': ['qa_dependency'],
                          'before': {'version': '0.1-fixture'}, 'after': {'version': '0.2-fixture'}},
           'consumer': {'source': 'consumer', 'scopeSymbols': ['consumer']}, 'sources': sources,
           'providerSides': {'before': ['before'], 'after': ['after']}, 'licenseRecords': []}
    call = {'id': 'UI-CALL-01', 'callee': 'decide', 'line': 4, 'column': 11,
            'status': 'BINDING_CONFLICT', 'mappingVerified': True,
            'beforeAccepts': True, 'afterAccepts': False,
            'qualification': 'Synthetic verified-dispatch UI control.',
            'evidence': [{'sourceId': 'consumer', 'line': 4, 'endLine': 4},
                         {'sourceId': 'before', 'line': 1, 'endLine': 2},
                         {'sourceId': 'after', 'line': 1, 'endLine': 2}]}
    arms = {}
    for key in 'ABC':
        arms[key] = {'accepted': True, 'nextAction': 'HOLD_UPDATE_AND_TEST', 'selectedCalls': 1,
                     'coreRecord': {'engineeringAcceptance': True, 'calls': [deepcopy(call)],
                                    'nextAction': 'HOLD_UPDATE_AND_TEST'}, 'unresolvedIntake': [],
                     'resources': {'cpuSeconds': 0.001},
                     'notes': bilingual('SYNTHETIC CONTROL: remove the unsupported keyword and verify behavior.',
                                        'CONTRÔLE SYNTHÉTIQUE : retirer l’argument incompatible et vérifier le comportement.')}
    mission = {'id': raw['id'], 'title': bilingual('SYNTHETIC: explicit signature change',
                                                'SYNTHÉTIQUE : changement de signature explicite'),
               'dependency': raw['dependency'], 'consumerRepo': 'synthetic-ui-control/consumer',
               'sourceLinks': [{'label': bilingual('Unsafe link control is inert', 'Lien non sûr neutralisé'),
                                'url': 'javascript:globalThis.QA_LINK_EXECUTED=true'}],
               'rawInput': raw, 'arms': arms}
    conditional = deepcopy(mission)
    conditional['id'] = conditional['rawInput']['id'] = 'UI-CONTROL-02'
    conditional['title'] = bilingual('SYNTHETIC: unresolved dispatch retained',
                                     'SYNTHÉTIQUE : appel cible non résolu conservé')
    for arm in conditional['arms'].values():
        arm['nextAction'] = arm['coreRecord']['nextAction'] = 'REVIEW_UNRESOLVED_SCOPE'
        arm['coreRecord']['engineeringAcceptance'] = False
        row = arm['coreRecord']['calls'][0]
        row['mappingVerified'] = False
        row['qualification'] = 'Conditional on the declared target; runtime dispatch remains unproved.'
    production = {'schema': 'agi-alpha-intake-transfer-production/v1',
                  'missions': [mission['id'], conditional['id']],
                  'evidenceSHA256': digest('synthetic UI controls, never study evidence'),
                  'completeAcceptanceEvidence': {'status': 'PASS', 'scope': 'complete-useful-deliverable',
                                                 'independentlyVerified': True,
                                                 'receiptSHA256': digest('synthetic receipt'),
                                                 'verifierSHA256': digest('synthetic verifier')}, 'arms': {}}
    for key in 'ABC':
        production['arms'][key] = {'attemptedMissionIds': production['missions'],
                                  'acceptedMissionIds': production['missions'],
                                  'completeRecurringCostCents': None,
                                  'completeConstructionCostCents': None,
                                  'resources': {'scope': 'known-process-lower-bound',
                                                'cpuSecondsPerAccepted': 0.001,
                                                'wallSecondsPerAccepted': 0.002}}
        if key != 'A':
            production['arms'][key]['asset'] = {'id': 'synthetic-ui-asset-' + key,
                                               'path': 'SYNTHETIC-UI-CONTROL/' + key,
                                               'sha256': digest('synthetic-ui-asset-' + key)}
    return {'schema': 'agi-alpha-transfer-demo/v1', 'qaSynthetic': True,
            'summary': {'headline': bilingual('SYNTHETIC UI CONTROL', 'CONTRÔLE SYNTHÉTIQUE'),
                        'finding': bilingual('No study outcomes are loaded. These controls exercise presentation and exact engine replay.',
                                             'Aucun résultat d’étude chargé. Ces contrôles vérifient l’interface et le moteur exact.')},
            'missions': [mission, conditional],
            'primaryConfirmation': {'finding': bilingual('SYNTHETIC primary-failure display control; not a study finding.',
                                                         'Contrôle SYNTHÉTIQUE d’affichage d’un échec primaire; aucun résultat d’étude.')},
            'capability': {'title': bilingual('Synthetic retained asset', 'Actif conservé synthétique'),
                           'path': 'SYNTHETIC-UI-CONTROL/B', 'sha256': digest('synthetic-ui-asset-B'),
                           'mechanism': bilingual('Fixture only; no transfer claim.', 'Exemple uniquement; aucun transfert revendiqué.'),
                           'boundary': bilingual('No production source or outcome was inspected to create this fixture.',
                                                  'Aucune source de production ni résultat inspecté pour créer cet exemple.')},
            'priorMarkets': {'summary': bilingual('Synthetic prior-study card.', 'Carte d’étude antérieure synthétique.'),
                             'primaryNegative': bilingual('Synthetic preserved-negative marker.', 'Marqueur négatif conservé synthétique.')},
            'productionMarketRecord': production,
            'scenarioDefaults': {'costs': {key: {'completeRecurringCostCents': None,
                                                'completeConstructionCostCents': None} for key in 'ABC'}},
            'sources': [{'title': 'Synthetic source register control', 'url': 'javascript:alert(1)',
                         'version': 'UI-CONTROL', 'license': 'Synthetic metadata; no license grant',
                         'role': bilingual('Rendering control only.', 'Contrôle d’affichage uniquement.')}],
            'limitations': [bilingual('THIS IS NOT STUDY EVIDENCE.', 'CECI N’EST PAS UNE PREUVE D’ÉTUDE.')]}


def generate(output: Path) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    records = {}
    for name in ('equivalent-unknown', 'blocked-complete-handoff', 'missing-record'):
        data = fixture()
        if name == 'blocked-complete-handoff':
            data['productionMarketRecord'].pop('completeAcceptanceEvidence')
        if name == 'missing-record':
            data.pop('productionMarketRecord')
        path = output / (name + '.json')
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')
        records[name] = build(path, output / (name + '.html'))
    return records


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=Path(__file__).with_name('ui-qa-synthetic'))
    args = parser.parse_args()
    print(json.dumps(generate(args.out), indent=2))
