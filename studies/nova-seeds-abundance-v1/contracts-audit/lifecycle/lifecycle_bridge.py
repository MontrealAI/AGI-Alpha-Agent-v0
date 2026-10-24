# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations
import argparse, hashlib, itertools, json, sqlite3, sys, tempfile, time
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VENDOR = Path(__file__).resolve().parent / 'vendor'
sys.path.insert(0, str(VENDOR))
from alpha_factory_v1.core.runtime.store import Journal, Conflict
from alpha_factory_v1.core.runtime.successor.jobs import JobDispatcher, JobResult
from alpha_factory_v1.core.runtime.successor.protocol import BehaviorArtifact, CandidateReleaseManifest, EvidenceRecord, ExecutionAuthorization, Institution, JobContract, JobDependency, JobGraph, MissionConstitution, PolicyProgram, ResourceBudget, TypedPort, WorldProgram, digest
from alpha_factory_v1.core.runtime.successor.state import EvidenceSubmission, SuccessorStore
from alpha_factory_v1.core.runtime.successor.trust import local_principals, sign_record


def filehash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def clean(value):
    if type(value) is float:
        return format(value, '.17g')
    if isinstance(value, dict):
        return {k: clean(v) for k, v in value.items()}
    if isinstance(value, list):
        return [clean(v) for v in value]
    return value


def valid(mission, plan):
    cs, slots = plan['calibrations'], plan['slots']
    if len(cs) != 3 or len(slots) != 4 or any(c not in [0, 1] for c in cs) or any(t not in range(4) for t in slots):
        return False
    for t in range(1, 4):
        active = [j for j, s in enumerate(slots) if s == t]
        if len(active) > mission['capacity'] or active and mission['calibrationDuration'] and t < 3 and cs[t]:
            return False
        previous = [c for c in range(3) if cs[c] and (c < t or not mission['calibrationDuration'] and c == t)]
        if active and not previous:
            return False
        if any(t - max(previous) > mission['jobs'][j]['ttl'] for j in active):
            return False
    return True


def enumerate_reference(mission):
    best = None
    for cs in itertools.product(range(2), repeat=3):
        for slots in itertools.product(range(4), repeat=4):
            plan = {'calibrations': list(cs), 'slots': list(slots)}
            if valid(mission, plan):
                objective = 100 * sum(job['utility'] for i, job in enumerate(mission['jobs']) if slots[i] == 0) + sum(cs)
                if best is None or objective < best['objective']:
                    best = {'objective': objective, 'plan': plan}
    return {**best, 'assignmentsEnumerated': 2048}


def replay(world, plan):
    mission = world['mission']
    assert valid(mission, plan)
    outcomes = []
    for i, tick in enumerate(plan['slots']):
        if not tick:
            outcomes.append({'id': mission['jobs'][i]['id'], 'utility': 0, 'useful': False})
            continue
        calibration = max(t for t in range(3) if plan['calibrations'][t] and (t < tick or not mission['calibrationDuration'] and t == tick))
        error = abs(world['bias'][tick] - world['bias'][calibration] + world['noise'][i][tick])
        useful = not world['failedSlots'][tick] and error <= mission['jobs'][i]['tolerance']
        outcomes.append({'id': mission['jobs'][i]['id'], 'utility': mission['jobs'][i]['utility'] if useful else 0, 'useful': useful})
    return {'utility': sum(x['utility'] for x in outcomes), 'completedJobs': sum(x['useful'] for x in outcomes), 'outcomes': outcomes}


def run(evidence_path: Path, output_path: Path):
    data = json.loads(evidence_path.read_text())
    assert data['schema'] == 'nova-seeds.dispatcher-development-case/v1'
    for relative, expected in data['sourceSha256'].items():
        assert filehash(Path(__file__).resolve().parent / relative) == expected
    original_data = data
    assert data['world']['mission']['id'] != data['freshScope']['world']['mission']['id']
    for trial in [data, data['freshScope']]:
        mission, authority = trial['world']['mission'], trial['world']['mission']['authority']
        assert authority['mode'] == 'fixture' and authority['missionId'] == mission['id']
        assert authority['currencyCaps'] == {'USDC': '0', 'AGIALPHA': '0'}
    started, cpu_started = time.perf_counter_ns(), time.process_time_ns()
    trust, keys = local_principals()
    now = datetime.now(timezone.utc)
    expires = (now + timedelta(hours=1)).isoformat(timespec='seconds').replace('+00:00', 'Z')
    expired = (now - timedelta(hours=1)).isoformat(timespec='seconds').replace('+00:00', 'Z')
    negatives, accepted, callback_outputs, graphs = [], [], {}, []
    source_files = [VENDOR / 'alpha_factory_v1/core/runtime' / p for p in ['store.py', 'successor/jobs.py', 'successor/protocol.py', 'successor/state.py', 'successor/trust.py', 'successor/signatures.py']]
    source_hashes = {str(p.relative_to(ROOT)): filehash(p) for p in source_files}
    definitions = [('identify', 'constitution', ['Identify']), ('learn', 'evidence', ['Out-Learn']), ('think', 'formation', ['Out-Think']), ('design', 'formation', ['Out-Design']), ('strategise', 'challenge', ['Out-Strategise']), ('execute', 'verification', ['Out-Execute']), ('accept', 'admission', []), ('evolve', 'renewal', ['Out-Evolve'])]

    def negative(label, function):
        try:
            function()
        except (ValueError, Conflict) as error:
            negatives.append({'label': label, 'rejected': True, 'reason': str(error)})
        else:
            raise AssertionError(label + ' did not reject')

    with tempfile.TemporaryDirectory(prefix='nova-writer10-lifecycle-') as temporary:
        journal = Journal.initialize(Path(temporary) / 'agent')
        for name in ['identity.key', 'api.token']:
            (journal.root / name).unlink()
        store = SuccessorStore(journal, trust)
        original_authorization, original_evidence = None, None
        for generation in [0, 1]:
            data = original_data if generation == 0 else {**original_data['freshScope'], 'sourceSha256': original_data['sourceSha256']}
            mission = data['world']['mission']
            institution_id, mission_id = f'nova-local-{generation}', f'nova-copy-mission-{generation}'
            environment = digest('writer10-environment', {'world': clean(data['world']), 'mission': mission_id})
            constitution = MissionConstitution(mission_id=mission_id, owner='local-controller', objective='Check copied calibration-aware resource allocation under fresh local scope', scope='synthetic development rehearsal only', authority_ceiling='sandbox', prohibited_actions=['network', 'live-payment', 'credential-use'], budget=ResourceBudget(limits={'callbacks': 8}, enforceable=['callbacks'], unknown_costs=['human-effort', 'commercial-demand']))
            institution = Institution(id=institution_id, constitution=constitution, controller='local-controller', predecessor_id=None if generation == 0 else 'nova-local-0')
            store.create_institution(institution, {'callbacks': 8})
            observation_id = f'observations-g{generation}'
            observation = EvidenceRecord(evidence_id=observation_id, source='actual Node synthetic development execution', acquired_at=now.isoformat(timespec='seconds').replace('+00:00', 'Z'), content_digest=digest('writer10-observations', clean(data['world'])), permitted_uses=['constitution', 'evidence', 'formation', 'challenge', 'verification', 'admission', 'renewal'], valid_until=expires, scope=mission_id, uncertainty='synthetic observations; no physical truth claim', accepted_by='local-controller')
            submission = EvidenceSubmission(institution_id=institution_id, evidence=observation)
            evidence_envelope = sign_record(keys['local-controller'], 'local-controller', 'evidence', submission)
            if generation == 1:
                negative('copied-evidence-envelope-rejected-for-successor', lambda: store.record_evidence(institution_id, original_evidence, request_id='reject-copied-evidence'))
            else:
                original_evidence = evidence_envelope
            stale = EvidenceSubmission(institution_id=institution_id, evidence=observation.model_copy(update={'evidence_id': observation_id+'-stale', 'valid_until': expired}))
            negative(f'g{generation}-stale-observations', lambda: store.record_evidence(institution_id, sign_record(keys['local-controller'], 'local-controller', 'evidence', stale), request_id='reject-stale-evidence'))
            store.record_evidence(institution_id, evidence_envelope, request_id=f'fresh-evidence-{generation}')
            world_program = WorldProgram(world_id=f'instrument-world-{generation}', artifact_digest=data['modelDigest'], inputs=[TypedPort(name='mission', type_name='nova-seeds-mission/v1')], state=[TypedPort(name='calibration-age', type_name='integer ticks'), TypedPort(name='resource-occupancy', type_name='finite slots')], transitions=['calibration resets calibration age', 'sample occupies bounded capacity'], invariants=['job calibration age does not exceed its declared TTL', 'nonzero-duration calibration excludes concurrent sample use'], outputs=[TypedPort(name='feasible-schedule', type_name='finite calibration flags and job slots')], uncertainty='synthetic finite model; physical validity not established', assumptions=['stationary bias within a calibration interval', 'bounded measurement noise'], evidence=[observation_id], falsifiers=['measurement drift can invalidate nominally feasible work'])
            world_commitment = digest('world-program', world_program)
            policy_program = PolicyProgram(policy_id=f'instrument-policy-{generation}', artifact_digest=data['sourceSha256']['../../research/src/engine_adapter.mjs'], objective='minimize 100 times unserved utility plus calibration count', decision_rules=['enumerate the bounded feasible assignment model with existing Alpha engine'], admissible_actions=['calibrate', 'sample', 'leave-unserved'], constraints=['fresh fixture scope', 'no live payment or external instrument actuation'], abstention=['refuse unsupported mission geometry or absent scoped authority'], dependencies=[world_commitment], configuration={'capacity': mission['capacity'], 'horizon': mission['horizon']})
            manifest = CandidateReleaseManifest(release_id=f'nova-release-{generation}', institution_id=institution_id, mission_id=mission_id, producer='local-producer', environment_digest=environment, artifacts=[BehaviorArtifact(name='node-development-evidence', role='other', digest=filehash(evidence_path)), BehaviorArtifact(name='research-lifecycle-wrapper', role='source', digest=filehash(Path(__file__)))], world_digest=world_commitment, policy_digest=digest('policy-program', policy_program), configuration={'scope': 'read-and-replay', 'world': 'synthetic', 'node_execution': 'precomputed'} )
            release = digest('release', manifest)
            store.register_release(institution_id, manifest, request_id=f'freeze-{generation}')
            jobs, edges = [], []
            for index, (stage, family, labels) in enumerate(definitions):
                worker = 'local-verifier' if family in {'challenge', 'verification', 'admission'} else 'local-producer'
                job = JobContract(job_id=f'g{generation}-{stage}', family=family, worker=worker, acceptance_owner='local-controller', release_digest=release, environment_digest=environment, inputs={} if index == 0 else {f'p{index-1}': 'writer10-stage-evidence/v1'}, outputs={f'p{index}': 'writer10-stage-evidence/v1'}, input_evidence=[observation_id], critical_functions=[stage], resources={'callbacks': 1}, valid_until=expires, institution_id=institution_id, mission_id=mission_id, allowed_tools=['pure-research-callback'], effects=[], acceptance_conditions=['callback output digest matches reviewed exact bytes', 'no external effects or operating grant'])
                jobs.append(job)
                if index:
                    edges.append(JobDependency(source=jobs[-2].job_id, target=job.job_id, kind='evidence', required_type='writer10-stage-evidence/v1'))
            graph = JobGraph(jobs=jobs, edges=edges, required_functions=[x[0] for x in definitions])
            dispatcher = JobDispatcher(store, institution_id)
            dispatcher.seal(graph)
            graphs.append({'institution': institution_id, 'mission': mission_id, 'releaseDigest': release, 'graphDigest': digest('job-graph', graph), 'jobs': [{'job': j.job_id, 'publishedFamily': j.family, 'tiLabels': definitions[i][2]} for i, j in enumerate(jobs)]})

            def authorize(job, suffix='', until=expires):
                a = ExecutionAuthorization(authorization_id=f'{job.job_id}-authorization{suffix}', acting_identity=job.worker, job_terms_digest=digest('job-terms', job), release_digest=release, environment_digest=environment, capabilities=['pure-research-callback'], reservation_id=f'{job.job_id}-reservation{suffix}', expires_at=until)
                return sign_record(keys['local-controller'], 'local-controller', 'execution', a)

            if generation == 1:
                negative('copied-authority-rejected-for-successor-mission', lambda: dispatcher.dispatch(jobs[0].job_id, original_authorization))
            negative(f'g{generation}-dependency-before-accepted-evidence', lambda: dispatcher.dispatch(jobs[1].job_id, authorize(jobs[1])))
            negative(f'g{generation}-expired-authority', lambda: dispatcher.dispatch(jobs[0].job_id, authorize(jobs[0], '-expired', expired)))
            for i, job in enumerate(jobs):
                stage, family, labels = definitions[i]
                auth = authorize(job)
                if generation == 0 and i == 0:
                    original_authorization = auth
                dispatcher.dispatch(job.job_id, auth)
                prior = None if i == 0 else callback_outputs[jobs[i-1].job_id]['outputDigest']

                def handler(stage=stage):
                    common = {'mission': mission_id, 'generation': generation, 'priorOutputDigest': prior, 'inputEvidenceSha256': filehash(evidence_path), 'tiStage': stage}
                    if stage == 'identify':
                        body = {'objective': constitution.objective, 'sourceMission': mission['id'], 'horizon': mission['horizon'], 'authorityCeiling': 'sandbox', 'paidActions': False}
                    elif stage == 'learn':
                        body = {'developmentSelection': f'seed 1, epoch {generation}, ordinary; generator metadata not passed to planners', 'knownModel': clean(mission['knownModel']), 'evidenceStatus': 'precomputed actual Node development execution', 'freshWorldDigest': digest('writer10-fresh-world', clean(data['world'])), 'sourceDigest': data['sourceSha256']}
                    elif stage == 'think':
                        body = {'worldProgram': world_program.model_dump(mode='json'), 'policyProgram': policy_program.model_dump(mode='json'), 'declarationBoundary': 'typed source-bound model and policy declarations; not physical certification or action permission', 'modelDigest': data['modelDigest']}
                    elif stage == 'design':
                        body = {'artifact': 'calibration-sharing finite resource-use adapter', 'compiler': 'existing Alpha Out-Execute', 'modelBytes': data['modelBytes'], 'nodeArtifactDigest': data['verified']['completionHash'], 'constructiveChange': 'share still-valid calibration across jobs'}
                    elif stage == 'strategise':
                        exact = enumerate_reference(mission)
                        assert exact['objective'] == data['verified']['objective'] == data['completeClone']['objective']
                        body = {'matchedExpert': exact, 'completeCopyObjective': data['completeClone']['objective'], 'residualPlanningAdvantage': 0, 'evaluationStatus': 'actual Python enumeration in this callback'}
                    elif stage == 'execute':
                        evaluated = replay(data['world'], data['verified']['plan'])
                        assert evaluated['utility'] == data['evaluated']['verified']['utility']
                        assert evaluated['completedJobs'] == data['evaluated']['verified']['completedJobs']
                        body = {'replayed': evaluated, 'nodePlannerStatus': 'precomputed execution', 'callbackStatus': 'actual independent Python replay', 'physicalInstrument': 'simulated'}
                    elif stage == 'accept':
                        body = {'acceptedFor': 'public reproducible synthetic research evidence', 'productionGrant': False, 'independentOrganization': False, 'unknownCosts': ['human-effort', 'commercial-demand']}
                    else:
                        copy_result = replay(data['world'], data['completeClone']['plan'])
                        assert copy_result['utility'] == data['evaluated']['verified']['utility']
                        body = {'completeCopy': copy_result, 'residualUsefulOutputAdvantage': 0, 'commercialProfit': 'not measured', 'furtherMissionRequires': ['fresh institution terms', 'fresh execution authorization', 'fresh scoped evidence'], 'independence': 'distinct local fixture roles under same operator'}
                    return {**common, **body}

                value = dispatcher.execute_tool(job.job_id, tool='pure-research-callback', actor=job.worker, invocation_id='once', handler=handler, retain_result=True)
                output_digest = digest('job-tool-output', value)
                negative(f'{job.job_id}-duplicate-invocation', lambda: dispatcher.execute_tool(job.job_id, tool='pure-research-callback', actor=job.worker, invocation_id='once', handler=lambda: {'shouldNotRun': True}))
                result = JobResult(job_id=job.job_id, authorization_id=auth.payload['authorization_id'], terms_digest=digest('job-terms', job), output_digest=output_digest, outputs=job.outputs, accepted=True, accepted_by='local-controller', valid_until=expires, permitted_uses=['dependency'], actual_resources={'callbacks': 1}, candidate_verdict='local-research-replay-only')
                envelope = sign_record(keys['local-controller'], 'local-controller', 'job-acceptance', result)
                dispatcher.complete(envelope)
                accepted.append(envelope.model_dump(mode='json'))
                callback_outputs[job.job_id] = {'output': value, 'outputDigest': output_digest}
            assert store.read(institution_id)['resources']['spent'] == {'callbacks': 8}
            assert store.read(institution_id)['grants'] == {}
            state = journal.latest(dispatcher.key)
            for job_id, entry in callback_outputs.items():
                if job_id.startswith(f'g{generation}-'):
                    tool = state['runs'][job_id][-1]['tools']['once']
                    assert tool['result_digest'] == entry['outputDigest']
                    assert digest('job-tool-output', json.loads(tool['result_json'])) == entry['outputDigest']
        journal_status = journal.verify()
        public_events = []
        with sqlite3.connect(journal.path) as cx:
            for sequence, body, hashed, signature in cx.execute('SELECT seq,body,hash,signature FROM events ORDER BY seq'):
                public_events.append({'sequence': sequence, 'body': json.loads(body), 'hash': hashed, 'signature': signature})
        public_keys = {name: trust.anchor(name, role).public_key for name, role in [('local-controller', 'controller'), ('local-producer', 'producer'), ('local-verifier', 'verifier')]}
    output = {'schema': 'nova-seeds.published-job-dispatcher-bridge/v1', 'sourceCommit': '197147ffd22c5ae13113162afffaf3ce9c10aa2e', 'sourceSha256': source_hashes, 'scope': 'published SUCCESSOR local JobDispatcher with pure callbacks; no held Harness execution or production permission', 'nodeEvidenceSha256': filehash(evidence_path), 'roles': {'operator': 'one research operator', 'signers': 'distinct ephemeral local fixture keys', 'independence': 'not independent institutions or external reviewers'}, 'credentialHandling': 'Journal initialization created ephemeral credentials only in disposable temporary directory; identity.key and api.token immediately unlinked after loading; no credential retained in output; local-principal keys remained memory-only', 'graphs': graphs, 'callbackOutputs': callback_outputs, 'acceptances': accepted, 'negativeCases': negatives, 'journalVerification': journal_status, 'journalPublicKey': journal.public, 'localPrincipalPublicKeys': public_keys, 'publicJournalEvents': public_events, 'costs': {'wallMicroseconds': (time.perf_counter_ns()-started)//1000, 'cpuMicroseconds': (time.process_time_ns()-cpu_started)//1000, 'executedCallbacks': 16, 'independentEnumerations': 2, 'assignmentsPerEnumeration': 2048, 'humanEffort': 'unknown'}, 'productionGrants': 0, 'liveTransactions': 0}
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, indent=2)+'\n')
    print(json.dumps({'output': str(output_path), 'callbacks': 16, 'negativeCases': len(negatives), 'journalEvents': journal_status['events'], 'productionGrants': 0}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    run(args.evidence.resolve(), args.output.resolve())
