"""Test-only real PTY driver. The only accepted signing material is a fixed public fixture."""
import errno
import hashlib
import json
import os
from pathlib import Path
import pty
import select
import signal
import subprocess
import sys
import termios
import time
from urllib.parse import urlparse


def interrupted(_signal, _frame):
    raise RuntimeError("Disposable PTY driver interrupted")


def main():
    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    node, action, plan_hash, result_file = sys.argv[1:]
    assert action in ("create", "wrong-key", "checkpoint", "refuse")
    assert len(plan_hash) == 64 and all(c in "0123456789abcdef" for c in plan_hash)
    endpoints = [urlparse(os.environ[name]) for name in ("ALPHA_READ_ONLY_RPC_URL", "ALPHA_RAW_RELAY_RPC_URL")]
    assert all(url.scheme == "https" and url.hostname == "127.0.0.1" for url in endpoints)
    assert endpoints[0].netloc == endpoints[1].netloc
    cwd = Path(__file__).resolve().parent.parent
    master, slave = pty.openpty()
    initial = termios.tcgetattr(slave)
    output = bytearray()
    command = [node, "--max-old-space-size=384", str(cwd / "node_modules/hardhat/internal/cli/cli.js"),
               "run", "--no-compile", "--config", "hardhat.creator.config.js", "--network", "mainnet", "scripts/deploy-mainnet-creator.js"]
    child = subprocess.Popen(command, cwd=cwd, stdin=slave, stdout=slave, stderr=slave,
                             env=os.environ.copy(), close_fds=True, start_new_session=True)
    deadline = time.monotonic() + 600
    confirmations = prompts = 0
    synthetic = b"0x" + b"11" * 32
    wrong = b"0x" + b"22" * 32
    try:
        while True:
            assert time.monotonic() < deadline, "Bounded creator CLI rehearsal timeout"
            ready, _, _ = select.select([master], [], [], 0.05)
            if ready:
                try:
                    data = os.read(master, 65536)
                except OSError as error:
                    if error.errno != errno.EIO:
                        raise
                    data = b""
                output.extend(data)
                assert len(output) <= 1024 * 1024, "Bounded private PTY output exhausted"
            if b"to approve these five creations only:" in output and not confirmations:
                assert action in ("create", "wrong-key"), "Unexpected signing confirmation"
                text = output.decode("utf-8", errors="strict")
                start = text.index('{\r\n  "schema": "agialpha.creator-terminal-review.v1"')
                review, _ = json.JSONDecoder().raw_decode(text[start:])
                assert review["planSha256"] == plan_hash and review["chainId"] == 1
                assert review["creatorOperations"] == 5 and review["governorOperationsSignedHere"] == 0
                assert len(review["transactions"]) == 5 and review["transportTrust"]["sha256"]
                for transaction in review["transactions"]:
                    assert transaction["envelope"]["to"] is None and transaction["envelope"]["type"] == 2
                os.write(master, b"DEPLOY " + plan_hash.encode("ascii") + b"\r")
                confirmations += 1
            if b"input hidden):" in output and not prompts:
                assert action in ("create", "wrong-key") and confirmations == 1
                assert not termios.tcgetattr(slave)[3] & termios.ECHO
                os.write(master, (synthetic if action == "create" else wrong) + b"\r")
                prompts += 1
            if child.poll() is not None and not ready:
                break
        code = child.wait(timeout=5)
        assert code == (1 if action in ("wrong-key", "refuse") else 0), "Unexpected creator CLI result"
        assert confirmations == prompts == (1 if action in ("create", "wrong-key") else 0)
        assert termios.tcgetattr(slave) == initial, "Terminal mode was not restored"
        assert synthetic not in output and wrong not in output, "Fixture key echoed"
        assert b"PRIVATE KEY" not in output and b"ALPHA_PROVIDER_SECRET_SENTINEL" not in output
        report = {"schema": "agialpha.creator-native-pty.v1", "action": action, "exitCode": code,
                  "confirmations": confirmations, "keyPrompts": prompts, "terminalRestored": True,
                  "transcriptSha256": hashlib.sha256(output).hexdigest(), "transcriptBytes": len(output),
                  "rawTranscriptRetained": False, "fixedPublicFixtureKeyOnly": True}
        with open(result_file, "x", encoding="utf-8") as stream:
            json.dump(report, stream, indent=2)
            stream.write("\n")
    finally:
        if child.poll() is None:
            os.killpg(child.pid, signal.SIGKILL)
            child.wait(timeout=5)
        os.close(master)
        os.close(slave)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        print("Disposable creator PTY rehearsal stopped; private transcript omitted.", file=sys.stderr)
        sys.exit(1)
