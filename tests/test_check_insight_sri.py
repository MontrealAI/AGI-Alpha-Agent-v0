from pathlib import Path

import pytest

from scripts.check_insight_sri import _hash, check_directory


def test_accepts_uppercase_and_query_string(tmp_path: Path) -> None:
    bundle = tmp_path / "insight.bundle.js"
    bundle.write_text("console.log('hi');", encoding="utf-8")

    sri = _hash(bundle)
    html = tmp_path / "index.html"
    html.write_text(
        f"""
        <html>
          <body>
            <SCRIPT
              SRC="insight.bundle.js?v=123"
              INTEGRITY="{sri}"
              crossorigin="anonymous"
            ></SCRIPT>
          </body>
        </html>
        """,
        encoding="utf-8",
    )

    assert check_directory(tmp_path) == 0


def test_accepts_unquoted_src(tmp_path: Path) -> None:
    bundle = tmp_path / "insight.bundle.js"
    bundle.write_text("console.log('hi');", encoding="utf-8")

    sri = _hash(bundle)
    html = tmp_path / "index.html"
    html.write_text(
        f"""
        <html>
          <body>
            <script src=insight.bundle.js integrity="{sri}" crossorigin="anonymous"></script>
          </body>
        </html>
        """,
        encoding="utf-8",
    )

    assert check_directory(tmp_path) == 0


@pytest.mark.parametrize(
    "html_snippet",
    [
        '<html><body><script src="insight.bundle.js"></script></body></html>',
        '<html><body><script src="other.js" integrity="abc"></script></body></html>',
    ],
)
def test_missing_integrity_or_script_tag_fails(tmp_path: Path, html_snippet: str) -> None:
    bundle = tmp_path / "insight.bundle.js"
    bundle.write_text("console.log('hi');", encoding="utf-8")

    html = tmp_path / "index.html"
    html.write_text(html_snippet, encoding="utf-8")

    assert check_directory(tmp_path) == 1
