# SPDX-License-Identifier: Apache-2.0
"""Build the publication source twice and retain the compiler's actual output."""
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
for index in (1, 2):
    run = subprocess.run(
        ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", "AGI_ALPHA_Productive_Transfer.tex"],
        cwd=ROOT, capture_output=True, check=False,
    )
    (ROOT / f"latex-pass-{index}.txt").write_bytes(run.stdout + run.stderr)
    if run.returncode:
        raise SystemExit(f"LaTeX pass {index} failed; preserved compiler output")
print(json.dumps({"passes": 2, "pdf": "AGI_ALPHA_Productive_Transfer.pdf", "status": "COMPILED"}))
