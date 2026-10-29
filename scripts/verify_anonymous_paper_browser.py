# SPDX-License-Identifier: Apache-2.0
"""One bounded headed anonymous readback; capture never implies PDF rendering."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import shutil
import signal
import socket
import stat
import struct
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from contrib.invention_automation.public_reader import (
    COMMIT,
    EXPECTED_SHA256,
    PATH,
    REPOSITORY,
    retrieve,
)

SOURCE_BASE = "939549e6487aa4cfc14b8385b52f701a1a0c8d2b"
ENVELOPE_END = datetime(2026, 10, 29, 18, 29, tzinfo=UTC)
PROFILE_LIMIT = 67_108_864
JS = """
const brief=raw=>{try{const u=new URL(raw,location.href);return {
 origin:u.origin,path:u.pathname,query_keys:[...new Set(u.searchParams.keys())].sort(),
 fragment_present:!!u.hash};}catch{return {invalid_url:true};}};
return {title:document.title,ready_state:document.readyState,location:brief(location.href),
 visible_text:(document.body?.innerText||'').slice(0,6000),
 canvas_count:document.querySelectorAll('canvas').length,
 embed_count:document.querySelectorAll('embed,object').length,
 frames:[...document.querySelectorAll('iframe')].slice(0,4).map((f,index)=>({
 index,source:brief(f.src),width:f.clientWidth,height:f.clientHeight}))};
"""


class ProbeError(RuntimeError):
    pass


def write_json(path: Path, value: Any) -> None:
    with path.open("x", encoding="utf-8") as output:
        output.write(json.dumps(value, sort_keys=True, indent=2) + "\n")


def profile_bytes(path: Path) -> int:
    total, count = 0, 0
    for root, _, names in os.walk(path, followlinks=False):
        for name in names:
            try:
                item = (Path(root) / name).lstat()
            except FileNotFoundError:
                continue
            count += 1
            if count > 20_000:
                raise ProbeError("profile file-count bound")
            if stat.S_ISREG(item.st_mode):
                total += item.st_size
            if total > PROFILE_LIMIT:
                raise ProbeError("profile exceeded 64 MiB")
    return total


def safe_dom(value: dict[str, Any]) -> dict[str, Any]:
    value["visible_text"] = re.sub(r"https?://\S+", "[URL omitted]", value.get("visible_text", ""))[
        :6000
    ]
    return value


def probe(output: Path, record: dict[str, Any]) -> None:
    tools = {
        name: shutil.which(name)
        for name in ("google-chrome", "chromedriver", "Xvfb", "xvfb-run", "xauth")
    }
    missing = [name for name, path in tools.items() if path is None]
    if missing:
        record.update(
            status="BLOCKED", reason="required preinstalled tools absent", missing_tools=missing
        )
        return
    if (ENVELOPE_END - datetime.now(UTC)).total_seconds() < 180:
        record.update(status="BLOCKED", reason="insufficient inherited verification envelope")
        return
    deadline = time.monotonic() + 160
    versions = {}
    for name in ("google-chrome", "chromedriver"):
        value = subprocess.run(
            [tools[name], "--version"], capture_output=True, text=True, timeout=5, check=True
        )
        versions[name] = value.stdout.strip()[:300]
    record["versions"] = versions
    majors = [re.search(r"\b(\d+)\.", versions[name]) for name in ("google-chrome", "chromedriver")]
    if not all(majors) or majors[0].group(1) != majors[1].group(1):
        record.update(status="BLOCKED", reason="Chrome and ChromeDriver major mismatch")
        return
    raw_url = f"https://raw.githubusercontent.com/{REPOSITORY}/{COMMIT}/{PATH}"
    raw, pdf = retrieve(raw_url, 1_048_576)
    identity = hashlib.sha256(raw).hexdigest()
    if len(raw) != 622_931 or not raw.startswith(b"%PDF-") or identity != EXPECTED_SHA256:
        raise ProbeError("immutable PDF byte identity mismatch")
    record["pdf"] = {**pdf, "sha256": identity}
    source_url = f"https://github.com/{REPOSITORY}/blob/{COMMIT}/{PATH}"
    record["source_url"] = source_url
    temporary = os.environ.get("RUNNER_TEMP")
    if not temporary:
        record.update(status="BLOCKED", reason="RUNNER_TEMP unavailable")
        return
    profile = Path(tempfile.mkdtemp(prefix="paper-headed-profile-", dir=temporary))
    record["fresh_profile"] = True
    log_path = profile.parent / (profile.name + "-process.log")
    driver_log = profile.parent / (profile.name + "-driver.log")
    with socket.socket() as selected:
        selected.bind(("127.0.0.1", 0))
        port = selected.getsockname()[1]
    endpoint = f"http://127.0.0.1:{port}"
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    session, process, peak = None, None, 0

    def check_profile() -> None:
        nonlocal peak
        peak = max(peak, profile_bytes(profile))
        if time.monotonic() >= deadline:
            raise ProbeError("overall probe deadline")

    def call(method: str, path: str, value: Any = None, timeout: float = 12) -> Any:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise ProbeError("overall probe deadline")
        request = urllib.request.Request(
            endpoint + path,
            method=method,
            data=None if value is None else json.dumps(value).encode(),
            headers={"Content-Type": "application/json"},
        )
        try:
            response = opener.open(request, timeout=min(timeout, remaining))
        except urllib.error.HTTPError as error:
            body = json.loads(error.read(65_536))
            raise ProbeError(
                "WebDriver " + str(body.get("value", {}).get("error", "unknown"))
            ) from None
        with response:
            body = response.read(6_000_001)
        if len(body) > 6_000_000:
            raise ProbeError("WebDriver response byte bound")
        value = json.loads(body).get("value")
        if isinstance(value, dict) and value.get("error"):
            raise ProbeError("WebDriver " + str(value["error"]))
        return value

    def sc(method: str, path: str, value: Any = None, timeout: float = 12) -> Any:
        return call(method, "/session/" + session + path, value, timeout)

    def capture(name: str) -> None:
        check_profile()
        png = base64.b64decode(sc("GET", "/screenshot"), validate=True)
        if not png.startswith(b"\x89PNG\r\n\x1a\n") or len(png) > 4_194_304:
            raise ProbeError("invalid or oversized screenshot")
        width, height = struct.unpack(">II", png[16:24])
        if not (1 <= width <= 4096 and 1 <= height <= 4096):
            raise ProbeError("screenshot dimension bound")
        with (output / name).open("xb") as target:
            target.write(png)
        record.setdefault("captures", []).append(
            {
                "file": name,
                "bytes": len(png),
                "sha256": hashlib.sha256(png).hexdigest(),
                "width": width,
                "height": height,
            }
        )

    try:
        with log_path.open("xb") as log:
            process = subprocess.Popen(
                [
                    tools["xvfb-run"],
                    "-a",
                    "--server-args=-screen 0 1440x1100x24 -nolisten tcp",
                    tools["chromedriver"],
                    "--port=" + str(port),
                    "--allowed-ips=127.0.0.1",
                    "--log-path=" + str(driver_log),
                ],
                stdout=log,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
            ready_end = min(deadline, time.monotonic() + 15)
            while True:
                if process.poll() is not None or time.monotonic() >= ready_end:
                    raise ProbeError("preinstalled headed WebDriver unavailable")
                try:
                    if call("GET", "/status", timeout=1).get("ready"):
                        break
                except (OSError, ValueError, ProbeError):
                    pass
                time.sleep(0.25)
            capabilities = {
                "browserName": "chrome",
                "pageLoadStrategy": "eager",
                "acceptInsecureCerts": False,
                "goog:chromeOptions": {
                    "binary": tools["google-chrome"],
                    "args": [
                        "--user-data-dir=" + str(profile),
                        "--disable-background-networking",
                        "--disable-sync",
                        "--no-first-run",
                        "--no-default-browser-check",
                        "--disk-cache-size=1048576",
                        "--media-cache-size=1048576",
                        "--window-size=1440,1100",
                    ],
                },
            }
            created = call(
                "POST", "/session", {"capabilities": {"alwaysMatch": capabilities}}, timeout=20
            )
            session = created["sessionId"]
            record["browser_version"] = created.get("capabilities", {}).get(
                "browserVersion", "UNKNOWN"
            )
            sc("POST", "/timeouts", {"pageLoad": 20_000, "script": 10_000, "implicit": 0})
            sc("POST", "/window/rect", {"x": 0, "y": 0, "width": 1440, "height": 1100})
            check_profile()
            try:
                sc("POST", "/url", {"url": source_url}, timeout=22)
                record["navigation"] = "COMPLETED"
            except ProbeError as error:
                record["navigation"] = str(error)
            started = time.monotonic()
            for target, name in ((15, "headed-after-15s.png"), (50, "headed-after-50s.png")):
                while time.monotonic() - started < target:
                    check_profile()
                    time.sleep(max(0, min(1, target - (time.monotonic() - started))))
                capture(name)
            record["real_wait_seconds"] = time.monotonic() - started
            top = safe_dom(sc("POST", "/execute/sync", {"script": JS, "args": []}))
            write_json(output / "top-dom.json", top)
            frames = []
            for index in range(min(2, len(top.get("frames", [])))):
                try:
                    sc("POST", "/frame", {"id": index})
                    frames.append(
                        {
                            "index": index,
                            "diagnostic": safe_dom(
                                sc("POST", "/execute/sync", {"script": JS, "args": []})
                            ),
                        }
                    )
                except (OSError, ValueError, ProbeError) as error:
                    frames.append({"index": index, "error_category": type(error).__name__})
                finally:
                    sc("POST", "/frame", {"id": None})
            write_json(output / "frame-dom.json", frames)
            check_profile()
            record["status"] = "CAPTURED_REQUIRES_VISUAL_INSPECTION"
    finally:
        if session:
            try:
                sc("DELETE", "", timeout=5)
            except (OSError, ValueError, ProbeError):
                pass
        if process:
            try:
                os.killpg(process.pid, signal.SIGTERM)
                process.wait(timeout=5)
            except ProcessLookupError:
                pass
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait(timeout=5)
        try:
            record["profile_peak_observed_bytes"] = max(peak, profile_bytes(profile))
            record["private_logs"] = {
                name: {
                    "bytes": path.stat().st_size,
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                }
                for name, path in (("driver", driver_log), ("process", log_path))
                if path.is_file()
            }
        finally:
            # Preserve raw evidence; the hosted runner owns its temporary lifecycle.
            for name, path in (("driver", driver_log), ("process", log_path)):
                if path.is_file():
                    with path.open("rb") as source:
                        with (output / (name + "-original-private.log")).open("xb") as target:
                            shutil.copyfileobj(source, target)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=False, exist_ok=False)
    record: dict[str, Any] = {
        "schema": "agialpha/anonymous-headed-paper-probe/v1",
        "status": "FAILED",
        "software_base_commit": SOURCE_BASE,
        "probe_commit": os.environ.get("GITHUB_SHA", "UNKNOWN"),
        "probe_source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "paper_commit": COMMIT,
        "envelope_end": ENVELOPE_END.isoformat(),
        "fresh_profile": False,
        "credential_or_cookie_import": False,
        "headed": True,
        "real_wait_limit_seconds": 50,
        "profile_limit_bytes": PROFILE_LIMIT,
        "scope": "One public-paper browser verification only; no candidate generation or software qualification.",
        "rendering": "REQUIRES_VISUAL_INSPECTION",
    }
    try:
        probe(args.output, record)
    except Exception as error:  # noqa: BLE001 - preserve partial verification failures
        record.update(status="FAILED", reason=type(error).__name__ + ": " + str(error)[:300])
    finally:
        write_json(args.output / "receipt.json", record)
    print(json.dumps({"status": record["status"], "rendering": record["rendering"]}))
    return 0 if record["status"] == "CAPTURED_REQUIRES_VISUAL_INSPECTION" else 1


if __name__ == "__main__":
    raise SystemExit(main())
