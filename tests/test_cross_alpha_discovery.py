# SPDX-License-Identifier: Apache-2.0
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
import tempfile
import types
from unittest.mock import patch, Mock
import threading
import time

STUB = "alpha_factory_v1/demos/cross_industry_alpha_factory/cross_alpha_discovery_stub.py"


class TestCrossAlphaDiscoveryStub(unittest.TestCase):
    def test_list_option(self) -> None:
        result = subprocess.run([sys.executable, STUB, "--list"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        data = json.loads(result.stdout)
        self.assertIsInstance(data, list)
        self.assertGreaterEqual(len(data), 5)

    def test_sampling(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp) / "log.json"
            result = subprocess.run(
                [
                    sys.executable,
                    STUB,
                    "--sample",
                    "-n",
                    "2",
                    "--seed",
                    "1",
                    "--ledger",
                    str(ledger),
                    "--model",
                    "gpt-4o-mini",
                ],
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(ledger.exists())
            logged = json.loads(ledger.read_text())
            self.assertIsInstance(logged, list)
            self.assertEqual(len(logged), 2)
            self.assertEqual(len(logged), len({json.dumps(i, sort_keys=True) for i in logged}))

    def test_accumulate_entries(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp) / "log.json"
            for seed in ("1", "2"):
                result = subprocess.run(
                    [
                        sys.executable,
                        STUB,
                        "--sample",
                        "-n",
                        "1",
                        "--seed",
                        seed,
                        "--ledger",
                        str(ledger),
                        "--model",
                        "gpt-4o-mini",
                    ],
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(result.returncode, 0, result.stderr)

            logged = json.loads(ledger.read_text())
            self.assertIsInstance(logged, list)
            self.assertEqual(len(logged), 2)

    def test_env_overrides_default_ledger(self) -> None:
        with tempfile.TemporaryDirectory() as home:
            default = Path(home) / ".alpha_factory" / "cross_alpha_log.json"
            with tempfile.TemporaryDirectory() as tmp:
                ledger = Path(tmp) / "env_log.json"
                env = os.environ.copy()
                env["HOME"] = home
                env["CROSS_ALPHA_LEDGER"] = str(ledger)
                result = subprocess.run(
                    [
                        sys.executable,
                        STUB,
                        "--sample",
                        "-n",
                        "1",
                        "--seed",
                        "3",
                        "--model",
                        "gpt-4o-mini",
                    ],
                    capture_output=True,
                    text=True,
                    env=env,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertFalse(default.exists(), "default ledger should not be used")
                self.assertTrue(ledger.exists())
                data = json.loads(ledger.read_text())
                self.assertIsInstance(data, list)
                self.assertEqual(len(data), 1)

    def test_default_ledger_creation(self) -> None:
        with tempfile.TemporaryDirectory() as home:
            env = os.environ.copy()
            env["HOME"] = home
            env.pop("CROSS_ALPHA_LEDGER", None)
            default = Path(home) / ".alpha_factory" / "cross_alpha_log.json"
            result = subprocess.run(
                [
                    sys.executable,
                    STUB,
                    "--sample",
                    "-n",
                    "1",
                    "--seed",
                    "5",
                    "--model",
                    "gpt-4o-mini",
                ],
                capture_output=True,
                text=True,
                env=env,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(default.exists())
            data = json.loads(default.read_text())
            self.assertIsInstance(data, list)
            self.assertEqual(len(data), 1)

    def test_no_log_flag(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp) / "no_log.json"
            result = subprocess.run(
                [
                    sys.executable,
                    STUB,
                    "--sample",
                    "-n",
                    "1",
                    "--seed",
                    "4",
                    "--ledger",
                    str(ledger),
                    "--no-log",
                    "--model",
                    "gpt-4o-mini",
                ],
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse(ledger.exists())

    def test_openai_response_format(self) -> None:
        from alpha_factory_v1.demos.cross_industry_alpha_factory import (
            cross_alpha_discovery_stub as stub,
        )

        resp = types.SimpleNamespace(
            choices=[
                types.SimpleNamespace(
                    message=types.SimpleNamespace(
                        content='[{"sector":"Test","opportunity":"Unverified provider idea"}]'
                    )
                )
            ]
        )
        openai_mock = types.SimpleNamespace(ChatCompletion=types.SimpleNamespace(create=Mock(return_value=resp)))

        with patch.dict(os.environ, {"OPENAI_API_KEY": "x"}):
            with patch.object(stub, "openai", openai_mock):
                stub.discover_alpha(num=1, ledger=None, model="gpt-4o-mini", generate=True)

        openai_mock.ChatCompletion.create.assert_called_once()
        kwargs = openai_mock.ChatCompletion.create.call_args.kwargs
        self.assertEqual(kwargs.get("response_format"), {"type": "json_object"})
        self.assertEqual(kwargs.get("timeout"), stub.OPENAI_TIMEOUT_SEC)

    def test_openai_v1_response_format(self) -> None:
        from alpha_factory_v1.demos.cross_industry_alpha_factory import (
            cross_alpha_discovery_stub as stub,
        )

        resp = types.SimpleNamespace(
            choices=[
                types.SimpleNamespace(
                    message=types.SimpleNamespace(
                        content='[{"sector":"Test","opportunity":"Unverified provider idea"}]'
                    )
                )
            ]
        )
        openai_mock = types.SimpleNamespace(
            chat=types.SimpleNamespace(completions=types.SimpleNamespace(create=Mock(return_value=resp)))
        )

        with patch.dict(os.environ, {"OPENAI_API_KEY": "x"}):
            with patch.object(stub, "openai", openai_mock):
                stub.discover_alpha(num=1, ledger=None, model="gpt-4o-mini", generate=True)

        openai_mock.chat.completions.create.assert_called_once()
        kwargs = openai_mock.chat.completions.create.call_args.kwargs
        self.assertEqual(kwargs.get("response_format"), {"type": "json_object"})
        self.assertEqual(kwargs.get("timeout"), stub.OPENAI_TIMEOUT_SEC)

    def test_concurrent_writes(self) -> None:
        from alpha_factory_v1.demos.cross_industry_alpha_factory import (
            cross_alpha_discovery_stub as stub,
        )

        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp) / "thread_log.json"

            def worker(seed: int) -> None:
                stub.discover_alpha(num=1, seed=seed, ledger=ledger, model="gpt-4o-mini", sample=True)

            threads = [threading.Thread(target=worker, args=(i,)) for i in range(5)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

            data = json.loads(ledger.read_text())
            self.assertEqual(len(data), 5)

    def test_missing_openai_fails_without_writing(self) -> None:
        from alpha_factory_v1.demos.cross_industry_alpha_factory import cross_alpha_discovery_stub as stub

        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp) / "log.json"
            with patch.object(stub, "openai", None), patch.dict(os.environ, {"OPENAI_API_KEY": "test"}):
                with self.assertRaisesRegex(ValueError, "requires the OpenAI package"):
                    stub.discover_alpha(generate=True, ledger=ledger)
            self.assertFalse(ledger.exists())

    def test_invalid_provider_json_never_writes(self) -> None:
        from alpha_factory_v1.demos.cross_industry_alpha_factory import cross_alpha_discovery_stub as stub

        invalid_responses = [
            '{"sector":"A","sector":"B","opportunity":"C"}',
            *(
                '{"sector":"A","opportunity":"B","extra":' + value + "}"
                for value in ("NaN", "Infinity", "-Infinity", "1e999", "-1e999")
            ),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp) / "log.json"
            for content in invalid_responses:
                for existing in (False, True):
                    with self.subTest(content=content, existing=existing):
                        ledger.unlink(missing_ok=True)
                        if existing:
                            ledger.write_bytes(b"[ ]\n")
                        response = types.SimpleNamespace(
                            choices=[types.SimpleNamespace(message=types.SimpleNamespace(content=content))]
                        )
                        provider = types.SimpleNamespace(
                            ChatCompletion=types.SimpleNamespace(create=Mock(return_value=response))
                        )
                        with patch.object(stub, "openai", provider), patch.dict(os.environ, {"OPENAI_API_KEY": "test"}):
                            with self.assertRaisesRegex(ValueError, "provider generation failed; no sample fallback"):
                                stub.discover_alpha(generate=True, ledger=ledger)
                        provider.ChatCompletion.create.assert_called_once()
                        if existing:
                            self.assertEqual(ledger.read_bytes(), b"[ ]\n")
                        else:
                            self.assertFalse(ledger.exists())

    def test_nonfinite_serialization_preserves_existing_ledger(self) -> None:
        from alpha_factory_v1.demos.cross_industry_alpha_factory import cross_alpha_discovery_stub as stub

        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp) / "log.json"
            ledger.write_bytes(b"[ ]\n")
            # Defense in depth if a future caller constructs an invalid in-memory pick.
            samples = [{"sector": "A", "opportunity": "B", "extra": float("inf")}]
            with patch.object(stub, "SAMPLE_ALPHA", samples):
                with self.assertRaises(ValueError):
                    stub.discover_alpha(sample=True, seed=0, ledger=ledger)
            self.assertEqual(ledger.read_bytes(), b"[ ]\n")
            self.assertLessEqual({p.name for p in Path(tmp).iterdir()}, {"log.json", "log.json.lock"})

    def test_invalid_ledger_is_preserved(self) -> None:
        from alpha_factory_v1.demos.cross_industry_alpha_factory import cross_alpha_discovery_stub as stub

        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp) / "log.json"
            for content in (
                b"{truncated",
                b"null",
                b"42",
                b"[1]",
                b"{}",
                b'[ {"sector": "Test"} ]',
                b'{"sector": "A", "opportunity": "B", "extra": NaN}',
                b'{"sector": "A", "opportunity": "B", "extra": Infinity}',
                b'{"sector": "A", "opportunity": "B", "extra": 1e999}',
                b'{"sector": "A", "opportunity": "B", "extra": -1e999}',
                b'{"sector": "A", "opportunity": "B", "extra": -Infinity}',
                b'[{"sector": 3, "opportunity": "B"}]',
                b'[{"sector": "A", "opportunity": " "}]',
                b'{"sector": "A", "sector": "B", "opportunity": "C"}',
                b"\xff",
            ):
                with self.subTest(content=content):
                    ledger.write_bytes(content)
                    with self.assertRaisesRegex(ValueError, "refusing to overwrite"):
                        stub.discover_alpha(sample=True, ledger=ledger)
                    self.assertEqual(ledger.read_bytes(), content)

    def test_unavailable_lock_fails_closed(self) -> None:
        from alpha_factory_v1.demos.cross_industry_alpha_factory import cross_alpha_discovery_stub as stub

        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp) / "log.json"
            ledger.write_text("[]")
            with (
                patch.object(stub, "FileLock", None),
                patch.object(stub, "fcntl", None),
                patch.object(stub, "msvcrt", None),
            ):
                with self.assertRaisesRegex(ValueError, "supported OS file lock"):
                    stub.discover_alpha(sample=True, ledger=ledger)
            self.assertEqual(ledger.read_text(), "[]")

    def test_failed_replace_preserves_ledger_and_cleans_temporary_file(self) -> None:
        from alpha_factory_v1.demos.cross_industry_alpha_factory import cross_alpha_discovery_stub as stub

        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp) / "log.json"
            ledger.write_text("[]")
            with patch.object(stub.os, "replace", side_effect=OSError("write failed")):
                with self.assertRaisesRegex(OSError, "write failed"):
                    stub.discover_alpha(sample=True, ledger=ledger)
            self.assertEqual(ledger.read_text(), "[]")
            self.assertLessEqual({p.name for p in Path(tmp).iterdir()}, {"log.json", "log.json.lock"})

    def test_fallback_lock_serializes_processes(self) -> None:
        self._check_process_writers(use_filelock=False)

    def test_mixed_filelock_and_fallback_serialize_processes(self) -> None:
        try:
            import filelock  # noqa: F401 - exercise mixed optional-dependency writers
        except ImportError:
            self.skipTest("filelock not installed")
        with self.subTest(owner="filelock", writers="native"):
            self._check_process_writers(use_filelock=True)
        with self.subTest(owner="native", writers="filelock"):
            self._check_process_writers(use_filelock=False, child_filelock=True)

    def _check_process_writers(self, *, use_filelock: bool, child_filelock: bool = False) -> None:
        from alpha_factory_v1.demos.cross_industry_alpha_factory import cross_alpha_discovery_stub as stub

        # Explicitly force the dependency-light path even in the full dev environment.
        script = """
import sys
from pathlib import Path
from alpha_factory_v1.demos.cross_industry_alpha_factory import cross_alpha_discovery_stub as stub
ledger, marker, seed, use_filelock = sys.argv[1:]
if use_filelock == "0":
    stub.FileLock = None
Path(marker).touch()
stub.discover_alpha(sample=True, seed=int(seed), ledger=Path(ledger))
"""
        with (
            tempfile.TemporaryDirectory() as tmp,
            patch.object(stub, "FileLock", stub.FileLock if use_filelock else None),
        ):
            ledger = Path(tmp) / "process_log.json"
            markers = [Path(tmp) / f"ready-{i}" for i in range(5)]
            processes = []
            try:
                # Hold the exact stable sidecar before launching writers. None may
                # complete or create the ledger until the parent releases the lock.
                with stub._ledger_lock(ledger):
                    for seed, marker in enumerate(markers):
                        processes.append(
                            subprocess.Popen(
                                [
                                    sys.executable,
                                    "-c",
                                    script,
                                    str(ledger),
                                    str(marker),
                                    str(seed),
                                    str(int(child_filelock)),
                                ],
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                text=True,
                            )
                        )
                    deadline = time.monotonic() + 10
                    while not all(marker.exists() for marker in markers) and time.monotonic() < deadline:
                        time.sleep(0.01)
                    self.assertTrue(
                        all(marker.exists() for marker in markers), "writers did not reach ledger operation"
                    )
                    for process in processes:
                        with self.assertRaises(subprocess.TimeoutExpired):
                            process.wait(timeout=0.1)
                    self.assertFalse(ledger.exists(), "writer bypassed held cross-process lock")
                for process in processes:
                    stdout, stderr = process.communicate(timeout=10)
                    self.assertEqual(process.returncode, 0, stdout + stderr)
                data = json.loads(ledger.read_text())
                self.assertEqual(len(data), 5)
                self.assertEqual({item["sector"] for item in data}, {item["sector"] for item in stub.SAMPLE_ALPHA[:5]})
            finally:
                for process in processes:
                    if process.poll() is None:
                        process.kill()
                    process.communicate()

    def test_fallback_lock_released_after_process_death(self) -> None:
        from alpha_factory_v1.demos.cross_industry_alpha_factory import cross_alpha_discovery_stub as stub

        script = """
import sys
import time
from pathlib import Path
from alpha_factory_v1.demos.cross_industry_alpha_factory import cross_alpha_discovery_stub as stub
stub.FileLock = None
with stub._ledger_lock(Path(sys.argv[1])):
    Path(sys.argv[2]).touch()
    time.sleep(60)
"""
        with tempfile.TemporaryDirectory() as tmp, patch.object(stub, "FileLock", None):
            ledger = Path(tmp) / "log.json"
            marker = Path(tmp) / "locked"
            ledger.write_text("[]")
            process = subprocess.Popen(
                [sys.executable, "-c", script, str(ledger), str(marker)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            try:
                deadline = time.monotonic() + 10
                while not marker.exists() and time.monotonic() < deadline:
                    time.sleep(0.01)
                self.assertTrue(marker.exists(), "child never acquired lock")
                process.kill()
                process.communicate(timeout=10)
                # A separate writer with a timeout proves OS cleanup, without
                # risking a stuck test if a killed process leaves a stale lock.
                result = subprocess.run(
                    [
                        sys.executable,
                        "-c",
                        "from pathlib import Path; "
                        "from alpha_factory_v1.demos.cross_industry_alpha_factory import cross_alpha_discovery_stub as s; "
                        "import sys; s.FileLock = None; s.discover_alpha(sample=True, seed=1, ledger=Path(sys.argv[1]))",
                        str(ledger),
                    ],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(json.loads(ledger.read_text()), [stub.SAMPLE_ALPHA[1]])
            finally:
                if process.poll() is None:
                    process.kill()
                process.communicate()

    def test_concurrent_writes_with_filelock(self) -> None:
        try:
            import filelock
        except Exception:  # pragma: no cover - optional dependency
            self.skipTest("filelock not installed")

        from alpha_factory_v1.demos.cross_industry_alpha_factory import (
            cross_alpha_discovery_stub as stub,
        )

        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp) / "thread_lock_log.json"

            def worker(seed: int) -> None:
                stub.discover_alpha(num=1, seed=seed, ledger=ledger, model="gpt-4o-mini", sample=True)

            threads = [threading.Thread(target=worker, args=(i,)) for i in range(5)]
            with patch.object(stub, "FileLock", filelock.FileLock):
                for t in threads:
                    t.start()
                for t in threads:
                    t.join()

            data = json.loads(ledger.read_text())
            self.assertIsInstance(data, list)
            self.assertEqual(len(data), 5)
            self.assertEqual(len(data), len({json.dumps(i, sort_keys=True) for i in data}))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
