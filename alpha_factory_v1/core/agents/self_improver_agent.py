# SPDX-License-Identifier: Apache-2.0
"""Agent applying validated patches to the local repository."""

from __future__ import annotations

import asyncio
import fnmatch
import shutil
import subprocess
import tempfile
import textwrap
from pathlib import Path
from typing import Sequence

from alpha_factory_v1.core.agents.base_agent import BaseAgent
from alpha_factory_v1.core.self_evolution import self_improver
from alpha_factory_v1.core.utils.patch_guard import is_patch_valid

try:  # optional dependency
    import git  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - optional
    git = None

__all__ = ["SelfImproverAgent"]


def _files_from_diff(diff: str) -> list[str]:
    files: set[str] = set()
    for line in diff.splitlines():
        if line.startswith("+++") or line.startswith("---"):
            parts = line.split(maxsplit=1)
            if len(parts) != 2:
                continue
            path = parts[1]
            if path.startswith("a/") or path.startswith("b/"):
                path = path[2:]
            files.add(path)
    return list(files)


class SelfImproverAgent(BaseAgent):
    """Run :func:`self_improver.improve_repo` and merge successful patches."""

    def __init__(
        self,
        bus: object,
        ledger: object,
        repo: str | Path,
        patch_file: str | Path,
        *,
        metric_file: str = "metric.txt",
        log_file: str = "improver_log.json",
        allowed: Sequence[str] | None = None,
        backend: str = "gpt-4o",
        island: str = "default",
    ) -> None:
        super().__init__("self_improver", bus, ledger, backend=backend, island=island)
        self.repo = Path(repo)
        self.patch_file = Path(patch_file)
        self.metric_file = metric_file
        self.log_file = log_file
        self.allowed = list(allowed or ["**"])

    async def handle(self, _env: object) -> None:  # pragma: no cover - no messaging
        """Ignore messages since this agent only operates locally."""
        return None

    def _check_allowed(self, diff: str) -> None:
        files = _files_from_diff(diff)
        for f in files:
            if not any(fnmatch.fnmatch(f, pat) for pat in self.allowed):
                raise ValueError(f"file '{f}' not allowed")

    async def run_cycle(self) -> None:
        """Apply the proposed patch if valid and update the metric file."""
        if git is None:
            raise RuntimeError("GitPython is required")
        diff = self.patch_file.read_text()
        if not is_patch_valid(diff):
            raise ValueError("Invalid or unsafe patch")
        self._check_allowed(diff)
        delta, clone = await asyncio.to_thread(
            self_improver.improve_repo,
            str(self.repo),
            str(self.patch_file),
            self.metric_file,
            self.log_file,
            False,
        )
        try:
            if delta <= 0:
                return
            repo = git.Repo(self.repo)
            head = repo.head.commit.hexsha
            try:
                normalized = textwrap.dedent(diff).lstrip("\n")
                normalized_lines = []
                for line in normalized.splitlines():
                    if line.startswith("@@") and "-" not in line and "+" not in line:
                        normalized_lines.append("@@ -1 +1 @@")
                    else:
                        normalized_lines.append(line)
                normalized = "\n".join(normalized_lines)
                if normalized and not normalized.endswith("\n"):
                    normalized += "\n"
                with tempfile.NamedTemporaryFile("w+", delete=False) as tf:
                    tf.write(normalized)
                    patch_path = tf.name
                patch_result = subprocess.run(
                    ["patch", "-p1", "-i", patch_path],
                    cwd=self.repo,
                    capture_output=True,
                    text=True,
                )
                if patch_result.returncode != 0:
                    raise RuntimeError(f"patch command failed:\n{patch_result.stdout}{patch_result.stderr}")
                repo.index.add([self.metric_file])
                repo.index.commit("self-improvement patch")
            except Exception:  # noqa: BLE001
                repo.git.reset("--hard", head)
                raise
            finally:
                if "patch_path" in locals():
                    Path(patch_path).unlink(missing_ok=True)
        finally:
            shutil.rmtree(clone, ignore_errors=True)
