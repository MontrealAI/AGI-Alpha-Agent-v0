"""Read actual supplied artifact bytes in RAM; persist only a member inventory."""
import datetime
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import stat
import sys
import urllib.request
import zipfile


def audit(spec):
    artifact = spec['artifact']
    expected = artifact['size_in_bytes']
    assert type(expected) is int and 0 < expected <= 250_000_000
    assert artifact['workflow_run']['head_sha'] == '24d58598f896106323f2c120487586bdf5104612'
    assert artifact['digest'].startswith('sha256:') and not artifact['expired']
    memory = io.BytesIO(); outer = hashlib.sha256(); total = 0
    with urllib.request.urlopen(spec['download_url'], timeout=60) as response:
        while True:
            chunk = response.read(min(1_000_000, expected - total + 1))
            if not chunk:
                break
            total += len(chunk); assert total <= expected, 'Artifact exceeds API byte size'
            outer.update(chunk); memory.write(chunk)
    assert total == expected and 'sha256:' + outer.hexdigest() == artifact['digest'], 'API outer size/SHA256 mismatch'
    memory.seek(0); members = []; names = set(); regular = set()
    with zipfile.ZipFile(memory) as archive:
        infos = archive.infolist()
        assert len(infos) <= 20_000 and sum(item.file_size for item in infos) <= 1_500_000_000
        for item in infos:
            name = item.filename; clean = name.rstrip('/') if item.is_dir() else name; path = PurePosixPath(clean)
            assert clean and not any(ord(c) < 32 or ord(c) == 127 for c in name)
            assert '\\' not in name and not path.is_absolute() and str(path) == clean and '..' not in path.parts
            assert ':' not in path.parts[0] and clean not in names and not item.flag_bits & 1
            kind = stat.S_IFMT(item.external_attr >> 16)
            assert kind in ({0, stat.S_IFDIR} if item.is_dir() else {0, stat.S_IFREG})
            names.add(clean)
            if not item.is_dir():
                regular.add(clean)
            member_sha = hashlib.sha256(); count = 0
            with archive.open(item) as stream:
                while True:
                    chunk = stream.read(1_000_000)
                    if not chunk:
                        break
                    count += len(chunk); member_sha.update(chunk)
            assert count == item.file_size and (not item.is_dir() or count == 0)
            members.append({'path': name, 'bytes': count, 'sha256': member_sha.hexdigest(),
                            'crc32': f'{item.CRC:08x}', 'directory': item.is_dir()})
        assert all(str(parent) not in regular for name in names for parent in PurePosixPath(name).parents)
    record = {'schema': 'successor/original-pr-artifact-ram-custody/v1',
              'scope': '24d/d3ba pull-request attempt1 only; no accepted-main or release qualification',
              'runId': artifact['workflow_run']['id'], 'runAttempt': 1,
              'headCommit': artifact['workflow_run']['head_sha'],
              'syntheticCheckout': 'd3ba2c3a4a275d7f2c7619504b703f931b8c4507',
              'syntheticTree': 'ffa3d663519e713eca31a9840b8bf6816e53e12a',
              'syntheticParents': ['5a5340a15698165bceb21e252f3bec58d7fd8298', '24d58598f896106323f2c120487586bdf5104612'],
              'artifactId': artifact['id'], 'artifactName': artifact['name'],
              'artifactCreatedAt': artifact['created_at'], 'artifactUpdatedAt': artifact['updated_at'],
              'outerBytes': total, 'outerSha256': outer.hexdigest(), 'outerByteIdentityVerified': True,
              'allMemberCrcAndSha256Verified': True, 'allMembersUniqueSafePaths': True,
              'memberCount': len(members), 'members': members, 'rawZipPersisted': False,
              'archiveExtracted': False, 'artifactExecuted': False,
              'verifiedAt': datetime.datetime.now(datetime.timezone.utc).isoformat()}
    target = Path('/dev/shm/alpha24d-other-original-custody') / (str(artifact['id']) + '-custody.json')
    assert not target.exists(); target.write_text(json.dumps(record, indent=2) + '\n'); memory.close()
    return {'artifactId': artifact['id'], 'bytes': total, 'sha256': record['outerSha256'], 'members': len(members),
            'reportSha256': hashlib.sha256(target.read_bytes()).hexdigest()}


if __name__ == '__main__':
    for spec in json.load(sys.stdin):
        print(json.dumps(audit(spec)), flush=True)
