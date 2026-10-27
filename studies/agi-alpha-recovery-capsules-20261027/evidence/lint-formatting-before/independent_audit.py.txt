# SPDX-License-Identifier: Apache-2.0
import argparse, ast, hashlib, json
from pathlib import Path

def audit(base):
    rows=[]
    for row in json.loads((base/"inputs/confirmation/source_manifest.json").read_text())["cases"]:
        name=Path(row["name"]).stem
        inp=base/"inputs/confirmation"/row["name"]
        out=base/"deliveries"/name/"recovered.ipynb"
        identity=json.loads((out.parent/"identity.json").read_text())
        changes=json.loads((out.parent/"changes.json").read_text())
        a,b=json.loads(inp.read_text()),json.loads(out.read_text())
        changed=[i for i,(x,y) in enumerate(zip(a["cells"],b["cells"])) if x["source"]!=y["source"]]
        declared={x["cell"] for x in changes}
        checks={
            "input_sha":hashlib.sha256(inp.read_bytes()).hexdigest()==identity["input_sha256"]==row["code_only_sha256"],
            "output_sha":hashlib.sha256(out.read_bytes()).hexdigest()==identity["output_sha256"],
            "code_cell_count":len(a["cells"])==len(b["cells"])==row["code_cells"],
            "original_code_cell_indices":all(x["metadata"]["upstream_cell_index"]==y["metadata"]["upstream_cell_index"] for x,y in zip(a["cells"],b["cells"])),
            "no_prose_or_stored_output":all(x["cell_type"]=="code" and not x.get("outputs") for x in b["cells"]),
            "all_edits_declared":set(changed)==declared
        }
        rows.append({"case":name,"checks":checks,"changed_cells":changed,"declared_changed_cells":sorted(declared),"accepted":all(checks.values())})
    csv_bytes=(base/"inputs/iris.csv").read_bytes()
    provenance=json.loads((base/"inputs/iris-provenance.json").read_text())
    notebook=json.loads((base/"deliveries/05.02-Introducing-Scikit-Learn/recovered.ipynb").read_text())
    source=notebook["cells"][0]["source"]
    source="".join(source) if isinstance(source,list) else source
    assignment=next(node for node in ast.walk(ast.parse(source)) if isinstance(node,ast.Assign) and any(isinstance(target,ast.Name) and target.id=="_iris_source_csv" for target in node.targets))
    embedded=ast.literal_eval(assignment.value).encode()
    data_checks={
        "frozen_csv_sha256":hashlib.sha256(csv_bytes).hexdigest()==provenance["sha256"],
        "frozen_csv_git_blob":hashlib.sha1(b"blob "+str(len(csv_bytes)).encode()+b"\0"+csv_bytes).hexdigest()==provenance["git_blob_sha"],
        "embedded_fixture_exact":embedded==csv_bytes
    }
    return {"schema":"independent-identity-audit/v1","cases":rows,"data_checks":data_checks,"accepted":all(row["accepted"] for row in rows) and all(data_checks.values())}

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("study",type=Path)
    p.add_argument("--output",type=Path)
    args=p.parse_args()
    result=audit(args.study)
    if args.output: args.output.write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps({"accepted":result["accepted"],"cases":len(result["cases"])}))
    raise SystemExit(0 if result["accepted"] else 1)
