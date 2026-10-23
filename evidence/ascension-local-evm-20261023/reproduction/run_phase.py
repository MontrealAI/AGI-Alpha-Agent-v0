#!/usr/bin/env python3
"""Record bounded phases of the existing isolated local Ascension rehearsal."""
from __future__ import annotations

import hashlib
import json
import os
from urllib.parse import urlsplit
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone

BASE = Path(__file__).resolve().parent
SOURCE = BASE / "source"
EVIDENCE = BASE / "evidence"
PROJECT = SOURCE / "tests/contracts"
NODE = Path("/workspace/scratch/5d02e86cc826/thermal-toolchain/node-v22.17.1-linux-x64/bin/node")
PYTHON = Path("/workspace/scratch/5d02e86cc826/thermal-python/bin/python")
NPM = NODE.parent.parent / "lib/node_modules/npm/bin/npm-cli.js"
ENV = {
    "PATH": str(NODE.parent) + ":/usr/bin:/bin",
    "CI": "1",
    "HARDHAT_DISABLE_TELEMETRY_PROMPT": "true",
    "ALPHA_PYTHON": str(PYTHON),
    "PYTHONPATH": str(SOURCE),
    "PYTHONNOUSERSITE": "1",
    "NO_DISCLAIMER": "1",
    "OPENAI_AGENTS_DISABLE_TRACING": "true",
}
TESTS = [
    "test/ascension/lifecycle.test.js",
    "test/ascension/marketplace.test.js",
    "test/ascension/settlement.test.js",
    "test/ascension/native-handoff.test.js",
    "test/ascension/successor-adapter.test.js",
]


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    if len(sys.argv) != 4:
        raise SystemExit("Usage: run_phase.py PHASE NEW_LABEL EXECUTION_CONTEXT")
    phase, label, context = sys.argv[1:]
    if not label.replace("-", "").replace("_", "").isalnum():
        raise SystemExit("Label must contain only ASCII letters, digits, hyphens or underscores")
    env = dict(ENV)
    timeout = 600
    if phase == "install":
        # Dependency acquisition alone uses the runtime-supplied, credential-free
        # proxy and public CA. EVM/test phases keep the original scrubbed ENV.
        proxy = os.environ.get("HTTPS_PROXY")
        if proxy:
            parsed = urlsplit(proxy)
            if (parsed.scheme != "http" or parsed.hostname != "browser-proxy" or parsed.port != 8889
                    or parsed.username is not None or parsed.password is not None):
                raise SystemExit("Unexpected dependency acquisition proxy; refuse implicit credentials")
            env.update({key: proxy for key in ["HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"]})
        ca = os.environ.get("NODE_EXTRA_CA_CERTS")
        if ca:
            certificate = Path(ca)
            contents = certificate.read_bytes()
            if b"BEGIN CERTIFICATE" not in contents or b"PRIVATE KEY" in contents:
                raise SystemExit("Runtime CA input is not a public certificate bundle")
            env["NODE_EXTRA_CA_CERTS"] = str(certificate)
        command = [str(NODE), str(NPM), "ci", "--ignore-scripts", "--no-audit", "--no-fund",
                   "--userconfig=" + str(BASE / "npm-user-empty.npmrc"),
                   "--globalconfig=" + str(BASE / "npm-global-empty.npmrc"),
                   "--cache=" + str(BASE / "npm-cache"), "--fetch-retries=0", "--fetch-timeout=60000"]
        timeout = 180
    elif phase == "dependencies-node":
        command = [str(NODE), str(BASE / "check_node_dependencies.cjs")]
        timeout = 60
    elif phase == "dependencies-python":
        command = [str(PYTHON), str(BASE / "check_python_dependencies.py")]
        timeout = 60
    elif phase == "tests":
        env["SUCCESSOR_EVM_EVIDENCE_DIR"] = str(EVIDENCE / "native-adapter")
        command = [str(NODE), "node_modules/.bin/hardhat", "--config", "hardhat.config.js",
                   "--network", "hardhat", "test", *TESTS]
        timeout = 900
    elif phase == "demo":
        output = EVIDENCE / "demo-receipt.json"
        if output.exists():
            raise SystemExit("Refusing to overwrite the existing demo receipt")
        env["ASCENSION_DEMO_OUTPUT"] = str(output)
        command = [str(NODE), "node_modules/.bin/hardhat", "--config", "hardhat.config.js",
                   "--network", "hardhat", "run", "--no-compile", "scripts/demo.js"]
        timeout = 180
    elif phase == "rounding":
        output = EVIDENCE / "small-integers" / label
        if output.exists():
            raise SystemExit("Refusing to overwrite small-integer evidence")
        env["ASCENSION_SMALL_INTEGER_PROTOCOL"] = str(EVIDENCE / "payout-small-integers-protocol.json")
        env["ASCENSION_SMALL_INTEGER_OUTPUT"] = str(output)
        command = [str(NODE), "node_modules/.bin/hardhat", "--config", "hardhat.config.js",
                   "--network", "hardhat", "test", "--no-compile",
                   "test/ascension/payout-small-integers.local.test.js"]
        timeout = 180
    else:
        raise SystemExit("Unknown phase")

    stdout = EVIDENCE / (label + ".stdout.txt")
    stderr = EVIDENCE / (label + ".stderr.txt")
    receipt = EVIDENCE / (label + ".json")
    for target in (stdout, stderr, receipt):
        if target.exists():
            raise SystemExit("Refusing to overwrite evidence: " + str(target))
    record = {
        "schema": "ascension-local-evm-phase/v1", "phase": phase, "label": label,
        "executionContext": context, "startedAt": utc(), "command": command,
        "workingDirectory": str(PROJECT), "environment": env,
        "timeoutSeconds": timeout, "sourceManifestSha256": sha(EVIDENCE / "source-copy.json"),
        "runnerSha256": sha(Path(__file__)),
        "nodeExecutableSha256": sha(NODE), "pythonExecutable": str(PYTHON.resolve()),
        "networkBoundary": "Application guards require an unforked in-process Hardhat provider. This is not OS-wide egress isolation. Initial dependency acquisition may use the public npm registry.",
        "credentialsOrExternalProviderSupplied": False,
    }
    print(json.dumps({"phase": phase, "label": label, "startedAt": record["startedAt"]}), flush=True)
    code = 1
    with stdout.open("xb") as out, stderr.open("xb") as err:
        try:
            result = subprocess.run(command, cwd=PROJECT, env=env, stdout=out, stderr=err, timeout=timeout)
            code = result.returncode
            record["exitCode"] = code
        except subprocess.TimeoutExpired as exc:
            record["exitCode"] = None
            record["error"] = {"type": type(exc).__name__, "message": str(exc)}
        except OSError as exc:
            record["exitCode"] = None
            record["error"] = {"type": type(exc).__name__, "message": str(exc), "errno": exc.errno}
    record["finishedAt"] = utc()
    record["stdout"] = {"path": stdout.name, "bytes": stdout.stat().st_size, "sha256": sha(stdout)}
    record["stderr"] = {"path": stderr.name, "bytes": stderr.stat().st_size, "sha256": sha(stderr)}
    with receipt.open("x") as stream:
        stream.write(json.dumps(record, indent=2) + "\n")
    print(json.dumps({"phase": phase, "label": label, "exitCode": record["exitCode"],
                      "error": record.get("error"), "receipt": str(receipt),
                      "finishedAt": record["finishedAt"]}), flush=True)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
