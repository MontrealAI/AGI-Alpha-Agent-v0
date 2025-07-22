import base64
import hashlib
import re
from pathlib import Path


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
