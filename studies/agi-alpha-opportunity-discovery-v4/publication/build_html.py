"""Render the fixed Markdown paper as a standalone, network-free HTML edition."""

from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path
import re
import subprocess


HERE = Path(__file__).resolve().parent
TITLE = "AGI ALPHA FLYWHEEL — When Capability Creates Opportunity"
SUBTITLE = (
    "Transformational Intelligence, Experience-Trained Specialists and the "
    "Expanding Frontier of Profitable Work"
)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> None:
    source = HERE / "PAPER.md"
    raw = source.read_bytes()
    manuscript = raw.decode("utf-8")
    assert manuscript.startswith("# " + TITLE + "\n")
    assert "**Vincent Boucher — President of MONTREAL.AI**" in manuscript
    # Presentation-only heading attributes keep the exact manuscript text intact.
    prepared = manuscript.replace(
        "# " + TITLE + "\n", "# " + TITLE + " {.paper-title .unlisted .unnumbered}\n", 1
    ).replace(
        "## " + SUBTITLE + "\n", "## " + SUBTITLE + " {.paper-subtitle .unlisted .unnumbered}\n", 1
    )
    version = subprocess.run(["pandoc", "--version"], check=True, capture_output=True, text=True).stdout.splitlines()[0]
    command = [
        "pandoc", "--from=markdown+header_attributes+tex_math_dollars+pipe_tables", "--to=html5",
        "--standalone", "--section-divs", "--toc", "--toc-depth=2", "--mathml", "--no-highlight",
        "--wrap=none", "--template=" + str(HERE / "paper.template.html"),
        "--metadata=title:" + TITLE, "--metadata=lang:en", "--metadata=source_sha256:" + sha(raw),
    ]
    result = subprocess.run(command, input=prepared, capture_output=True, text=True, cwd=HERE, check=True)
    html = result.stdout
    html = re.sub(
        r'<p>(<math display="block".*?</math>)</p>',
        r'<div class="equation-scroll" role="region" aria-label="Mathematical equation" tabindex="0">\1</div>',
        html, flags=re.DOTALL,
    )
    figures = []
    for relative in re.findall(r'<img\b[^>]*\bsrc="([^"]+)"', html):
        path = (HERE / relative).resolve()
        assert path.parent == (HERE / "figures").resolve() and path.suffix.lower() == ".png", relative
        image = path.read_bytes()
        html = html.replace('src="' + relative + '"', 'src="data:image/png;base64,' + base64.b64encode(image).decode() + '"')
        figures.append({"path": relative, "bytes": len(image), "sha256": sha(image)})
    assert len(figures) == 6
    assert "<script" not in html.lower()
    assert all(x.startswith("data:image/png;base64,") for x in re.findall(r'<img\b[^>]*\bsrc="([^"]+)"', html))
    assert source.read_bytes() == raw, "Manuscript changed during build; rerun from the new fixed version."
    destination = HERE / "AGI_ALPHA_FLYWHEEL_v4.html"
    destination.write_text(html, encoding="utf-8")
    receipt = {
        "schema": "standalone-paper-html-build/v1", "pandoc_version": version,
        "source": {"path": "PAPER.md", "bytes": len(raw), "sha256": sha(raw)},
        "builder_sha256": sha(Path(__file__).read_bytes()),
        "template_sha256": sha((HERE / "paper.template.html").read_bytes()),
        "output": {"path": destination.name, "bytes": len(html.encode()), "sha256": sha(html.encode())},
        "embedded_figures": figures, "figure_count": len(figures),
        "mathematics": "Native MathML; no external renderer or scripts.",
        "source_text_modified": False,
        "presentation_transform": "Two title-heading attributes exclude front matter from contents; display equations receive accessible scroll containers; manuscript text unchanged.",
        "external_dependencies": [], "pandoc_stderr": result.stderr.strip(),
    }
    (HERE / "HTML_BUILD.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"output": receipt["output"], "figures": len(figures), "source_sha256": sha(raw)}))


if __name__ == "__main__":
    main()
