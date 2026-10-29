# SPDX-License-Identifier: Apache-2.0
"""Bounded failure evidence without Docker, changed acceptance or operator secrets."""

from __future__ import annotations

import io
import json
from pathlib import Path
import subprocess
import sys
import time
from typing import Any
import urllib.error

import pytest
import yaml

from scripts import validate_legacy_compose as validator

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def calls(monkeypatch: pytest.MonkeyPatch) -> list[tuple[list[str], dict[str, Any]]]:
    seen: list[tuple[list[str], dict[str, Any]]] = []
    monkeypatch.setenv("API_TOKEN", "operator-secret-must-not-escape")
    monkeypatch.setenv("DOCKER_HOST", "tcp://unapproved-operator-daemon:2375")
    monkeypatch.setenv("COMPOSE_FILE", "unapproved-operator-stack.yml")

    def run(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        seen.append((command, kwargs))
        assert set(kwargs["env"]) <= {"PATH", "HOME", "SYSTEMROOT", "TMPDIR", "COMPOSE_DISABLE_ENV_FILE"}
        assert kwargs["env"]["COMPOSE_DISABLE_ENV_FILE"] == "1"
        if "up" in command:
            fixture = yaml.safe_load(Path(command[command.index("-f") + 1]).read_text())
            service = fixture["services"]["ui"]
            assert service["healthcheck"]["start_period"] == "180s"
            assert service["healthcheck"]["interval"] == "2s"
            assert service["healthcheck"]["retries"] == 3
            assert service["healthcheck"]["timeout"] == "5s"
            assert service["command"] == ["sh", "-c", "npm ci && exec npm run dev -- --host 0.0.0.0 --port 3000"]
            assert command[-5:] == ["up", "-d", "--wait", "--wait-timeout", "240"]
            assert kwargs["timeout"] == 360 and kwargs["check"] is True
        else:
            assert command[-3:] == ["down", "--volumes", "--remove-orphans"]
            assert kwargs["timeout"] == 60 and kwargs["check"] is True
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(validator.subprocess, "run", run)
    return seen


def diagnostics(monkeypatch: pytest.MonkeyPatch, seen: list[Any]) -> None:
    def capture(command: list[str], env: dict[str, str], timeout: float = 8) -> dict[str, object]:
        assert seen and "up" in seen[0][0]
        assert not any("down" in row[0] for row in seen)
        assert set(env) <= {"PATH", "HOME", "SYSTEMROOT", "TMPDIR", "COMPOSE_DISABLE_ENV_FILE"}
        assert timeout == 8
        if "logs" in command:
            assert command[-6:] == ["logs", "--no-color", "--timestamps", "--tail", "100", "ui"]
            return {"status": "ok", "returncode": 0, "truncated": False, "tail": "npm startup not ready"}
        assert command == [
            "docker",
            "inspect",
            "--type",
            "container",
            "--format",
            "{{json .State}}",
            "alpha-dev-ui-acceptance",
        ]
        return {
            "status": "ok",
            "returncode": 0,
            "truncated": False,
            "tail": json.dumps(
                {
                    "Status": "running",
                    "OOMKilled": False,
                    "ExitCode": 0,
                    "Config": {"Env": ["SECRET=forbidden"]},
                    "Health": {
                        "Status": "unhealthy",
                        "FailingStreak": 3,
                        "Test": ["forbidden-env-dump"],
                        "Log": [{"Start": "before", "End": "after", "ExitCode": 1, "Output": "connection refused"}],
                    },
                }
            ),
        }

    monkeypatch.setattr(validator, "_diagnostic_command", capture)


def test_startup_failure_saved_before_cleanup_without_config_or_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, calls: list[Any], capsys: Any
) -> None:
    diagnostics(monkeypatch, calls)
    original_run = validator.subprocess.run
    error = subprocess.CalledProcessError(1, ["bounded-compose-up"])

    def run(command: list[str], **kwargs: Any) -> Any:
        value = original_run(command, **kwargs)
        if "up" in command:
            raise error
        assert output.is_file()
        return value

    monkeypatch.setattr(validator.subprocess, "run", run)
    output = tmp_path / "evidence/legacy-compose-failure.json"
    with pytest.raises(subprocess.CalledProcessError) as failure:
        validator.validate_dev_ui(ROOT, output)
    assert failure.value is error
    report = json.loads(output.read_text())
    assert report["passed"] is False and report["startup_returncode"] == 1
    assert report["container_state"]["health_log"][0]["Output"] == "connection refused"
    assert report["disk_bytes"]["free"] >= 0
    assert len(calls) == 2 and "down" in calls[-1][0]
    serialized = output.read_text() + capsys.readouterr().err
    assert all(
        value not in serialized
        for value in ("forbidden", "Config", "SECRET=", "operator-secret-must-not-escape", "unapproved-operator")
    )


@pytest.mark.parametrize("failed_route", [0, 1])
def test_http_module_failure_keeps_both_acceptance_contracts_and_collects_before_cleanup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, calls: list[Any], failed_route: int
) -> None:
    diagnostics(monkeypatch, calls)
    requests: list[str] = []
    routes = ["/src/Telemetry.ts", "/@fs/ui/alpha_factory_v1/core/telemetry.js"]
    bodies = [b"initTelemetry", b"function initTelemetry"]

    def open_url(url: str, timeout: int) -> Any:
        index = len(requests)
        requests.append(url)
        assert timeout == 15 and url == "http://127.0.0.1:3000" + routes[index]
        response = io.BytesIO(b"missing required module" if index == failed_route else bodies[index])
        response.status = 200
        return response

    monkeypatch.setattr(validator.urllib.request, "urlopen", open_url)
    output = tmp_path / "legacy-compose-failure.json"
    with pytest.raises(ValueError, match="Development UI module did not load"):
        validator.validate_dev_ui(ROOT, output)
    assert len(requests) == failed_route + 1
    assert json.loads(output.read_text())["error_type"] == "ValueError"
    assert "down" in calls[-1][0]


@pytest.mark.parametrize(
    "diagnostic_error", [OSError("do not leak diagnostic details"), subprocess.TimeoutExpired("do not leak command", 8)]
)
@pytest.mark.parametrize("cleanup_failure", [False, True])
def test_broken_diagnostics_or_cleanup_never_mask_original_startup_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    calls: list[Any],
    diagnostic_error: Exception,
    cleanup_failure: bool,
) -> None:
    original_run = validator.subprocess.run
    error = subprocess.TimeoutExpired("original startup command", 360)

    def run(command: list[str], **kwargs: Any) -> Any:
        original_run(command, **kwargs)
        if "up" in command:
            raise error
        if cleanup_failure:
            raise subprocess.CalledProcessError(7, ["cleanup"])

    def capture(*args: Any, **kwargs: Any) -> Any:
        raise diagnostic_error

    monkeypatch.setattr(validator.subprocess, "run", run)
    monkeypatch.setattr(validator, "_diagnostic_command", capture)
    output = tmp_path / "legacy-compose-failure.json"
    with pytest.raises(subprocess.TimeoutExpired) as failure:
        validator.validate_dev_ui(ROOT, output)
    assert failure.value is error
    report = json.loads(output.read_text())
    assert report["ui_logs"]["status"] == report["container_state"]["status"] == "diagnostic-failed"
    assert "do not leak" not in output.read_text()
    assert "down" in calls[-1][0]


def test_unexpected_inspect_failure_never_dumps_raw_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, calls: list[Any]
) -> None:
    error = ValueError("module failed")
    monkeypatch.setattr(
        validator,
        "_diagnostic_command",
        lambda *args: {"status": "command-failed", "tail": '{"Config":{"Env":["SECRET=forbidden"]}}', "returncode": 1},
    )
    output = tmp_path / "legacy-compose-failure.json"
    validator._dev_ui_failure(ROOT, ["docker", "compose"], {}, error, output)
    report = json.loads(output.read_text())
    assert "tail" not in report["container_state"]


def test_output_write_failure_cannot_replace_original_or_skip_cleanup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, calls: list[Any]
) -> None:
    diagnostics(monkeypatch, calls)
    original_run = validator.subprocess.run
    original_write = Path.write_text
    error = subprocess.CalledProcessError(1, ["up"])

    def run(command: list[str], **kwargs: Any) -> Any:
        original_run(command, **kwargs)
        if "up" in command:
            raise error

    def write(path: Path, *args: Any, **kwargs: Any) -> int:
        if path.name == "legacy-compose-failure.json":
            raise OSError("disk full")
        return original_write(path, *args, **kwargs)

    monkeypatch.setattr(validator.subprocess, "run", run)
    monkeypatch.setattr(Path, "write_text", write)
    with pytest.raises(subprocess.CalledProcessError) as failure:
        validator.validate_dev_ui(ROOT, tmp_path / "legacy-compose-failure.json")
    assert failure.value is error and "down" in calls[-1][0]


def test_success_does_not_collect_failure_evidence_and_cleanup_failure_still_fails(
    monkeypatch: pytest.MonkeyPatch, calls: list[Any]
) -> None:
    def open_url(url: str, timeout: int) -> Any:
        response = io.BytesIO(b"function initTelemetry")
        response.status = 200
        return response

    monkeypatch.setattr(validator.urllib.request, "urlopen", open_url)
    monkeypatch.setattr(
        validator, "_dev_ui_failure", lambda *args: pytest.fail("success must not emit failure diagnostics")
    )
    validator.validate_dev_ui(ROOT)
    original_run = validator.subprocess.run
    error = subprocess.CalledProcessError(9, ["cleanup"])

    def run(command: list[str], **kwargs: Any) -> Any:
        original_run(command, **kwargs)
        if "down" in command:
            raise error

    monkeypatch.setattr(validator.subprocess, "run", run)
    with pytest.raises(subprocess.CalledProcessError) as failure:
        validator.validate_dev_ui(ROOT)
    assert failure.value is error


@pytest.mark.parametrize("timeout", [False, True])
def test_real_capture_bounds_tail_and_terminates_a_timed_out_diagnostic(
    monkeypatch: pytest.MonkeyPatch, timeout: bool
) -> None:
    monkeypatch.setenv("API_TOKEN", "operator-secret-must-not-escape")
    script = "import os,time; os.write(1,b'x'*200000+b'operator-secret-must-not-escape/FINAL');" + (
        "time.sleep(30)" if timeout else ""
    )
    started = time.monotonic()
    result = validator._diagnostic_command([sys.executable, "-c", script], {}, timeout=0.1 if timeout else 2)
    assert time.monotonic() - started < 3
    assert result["status"] == ("timed-out" if timeout else "ok")
    assert result["truncated"] and len(result["tail"]) <= 16_384
    assert result["tail"].endswith("[REDACTED]/FINAL")
    assert "operator-secret-must-not-escape" not in result["tail"]


def test_http_transport_error_remains_the_original_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, calls: list[Any]
) -> None:
    diagnostics(monkeypatch, calls)
    error = urllib.error.URLError("bounded local readiness failure")

    def open_url(*args: Any, **kwargs: Any) -> Any:
        raise error

    monkeypatch.setattr(validator.urllib.request, "urlopen", open_url)
    output = tmp_path / "legacy-compose-failure.json"
    with pytest.raises(urllib.error.URLError) as failure:
        validator.validate_dev_ui(ROOT, output)
    assert failure.value is error
    assert json.loads(output.read_text())["error_type"] == "URLError"
    assert "down" in calls[-1][0]


@pytest.mark.parametrize("dev_ui", [False, True])
def test_cli_keeps_success_report_and_uses_failure_sibling_only_for_ui(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: Any, dev_ui: bool
) -> None:
    names = [
        "alpha_factory_v1/docker-compose.yml",
        "alpha_factory_v1/docker-compose.override.yml",
        "alpha_factory_v1/demos/aiga_meta_evolution/docker-compose.aiga.yml",
        "alpha_factory_v1/demos/era_of_experience/docker-compose.experience.yml",
        "alpha_factory_v1/demos/macro_sentinel/docker-compose.macro.yml",
        "alpha_factory_v1/demos/self_healing_repo/docker-compose.selfheal.yml",
    ]
    monkeypatch.setattr(
        validator.subprocess, "check_output", lambda *args, **kwargs: ("\0".join(names) + "\0").encode()
    )
    output = tmp_path / "evidence/custom-success-report.json"
    seen: list[Any] = []
    monkeypatch.setattr(validator, "validate_dev_ui", lambda *args: seen.append(args))
    monkeypatch.setattr(sys, "argv", ["validator", "--output", str(output), *(["--dev-ui"] if dev_ui else [])])
    validator.main()
    assert seen == ([(ROOT, output.with_name("legacy-compose-failure.json"))] if dev_ui else [])
    report = json.loads(output.read_text())
    assert report == json.loads(capsys.readouterr().out)
    assert report["passed"] is True
    assert report["development_ui_modules_loaded"] is dev_ui
    assert report["compose_default_and_all_profiles_validated"] is False
    assert report["local_copy_inputs_resolve"] is True
    assert report["operator_secrets_loaded"] is report["research_services_started"] is False
    assert len(report["shared_dockerfile_consumers"]) == 6
    assert not output.with_name("legacy-compose-failure.json").exists()


def test_multibyte_and_credential_replacement_still_obey_byte_ceiling(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("API_TOKEN", "x")
    result = validator._diagnostic_command(
        [sys.executable, "-c", "import os;os.write(1,b'x'*4000+b'\\xff'*9000)"], {}, timeout=2
    )
    assert result["status"] == "ok"
    assert len(result["tail"].encode("utf-8")) <= 16_384
    assert result["truncated"]


@pytest.mark.parametrize("mode", ["tail-boundary", "chunk-boundary", "eof-prefix", "utf8"])
def test_credentials_are_masked_before_trimming_and_across_stream_boundaries(
    monkeypatch: pytest.MonkeyPatch, mode: str
) -> None:
    secret = "FICTIONAL_CREDENTIAL_0123456789"
    if mode == "utf8":
        secret = "FICTIONAL_é_🔐_CREDENTIAL"
    monkeypatch.setenv("API_TOKEN", secret)
    encoded = secret.encode()
    if mode == "tail-boundary":
        body = encoded + b"z" * (16_384 - len(encoded) + 4)
        script = "import os;os.write(1," + repr(body) + ")"
    elif mode == "chunk-boundary":
        script = (
            'import os,time;os.write(1,b"x"*4090+'
            + repr(encoded[:7])
            + ");time.sleep(.02);os.write(1,"
            + repr(encoded[7:] + b"/END")
            + ")"
        )
    elif mode == "eof-prefix":
        script = 'import os;os.write(1,b"before/"+' + repr(encoded[:17]) + ")"
    else:
        script = (
            "import os,time;os.write(1,"
            + repr(encoded[:12])
            + ");time.sleep(.02);os.write(1,"
            + repr(encoded[12:] + b"/END")
            + ")"
        )
    result = validator._diagnostic_command([sys.executable, "-c", script], {}, timeout=2)
    assert result["status"] == "ok"
    assert len(result["tail"].encode()) <= 16_384
    assert secret not in result["tail"] and secret[4:] not in result["tail"]
    if mode == "eof-prefix":
        assert secret[:17] not in result["tail"] and "[REDACTED]" in result["tail"]
    elif mode != "tail-boundary":
        assert "[REDACTED]" in result["tail"] and result["tail"].endswith("/END")


@pytest.mark.parametrize("secret", ['FICTIONAL-QUOTE-"-PASSWORD', "0", "FICTIONAL\\BACKSLASH\nCREDENTIAL"])
def test_decoded_json_credentials_are_masked_without_erasing_state(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, secret: str
) -> None:
    monkeypatch.setenv("API_TOKEN", secret)
    body = json.dumps(
        {
            "Error": secret,
            "ExitCode": 0,
            "OOMKilled": False,
            "Health": {"Status": "unhealthy", "FailingStreak": 0, "Log": [{"ExitCode": 0, "Output": secret}]},
            "Config": {"Env": ["forbidden"]},
        }
    ).encode()
    captured = validator._diagnostic_command(
        [sys.executable, "-c", "import os;os.write(1," + repr(body) + ")"], {}, timeout=2
    )
    decoded = json.loads(captured["tail"])
    assert decoded["Error"] == decoded["Health"]["Log"][0]["Output"] == "[REDACTED]"
    assert decoded["ExitCode"] == 0 and decoded["OOMKilled"] is False

    def capture(command: list[str], *args: Any) -> Any:
        return dict(captured) if "inspect" in command else {"status": "ok", "tail": "safe log", "returncode": 0}

    monkeypatch.setattr(validator, "_diagnostic_command", capture)
    output = tmp_path / "failure.json"
    validator._dev_ui_failure(ROOT, ["docker", "compose"], {}, ValueError("fixture acceptance failure"), output)
    report = json.loads(output.read_text())
    assert report["container_state"]["state"]["Error"] == "[REDACTED]"
    assert report["container_state"]["state"]["ExitCode"] == 0
    assert report["container_state"]["health_log"][0]["Output"] == "[REDACTED]"
    assert "Config" not in output.read_text() and "forbidden" not in output.read_text()


def test_overlapping_credentials_are_redacted_as_one_union(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("API_TOKEN", "abc")
    monkeypatch.setenv("API_SECRET", "bcdef")
    result = validator._diagnostic_command([sys.executable, "-c", "import os;os.write(1,b'abcdef/END')"], {}, timeout=2)
    assert result["tail"] == "[REDACTED]/END"


@pytest.mark.skipif(sys.platform != "linux", reason="Linux diagnostic process-group lifecycle regression")
@pytest.mark.parametrize("cleanup_failure", [None, "kill", "wait"])
def test_cancellation_kills_pipe_holding_descendant_after_leader_exit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, cleanup_failure: str | None
) -> None:
    import os
    import signal

    pid_path = tmp_path / "descendant.json"
    code = (
        "import os,time,json; p=os.fork();\nif p==0:\n open("
        + repr(str(pid_path))
        + ',"w").write(json.dumps({"pid":os.getpid(),"group":os.getpgrp()}));time.sleep(20)\nelse: os._exit(0)'
    )
    original_selector = validator.selectors.DefaultSelector
    original_wait = validator.subprocess.Popen.wait
    original_kill = validator.os.killpg
    cancellation = KeyboardInterrupt("fixture original cancellation")

    class CancelSelector(original_selector):
        def select(self, timeout: float | None = None) -> Any:
            value = super().select(timeout)
            if pid_path.exists():
                raise cancellation
            return value

    def fail_wait(process: Any, *args: Any, **kwargs: Any) -> Any:
        value = original_wait(process, *args, **kwargs)
        if cleanup_failure == "wait":
            raise OSError("fixture wait failure after reaping")
        return value

    def fail_kill(group: int, requested_signal: int) -> None:
        original_kill(group, requested_signal)
        if cleanup_failure == "kill":
            raise OSError("fixture kill failure after delivery")

    monkeypatch.setattr(validator.selectors, "DefaultSelector", CancelSelector)
    monkeypatch.setattr(validator.subprocess.Popen, "wait", fail_wait)
    monkeypatch.setattr(validator.os, "killpg", fail_kill)
    try:
        with pytest.raises(KeyboardInterrupt) as failure:
            validator._diagnostic_command([sys.executable, "-c", code], {}, timeout=2)
        assert failure.value is cancellation
        child = json.loads(pid_path.read_text())
        state = Path("/proc") / str(child["pid"]) / "stat"
        deadline = time.monotonic() + 1
        while state.exists() and state.read_text().split()[2] != "Z" and time.monotonic() < deadline:
            time.sleep(0.01)
        assert not state.exists() or state.read_text().split()[2] == "Z"
    finally:
        if pid_path.exists():
            try:
                original_kill(json.loads(pid_path.read_text())["group"], signal.SIGKILL)
            except ProcessLookupError:
                pass


def test_structured_overlapping_credentials_do_not_leave_a_prefix(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("API_TOKEN", "abc")
    monkeypatch.setenv("API_SECRET", "bcdef")
    result = validator._diagnostic_command(
        [sys.executable, "-c", 'import os;os.write(1,b\'{"Error":"abcdef","ExitCode":0}\')'], {}, timeout=2
    )
    assert json.loads(result["tail"]) == {"Error": "[REDACTED]", "ExitCode": 0}


def test_oversized_redaction_context_withholds_text_instead_of_retaining_fragments(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret = "FICTIONAL_" + "x" * 20_000
    monkeypatch.setenv("API_TOKEN", secret)
    body = json.dumps({"Error": secret}).encode()
    result = validator._diagnostic_command(
        [sys.executable, "-c", "import os;os.write(1," + repr(body) + ")"], {}, timeout=2
    )
    assert result["status"] == "output-withheld"
    assert result["tail"] == "" and result["returncode"] == 0


def test_overlap_credential_split_after_an_earlier_complete_match(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("API_TOKEN", "abc")
    monkeypatch.setenv("API_SECRET", "bcdef")
    code = "import os,time;os.write(1,b'zzabcde');time.sleep(.02);os.write(1,b'f/END')"
    result = validator._diagnostic_command([sys.executable, "-c", code], {}, timeout=2)
    assert result["tail"] == "zz[REDACTED]/END"


def test_masked_prefix_never_reappears_when_redaction_shortens_the_capture(monkeypatch: pytest.MonkeyPatch) -> None:
    secret = "FICTIONAL-CREDENTIAL-0123456789"
    monkeypatch.setenv("API_TOKEN", secret)
    body = secret.encode() + (secret.encode() + b"/") * 1400
    result = validator._diagnostic_command(
        [sys.executable, "-c", "import os;os.write(1," + repr(body) + ")"], {}, timeout=2
    )
    assert result["truncated"] and secret[4:] not in result["tail"]
    assert "0123456789" not in result["tail"]
    assert len(result["tail"].encode()) <= 16_384


def test_decoded_json_credentials_in_keys_are_redacted(monkeypatch: pytest.MonkeyPatch) -> None:
    secret = 'FICTIONAL-JSON-KEY-"-CREDENTIAL'
    monkeypatch.setenv("API_TOKEN", secret)
    body = json.dumps({secret: "public value", "Error": secret, "ExitCode": 0}).encode()
    result = validator._diagnostic_command(
        [sys.executable, "-c", "import os;os.write(1," + repr(body) + ")"], {}, timeout=2
    )
    decoded = json.loads(result["tail"])
    assert secret not in decoded
    assert decoded == {"[REDACTED]": "public value", "Error": "[REDACTED]", "ExitCode": 0}


@pytest.mark.parametrize(
    ("secret", "invalid_utf8"),
    [
        ("FICTIONAL-a\ufffdb-END", b"FICTIONAL-a\xffb-END"),
        ("\ufffd", b"\xff"),
        ("FICTIONAL-\ufffd\ufffd\ufffd-CREDENTIAL", b"FICTIONAL-\xed\xa0\x80-CREDENTIAL"),
    ],
)
@pytest.mark.parametrize("chunked", [False, True])
def test_invalid_utf8_decoding_cannot_reintroduce_known_credentials(
    monkeypatch: pytest.MonkeyPatch, secret: str, invalid_utf8: bytes, chunked: bool
) -> None:
    monkeypatch.setenv("API_TOKEN", secret)
    body = invalid_utf8 + b"/PUBLIC-END"
    split = max(1, len(invalid_utf8) // 2)
    code = (
        "import os,time;os.write(1," + repr(body[:split]) + ");time.sleep(.02);os.write(1," + repr(body[split:]) + ")"
        if chunked
        else "import os;os.write(1," + repr(body) + ")"
    )
    result = validator._diagnostic_command([sys.executable, "-c", code], {}, timeout=2)
    assert result["status"] == "ok"
    assert result["tail"] == "[REDACTED]/PUBLIC-END"
    assert secret not in result["tail"]
    assert len(result["tail"].encode()) <= 16_384


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        (b'{"Error":"FICTIONAL-a\xffb-END","ExitCode":0}', {"Error": "[REDACTED]", "ExitCode": 0}),
        (b'{"FICTIONAL-a\xffb-END":"public","ExitCode":0}', {"[REDACTED]": "public", "ExitCode": 0}),
    ],
)
def test_invalid_utf8_json_strings_and_keys_are_redacted_without_erasing_state(
    monkeypatch: pytest.MonkeyPatch, body: bytes, expected: dict[str, object]
) -> None:
    secret = "FICTIONAL-a\ufffdb-END"
    monkeypatch.setenv("API_TOKEN", secret)
    monkeypatch.setenv("API_SECRET", "0")
    result = validator._diagnostic_command(
        [sys.executable, "-c", "import os;os.write(1," + repr(body) + ")"], {}, timeout=2
    )
    assert result["status"] == "ok"
    assert json.loads(result["tail"]) == expected
    assert secret not in result["tail"]


def test_invalid_utf8_at_eof_cannot_reintroduce_a_known_credential_prefix(monkeypatch: pytest.MonkeyPatch) -> None:
    secret = "FICTIONAL-a\ufffdb-END"
    monkeypatch.setenv("API_TOKEN", secret)
    result = validator._diagnostic_command(
        [sys.executable, "-c", "import os;os.write(1,b'public/FICTIONAL-a\\xff')"], {}, timeout=2
    )
    assert result["status"] == "ok"
    assert result["tail"] == "public/[REDACTED]"


@pytest.mark.parametrize(
    ("credentials", "body"),
    [
        (("FOO", "X[REDACTED]Y", "L[REDACTED]R"), b"LXFOOYR"),
        (("FOO", "X[REDACTED]Y"), b'{"Error":"XFOOY","ExitCode":0}'),
        (("FOO", "X[REDACTED]Y"), b'{"XFOOY":"public","ExitCode":0}'),
    ],
)
def test_redaction_marker_adjacency_withholds_recreated_known_values(
    monkeypatch: pytest.MonkeyPatch, credentials: tuple[str, ...], body: bytes
) -> None:
    monkeypatch.setattr(validator, "_credentials", lambda: credentials)
    result = validator._diagnostic_command(
        [sys.executable, "-c", "import os;os.write(1," + repr(body) + ")"], {}, timeout=2
    )
    assert result["status"] == "output-withheld" and result["tail"] == ""
