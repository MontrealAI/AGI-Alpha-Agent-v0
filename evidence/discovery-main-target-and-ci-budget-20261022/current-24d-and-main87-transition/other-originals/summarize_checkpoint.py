"""Join captured original-run metadata and RAM custody evidence, without execution."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import re

ROOT = Path('/dev/shm/alpha24d-other-original-custody')
HEAD = '24d58598f896106323f2c120487586bdf5104612'
CHECKOUT = 'd3ba2c3a4a275d7f2c7619504b703f931b8c4507'
TREE = 'ffa3d663519e713eca31a9840b8bf6816e53e12a'
RUNS = {'recovery': 39726232029, 'wallet': 39726231992,
        'world': 39726231984, 'Smoke': 39726232060,
        'authority': 39726232031, 'PRCI': 39726232035,
        'business': 39726231983, 'homepage': 39726232054,
        'TI': 39726231986, 'cross': 39726232043}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stamp(value):
    return datetime.fromisoformat(value)


def checkout_observation(log):
    lines = log['selectedSourceUploadErrorLines']
    for command, result in zip(lines, lines[1:]):
        unix = command['text'].endswith('/git log -1 --format=%H')
        windows = re.search(r'\[command\]"[^"\r\n]*[\\/]git\.exe" log -1 --format=%H$', command['text'])
        if result['line'] != command['line'] + 1 or not (unix or windows):
            continue
        for commit in [CHECKOUT, HEAD]:
            if re.fullmatch(r'\S+\s+' + commit, result['text']):
                return True, ('quoted-Windows-git.exe' if windows else 'Unix-git') + '-adjacent-result', commit
    if log.get('exactCheckoutGitLogResultObserved'):
        return True, 'original-command-pattern', CHECKOUT
    return False, 'not-observed', None


def main():
    head_record = json.loads((ROOT / 'head-git-commit.json').read_text())
    checkout_record = json.loads((ROOT / 'checkout-git-commit.json').read_text())
    assert head_record['sha'] == HEAD and head_record['tree']['sha'] == TREE
    assert checkout_record['sha'] == CHECKOUT and checkout_record['tree']['sha'] == TREE
    assert [p['sha'] for p in checkout_record['parents']] == ['5a5340a15698165bceb21e252f3bec58d7fd8298', HEAD]
    evidence = {}
    findings = []
    jobs = {}
    artifacts = {}
    for path in sorted(ROOT.glob('*.json')):
        if '-jobs' not in path.name and '-artifacts' not in path.name:
            continue
        data = json.loads(path.read_text())
        key = 'jobs' if '-jobs' in path.name else 'artifacts'
        if key not in data:
            continue
        assert type(data['total_count']) is int
        assert data['total_count'] == len(data[key]) <= 100
        for value in data[key]:
            if key == 'jobs':
                assert value['run_id'] in RUNS.values()
                assert value['run_attempt'] == 1 and value['head_sha'] == HEAD
                if value['status'] == 'completed':
                    existing = jobs.get(value['id'])
                    if existing and existing[0]['conclusion'] != value['conclusion']:
                        findings.append({'kind': 'conflicting-completed-job', 'jobId': value['id']})
                    jobs[value['id']] = (value, path)
            else:
                assert value['workflow_run']['id'] in RUNS.values()
                assert value['workflow_run']['head_sha'] == HEAD
                existing = artifacts.get(value['id'])
                if existing:
                    for field in ['name', 'size_in_bytes', 'digest', 'created_at']:
                        assert existing[0][field] == value[field], (value['id'], field)
                artifacts[value['id']] = (value, path)

    completed_job_observations = []
    for jid, (job, job_path) in sorted(jobs.items()):
        log_path = ROOT / f'job-{jid}-log-evidence.json'
        log = json.loads(log_path.read_text()) if log_path.is_file() else None
        failed_steps = [s['name'] for s in job['steps'] if s['conclusion'] == 'failure']
        completed_job_observations.append({
            'jobId': jid, 'runId': job['run_id'], 'name': job['name'],
            'conclusion': job['conclusion'], 'failedStepNames': failed_steps,
            'logEvidenceCaptured': log is not None,
            'exactCheckoutGitLogResultObserved': checkout_observation(log)[0] if log else None,
            'checkoutObservationFormat': checkout_observation(log)[1] if log else None,
            'actualCheckoutCommit': checkout_observation(log)[2] if log else None,
            'fullScopeJSONOutputObserved': log.get('fullScopeJSONOutputObserved') if log else None,
            'jobRecordFile': job_path.name,
            'logEvidenceFile': log_path.name if log else None})
        evidence[job_path.name] = {'bytes': job_path.stat().st_size, 'sha256': digest(job_path)}
        if log:
            evidence[log_path.name] = {'bytes': log_path.stat().st_size, 'sha256': digest(log_path)}
        if failed_steps:
            findings.append({'kind': 'original-job-failed-steps', 'jobId': jid,
                             'name': job['name'], 'failedStepNames': failed_steps})
        if log and 'Validate paper scope' in job['name'] and log.get('fullScopeJSONOutputObserved') is not True:
            findings.append({'kind': 'full-classifier-output-not-captured', 'jobId': jid})

    bound = []
    pending_archives = []
    for aid, (artifact, artifact_path) in sorted(artifacts.items()):
        custody_path = ROOT / f'{aid}-custody.json'
        if not custody_path.is_file():
            pending_archives.append(aid)
            continue
        custody = json.loads(custody_path.read_text())
        assert custody['outerBytes'] == artifact['size_in_bytes']
        assert 'sha256:' + custody['outerSha256'] == artifact['digest']
        assert custody['allMemberCrcAndSha256Verified']
        assert custody['allMembersUniqueSafePaths']
        matches = []
        for jid, (job, job_path) in jobs.items():
            if job['run_id'] != artifact['workflow_run']['id']:
                continue
            log_path = ROOT / f'job-{jid}-log-evidence.json'
            if not log_path.is_file():
                continue
            log = json.loads(log_path.read_text())
            lines = '\n'.join(item['text'] for item in log['selectedSourceUploadErrorLines'])
            if str(aid) not in lines or artifact['digest'][7:] not in lines:
                continue
            if not (stamp(job['started_at']) <= stamp(artifact['created_at']) <= stamp(job['completed_at'])):
                continue
            matches.append((job, job_path, log, log_path))
        if len(matches) != 1:
            findings.append({'kind': 'original-upload-binding-not-unique', 'artifactId': aid,
                             'candidateJobIds': [x[0]['id'] for x in matches]})
            continue
        job, job_path, log, log_path = matches[0]
        observed, observation_format, actual_commit = checkout_observation(log)
        if not observed:
            findings.append({'kind': 'checkout-log-result-not-observed', 'artifactId': aid,
                             'jobId': job['id']})
        refs = [artifact_path, custody_path, job_path, log_path]
        evidence.update({p.name: {'bytes': p.stat().st_size, 'sha256': digest(p)} for p in refs})
        bound.append({'artifactId': aid, 'runId': job['run_id'], 'jobId': job['id'],
                      'producerConclusion': job['conclusion'], 'name': artifact['name'],
                      'bytes': custody['outerBytes'], 'sha256': custody['outerSha256'],
                      'members': custody['memberCount'],
                      'scope': 'optional-preview-nonacceptance' if artifact['name'].startswith('paper-preview-') else 'original-workflow-producer-artifact',
                      'checkoutGitLogResultObserved': observed,
                      'checkoutObservationFormat': observation_format,
                      'actualCheckoutCommit': actual_commit,
                      'verifiedCheckoutTree': TREE if observed else None,
                      'runSyntheticCheckoutContext': CHECKOUT,
                      'artifactTimestampWithinOriginalJob': True,
                      'artifactIdAndDigestInOriginalUploadLog': True,
                      'evidenceFiles': [p.name for p in refs]})

    latest = None
    for line in (ROOT / 'monitor-jobs-polls.jsonl').read_text().splitlines():
        latest = json.loads(line)
    assert latest is not None
    latest_rows = {row['id']: row for row in latest['rows']}
    workflows = []
    for label, rid in RUNS.items():
        path = ROOT / f'{label}-run-completed.json'
        if not path.is_file():
            path = ROOT / f'{label}-run-initial.json'
        value = json.loads(path.read_text())
        assert value['id'] == rid and value['head_sha'] == HEAD and value['run_attempt'] == 1
        state = latest_rows.get(rid, value)
        final_lists = (ROOT / f'{label}-jobs.json').is_file() and (ROOT / f'{label}-artifacts.json').is_file()
        final_run = value['status'] == 'completed'
        workflows.append({'label': label, 'runId': rid, 'status': state['status'],
                          'conclusion': state['conclusion'], 'completeFinalListsCaptured': final_lists,
                          'completeFinalRunCaptured': final_run,
                          'runRecordFile': path.name})
        evidence[path.name] = {'bytes': path.stat().st_size, 'sha256': digest(path)}
        if state['status'] == 'completed' and state['conclusion'] != 'success':
            findings.append({'kind': 'original-workflow-nonsuccess', 'runId': rid,
                             'conclusion': state['conclusion']})
    for name in ['head-git-commit.json', 'checkout-git-commit.json', 'paper-scope-d3ba.yml',
                 'executor-transient-failure.json', 'local-observation-errors.json',
                 'checkpoint-generator-failures.json', 'verify_zip_ram.py',
                 'summarize_logs.py', 'summarize_checkpoint.py',
                 'historical-summarize_logs-unix-only.py',
                 'job-119667611665-windows-format-observation.json']:
        path = ROOT / name
        if path.is_file():
            evidence[name] = {'bytes': path.stat().st_size, 'sha256': digest(path)}
    gate_logs = []
    for path in sorted(ROOT.glob('*-full-log.json')):
        value = json.loads(path.read_text())
        log_path = ROOT / f"job-{value['jobId']}-log-evidence.json"
        log = json.loads(log_path.read_text())
        assert hashlib.sha256(value['raw'].encode()).hexdigest() == log['decodedLogUtf8Sha256']
        evidence[path.name] = {'bytes': path.stat().st_size, 'sha256': digest(path)}
        gate_logs.append({'jobId': value['jobId'], 'fullDecodedLogFile': path.name,
                          'matchesOriginalDecodedLogHash': True,
                          'modeAndResultLines': [line for line in value['raw'].splitlines()
                                                 if re.search(r'\s[A-Z_]*(?:RESULT|MODE):\s', line)]})
    all_final = all(w['status'] == 'completed' and w['completeFinalRunCaptured']
                    and w['completeFinalListsCaptured'] for w in workflows)
    missing_logs = [j['jobId'] for j in completed_job_observations
                    if not j['logEvidenceCaptured'] and j['conclusion'] != 'skipped']
    report = {'schema': 'alpha24d-original-workflow-custody-checkpoint/v2',
              'scope': 'PR24d/d3ba attempt1 only; no accepted-main/release qualification',
              'observedAt': datetime.now(timezone.utc).isoformat(),
              'lastMetadataObservationAt': latest['observedAt'],
              'head': HEAD, 'checkout': CHECKOUT, 'tree': TREE,
              'checkoutParents': ['5a5340a15698165bceb21e252f3bec58d7fd8298', HEAD],
              'workflows': workflows, 'latestPendingOriginalJobStates': latest['rows'],
              'completedOriginalJobs': completed_job_observations,
              'smallStatusGateLogs': gate_logs,
              'missingCompletedOriginalJobLogIds': missing_logs,
              'boundActualArchives': bound, 'pendingArchiveIds': pending_archives,
              'allOriginalWorkflowsHaveFinalRecords': all_final,
              'custodyStatus': 'FINDINGS' if findings else 'CLEAR_FOR_CAPTURED_ARCHIVES',
              'originalResultStatus': 'COMPLETE' if all_final and not pending_archives and not missing_logs else 'PENDING',
              'findings': findings, 'evidenceFiles': evidence,
              'rawZipPersisted': False, 'archiveExtracted': False, 'artifactExecuted': False}
    suffix = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    target = ROOT / f'custody-checkpoint-{suffix}.json'
    target.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'file': str(target), 'sha256': digest(target),
                      'boundArchives': len(bound), 'pendingArchives': pending_archives,
                      'completedWorkflows': sum(w['status'] == 'completed' for w in workflows),
                      'allOriginalResultsFinal': all_final, 'findings': findings}))


if __name__ == '__main__':
    main()
