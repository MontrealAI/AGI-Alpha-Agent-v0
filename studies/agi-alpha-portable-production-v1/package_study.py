# SPDX-License-Identifier: Apache-2.0
"""Create an exact inventory and a self-contained study archive, excluding build caches."""
from pathlib import Path
import argparse
import hashlib
import json
import zipfile

ROOT=Path(__file__).resolve().parent
EXCLUDED_SUFFIXES={".aux",".log",".out",".toc",".pyc",".synctex.gz"}
EXCLUDED_NAMES={"MANIFEST.sha256","publication_receipt.json","publication_receipt.md"}


def files():
    return sorted(p for p in ROOT.rglob("*") if p.is_file()
                  and not p.is_symlink() and "__pycache__" not in p.parts
                  and not any(p.name.endswith(suffix) for suffix in EXCLUDED_SUFFIXES)
                  and p.name not in EXCLUDED_NAMES and p.suffix!=".zip")


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("output",type=Path,help="New ZIP path outside the study tree")
    args=parser.parse_args()
    output=args.output.resolve()
    if output.exists():raise SystemExit("Refusing existing archive; use a new name.")
    if output.with_suffix(".inventory.json").exists():raise SystemExit("Refusing existing inventory sidecar; use a new name.")
    if output.is_relative_to(ROOT):raise SystemExit("Archive must be outside the study tree.")
    members=files()
    records=[{"path":p.relative_to(ROOT).as_posix(),"bytes":p.stat().st_size,
              "sha256":hashlib.sha256(p.read_bytes()).hexdigest(),
              "git_blob_sha1":hashlib.sha1(b"blob "+str(p.stat().st_size).encode()+b"\0"+p.read_bytes()).hexdigest()}
             for p in members]
    manifest=ROOT/"MANIFEST.sha256"
    manifest.write_text("".join(f'{r["sha256"]}  {r["path"]}\n' for r in records))
    output.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(output,"x",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for p in [*members,manifest]:
            name=ROOT.name+"/"+p.relative_to(ROOT).as_posix()
            entry=zipfile.ZipInfo(name,date_time=(2026,10,28,0,0,0))
            entry.compress_type=zipfile.ZIP_DEFLATED
            entry.external_attr=0o100644<<16
            z.writestr(entry,p.read_bytes())
    with zipfile.ZipFile(output) as z:
        if z.testzip() is not None:raise SystemExit("ZIP CRC verification failed")
        for row in records:
            data=z.read(ROOT.name+"/"+row["path"])
            if hashlib.sha256(data).hexdigest()!=row["sha256"]:raise SystemExit("ZIP member mismatch")
    result={"archive":str(output),"file_count":len(records)+1,"uncompressed_bytes":sum(r["bytes"] for r in records)+manifest.stat().st_size,
            "archive_bytes":output.stat().st_size,"archive_sha256":hashlib.sha256(output.read_bytes()).hexdigest(),
            "manifest_sha256":hashlib.sha256(manifest.read_bytes()).hexdigest(),"members":records,
            "scope":"Post-execution delivery inventory. No scientific preregistration or digital-signature claim."}
    output.with_suffix(".inventory.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps({k:v for k,v in result.items() if k!="members"}))


if __name__=="__main__":main()
