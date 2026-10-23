from pathlib import Path
import hashlib
import importlib
from importlib.metadata import version
import json
import sys

source = Path(__file__).resolve().parent / "source"
modules = [
    "alpha_factory_v1.core.runtime.engine",
    "alpha_factory_v1.core.runtime.store",
    "alpha_factory_v1.core.runtime.ascension",
    "alpha_factory_v1.core.runtime.successor.ascension",
]
records = []
for name in modules:
    module = importlib.import_module(name)
    path = Path(module.__file__).resolve()
    if not path.is_relative_to(source):
        raise RuntimeError("Native module did not resolve to copied source: " + name)
    records.append({"module": name, "path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
from eth_hash.auto import keccak
assert keccak(b"").hex() == "c5d2460186f7233c927e7db2dcc703c0e500b653ca82273b7bfad8045d85a470"
print(json.dumps({
    "python": sys.version, "executable": sys.executable,
    "dependencies": {name: version(name) for name in ["eth-hash", "pycryptodome", "cryptography", "pydantic"]},
    "nativeSourceModules": records, "keccakEmptyVectorPassed": True,
    "journalInitialized": False, "externalProviderInvoked": False,
}, indent=2))
