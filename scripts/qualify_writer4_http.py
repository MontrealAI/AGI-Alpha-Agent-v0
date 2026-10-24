# SPDX-License-Identifier: Apache-2.0
"""CI orchestration for the unchanged Writer4 full HTTP QA, not a new browser test."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
from urllib.request import urlopen


def identity(path: Path) -> dict[str, object]:
    raw = path.read_bytes()
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def main() -> int:
    repository = Path.cwd().resolve()
    expected = os.environ["TAE_EXPECTED_HEAD_SHA"]
    base = os.environ["TAE_EXPECTED_BASE_SHA"]
    if not all(re.fullmatch(r"[0-9a-f]{40}", value) for value in (expected, base)):
        raise RuntimeError("Exact GitHub head/base identities required")
    task = Path(os.environ["RUNNER_TEMP"]) / (
        "writer4-http-" + os.environ["GITHUB_RUN_ID"] + "-" + os.environ["GITHUB_RUN_ATTEMPT"]
    )
    if task.exists() or task.is_symlink():
        raise RuntimeError("Fresh task directory required; do not replace earlier evidence")
    private, public = task / "private", task / "public"
    private.mkdir(parents=True)
    public.mkdir()
    phases: dict[str, int] = {}
    source = repository / "studies/transformational-autonomous-enterprises-v1"
    bundle = task / "companion"
    original = bundle / "Successor_Omega_Harness"
    derived = bundle / "Successor_Omega_Harness_Engineering_Fixed"
    qa = private / "qa"
    token = ""
    server = None
    server_log = None
    failure = None
    served = {}
    toolchain: dict[str, object] = {"python": sys.version.split()[0]}
    # No inherited service credentials, NODE_OPTIONS/NODE_PATH or RPC endpoints.
    environment = {key: os.environ[key] for key in ("PATH", "HOME", "LANG", "TMPDIR") if key in os.environ}
    environment["LANG"] = "C.UTF-8"

    def run(label: str, arguments: list[str], cwd: Path, *, required: bool = True) -> int:
        with (private / (label + ".stdout")).open("wb") as out, (private / (label + ".stderr")).open("wb") as err:
            result = subprocess.run(arguments, cwd=cwd, env=environment, stdout=out, stderr=err, check=False)
        phases[label] = result.returncode
        print(label + " exit=" + str(result.returncode), flush=True)
        if required and result.returncode:
            raise RuntimeError(label + " failed; original output hashes are retained")
        return result.returncode

    def clean(value: object) -> object:
        if isinstance(value, str):
            return value.replace(token, "[local-action-token-redacted]") if isinstance(token, str) and token else value
        if isinstance(value, list):
            return [clean(item) for item in value]
        if isinstance(value, dict):
            return {key: clean(item) for key, item in value.items()}
        return value

    try:
        observed = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repository, text=True).strip()
        if observed != expected:
            raise RuntimeError("CI checkout differs from the exact reviewed head")
        subprocess.run(["git", "merge-base", "--is-ancestor", base, expected], cwd=repository, check=True)
        # Presence is a mechanical guard only, never an approval/denial decision.
        # The existing owner must first qualify and reconcile actual guarded main.
        subprocess.run(
            ["git", "cat-file", "-e", base + ":scripts/check_held_native_source.py"], cwd=repository, check=True
        )
        run("held-source-identities", [sys.executable, "scripts/check_held_native_source.py"], repository)
        node = shutil.which("node", path=environment["PATH"])
        if node is None:
            raise RuntimeError("Node was not found in the selected CI toolchain")
        toolchain["node"] = subprocess.check_output([node, "--version"], env=environment, text=True).strip()
        toolchain["npm"] = subprocess.check_output(["npm", "--version"], env=environment, text=True).strip()
        if toolchain["node"] != "v24.19.0":
            raise RuntimeError("The documented Node24.19.0 QA context is required")
        shutil.copytree(source, bundle)
        # Reuse checkout-contained, checksum-bound parts and eight corrections.
        # No --download fallback or branch-selected replacement archive is used.
        run("assemble", [sys.executable, "ASSEMBLE.py"], bundle)
        run("extract", [sys.executable, "-m", "zipfile", "-e", "Successor_Omega_Harness_Companion.zip", "."], bundle)
        run("original-before", [sys.executable, str(original / "VERIFY.py")], bundle)
        run("derive", [sys.executable, "APPLY_QUEUE_INPUT_FIX.py", str(original), str(derived)], bundle)
        run("derived-before", [sys.executable, "APPLY_QUEUE_INPUT_FIX.py", "--verify", str(derived)], bundle)
        run("setup", [node, "study/setup.mjs"], derived)
        run("setup-check", [node, "study/setup.mjs", "--check"], derived)
        run(
            "browser-tools",
            ["npm", "ci", "--prefix", "study/browser-tools", "--ignore-scripts", "--no-audit", "--no-fund"],
            derived,
        )
        for package in ("playwright", "@sparticuz/chromium"):
            package_file = derived / "study/browser-tools/node_modules" / package / "package.json"
            toolchain[package] = {
                "version": json.loads(package_file.read_text())["version"], **identity(package_file)
            }
        server_log = (private / "server.log").open("wb")
        server = subprocess.Popen(
            [node, "study/server.mjs"], cwd=derived, env=environment, stdout=server_log, stderr=server_log
        )
        # The existing server stays on127.0.0.1:8765, with unchanged Host/Origin rules.
        #30s follows the browser's normal readiness convention; no native run starts here.
        deadline = time.monotonic() + 30
        while True:
            try:
                if server.poll() is not None:
                    raise RuntimeError("Owned HTTP server exited before readiness")
                with urlopen("http://127.0.0.1:8765/api/status", timeout=2) as response:
                    if response.geturl() != "http://127.0.0.1:8765/api/status":
                        raise RuntimeError("Unexpected HTTP status redirect")
                    status = json.load(response)
                if server.poll() is not None:
                    raise RuntimeError("Owned HTTP server exited during readiness")
                if status.get("local") is not True or status.get("busy") is not False:
                    raise RuntimeError("Expected idle fixed local server")
                token = status["token"]
                if not isinstance(token, str) or not token:
                    raise RuntimeError("Missing local action token")
                break
            except OSError:
                if server.poll() is not None or time.monotonic() >= deadline:
                    raise RuntimeError("Existing HTTP server did not become reachable")
                time.sleep(0.25)
        for name in ("index.html", "app.js", "style.css", "evidence.js"):
            url = "http://127.0.0.1:8765/study/interface/" + name
            with urlopen(url, timeout=30) as response:
                if response.geturl() != url or response.read() != (derived / "study/interface" / name).read_bytes():
                    raise RuntimeError("HTTP resource differs from the verified derived source")
            served[name] = identity(derived / "study/interface" / name)
        if qa.exists():
            raise RuntimeError("QA output directory must be new")
        environment["TAE_QA_OUTPUT"] = str(qa)
        # This unmodified documented command performs Start/Stop and a fresh full
        # two-mission run through HTTP; it is deliberately not called UI-only.
        run("http-qa", [node, "study/interface/qa.cjs"], derived)
    except Exception as error:
        failure = str(error)
    finally:
        if server is not None:
            server.terminate()  # Its unchanged handler stops its own active local process group.
            try:
                server.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait()
        if server_log is not None:
            server_log.close()
        if original.is_dir():
            run("original-after", [sys.executable, str(original / "VERIFY.py")], bundle, required=False)
        if derived.is_dir():
            run(
                "derived-after", [sys.executable, "APPLY_QUEUE_INPUT_FIX.py", "--verify", str(derived)],
                bundle, required=False,
            )

        report = None
        qa_files = {}
        for name in ("browser-qa.json", "browser-qa-failed.json"):
            path = qa / name
            if path.is_file():
                qa_files[name] = identity(path)
                try:
                    raw = json.loads(path.read_text())
                    report = {key: raw[key] for key in (
                        "target", "browser", "executableSource", "checks", "errors", "startedAt", "finishedAt",
                        "passed", "failure", "lineageText"
                    ) if key in raw}
                    (public / name).write_text(json.dumps(clean(report), indent=2) + "\n")
                except (OSError, ValueError, TypeError) as error:
                    failure = failure or "Malformed QA report: " + str(error)
        for name in ("desktop-en.png", "desktop-fr.png", "mobile-fr.png", "mobile-en.png", "mobile-320.png"):
            path = qa / name
            if path.is_file():
                shutil.copy2(path, public / name)
        export = qa / "browser-export.json"
        reference = qa / "fresh-run-reference.json"
        if reference.is_file():
            qa_files[reference.name] = identity(reference)
        export_record = None
        if export.is_file():
            try:
                raw = json.loads(export.read_text())
                export_record = {**identity(export), "schema": raw.get("schema"),
                                 "currentProof": raw.get("currentProof"), "authority": raw.get("authority")}
            except (OSError, ValueError, AttributeError) as error:
                failure = failure or "Malformed browser export: " + str(error)
        closure = {}
        for relative in (
            "MANIFEST.sha256", "QUEUE_INPUT_OVERLAY.json", "study/interface/qa.cjs", "study/interface/app.js",
            "study/interface/index.html", "study/interface/style.css", "study/interface/evidence.js",
            "study/server.mjs", "study/setup.mjs", "study/run-demo.mjs", "study/browser-tools/package.json",
            "study/browser-tools/package-lock.json", "study/results/source-scope.json",
            "study/evaluation/SCORING_FREEZE_V2.json", "study/evaluation/checker.mjs", "study/evaluation/criteria.json",
        ):
            path = derived / relative
            if path.is_file():
                closure[relative] = identity(path)
        setup_records = []
        for path in sorted((derived / "study/setup-attempts").glob("setup-*.json")):
            raw = json.loads(path.read_text())
            setup_records.append({
                key: raw[key] for key in ("node", "testedNode", "ready", "pins", "elapsedMs") if key in raw
            })
            setup_records[-1]["dependencyLocks"] = [
                {key: event[key] for key in ("dependencyLock", "sha256")}
                for event in raw.get("events", []) if "dependencyLock" in event and "sha256" in event
            ]
        if failure is None and (report is None or report.get("passed") is not True or not all(
            phases.get(key) == 0 for key in ("http-qa", "original-after", "derived-after")
        )):
            failure = "QA report or final source verification did not pass"
        logs = {path.name: identity(path) for path in private.iterdir() if path.is_file()}
        passed = failure is None and report is not None and report.get("passed") is True and all(
            phases.get(key) == 0 for key in ("http-qa", "original-after", "derived-after")
        )
        receipt = {
            "schema": "tae.http-ui-ci-acceptance.v1", "passed": passed,
            "head": expected, "base": base, "runId": os.environ["GITHUB_RUN_ID"],
            "attempt": os.environ["GITHUB_RUN_ATTEMPT"], "phases": phases, "failure": clean(failure),
            "report": clean(report), "browserExport": clean(export_record), "privateLogIdentities": logs,
            "privateQaFileIdentities": qa_files,
            "derivedSourceClosure": closure, "setupRecords": clean(setup_records),
            "toolchain": toolchain,
            "httpServedSourceBytes": served,
            "originalArchiveSha256": "a622657df828aefb4a081d1e0f5d1fb665fcf69991383245b6ece7cb66bee7ee",
            "scope": "Existing full HTTP QA on corrected v5 research copy; source APIs/disposable local EVM. "
                     "No installed four-release, held native-host, economic-value or production settlement claim.",
            "omittedOriginalFourQualified": False, "priorDeniedObjectivesAttempted": False,
            "rawLogs": "Private runner scratch; exact hashes retained. Local action token is never published.",
        }
        (public / "acceptance.json").write_text(json.dumps(receipt, indent=2) + "\n")
        if failure:
            print(str(clean(failure)), file=sys.stderr)
            for label, code in phases.items():
                if code:
                    lines = (private / (label + ".stderr")).read_text(errors="replace").splitlines()[-40:]
                    print(str(clean("\n".join(lines))), file=sys.stderr)
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
