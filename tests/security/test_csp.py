import base64
import hashlib
import re
from pathlib import Path

from scripts.ensure_insight_csp import ensure_csp


def _hash_snippet(snippet: str) -> str:
    digest = hashlib.sha384(snippet.encode()).digest()
    return "'sha384-" + base64.b64encode(digest).decode() + "'"


def test_csp_hashes_match() -> None:
    html_path = Path("docs/alpha_agi_insight_v1/index.html")
    html = html_path.read_text()
    meta = re.search(r"<meta[^>]*Content-Security-Policy[^>]*content=\"([^\"]+)\"", html)
    assert meta, "CSP meta tag missing"
    csp = meta.group(1)
    match = re.search(r"script-src ([^;]+)", csp)
    assert match, "script-src missing in CSP"
    allowed_hashes = set(re.findall(r"'sha384-[^']+'", match.group(1)))
    inline_scripts = re.findall(r"<script(?![^>]*src)[^>]*>([\s\S]*?)</script>", html)
    computed = {_hash_snippet(s) for s in inline_scripts}
    assert computed <= allowed_hashes

    srcs = re.findall(r"<script[^>]*src=['\"]([^'\"]+)['\"]", html)
    assert len(srcs) == len(set(srcs))


def test_repair_preserves_inherited_sandbox_hashes(tmp_path: Path) -> None:
    page_script = "\nwindow.pageReady = true;\n"
    host_script = "\nwindow.parent.postMessage('ready', '*');\n"
    page = tmp_path / "index.html"
    host = tmp_path / "sandbox_worker_host.html"
    page.write_text(f"<html><head></head><body><script>{page_script}</script></body></html>", encoding="utf-8")
    host.write_text(f"<script>{host_script}</script>", encoding="utf-8")

    assert ensure_csp(tmp_path)
    policy = page.read_text(encoding="utf-8")
    assert _hash_snippet(page_script) in policy
    assert _hash_snippet(host_script) in policy
    script_sources = re.search(r"script-src ([^;]+)", policy)
    assert script_sources is not None
    assert "'unsafe-inline'" not in script_sources.group(1)
    assert not ensure_csp(tmp_path)

    updated_host = "\nwindow.parent.postMessage('updated', '*');\n"
    host.write_text(f"<script>{updated_host}</script>", encoding="utf-8")
    assert ensure_csp(tmp_path)
    policy = page.read_text(encoding="utf-8")
    assert _hash_snippet(updated_host) in policy
    assert _hash_snippet(host_script) not in policy
    assert _hash_snippet(page_script) in policy


def test_repair_without_sandbox_host(tmp_path: Path) -> None:
    snippet = "window.pageReady = true;"
    page = tmp_path / "index.html"
    page.write_text(f"<html><head></head><script>{snippet}</script></html>", encoding="utf-8")
    assert ensure_csp(tmp_path)
    assert _hash_snippet(snippet) in page.read_text(encoding="utf-8")
    assert not ensure_csp(tmp_path)
