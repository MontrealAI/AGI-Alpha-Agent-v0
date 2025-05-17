import os
import shutil
import sys
import subprocess
import tempfile
from pathlib import Path

MIN_PY = (3, 9)
MAX_PY = (3, 12)
MEM_DIR = Path(os.getenv("AF_MEMORY_DIR", f"{tempfile.gettempdir()}/alphafactory"))

COLORS = {
    'RED': '\033[31m',
    'GREEN': '\033[32m',
    'YELLOW': '\033[33m',
    'RESET': '\033[0m',
}

def banner(msg: str, color: str = 'GREEN') -> None:
    color_code = COLORS.get(color.upper(), '')
    reset = COLORS['RESET']
    print(f"{color_code}{msg}{reset}")


def check_python() -> bool:
    if sys.version_info < MIN_PY or sys.version_info >= MAX_PY:
        banner(
            f"Python {MIN_PY[0]}.{MIN_PY[1]}+ and <{MAX_PY[0]}.{MAX_PY[1]} required",
            'RED',
        )
        return False
    banner(f"Python {sys.version.split()[0]} detected", 'GREEN')
    return True


def check_cmd(cmd: str) -> bool:
    if shutil.which(cmd):
        banner(f"{cmd} found", 'GREEN')
        return True
    banner(f"{cmd} missing", 'RED')
    return False


def check_docker_daemon() -> bool:
    if not shutil.which('docker'):
        return False
    try:
        subprocess.run(['docker', 'info'], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        banner('docker daemon reachable', 'GREEN')
        return True
    except Exception:  # noqa: BLE001
        banner('docker daemon not running', 'RED')
        return False


def check_docker_compose() -> bool:
    if not shutil.which('docker'):
        banner('docker compose missing', 'RED')
        return False
    try:
        subprocess.run(
            ['docker', 'compose', 'version'],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        banner('docker compose available', 'GREEN')
        return True
    except Exception:  # noqa: BLE001
        banner('docker compose missing', 'RED')
        return False


def check_pkg(pkg: str) -> bool:
    """Return True if *pkg* is importable."""
    try:
        import importlib.util
        found = importlib.util.find_spec(pkg) is not None
    except Exception:  # pragma: no cover - importlib failure is unexpected
        found = False
    banner(f"{pkg} {'found' if found else 'missing'}", 'GREEN' if found else 'RED')
    return found


def ensure_dir(path: Path) -> None:
    if not path.exists():
        path.mkdir(parents=True, exist_ok=True)
        banner(f"Created {path}", 'YELLOW')
    else:
        banner(f"Using {path}", 'GREEN')


def main() -> None:
    banner("Alpha-Factory Preflight Check", 'YELLOW')
    ok = True
    ok &= check_python()
    ok &= check_cmd('docker')
    ok &= check_cmd('git')
    ok &= check_docker_daemon()
    ok &= check_docker_compose()
    ok &= check_pkg('openai')
    ok &= check_pkg('openai_agents')
    ensure_dir(MEM_DIR)

    for key in ('OPENAI_API_KEY', 'ANTHROPIC_API_KEY'):
        if os.getenv(key):
            banner(f"{key} set", 'GREEN')
        else:
            banner(f"{key} not set", 'YELLOW')

    if not ok:
        banner('Preflight checks failed. Please install required dependencies.', 'RED')
        sys.exit(1)

    banner('Environment looks good. You can now run install_alpha_factory_pro.sh', 'GREEN')

if __name__ == '__main__':
    main()
