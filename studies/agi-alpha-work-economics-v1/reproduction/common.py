"""Shared read-only identity checks and new-destination copying helpers."""
import hashlib
import json
import shutil
from pathlib import Path

EXPECTED_FREEZE = '41b8b56a39993e29dc313faa8633e36abd910872ab43e9a5dbe1ab2edc589407'
DEFAULT_ROOT = Path(__file__).resolve().parents[1]

def read_json(path):
    return json.loads(Path(path).read_text(), parse_constant=lambda x: (_ for _ in ()).throw(ValueError('Nonstandard JSON number: ' + x)))

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def child(root, name):
    root = Path(root).resolve()
    path = (root / name).resolve()
    if not path.is_relative_to(root) or path == root:
        raise ValueError('Path escapes source root: ' + str(name))
    return path

def verify_freeze(root):
    root = Path(root).resolve()
    freeze_path = root / 'protocol/FREEZE.json'
    if sha(freeze_path) != EXPECTED_FREEZE:
        raise ValueError('Freeze identity differs from the publicly committed original protocol.')
    freeze = read_json(freeze_path)
    issues = []
    for row in freeze['files']:
        path = child(root, row['path'])
        if not path.is_file() or path.stat().st_size != row['bytes'] or sha(path) != row['sha256']:
            issues.append(row['path'])
    if issues:
        raise ValueError('Frozen file mismatch: ' + ', '.join(issues))
    return freeze

def new_destination(source, destination):
    source, destination = Path(source).resolve(), Path(destination).resolve()
    if destination == source or destination.is_relative_to(source) or source.is_relative_to(destination):
        raise ValueError('Destination must be outside, and must not contain, the original companion.')
    if destination.exists():
        raise FileExistsError('Refusing an existing destination: ' + str(destination))
    if not destination.parent.is_dir():
        raise FileNotFoundError('Create the destination parent directory first: ' + str(destination.parent))
    destination.mkdir()
    return destination

def copy_files(source, destination, names):
    copied = []
    for name in sorted(set(names)):
        origin = child(source, name)
        if not origin.is_file():
            raise FileNotFoundError(origin)
        target = child(destination, name)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(origin, target)
        if sha(origin) != sha(target):
            raise ValueError('Copy integrity failed: ' + name)
        copied.append({'path': name, 'bytes': target.stat().st_size, 'sha256': sha(target)})
    return copied

def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')
