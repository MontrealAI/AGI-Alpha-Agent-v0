# SPDX-License-Identifier: Apache-2.0
"""Flatten the complete manuscript text and bibliography; vector figures stay external."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent / "paper"


def expand(path: Path) -> str:
    text = path.read_text()
    return re.sub(r"\\input\{([^}]+)\}",
                  lambda m: expand(ROOT / (m.group(1) if m.group(1).endswith(".tex") else m.group(1) + ".tex")), text)


def main() -> None:
    text = expand(ROOT / "paper.tex")
    text = text.replace(r"\bibliographystyle{plainnat}", "")
    text = text.replace(r"\bibliography{references}", (ROOT / "paper.bbl").read_text())
    header = "% Convenience flattened source. Compile with XeLaTeX and the complete archive's paper/figures/ beside it.\n"
    target = ROOT / "AGI_ALPHA_The_Advantage_You_Can_Build.tex"
    target.write_text(header + text)
    print(target)


if __name__ == "__main__":
    main()
