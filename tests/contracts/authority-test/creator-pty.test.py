"""Actual local Linux PTYs, disposable synthetic keys; no provider or live signing."""
import errno
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
import unittest

NODE = sys.argv[1] if len(sys.argv) > 1 else "node"
sys.argv = [sys.argv[0]]
CHILD = Path(__file__).with_name("creator-pty-child.cjs")
SYNTHETIC = b"0x" + b"11" * 32


class CreatorPtyTests(unittest.TestCase):
    def campaign(self, action):
        master, slave = pty.openpty()
        initial = termios.tcgetattr(slave)
        output = bytearray()
        process = subprocess.Popen(
            [NODE, str(CHILD)], stdin=slave, stdout=slave, stderr=slave,
            env={"PATH": "/usr/bin:/bin"}, close_fds=True,
        )
        deadline = time.monotonic() + 10

        def until(marker):
            while marker not in output:
                self.assertLess(time.monotonic(), deadline, "Bounded synthetic PTY wait exhausted")
                ready, _, _ = select.select([master], [], [], 0.1)
                if ready:
                    try:
                        data = os.read(master, 65536)
                    except OSError as error:
                        if error.errno == errno.EIO:
                            self.fail("PTY closed before expected public boundary")
                        raise
                    self.assertTrue(data, "PTY closed before expected public boundary")
                    output.extend(data)

        try:
            until(b"to approve these five creations only:")
            os.write(master, b"DEPLOY " + b"a" * 64 + b"\r")
            until(b"input hidden):")
            self.assertFalse(termios.tcgetattr(slave)[3] & termios.ECHO)
            if action == "sign":
                os.write(master, SYNTHETIC + b"\r")
                until(b"TERMINAL_OK")
                expected = 0
            elif action == "wrong-key":
                os.write(master, b"0x" + b"22" * 32 + b"\r")
                until(b"TERMINAL_STOPPED")
                expected = 1
            else:
                os.write(master, SYNTHETIC[:20])
                process.send_signal(signal.SIGINT)
                until(b"TERMINAL_STOPPED")
                expected = 1
            self.assertEqual(process.wait(timeout=5), expected)
            self.assertEqual(termios.tcgetattr(slave), initial)
            self.assertNotIn(SYNTHETIC, output)
            self.assertNotIn(b"0x" + b"22" * 32, output)
        finally:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=5)
            os.close(master)
            os.close(slave)

    def test_confirmation_then_real_tty_hidden_signer(self):
        self.campaign("sign")

    def test_wrong_key_is_not_echoed(self):
        self.campaign("wrong-key")

    def test_interrupt_restores_terminal(self):
        self.campaign("interrupt")


if __name__ == "__main__":
    unittest.main(verbosity=2)
