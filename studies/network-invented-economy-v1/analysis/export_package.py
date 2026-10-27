# SPDX-License-Identifier: Apache-2.0
"""Package immutable research evidence separately from the additive source release."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
RAW_RESULT_NAMES = {
    "training_runs.jsonl", "confirmation_runs.jsonl", "confirmation_ledgers.jsonl.gz",
    "sensitivity_runs.jsonl", "ablation_runs.json", "demo_data.json", "development-central.json",
    "publication_analysis_stdout.json",
}


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024*1024), b""):
            h.update(chunk)
    return h.hexdigest()


def record(path):
    return {"path": str(path.relative_to(ROOT)), "bytes": path.stat().st_size, "sha256": digest(path)}


def write_zip(destination, paths, notes):
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        raise RuntimeError(f"Archive already exists: {destination}")
    manifest = [record(p) for p in paths]
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for p, entry in zip(paths, manifest):
            info = zipfile.ZipInfo(entry["path"], date_time=(2026,10,27,0,0,0))
            info.compress_type = zipfile.ZIP_STORED if p.suffix in {".gz", ".pdf", ".png"} else zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, p.read_bytes())
        archive.writestr("ARCHIVE_README.txt", notes)
        archive.writestr("ARCHIVE_CONTENTS.json", json.dumps(manifest, indent=2, sort_keys=True)+"\n")
    with zipfile.ZipFile(destination) as archive:
        assert archive.testzip() is None
        for entry in manifest:
            assert hashlib.sha256(archive.read(entry["path"])).hexdigest() == entry["sha256"]
    return {"filename":destination.name,"bytes":destination.stat().st_size,"sha256":digest(destination),"entries":manifest}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--data-out",type=Path,required=True)
    parser.add_argument("--source-out",type=Path,required=True)
    parser.add_argument("--manifest",type=Path,default=ROOT/"publication/package_manifest.json")
    args=parser.parse_args()
    data=[]
    for p in (ROOT/"results").rglob("*"):
        if p.is_file() and "__pycache__" not in p.parts and p.suffix in {".json", ".jsonl", ".gz"}:
            data.append(p)
    for p in (ROOT/"evidence/development").rglob("*"):
        if p.is_file() and p.suffix in {".json", ".jsonl"}:
            data.append(p)
    for name in ("mechanism_witness.json","graph_demo.json","modeled_admission.json",
                 "native_accounting_check.json","native_confirmed_projection.json"):
        data.append(ROOT/"evidence"/name)
    data=sorted(set(data))
    assert ROOT/"results/confirmation_ledgers.jsonl.gz" in data
    source=[]
    for folder in ("src","tests","integration","analysis","sources","vendor","demo","evidence","paper"):
        for p in (ROOT/folder).rglob("*"):
            if not p.is_file() or "__pycache__" in p.parts or "build" in p.parts:
                continue
            if p.suffix in {".pyc", ".log", ".aux", ".out", ".bbl", ".blg"}:
                continue
            rel=p.relative_to(ROOT)
            if rel.parts[:2]==("evidence","development") and p in data:
                continue
            source.append(p)
    for p in (ROOT/"results").glob("*"):
        if p.is_file() and p.name not in RAW_RESULT_NAMES:
            source.append(p)
    # Keep review text; exclude the generated manifest to avoid a self-referential archive.
    source.extend(sorted((ROOT/"publication").glob("*.md")))
    source.extend(ROOT/name for name in ("README.md","LICENSE","requirements.txt"))
    source=sorted(set(source))
    for name, expected in json.loads((ROOT/"results/protocol_freeze.json").read_text())["source_hashes"].items():
        assert ROOT/name in source and digest(ROOT/name)==expected
    notes=("AGI ALPHA FLYWHEEL — PROFITABLE WORK FIRST. COMPOUNDING CAPABILITY WHEN WORTHWHILE.\n"
           "Independent coordination-mechanism foundry study; evidence cutoff 2026-10-26.\n"
           "Commercial-first reporting amendment 2026-10-27; frozen scientific protocol and results unchanged.\n"
           "Conditional modeled Beta profitability; optional enterprise Alpha remains unestablished.\n"
           "Commerce and paid jobs are modeled. Graph identity and authority use research fixtures.\n"
           "Local mathematics, cryptography, lifecycle and accounting checks are actual software executions.\n"
           "6,048 modeled histories: 2,304 training, 768 confirmation, 2,736 sensitivity, 240 ablation.\n"
           "Extract this archive at the study root; source and evidence archives share relative paths.\n"
           "ARCHIVE_CONTENTS.json binds every included entry by SHA-256.\n"
           "The source release supplies executable methods, tests, calibration, paper and EN/FR demo.\n"
           "The data archive supplies every primary ledger and all raw result streams.\n"
           "Publication review text is included in the source archive; publication/package_manifest.json is external.\n"
           "No live ENS, deployed service or realized sales; no Node22 native or browser visual qualification.\n"
           "Supplied manuscripts are cited/hashed and are not redistributed. No credentials or private clients.\n")
    result={"schema":"research-package-release/1", "source":write_zip(args.source_out,source,notes),
            "evidence":write_zip(args.data_out,data,notes),
            "protocol_sha256":digest(ROOT/"results/protocol_freeze.json"),
            "claims":"Conditional modeled Beta profitability; enterprise Alpha unestablished in primary confirmation.",
            "reporting_amendment":{"date":"2026-10-27",
                                   "path":"evidence/REPORTING_AMENDMENT_20261027.md",
                                   "scientific_protocol_changed":False},
            "source_publication_namespace":"studies/network-invented-economy-v1"}
    args.manifest.parent.mkdir(parents=True,exist_ok=True)
    args.manifest.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print(json.dumps({k:{n:v for n,v in result[k].items() if n!='entries'} for k in ('source','evidence')},indent=2))


if __name__=="__main__":
    main()
