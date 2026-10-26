import hashlib
import json
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from conventional import extract

def fixture(consumer, before, after=None, scopes=("run",), extra=None):
    src = {"consumer": {"path": "app.py", "text": consumer},
           "before": {"path": "samplelib/api.py", "text": before},
           "after": {"path": "samplelib/api.py", "text": after if after is not None else before}}
    sides = {"before": ["before"], "after": ["after"]}
    for side, mapping in (extra or {}).items():
        for ident, (path, text) in mapping.items():
            src[ident] = {"path": path, "text": text}
            sides[side].append(ident)
    for s in src.values():
        s.update(repository="example/example", commit="1"*40, sha256=hashlib.sha256(s["text"].encode()).hexdigest())
    return {"schema": "alpha-transfer-raw-task/v1", "id": "toy", "title": "Toy",
            "purpose": "Development only", "dependency": {"package": "samplelib", "importRoots": ["samplelib"],
            "before": {"version": "1"}, "after": {"version": "2"}},
            "consumer": {"source": "consumer", "scopeSymbols": list(scopes)}, "sources": src,
            "providerSides": sides, "licenseRecords": []}

class Tests(unittest.TestCase):
    def test_alias_function(self):
        r = extract(fixture("from samplelib.api import send as emit\ndef run():\n    return emit(1, mode=2)\n",
                            "def send(x, mode=1): pass\n"))
        self.assertEqual(r["claims"][0]["before"], {"source":"before", "symbol":"send"})
        self.assertEqual(r["claims"][0]["callee"], "emit")
        self.assertFalse(r["unresolved"])

    def test_module_alias_and_local_alias(self):
        r = extract(fixture("import samplelib.api as api\ndef run():\n    send = api.send\n    return send(1)\n",
                            "def send(x): pass\n"))
        self.assertEqual(len(r["claims"]), 1)

    def test_constructor_receiver(self):
        r = extract(fixture("from samplelib.api import Client\ndef run():\n    client = Client()\n    return client.send(1)\n",
                            "class Client:\n    def __init__(self): pass\n    def send(self, x): pass\n"))
        self.assertEqual([c["before"]["symbol"] for c in r["claims"]], ["Client.__init__", "Client.send"])

    def test_super(self):
        r = extract(fixture("from samplelib.api import Client\nclass Handler(Client):\n    def __init__(self):\n        super().__init__(x=1)\n",
                            "class Client:\n    def __init__(self, x=1): pass\n", scopes=("Handler.__init__",)))
        self.assertEqual(len(r["claims"]), 1)
        self.assertEqual(r["claims"][0]["before"]["symbol"], "Client.__init__")

    def test_reexport(self):
        r = extract(fixture("from samplelib import send\ndef run():\n    return send(1)\n", "def send(x): pass\n",
            extra={"before":{"binit":("samplelib/__init__.py", "from .api import send\n")},
                   "after":{"ainit":("samplelib/__init__.py", "from .api import send\n")}}))
        self.assertEqual(r["claims"][0]["before"]["symbol"], "send")
        self.assertEqual(r["claims"][0]["before"]["source"], "before")

    def test_decorated_and_expanded(self):
        r = extract(fixture("from samplelib.api import send\ndef run(**kw):\n    return send(**kw)\n",
                            "@decorator\ndef send(x): pass\n"))
        self.assertFalse(r["claims"])
        self.assertEqual(len(r["unresolved"]), 1)

    def test_dynamic(self):
        r = extract(fixture("import samplelib.api as api\ndef run(name):\n    return getattr(api, name)(1)\n",
                            "def send(x): pass\n"))
        self.assertFalse(r["claims"])
        self.assertEqual(len(r["unresolved"]), 1)

    def test_branch_uncertainty(self):
        r = extract(fixture("from samplelib.api import send, recv\ndef run(flag):\n    if flag:\n        fn = send\n    else:\n        fn = recv\n    return fn(1)\n",
                            "def send(x): pass\ndef recv(x): pass\n"))
        self.assertFalse(r["claims"])
        self.assertEqual(len(r["unresolved"]), 1)

    def test_scope(self):
        r = extract(fixture("from samplelib.api import send\ndef ignored():\n    return send(2)\ndef run():\n    return send(1)\n",
                            "def send(x): pass\n"))
        self.assertEqual(len(r["claims"]), 1)
        self.assertEqual(r["claims"][0]["line"], 5)

    def test_side_missing(self):
        r = extract(fixture("from samplelib.api import send\ndef run():\n    return send(1)\n", "def send(x): pass\n", "def other(x): pass\n"))
        self.assertFalse(r["claims"])
        self.assertEqual(len(r["unresolved"]), 1)

    def test_ambiguous_definition(self):
        r = extract(fixture("from samplelib.api import send\ndef run():\n    return send(1)\n", "def send(x): pass\ndef send(x, y): pass\n"))
        self.assertFalse(r["claims"])
        self.assertEqual(len(r["unresolved"]), 1)

    def test_digest(self):
        task = fixture("from samplelib.api import send\ndef run():\n    return send(1)\n", "def send(x): pass\n")
        r = extract(task)
        self.assertEqual(r["inputSha256"], hashlib.sha256(json.dumps(task, sort_keys=True, ensure_ascii=False, separators=(",",":"), allow_nan=False).encode()).hexdigest())
        task["sources"]["before"]["text"] += "\n"
        with self.assertRaises(ValueError):
            extract(task)

    def test_import_after_function(self):
        r = extract(fixture("def run():\n    return emit(1)\nfrom samplelib.api import send as emit\n", "def send(x): pass\n"))
        self.assertEqual(len(r["claims"]), 1)

    def test_late_global_shadow(self):
        r = extract(fixture("from samplelib.api import send\ndef run():\n    return send(1)\nsend = lambda x: x\n", "def send(x): pass\n"))
        self.assertFalse(r["claims"])

    def test_unbound_local(self):
        r = extract(fixture("from samplelib.api import send\ndef run():\n    result = send(1)\n    send = lambda x: x\n    return result\n", "def send(x): pass\n"))
        self.assertFalse(r["claims"])

    def test_decorated_super(self):
        r = extract(fixture("from samplelib.api import Client\n@modify\nclass Handler(Client):\n    def __init__(self):\n        super().__init__()\n", "class Client:\n    def __init__(self): pass\n", scopes=("Handler.__init__",)))
        self.assertFalse(r["claims"])
        self.assertEqual(len(r["unresolved"]), 1)

    def test_match_body(self):
        r = extract(fixture("from samplelib.api import send\ndef run(x):\n    match x:\n        case 1:\n            return send(1)\n", "def send(x): pass\n"))
        self.assertEqual(len(r["claims"]), 1)

    def test_required_optional_import(self):
        r = extract(fixture("try:\n    from samplelib.api import send\nexcept ImportError:\n    raise RuntimeError('dependency required')\ndef run():\n    return send(1)\n", "def send(x): pass\n"))
        self.assertEqual(len(r["claims"]), 1)

if __name__ == "__main__":
    unittest.main()

