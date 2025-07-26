# SPDX-License-Identifier: Apache-2.0
"""Light-weight dependency check for demos and tests.

This helper validates that the Python packages required by the
Alpha‑Factory demos and unit tests are present.  When invoked with the
``--auto-install`` flag (or ``AUTO_INSTALL_MISSING=1`` environment
variable) it installs ``alpha_factory_v1/requirements-core.txt`` by
default before attempting to resolve any remaining missing packages with
``pip``.  Set ``ALPHA_FACTORY_FULL=1`` to install the heavier
``requirements.txt`` instead.  For air‑gapped environments supply
``--wheelhouse`` or set ``WHEELHOUSE=/path/to/wheels`` so ``pip`` can
resolve packages from a local directory.

The script prints a warning when packages are missing but continues to
run so the demos remain usable in restricted setups. Missing ``numpy`` or
``pandas`` normally aborts execution with an error unless the
``--allow-basic-fallback`` flag is supplied. It also performs a
quick TCP connection test to ``pypi.org`` to detect network access. When
``--auto-install`` is used without connectivity and no ``--wheelhouse``
is provided the script exits early with instructions rather than waiting
for ``pip`` timeouts.

Use ``--demo <name>`` to validate extra packages required by a specific
demo. Currently ``macro_sentinel`` checks for ``gradio``, ``aiohttp`` and
``qdrant-client``.
"""

import importlib.util
import subprocess
from alpha_factory_v1.scripts.preflight import check_openai_agents_version
import os
import sys
import argparse
import socket
import shutil
import urllib
import urllib.parse
import urllib.request
from pathlib import Path
from typing import List, Optional

NO_NETWORK_HINT = (
    "No network connectivity detected and no wheelhouse was provided.\n"
    "Set HTTP_PROXY or HTTPS_PROXY if your environment requires a proxy.\n"
    "Build wheels with './scripts/build_offline_wheels.sh' on a machine with\n"
    "internet access, copy the resulting 'wheels/' directory to this host,\n"
    "then re-run using 'python check_env.py --auto-install --wheelhouse <dir>'\n"
    "or set the WHEELHOUSE environment variable."
)


def check_pkg(pkg: str) -> bool:
    """Return ``True`` if *pkg* is importable."""
    try:
        return importlib.util.find_spec(pkg) is not None
    except Exception:  # pragma: no cover - importlib failure is unexpected
        return False


CORE = ["numpy", "yaml", "pandas"]


def warn_missing_core() -> List[str]:
    """Return any missing foundational packages and print a warning."""
    missing = [pkg for pkg in CORE if importlib.util.find_spec(pkg) is None]
    if missing:
        print("WARNING: Missing core packages:", ", ".join(missing))
    return missing


FULL_FEATURE = os.getenv("ALPHA_FACTORY_FULL", "0").lower() in {"1", "true", "yes"}

REQUIRED_BASE = [
    "pytest",
    "pytest_asyncio",
    "prometheus_client",
    "openai",
    "anthropic",
    "fastapi",
    "opentelemetry",
    "opentelemetry-api",
    "uvicorn",
    "httpx",
    "grpc",
    "cryptography",
    "numpy",
    "google.protobuf",
    "cachetools",
    "yaml",
    "click",
    "requests",
    "requests_mock",
    "pandas",
    "playwright.sync_api",
    "websockets",
    "pytest_benchmark",
    "hypothesis",
    "wheel",
]

HEAVY_EXTRAS = [
    "openai_agents",
    "google_adk",
    "sentence_transformers",
    "faiss",
    "chromadb",
    "scipy",
    "ortools",
    "transformers",
    "accelerate",
    "sentencepiece",
    "deap",
    "gymnasium",
    "ccxt",
    "yfinance",
    "newsapi",
    "feedparser",
    "neo4j",
    "psycopg2",
    "networkx",
    "sqlalchemy",
    "noaa_sdk",
    "llama_cpp_python",
    "ctransformers",
    "streamlit",
    "plotly",
]

REQUIRED = REQUIRED_BASE + (HEAVY_EXTRAS if FULL_FEATURE else [])

# Additional requirements for specific demos
DEMO_PACKAGES = {
    "macro_sentinel": [
        "gradio",
        "aiohttp",
        "qdrant_client",
    ],
    "era_experience": [
        "openai_agents",
        "gradio",
        "sentence_transformers",
    ],
}

# Optional integrations that may not be present in restricted environments.
OPTIONAL = [
    "openai_agents",
    "google_adk",
]

PIP_NAMES = {
    "openai_agents": "openai-agents",
    "google_adk": "google-adk",
    "grpc": "grpcio",
    "pytest_benchmark": "pytest-benchmark",
    "playwright.sync_api": "playwright",
    "websockets": "websockets",
    "google.protobuf": "protobuf",
    "cachetools": "cachetools",
    "yaml": "PyYAML",
    "gradio": "gradio",
    "aiohttp": "aiohttp",
    "sentence_transformers": "sentence-transformers",
    "opentelemetry": "opentelemetry-api",
    "opentelemetry-api": "opentelemetry-api",
    "qdrant_client": "qdrant-client",
    "faiss": "faiss-cpu",
    "scipy": "scipy",
    "ortools": "ortools",
    "transformers": "transformers",
    "accelerate": "accelerate",
    "sentencepiece": "sentencepiece",
    "deap": "deap",
    "gymnasium": "gymnasium[classic-control]",
    "ccxt": "ccxt",
    "yfinance": "yfinance",
    "newsapi": "newsapi-python",
    "feedparser": "feedparser",
    "neo4j": "neo4j",
    "psycopg2": "psycopg2-binary",
    "networkx": "networkx",
    "sqlalchemy": "SQLAlchemy",
    "noaa_sdk": "noaa-sdk",
    "llama_cpp_python": "llama-cpp-python",
    "ctransformers": "ctransformers",
    "streamlit": "streamlit",
    "plotly": "plotly",
}

IMPORT_NAMES = {
    "opentelemetry-api": "opentelemetry",
}


def has_network(timeout: float = 1.0) -> bool:
    """Return ``True`` if any of the test hosts is reachable.

    The function first checks for ``HTTP_PROXY`` or ``HTTPS_PROXY``
    and attempts to connect to the proxy if defined. It then tries
    ``pypi.org``, ``1.1.1.1`` and ``github.com`` in that order. If all
    socket attempts fail, a ``HEAD`` request to ``https://pypi.org`` is
    issued as a fallback so proxy-only environments still succeed.
    """

    hosts: list[tuple[str, int]] = []
    proxy = os.getenv("HTTPS_PROXY") or os.getenv("HTTP_PROXY")
    if proxy:
        try:
            parsed = urllib.parse.urlparse(proxy)
            if parsed.hostname:
                hosts.append(
                    (
                        parsed.hostname,
                        parsed.port or (443 if parsed.scheme == "https" else 80),
                    )
                )
        except Exception:
            pass

    hosts.extend(
        [
            ("pypi.org", 443),
            ("1.1.1.1", 443),
            ("github.com", 443),
        ]
    )

    for host in hosts:
        try:
            with socket.create_connection(host, timeout=timeout):
                return True
        except OSError:
            continue

    try:
        req = urllib.request.Request("https://pypi.org", method="HEAD")
        with urllib.request.urlopen(req, timeout=timeout):
            return True
    except Exception:
        return False


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate runtime dependencies",
        epilog=(
            "Example: pip wheel -r requirements-core.txt -w /media/wheels\n"
            "If no --wheelhouse is provided and the repository contains a"
            " 'wheels/' directory, that path is used automatically."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--auto-install",
        action="store_true",
        help="Attempt pip install of any missing packages",
    )
    parser.add_argument(
        "--wheelhouse",
        help=(
            "Optional path to a local wheelhouse for offline installs. "
            "Defaults to <repo>/wheels when that directory exists."
        ),
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=int(os.getenv("PIP_TIMEOUT", "600")),
        help="Seconds before pip install operations abort (default: 600)",
    )
    parser.add_argument(
        "--allow-basic-fallback",
        action="store_true",
        help="Continue even if numpy or pandas are missing",
    )
    parser.add_argument(
        "--demo",
        help="Validate additional packages for the specified demo",
    )
    parser.add_argument(
        "--skip-net-check",
        action="store_true",
        help="Skip the connectivity check to run quietly offline",
    )

    args = parser.parse_args(argv)

    wheelhouse = args.wheelhouse or os.getenv("WHEELHOUSE")
    if not wheelhouse:
        default_wh = Path(__file__).resolve().parent / "wheels"
        if default_wh.is_dir():
            wheelhouse = str(default_wh)

    wheel_path = Path(wheelhouse).resolve() if wheelhouse else None
    if wheel_path and not (wheel_path.is_dir() and any(wheel_path.glob("*.whl"))):
        print(f"Wheelhouse {wheel_path} has no wheels; falling back to network installs")
        wheel_path = None
    wheelhouse = str(wheel_path) if wheel_path else None
    auto = args.auto_install or os.getenv("AUTO_INSTALL_MISSING") == "1"
    heavy_auto = FULL_FEATURE
    skip_net_check = args.skip_net_check
    pip_timeout = args.timeout
    allow_basic = args.allow_basic_fallback
    demo = args.demo
    wheel_msg = f" (wheelhouse: {wheelhouse})" if wheelhouse else ""
    extra_required = DEMO_PACKAGES.get(demo, [])

    missing_core = [pkg for pkg in CORE if not check_pkg(pkg)]
    missing_required_tmp: list[str] = []
    for pkg in REQUIRED + extra_required:
        import_name = IMPORT_NAMES.get(pkg, pkg)
        try:
            spec = importlib.util.find_spec(import_name)
        except (ValueError, ModuleNotFoundError):
            spec = None
        if spec is None:
            missing_required_tmp.append(pkg)

    if wheelhouse:
        network_ok = True
    elif skip_net_check:
        network_ok = False
    elif auto and (missing_core or missing_required_tmp):
        network_ok = has_network()
        if not network_ok:
            print(NO_NETWORK_HINT)
            return 1
    else:
        network_ok = True

    if auto and (wheelhouse or network_ok):
        for pkg in ("numpy", "prometheus_client"):
            if not check_pkg(pkg):
                cmd = [sys.executable, "-m", "pip", "install", "--quiet"]
                if wheelhouse:
                    cmd += ["--no-index", "--find-links", wheelhouse]
                cmd += [PIP_NAMES.get(pkg, pkg)]
                print(
                    f"Ensuring {pkg} (timeout {pip_timeout}s):",
                    " ".join(cmd),
                    flush=True,
                )
                try:
                    subprocess.run(cmd, check=True, timeout=pip_timeout)
                except subprocess.SubprocessError as exc:
                    print(
                        f"Failed to install {pkg}{wheel_msg}",
                        getattr(exc, "returncode", ""),
                    )
                    return 1

    missing_core = warn_missing_core()

    if auto and missing_core and (wheelhouse or network_ok):
        cmd = [sys.executable, "-m", "pip", "install", "--quiet"]
        if wheelhouse:
            cmd += ["--no-index", "--find-links", wheelhouse]
        cmd += [PIP_NAMES.get(pkg, pkg) for pkg in missing_core]
        print(
            f"Attempting install of core packages (timeout {pip_timeout}s):",
            " ".join(cmd),
            flush=True,
        )
        try:
            subprocess.run(cmd, check=True, timeout=pip_timeout)
        except subprocess.SubprocessError as exc:
            print(
                f"Failed to install core packages{wheel_msg}",
                getattr(exc, "returncode", ""),
            )
            return 1
        missing_core = warn_missing_core()

    if missing_core and not allow_basic:
        print(
            "ERROR: numpy and pandas are required for realistic results. "
            "Re-run with --allow-basic-fallback to bypass this check."
        )
        return 1
    req_name = "requirements.txt" if FULL_FEATURE else "requirements-core.txt"
    req_file = Path(__file__).resolve().parent / "alpha_factory_v1" / req_name
    missing_required_pre: list[str] = []
    for pkg in REQUIRED + extra_required:
        import_name = IMPORT_NAMES.get(pkg, pkg)
        try:
            spec = importlib.util.find_spec(import_name)
        except (ValueError, ModuleNotFoundError):
            spec = None
        if spec is None:
            missing_required_pre.append(pkg)

    if auto and req_file.exists() and (wheelhouse or network_ok) and (missing_core or missing_required_pre):
        cmd = [sys.executable, "-m", "pip", "install", "--quiet"]
        if wheelhouse:
            cmd += ["--no-index", "--find-links", wheelhouse]
        cmd += ["-r", str(req_file)]
        print(
            f"Ensuring baseline requirements (timeout {pip_timeout}s):",
            " ".join(cmd),
            flush=True,
        )
        try:
            subprocess.run(cmd, check=True, timeout=pip_timeout)
        except subprocess.TimeoutExpired:
            print("Timed out installing baseline requirements.\n" + NO_NETWORK_HINT)
            if wheelhouse:
                print(f"Wheelhouse used: {wheelhouse}")
            return 1
        except subprocess.CalledProcessError as exc:
            stderr = exc.stderr or ""
            print(
                f"Failed to install baseline requirements{wheel_msg}",
                exc.returncode,
            )
            if any(kw in stderr.lower() for kw in ["connection", "temporary failure", "network", "resolve"]):
                print("Network failure detected.\n" + NO_NETWORK_HINT)
            return exc.returncode

    if heavy_auto:
        heavy_missing: list[str] = []
        for pkg in HEAVY_EXTRAS:
            import_name = IMPORT_NAMES.get(pkg, pkg)
            try:
                spec = importlib.util.find_spec(import_name)
            except (ValueError, ModuleNotFoundError):
                spec = None
            if spec is None:
                heavy_missing.append(pkg)

        if heavy_missing:
            if not wheelhouse and not skip_net_check:
                if not has_network():
                    print(NO_NETWORK_HINT)
                    return 1
            cmd = [sys.executable, "-m", "pip", "install", "--quiet"]
            if wheelhouse:
                cmd += ["--no-index", "--find-links", wheelhouse]
            cmd += [PIP_NAMES.get(pkg, pkg) for pkg in heavy_missing]
            print(
                f"Ensuring heavy extras (timeout {pip_timeout}s):",
                " ".join(cmd),
                flush=True,
            )
            try:
                subprocess.run(cmd, check=True, timeout=pip_timeout)
            except subprocess.SubprocessError as exc:
                print(
                    f"Failed to install heavy extras{wheel_msg}",
                    getattr(exc, "returncode", ""),
                )
                return 1

    missing_required: list[str] = []
    missing_optional: list[str] = []
    openai_agents_found = False
    openai_agents_attr_ok = False
    for pkg in REQUIRED + extra_required + OPTIONAL:
        import_name = IMPORT_NAMES.get(pkg, pkg)
        try:
            spec = importlib.util.find_spec(import_name)
        except (ValueError, ModuleNotFoundError):
            # handle cases where a namespace package left an invalid entry
            # or the root package itself is missing
            spec = None
        if spec is None:
            if pkg == "openai_agents":
                agents_spec = importlib.util.find_spec("agents")
                if agents_spec is not None:
                    try:
                        mod = importlib.import_module("agents")
                        openai_agents_attr_ok = hasattr(mod, "OpenAIAgent") or hasattr(mod, "Agent")
                    except Exception:
                        openai_agents_attr_ok = False
                    openai_agents_found = True
                    if openai_agents_attr_ok:
                        continue
            if pkg in OPTIONAL:
                missing_optional.append(pkg)
            else:
                missing_required.append(pkg)
        elif pkg in {"openai_agents", "agents"}:
            openai_agents_found = True
            try:
                mod = importlib.import_module(import_name)
                openai_agents_attr_ok = hasattr(mod, "OpenAIAgent") or hasattr(mod, "Agent")
            except Exception:
                openai_agents_attr_ok = False
    missing = missing_required + missing_optional
    if missing:
        print("WARNING: Missing packages:", ", ".join(missing))
        if auto and missing_required and (wheelhouse or network_ok):
            cmd = [sys.executable, "-m", "pip", "install", "--quiet"]
            if wheelhouse:
                cmd += ["--no-index", "--find-links", wheelhouse]
            packages = [PIP_NAMES.get(pkg, pkg) for pkg in missing_required]
            cmd += packages
            print(
                f"Attempting automatic install (timeout {pip_timeout}s):",
                " ".join(cmd),
                flush=True,
            )
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    check=True,
                    timeout=pip_timeout,
                )
            except subprocess.TimeoutExpired:
                print("Timed out installing packages.\n" + NO_NETWORK_HINT)
                if wheelhouse:
                    print(f"Wheelhouse used: {wheelhouse}")
                return 1
            except subprocess.CalledProcessError as exc:
                stderr = exc.stderr or ""
                print(
                    f"Automatic install failed with code{wheel_msg}",
                    exc.returncode,
                )
                if any(kw in stderr.lower() for kw in ["connection", "temporary failure", "network", "resolve"]):
                    print("Network failure detected.\n" + NO_NETWORK_HINT)
                return 1
            else:
                if result.returncode != 0:
                    print("Automatic install failed with code", result.returncode)
                    return result.returncode
                print("Install completed, verifying …")
                missing = [p for p in missing if importlib.util.find_spec(IMPORT_NAMES.get(p, p)) is None]
                missing_required = [p for p in missing if p not in OPTIONAL]
                if missing_required:
                    print(
                        "ERROR: The following packages are still missing after the installation attempt:",
                        ", ".join(missing_required),
                    )
                    return 1

        else:
            hint = "pip install " + " ".join(missing)
            if wheelhouse:
                hint = f"pip install --no-index --find-links {wheelhouse} " + " ".join(missing)
            print("Some features may be degraded. Install with:", hint)

    if openai_agents_found and not openai_agents_attr_ok:
        print("WARNING: openai_agents package lacks required API; skipping auto-install")
    elif openai_agents_found:
        try:
            mod = importlib.import_module("openai_agents")
        except Exception:
            try:
                mod = importlib.import_module("agents")
            except Exception:
                mod = None
        mod_spec = getattr(mod, "__spec__", None)
        if mod_spec is None:
            print("WARNING: openai_agents package lacks __spec__ metadata; skipping version check")
        elif allow_basic:
            if getattr(mod_spec, "loader", None) and not check_openai_agents_version():
                return 1
        else:
            if getattr(mod_spec, "loader", None) is None:
                print("WARNING: openai_agents package lacks __spec__ metadata")
            elif not check_openai_agents_version():
                return 1

    if demo == "macro_sentinel" and not os.getenv("ETHERSCAN_API_KEY"):
        print("WARNING: ETHERSCAN_API_KEY is unset; Etherscan collector disabled")

    if (shutil.which("pre-commit") or (Path(".git/hooks/pre-commit").exists())) and not shutil.which("ruff"):
        if auto and (wheelhouse or network_ok):
            cmd = [sys.executable, "-m", "pip", "install", "--quiet"]
            if wheelhouse:
                cmd += ["--no-index", "--find-links", wheelhouse]
            cmd.append("ruff")
            print(
                f"Installing Ruff (timeout {pip_timeout}s):",
                " ".join(cmd),
                flush=True,
            )
            try:
                subprocess.run(cmd, check=True, timeout=pip_timeout)
            except subprocess.SubprocessError as exc:
                print("Failed to install Ruff", getattr(exc, "returncode", ""))
                return 1
        else:
            print("WARNING: 'pre-commit' enabled but 'ruff' command not found")

    if not missing_required:
        print("Environment OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
