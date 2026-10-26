# SPDX-License-Identifier: Apache-2.0
"""Create a closed LaTeX source bundle; no research, installation or network."""
from pathlib import Path
import argparse
import hashlib
import json
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--extract", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists() or args.extract.exists():
        parser.error("Use new output and extraction paths.")
    pub = ROOT / "publication"
    payloads = {
        p.relative_to(pub).as_posix(): p.read_bytes()
        for p in sorted(pub.glob("*.tex"))
    }
    payloads.update({
        p.relative_to(pub).as_posix(): p.read_bytes()
        for p in sorted((pub / "figures").glob("*.pdf"))
    })
    for name in ("toolchain.json", "figure-manifest.json",
                 "succession-figure-manifest.json", "finance-figure-source.json"):
        payloads[name] = (pub / name).read_bytes()
    payloads["LICENSE"] = (ROOT / "LICENSE").read_bytes()
    payloads["README.txt"] = (
        "THE PRICE OF PROGRESS — LATEX SOURCE EDITION\n\n"
        "From this directory, with the documented TeX toolchain installed:\n"
        "  pdflatex -interaction=nonstopmode -halt-on-error paper.tex\n"
        "  pdflatex -interaction=nonstopmode -halt-on-error paper.tex\n\n"
        "All input prose and finished vector figures are included. No market replay,\n"
        "network, credential, paid service or production activation is required.\n"
        "Scientific figure regeneration and complete financial/production audits use\n"
        "the separately supplied complete research companion, which includes the\n"
        "exact data, source scripts, frozen protocols and original failed paths.\n\n"
        "Financial outcomes are modeled. Discovery cost D remains unpriced. No actual\n"
        "customer collections or second tested capability are established.\n"
    ).encode()
    manifest = {
        "schema": "agialpha-latex-source-closure/v1",
        "payloads": [
            {"path": k, "bytes": len(v), "sha256": digest(v)}
            for k, v in sorted(payloads.items())
        ],
        "all_scientific_data_included": False,
        "complete_companion_required_for_figure_regeneration": True,
    }
    payloads["SOURCE_MANIFEST.json"] = (json.dumps(manifest, indent=2) + "\n").encode()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(args.output, "x", compression=zipfile.ZIP_DEFLATED,
                         compresslevel=9) as z:
        for name, data in sorted(payloads.items()):
            info = zipfile.ZipInfo("AGI_ALPHA_LaTeX/" + name, (2026, 10, 26, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            z.writestr(info, data)
    with zipfile.ZipFile(args.output) as z:
        assert z.testzip() is None
        assert len(z.infolist()) == len(payloads)
        z.extractall(args.extract)
    for name, data in payloads.items():
        assert (args.extract / "AGI_ALPHA_LaTeX" / name).read_bytes() == data
    print(json.dumps({"archive": str(args.output), "bytes": args.output.stat().st_size,
                      "sha256": digest(args.output.read_bytes()),
                      "files": len(payloads), "actual_extraction_verified": True,
                      "compile_root": str(args.extract / "AGI_ALPHA_LaTeX")}))


if __name__ == "__main__":
    main()
