These records preserve the two actual blockers from main f836f06e8351e64db1da770e16e304b5feb01f28, tree 6aa458f1dad73205fe61ab8277abae785cb76fe4, Agent run40157168357. They are FAILED / NOT QUALIFIED evidence, not a released installation or a new capability-growth sample.

The quality gate reported1failed/504passed because historical CI omitted the new mandatory Strategy prerequisite. The gallery-minimal check asserted #main immediately after focused skip-link Enter. Its actual URL was not recorded, so a navigation race remains a hypothesis. Corrective PR4899 preserves all original conditions, adds the missing dependency and premerge policy contract, and awaits the exact canonical skip destination. The frozen scientific source and preferred papers are unchanged.

Both original ZIPs and both full job logs are retained byte-for-byte. The index splits the ZIPs into4MiB pieces only for transport. Original archive SHA-256 and each part identity are in MANIFEST.json. A read-only audit checked22nested ZIP containers/1146members/415unique text bodies/80images and independently checked both logs; CRCs/paths are valid and no exposed credentials were found. Two nested JPGs contain public MontrealAI workflow-dispatch UI, with no private account settings or credentials. No archive content was executed. No original Harness/Fleet permission or authority is conveyed.

To reconstruct an archive in a new empty directory containing these files, use the following ordinary byte concatenation and verify before any extraction:

```python
import hashlib, json
from pathlib import Path
index = json.loads(Path('MANIFEST.json').read_text())
for artifact in index['artifacts']:
    target = Path(artifact['archive'])
    assert target.name == str(target)
    digest = hashlib.sha256()
    total = 0
    with target.open('xb') as output:
        for part in artifact['parts']:
            path = Path(part['path'])
            assert path.name == str(path)
            data = path.read_bytes()
            assert len(data) == part['bytes']
            assert hashlib.sha256(data).hexdigest() == part['sha256']
            output.write(data)
            digest.update(data)
            total += len(data)
    assert total == artifact['bytes']
    assert digest.hexdigest() == artifact['sha256']
```

The corrective source and later actual release/public-install acceptance retain their own identities and required gates. This snapshot does not claim those later outcomes. Costs of failed CI, whole engineering/QA, human effort and monetary use remain unknown rather than converted into profit. Historical accepted releases and earlier evidence are preserved.
