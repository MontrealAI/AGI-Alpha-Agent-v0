# SPDX-License-Identifier: Apache-2.0
"""Read-only identity checks for the final review; not an efficacy evaluation."""
from __future__ import annotations

import datetime as dt
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
rows: list[dict] = []


def check(label, base, record, key="path", blob=None):
    path = base / record[key]
    result = {"group": label, "path": str(path.relative_to(ROOT)), "exists": path.is_file()}
    if path.is_file():
        body = path.read_bytes()
        digest = hashlib.sha256(body).hexdigest()
        result.update(sha256=digest, expectedSha256=record["sha256"],
                      sha256Matches=digest == record["sha256"], bytes=len(body))
        if "bytes" in record:
            result["bytesMatch"] = len(body) == record["bytes"]
        if blob:
            observed = hashlib.sha1(b"blob " + str(len(body)).encode() + b"\0" + body).hexdigest()
            result.update(gitBlob=observed, expectedGitBlob=record[blob], gitBlobMatches=observed == record[blob])
    rows.append(result)


specs = [
    ("protocol/candidate-freeze.json", "files", "."),
    ("protocol/followup-candidate-freeze.json", "files", "."),
    ("protocol/input-freeze.json", "tasks", "."),
    ("protocol/followup-input-freeze.json", "tasks", "."),
    ("protocol/execution-freeze.json", "files", "."),
    ("protocol/followup-execution-freeze.json", "files", "."),
    ("results/confirmation/campaign.json", "payloads", "."),
    ("results/followup/campaign.json", "payloads", "."),
    ("acceptance/TASK_ORACLE_FREEZE.json", "source_files", "acceptance"),
    ("acceptance-followup/TASK_ORACLE_FREEZE.json", "source_files", "acceptance-followup"),
    ("protocol/asset-B.json", "sourceClosure", "."),
    ("protocol/asset-C2.json", "sourceClosure", "."),
    ("vendor/native/SOURCE.json", "files", "vendor/native"),
    ("market/source-manifest.json", "files", "market/inherited"),
]
for document, key, base in specs:
    data = json.loads((ROOT / document).read_text())
    for item in data[key]:
        check(document, ROOT / base, item, blob="git_blob" if "git_blob" in item else None)

for document, base in [
    ("acceptance/source-identities.json", "acceptance"),
    ("acceptance-followup/source-identities-final.json", "acceptance-followup"),
]:
    for item in json.loads((ROOT / document).read_text()):
        check(document, ROOT / base, item, key="file", blob="git_blob")

document = "sources/literature/SOURCE_IDENTITIES.json"
for item in json.loads((ROOT / document).read_text())["files"]:
    check(document, ROOT / "sources/literature/upstream", item, key="local", blob="blob")

document = "publication/navigation-repair.json"
for item in json.loads((ROOT / document).read_text())["aliases"]:
    check(document, ROOT, item, key="original")
    check(document, ROOT, item, key="addedAlias")

for document in ["resources/accounting/final-asset-bindings.json", "market/production-followup.json"]:
    data = json.loads((ROOT / document).read_text())
    closure = data.get("source", data.get("evidenceClosure"))
    names = {
        "candidate": "protocol/followup-candidate-freeze.json",
        "execution": "protocol/followup-execution-freeze.json",
        "campaign": "results/followup/campaign.json",
        "independentAudit": "results/independent-followup-audit/summary.json",
        "verifier": "acceptance-followup/oracle/evaluate_handoff.py",
    }
    for key, path in names.items():
        check(document, ROOT, {"path": path, "sha256": closure[key]})
    for item in closure["assets"].values():
        check(document, ROOT, item)

for document in ["results/confirmation/campaign.json", "results/followup/campaign.json"]:
    data = json.loads((ROOT / document).read_text())
    is_followup = "/followup/" in document
    prefix = "followup-" if is_followup else ""
    for k, name in [("candidateFreezeSha256", "candidate"), ("inputFreezeSha256", "input")]:
        check(document, ROOT, {"path": f"protocol/{prefix}{name}-freeze.json", "sha256": data[k]})
    for item in data["attempts"]:
        task, arm = item["mission"], item["arm"]
        group = "followup" if is_followup else "confirmation"
        check(document, ROOT, {"path": f"results/{group}/{task}/{arm}/delivery/result.json", "sha256": item["resultSha256"]})

failures = [r for r in rows if not r["exists"] or not r.get("sha256Matches") or r.get("bytesMatch") is False or r.get("gitBlobMatches") is False]
report = {
    "schema": "agi-alpha-final-review-identity-check/v1",
    "checkedAt": dt.datetime.now(dt.UTC).isoformat(),
    "status": "PASS" if not failures else "FAIL",
    "checks": len(rows),
    "distinctPaths": len({r["path"] for r in rows}),
    "gitBlobChecks": sum("gitBlobMatches" in r for r in rows),
    "failures": failures,
    "rows": rows,
    "scope": "Read-only local consistency with retained freezes and source records. Does not authenticate original acquisition, test new outcomes, or independently verify external remote repositories.",
    "newCustomerJobs": 0,
    "frozenFilesModified": 0,
}
(OUT / "identity-check.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps({k: v for k, v in report.items() if k != "rows"}))
