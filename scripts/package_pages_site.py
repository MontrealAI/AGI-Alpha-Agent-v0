# SPDX-License-Identifier: Apache-2.0
"""Archive the tested public site and bind it to the source commit and release."""
from __future__ import annotations

import argparse
from html.parser import HTMLParser
import json
from pathlib import Path
import subprocess
import tarfile
import tomllib
from urllib.parse import unquote, urlsplit


class Links(HTMLParser):
    """Collect home-page navigation and public resource references."""

    def __init__(self) -> None:
        super().__init__()
        self.urls: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        for key, value in attrs:
            if value and ((tag == "a" and key == "href") or key == "src" or tag == "link" and key == "href"):
                self.urls.append(value)


def package(site: Path, output: Path) -> None:
    """Fail on broken workspace navigation and disallow links in the deployment archive."""
    site = site.resolve()
    version = tomllib.loads(Path("pyproject.toml").read_text())["project"]["version"]
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    parser = Links()
    parser.feed((site / "index.html").read_text(encoding="utf-8"))
    for url in parser.urls:
        parts = urlsplit(url)
        if parts.scheme or parts.netloc or not parts.path:
            continue
        target = (site / unquote(parts.path)).resolve()
        if not target.is_relative_to(site):
            raise ValueError(f"Workspace link escapes site: {url}")
        if target.is_dir():
            target /= "index.html"
        if not target.is_file():
            raise ValueError(f"Broken workspace navigation or asset: {url}")
    manifest = {
        "schema": 1,
        "version": version,
        "commit": commit,
        "url": "https://montrealai.github.io/AGI-Alpha-Agent-v0/",
        "build_run": "https://github.com/MontrealAI/AGI-Alpha-Agent-v0/actions",
    }
    (site / "release.json").write_text(json.dumps(manifest, indent=2) + "\n")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(output, "w:gz") as archive:
        for file in sorted(site.rglob("*")):
            if file.is_symlink():
                raise ValueError(f"Site must not contain symbolic links: {file}")
            if file.is_file():
                archive.add(file, arcname=file.relative_to(site).as_posix(), recursive=False)
    print(json.dumps({**manifest, "archive": str(output), "bytes": output.stat().st_size}))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", type=Path, default=Path("site"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    package(args.site, args.output)


if __name__ == "__main__":
    main()
