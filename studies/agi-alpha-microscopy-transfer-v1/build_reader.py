# SPDX-License-Identifier: Apache-2.0
"""Build the self-contained accessible paper reader from the final manuscript."""

from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main() -> None:
    """Render native MathML and embed the stylesheet and original study figures."""
    subprocess.run(
        [
            "pandoc",
            "manuscript.md",
            "--from=markdown",
            "--to=html5",
            "--standalone",
            "--metadata=title:AGI ALPHA FLYWHEEL — When Capability Creates Opportunity",
            "--mathml",
            "--embed-resources",
            "--toc",
            "--toc-depth=2",
            "--css=../browser/reader.css",
            "--template=../browser/reader-template.html",
            "--output=../browser/paper.html",
        ],
        cwd=ROOT / "paper",
        check=True,
    )
    print("Built a self-contained paper reader with native MathML and embedded figures.")


if __name__ == "__main__":
    main()
