# SPDX-License-Identifier: Apache-2.0
"""Run commands inside a restricted sandbox."""

from __future__ import annotations

import shutil
import subprocess
import os
from pathlib import Path
import tempfile
import threading
from typing import BinaryIO
from typing import Sequence

__all__ = ["SandboxTimeout", "SandboxUnavailable", "secure_run"]


class SandboxTimeout(Exception):
    """Raised when the sandboxed command exceeds the time limit."""


class SandboxUnavailable(RuntimeError):
    """No supported isolation backend is installed; host execution is forbidden."""


def _bounded_run(cmd: Sequence[str], timeout: int) -> subprocess.CompletedProcess[str]:
    """Drain both pipes concurrently, keeping at most 1 MiB in memory."""
    limit = 1024**2
    outputs = [bytearray(), bytearray()]
    lock = threading.Lock()
    overflow = threading.Event()
    with subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE) as process:

        def drain(stream: BinaryIO, index: int) -> None:
            while chunk := stream.read(8192):
                with lock:
                    remaining = limit - sum(map(len, outputs))
                    outputs[index].extend(chunk[:remaining])
                    if len(chunk) > remaining:
                        overflow.set()
                        process.kill()
                        return

        assert process.stdout is not None and process.stderr is not None
        readers = [
            threading.Thread(target=drain, args=(stream, i), daemon=True)
            for i, stream in enumerate((process.stdout, process.stderr))
        ]
        for reader in readers:
            reader.start()
        try:
            process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
            raise
        finally:
            for reader in readers:
                reader.join(timeout=1)
        if overflow.is_set():
            raise ValueError("sandbox output exceeds 1 MiB")
        return subprocess.CompletedProcess(
            cmd, process.returncode, *(bytes(x).decode(errors="replace") for x in outputs)
        )


def secure_run(cmd: Sequence[str]) -> subprocess.CompletedProcess[str]:
    """Execute ``cmd`` under ``firejail`` or ``docker`` constraints.

    The sandbox runs with seccomp, ``2`` CPU cores, ``2`` GB of RAM and a
    ``120`` second timeout. When the command exceeds the timeout a
    :class:`SandboxTimeout` is raised.
    """

    if not cmd:
        raise ValueError("sandbox command is empty")
    timeout = 120
    docker, firejail = shutil.which("docker"), shutil.which("firejail")
    if not docker and not firejail:
        raise SandboxUnavailable("install Docker or Firejail; generated code is never executed on the host")
    with tempfile.TemporaryDirectory(prefix="alpha-sandbox-") as temporary:
        stage = Path(temporary)
        stage.chmod(0o755)
        command = ["python3" if Path(cmd[0]).name.startswith("python") else cmd[0]]
        for i, argument in enumerate(cmd[1:]):
            path = Path(argument)
            # Only explicit regular input files enter the sandbox. Never share
            # all of /tmp, a repository, or an operator credential directory.
            if len(argument) < 4096 and path.is_absolute() and path.is_file():
                if path.is_symlink() or path.stat().st_size > 1024**2:
                    raise ValueError("sandbox inputs must be regular files of at most 1 MiB")
                copied = stage / f"input-{i}"
                shutil.copyfile(path, copied)
                copied.chmod(0o444)
                command.append(f"/work/input-{i}" if docker else str(copied))
            else:
                command.append(argument)
        name = stage.name
        if docker:
            full_cmd = [
                docker,
                "run",
                "--rm",
                "--name",
                name,
                "--network=none",
                "--cpus=2",
                "--memory=2g",
                "--pids-limit=64",
                "--read-only",
                "--cap-drop=ALL",
                "--user=65534:65534",
                "--tmpfs=/tmp:rw,noexec,nosuid,size=16m",
                "--security-opt=no-new-privileges",
                "--mount",
                f"type=bind,src={stage},dst=/work,readonly",
                "--workdir=/work",
                os.getenv("ALPHA_SANDBOX_IMAGE", "python:3.12-slim"),
                *command,
            ]
        else:
            assert firejail is not None
            full_cmd = [
                firejail,
                "--quiet",
                "--net=none",
                "--private",
                "--seccomp",
                "--caps.drop=all",
                "--nonewprivs",
                f"--whitelist={stage}",
                f"--read-only={stage}",
                "--rlimit-as=2147483648",
                "--rlimit-cpu=120",
                "--rlimit-fsize=1048576",
                *command,
            ]
        try:
            return _bounded_run(full_cmd, timeout)
        except subprocess.TimeoutExpired as exc:
            raise SandboxTimeout("sandbox exceeded its 120 second timeout") from exc
        finally:
            if docker:
                try:
                    subprocess.run([docker, "rm", "-f", name], capture_output=True, timeout=10, check=False)
                except subprocess.SubprocessError:
                    pass
