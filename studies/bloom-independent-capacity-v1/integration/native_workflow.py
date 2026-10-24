# SPDX-License-Identifier: Apache-2.0
"""Execute pure study stages through the unchanged Alpha JobDispatcher.

This fixture uses deliberately public, deterministic signing material. It opens
no service, has no external credentials, creates no AuthorityEnvelope, and must
never be used as a production identity or evidence of independent control.
"""

from __future__ import annotations

import hashlib
import json
import math
import platform
import sqlite3
import time
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import cryptography
import pydantic
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from .source_loader import native_modules, verify_vendor

FIXTURE_SCOPE = 'BLOOM_PUBLIC_LOCAL_TEST_ONLY_V1'
FIXTURE_TOKEN = b'PUBLIC-TEST-TOKEN-NO-SERVICE-NEVER-A-CREDENTIAL'
FAMILY_MAP = {
    'identify': 'constitution', 'out_learn': 'evidence', 'out_think': 'challenge',
    'out_design': 'formation', 'out_strategise': 'admission',
    'out_execute': 'verification', 'out_evolve': 'renewal',
}
ROLES = {
    'bloom-fixture-controller': ['controller', 'acceptance', 'worker', 'control'],
    'bloom-fixture-producer': ['producer', 'worker'],
    'bloom-fixture-verifier': ['verifier', 'acceptance', 'worker'],
}


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _utc():
    return datetime.now(UTC).isoformat(timespec='seconds').replace('+00:00', 'Z')


def to_wire(value):
    if value is None or type(value) in (str, bool, int):
        return value
    if type(value) is float:
        if not math.isfinite(value):
            raise ValueError('Non-finite measurements cannot enter native records')
        return format(Decimal(str(value)), 'f')
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise ValueError('Non-finite decimal measurement')
        return format(value, 'f')
    if isinstance(value, (list, tuple)):
        return [to_wire(item) for item in value]
    if type(value) is dict and all(type(key) is str for key in value):
        return {key: to_wire(item) for key, item in value.items()}
    raise TypeError('Stage outputs must be bounded JSON; convert array/scalar extensions explicitly')


def _write(path, value, canonical):
    path.parent.mkdir(parents=True, exist_ok=True)
    data = canonical(value) + b'\n'
    with path.open('xb') as stream:
        stream.write(data)
    return {'path': path.name, 'bytes': len(data), 'sha256': _sha(data)}


def _key(principal):
    seed = hashlib.sha256((FIXTURE_SCOPE + ':' + principal).encode()).digest()
    return Ed25519PrivateKey.from_private_bytes(seed)


def fixture_registry(trust_module):
    keys = {principal: _key(principal) for principal in ROLES}
    public = {'schema_version': 1, 'principals': {
        principal: {
            'public_key': key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw).hex(),
            'roles': ROLES[principal], 'provenance': 'local', 'independence_attestation': '',
        } for principal, key in keys.items()}}
    registry = trust_module.validate_external_trust_bytes(json.dumps(public).encode())
    return registry, keys, public


def _initialize_public_fixture(root, modules, public_registry):
    root.mkdir(parents=True, exist_ok=False, mode=0o700)
    store_module = modules['store']
    config = modules['models'].RuntimeConfig(name='bloom-public-fixture')
    contents = {
        'config.json': store_module.canonical(config.model_dump()),
        'identity.key': hashlib.sha256((FIXTURE_SCOPE + ':journal').encode()).digest(),
        'api.token': FIXTURE_TOKEN,
        'successor-trust.json': store_module.canonical(public_registry),
        'PUBLIC_TEST_FIXTURE.txt': (FIXTURE_SCOPE + '\nPublic test signing material; no service or external identity.\n').encode(),
    }
    for name, data in contents.items():
        store_module.private_write(root / name, data)
    with sqlite3.connect(root / 'journal.sqlite3') as cx:
        cx.execute('PRAGMA journal_mode=WAL')
        cx.execute('CREATE TABLE events(seq INTEGER PRIMARY KEY, mission TEXT NOT NULL, '
                   'body TEXT NOT NULL, hash TEXT NOT NULL UNIQUE, signature TEXT NOT NULL)')
        cx.execute('CREATE INDEX events_mission ON events(mission,seq)')
    journal = store_module.Journal(root)
    with journal.transaction() as cx:
        journal.append(cx, '@control', {'state': 'ready', 'config_hash': store_module.digest(config.model_dump())})
    return journal


def runtime_environment():
    return {'python': platform.python_version(), 'implementation': platform.python_implementation(),
            'system': platform.system(), 'machine': platform.machine(),
            'pydantic': pydantic.__version__, 'cryptography': cryptography.__version__}


def _source_rows(source_files):
    if not source_files or len(source_files) > 200:
        raise ValueError('Provide 1 to 200 frozen installed source files')
    result = []
    for path in source_files:
        path = Path(path)
        if path.is_symlink() or not path.is_file() or path.stat().st_size > 8_000_000:
            raise ValueError('Source must be a bounded regular file')
        data = path.read_bytes()
        result.append({'name': path.name, 'bytes': len(data), 'sha256': _sha(data)})
    return result


def execute_stages(output_dir, stages, *, mission_id, objective, source_paths,
                   bindings=None, institution_id='bloom-local-study'):
    """Run installed pure callbacks once, with genuine native typed dependencies.

    A stage has id, handler(inputs), optional family/label/depends_on/accept.
    Inputs contain the exact accepted predecessor wire artifacts. Floats returned
    by callbacks become explicit decimal strings; raw experiment files remain
    authoritative for scientific analysis. Work acceptance defaults to structural
    completion, not to a positive scientific verdict.
    """
    started_wall, started_cpu = time.perf_counter_ns(), time.process_time_ns()
    if not 1 <= len(stages) <= 32:
        raise ValueError('A bounded native graph requires 1 to 32 installed stages')
    bindings = to_wire(bindings or {})
    if bindings.get('execution_mode', 'synthetic-local') != 'synthetic-local':
        raise ValueError('Only synthetic-local fixture execution is supported')
    if bindings.get('authority', 'none') != 'none':
        raise ValueError('This fixture cannot carry operational authority')
    root = Path(output_dir).resolve()
    root.mkdir(parents=True, exist_ok=False)
    modules = native_modules()
    p, j, t = modules['successor.protocol'], modules['successor.jobs'], modules['successor.trust']
    registry, keys, public_registry = fixture_registry(t)
    journal = _initialize_public_fixture(root / 'journal', modules, public_registry)
    store = modules['successor.state'].SuccessorStore(journal, registry)
    sources = _source_rows(source_paths)
    installed_paths = {Path(path).resolve() for path in source_paths}
    environment = runtime_environment()
    environment_digest = p.digest('bloom-local-environment', environment)
    until = (datetime.now(UTC) + timedelta(days=1)).isoformat(timespec='seconds').replace('+00:00', 'Z')
    constitution = p.MissionConstitution(
        mission_id=mission_id, owner='bloom-fixture-controller', objective=objective,
        mission_distribution='See the separately frozen, source-bound scientific protocol.',
        scope='Disposable local development fixture; installed pure callbacks only.',
        evidence_rights=['Customer-owned public source and local evidence export.'],
        constraints=['No external service, financial action, independent-control claim, or production grant.'],
        prohibited_actions=['network', 'financial-transaction', 'external-dispatch', 'new-credentials', 'service-start'],
        authority_ceiling='none',
        budget=p.ResourceBudget(limits={'stage_calls': len(stages)}, units={'stage_calls': 'installed stage invocations'},
                                enforceable=['stage_calls'], unknown_costs=['provider-billing', 'human-fees', 'maintenance']),
        stop_conditions=['Native dependency, source, role, budget, or acceptance failure.'],
    )
    institution = p.Institution(id=institution_id, constitution=constitution, controller='bloom-fixture-controller')
    store.create_institution(institution, {'stage_calls': len(stages)})
    release = p.CandidateReleaseManifest(
        release_id='bloom-installed-callbacks-v1', institution_id=institution_id, mission_id=mission_id,
        producer='bloom-fixture-producer', environment_digest=environment_digest,
        artifacts=[p.BehaviorArtifact(name=f'source-{i:03}', role='source', digest=row['sha256'], location=row['name'])
                   for i, row in enumerate(sources)],
        configuration={'fixture_scope': FIXTURE_SCOPE, 'bindings_digest': p.digest('bloom-bindings', bindings)},
    )
    store.register_release(institution_id, release, request_id='freeze-installed-study')
    release_digest = p.digest('release', release)
    terms, dependencies, seen = [], {}, []
    for stage in stages:
        ident, handler = stage['id'], stage['handler']
        if ident in seen or not callable(handler):
            raise ValueError('Unique stage IDs and installed callables are required')
        for callback in (handler, stage.get('accept')):
            if callback is None:
                continue
            code = getattr(callback, '__code__', None)
            if code is None or Path(code.co_filename).resolve() not in installed_paths:
                raise ValueError('Every stage handler and acceptance callback must belong to an explicitly frozen installed source file')
        parents = stage.get('depends_on', seen[-1:])
        if not all(parent in seen for parent in parents):
            raise ValueError('Every dependency must identify an earlier stage')
        family = stage.get('family', FAMILY_MAP.get(ident))
        worker = ('bloom-fixture-verifier' if family in ('challenge', 'verification') else
                  'bloom-fixture-controller' if family == 'admission' else 'bloom-fixture-producer')
        owner = 'bloom-fixture-verifier' if worker == 'bloom-fixture-controller' else 'bloom-fixture-controller'
        terms.append(p.JobContract(
            job_id=ident, family=family, worker=worker, acceptance_owner=owner,
            release_digest=release_digest, environment_digest=environment_digest,
            institution_id=institution_id, mission_id=mission_id,
            goal=stage.get('label', ident), inputs={parent: 'bloom-stage-artifact/v1' for parent in parents},
            outputs={ident: 'bloom-stage-artifact/v1'}, critical_functions=[ident],
            resources={'stage_calls': 1}, valid_until=until, allowed_tools=['installed-study-stage'],
            effects=[], max_attempts=1,
            acceptance_conditions=['Exact current-source artifact and declared local work acceptance; scientific verdict retained separately.'],
        ))
        dependencies[ident] = list(parents)
        seen.append(ident)
    graph = p.JobGraph(jobs=terms, edges=[p.JobDependency(source=source, target=target, kind='evidence',
                      required_type='bloom-stage-artifact/v1') for target, parents in dependencies.items() for source in parents],
                      required_families=['constitution', 'evidence', 'formation', 'challenge', 'verification', 'admission', 'renewal'],
                      required_functions=seen)
    dispatcher = j.JobDispatcher(store, institution_id)
    dispatcher.seal(graph)
    output_manifest, values, receipts, failure = [], {}, [], None
    for index, (stage, contract) in enumerate(zip(stages, terms, strict=True)):
        stage_start, stage_cpu = time.perf_counter_ns(), time.process_time_ns()
        ident = contract.job_id
        authorization = p.ExecutionAuthorization(
            authorization_id=ident + '-attempt-1', acting_identity=contract.worker,
            job_terms_digest=p.digest('job-terms', contract), release_digest=release_digest,
            environment_digest=environment_digest, capabilities=['installed-study-stage'],
            reservation_id=ident + '-reservation-1', expires_at=until,
        )
        dispatched = False
        try:
            dispatcher.dispatch(ident, t.sign_record(keys['bloom-fixture-controller'], 'bloom-fixture-controller',
                                                    'execution', authorization))
            dispatched = True
            inputs = {parent: json.loads(p.canonical(values[parent])) for parent in dependencies[ident]}
            input_digest = p.digest('bloom-stage-inputs', inputs)

            def handler():
                begin_wall, begin_cpu = time.perf_counter_ns(), time.process_time_ns()
                if _source_rows(source_paths) != sources:
                    raise ValueError('Installed study source changed before execution')
                result = to_wire(stage['handler'](inputs))
                if _source_rows(source_paths) != sources:
                    raise ValueError('Installed study source changed during execution')
                return {'schema': 'bloom-stage-artifact/v1', 'stage': ident, 'input_digest': input_digest,
                        'inputs': {parent: p.digest('bloom-stage-artifact', values[parent]) for parent in inputs},
                        'result': result, 'handler_wall_ns': time.perf_counter_ns() - begin_wall,
                        'handler_cpu_ns': time.process_time_ns() - begin_cpu,
                        'authority': 'none', 'fixture_scope': FIXTURE_SCOPE}

            artifact = dispatcher.execute_tool(ident, tool='installed-study-stage', actor=contract.worker,
                                               invocation_id=ident + '-invoke-1', handler=handler, retain_result=True)
            accepted = bool(stage['accept'](artifact)) if callable(stage.get('accept')) else True
            result = j.JobResult(
                job_id=ident, authorization_id=authorization.authorization_id,
                terms_digest=p.digest('job-terms', contract), output_digest=p.digest('bloom-stage-artifact', artifact),
                outputs=contract.outputs, accepted=accepted, accepted_by=contract.acceptance_owner,
                valid_until=until, permitted_uses=['dependency'] if accepted else [],
                candidate_verdict='See retained scientific result; local work acceptance is separate.',
                actual_resources={'stage_calls': 1}, failures=[] if accepted else ['Local work acceptance rejected.'],
            )
            dispatcher.complete(t.sign_record(keys[contract.acceptance_owner], contract.acceptance_owner,
                                              'job-acceptance', result))
            values[ident] = artifact
            file = _write(root / 'stage_artifacts' / f'{index:02}-{ident}.json', artifact, p.canonical)
            file['path'] = 'stage_artifacts/' + file['path']
            output_manifest.append(file)
            receipts.append({'stage': ident, 'family': contract.family, 'worker': contract.worker,
                             'acceptance_owner': contract.acceptance_owner, 'accepted_work': accepted,
                             'acceptance_scope': 'supplied-local-check' if callable(stage.get('accept')) else 'structural-work-completion-only',
                             'result_digest': result.output_digest, 'artifact': file,
                             'stage_wall_ns': time.perf_counter_ns() - stage_start,
                             'stage_cpu_ns': time.process_time_ns() - stage_cpu,
                             'handler_wall_ns': artifact['handler_wall_ns'], 'handler_cpu_ns': artifact['handler_cpu_ns'],
                             'native_reserved_and_charged': {'stage_calls': 1}})
            if not accepted:
                failure = {'stage': ident, 'kind': 'local-work-rejected'}
                break
        except Exception as exc:
            failure = {'stage': ident, 'kind': type(exc).__name__, 'message': str(exc)[:1000]}
            if dispatched:
                try:
                    dispatcher.recover_job(t.sign_record(keys['bloom-fixture-controller'], 'bloom-fixture-controller',
                        'job-recovery', {'institution_id': institution_id, 'job_id': ident,
                                        'authorization_id': authorization.authorization_id, 'reason': 'Retain failed or uncertain local study attempt.'}))
                except Exception as recovery:
                    failure['recovery_error'] = str(recovery)[:500]
            receipts.append({'stage': ident, 'family': contract.family, 'failure': failure,
                             'stage_wall_ns': time.perf_counter_ns() - stage_start,
                             'stage_cpu_ns': time.process_time_ns() - stage_cpu})
            break
    store.recover(institution_id, t.sign_record(keys['bloom-fixture-controller'], 'bloom-fixture-controller',
                  'recovery', {'institution_id': institution_id}), request_id='finish-stopped')
    journal.control(True)
    state = store.read(institution_id)
    if state['proofs'] or state['grants'] or not state['stopped']:
        raise ValueError('Public fixture unexpectedly acquired proof, authority, or active execution')
    graph_state = journal.latest(dispatcher.key)
    verification = journal.verify()
    _write(root / 'native_graph.json', graph.model_dump(mode='json'), p.canonical)
    _write(root / 'native_graph_history.json', graph_state, p.canonical)
    _write(root / 'native_institution.json', state, p.canonical)
    _write(root / 'native_source_manifest.json', sources, p.canonical)
    backup = journal.backup(root / 'PUBLIC_FIXTURE_RECOVERY.zip')
    backup['path'] = Path(backup['path']).name
    backup['key_material_scope'] = 'Public deterministic TEST ONLY; not external credentials.'
    restored = modules['store'].Journal.restore(root / backup['path'], root / 'restored-journal')
    restored_store = modules['successor.state'].SuccessorStore(restored, registry)
    restored_state = restored_store.read(institution_id)
    revalidation = {
        'graph': restored.latest(dispatcher.key)['graph_digest'] == graph_state['graph_digest'],
        'policy': restored_state['institution']['constitution'] == state['institution']['constitution'],
        'environment': runtime_environment() == environment,
        'artifacts': all(_sha((root / row['path']).read_bytes()) == row['sha256'] for row in output_manifest),
        'installed_sources': _source_rows(source_paths) == sources,
        'vendor_source': bool(verify_vendor()),
    }
    restored_verification = restored.verify()
    restoration = {'native_Journal_restore_executed': True, 'journal': restored_verification,
                   'stopped': restored_state['stopped'], 'global_control': restored.latest('@control')['state'],
                   'active_proofs': list(restored_state['proofs']), 'active_grants': list(restored_state['grants']),
                   'revalidated_conditions': revalidation, 'continuation_authorized': False,
                   'interpretation': 'Same-context fixture reconstruction only. Changed environments, policy, artifacts, and authority require fresh checks.'}
    if not restoration['stopped'] or restoration['global_control'] != 'paused' or restoration['active_proofs'] or restoration['active_grants']:
        raise ValueError('Restored public fixture must remain inactive')
    receipt = {'schema': 'bloom-native-workflow-receipt/v1', 'created_at': _utc(), 'fixture_scope': FIXTURE_SCOPE,
               'status': 'completed' if failure is None else 'stopped-on-failure', 'failure': failure,
               'mission_id': mission_id, 'institution_id': institution_id, 'release_digest': release_digest,
               'environment': environment, 'environment_digest': environment_digest, 'bindings': bindings,
               'graph_digest': p.digest('job-graph', graph), 'stage_receipts': receipts,
               'completed_stages': list(values), 'not_run_stages': [stage['id'] for stage in stages if stage['id'] not in values],
               'journal': verification, 'resource_ledger': state['resources'], 'backup': backup, 'restoration': restoration,
               'total_wall_ns': time.perf_counter_ns() - started_wall, 'total_cpu_ns': time.process_time_ns() - started_cpu,
               'cost_scope': 'Includes source checks, journal setup, dispatch, callbacks, local acceptance, backup and restoration; excludes final receipt serialization and caller work.',
               'native_authority_grants': [], 'external_submission': 'NOT_SUBMITTED', 'settlement': 'NOT_CONNECTED',
               'independent_control': False,
               'limitations': ['All signing seeds are public fixture material.', 'Local role separation is not organizational independence.',
                               'Native structural work acceptance is not scientific superiority.',
                               'Integer stage_calls are invocation counts, not CPU instructions or currency.',
                               'Floating-point callback measurements are serialized as decimal strings.']}
    _write(root / 'native_workflow_receipt.json', receipt, p.canonical)
    return {'receipt': receipt, 'stage_artifacts': values, 'directory': str(root)}
