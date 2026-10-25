from __future__ import annotations

import csv
import hashlib
import io
import json
import re
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def verify() -> dict:
    checks = 0

    def require(condition: bool, message: str) -> None:
        nonlocal checks
        checks += 1
        if not condition:
            raise AssertionError(message)

    def digest(data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()

    report = json.loads((HERE / "source-missions-report.json").read_text())
    commit = report["sourceCommit"]
    require(
        isinstance(commit, str)
        and re.fullmatch(r"[0-9a-f]{40}", commit) is not None
        and subprocess.check_output(["git", "cat-file", "-t", commit], cwd=ROOT, text=True).strip() == "commit",
        "recorded mission source commit is unavailable",
    )
    require(report["economics"]["completeAgentCost"] is None, "unobserved total cost must stay unknown")
    require(report["totalGuideComputeInvocations"] == 4, "two missions plus two actual workspace recomputations")
    methods, inputs = set(), set()
    for mission in report["missions"]:
        directory = HERE / mission["mission"]
        receipt = json.loads((directory / "receipt.json").read_text())
        result = json.loads((directory / "result.json").read_text())
        workspace = json.loads((directory / "workspace.json").read_text())
        manifest_data = (ROOT / receipt["sourceManifest"]).read_bytes()
        require(digest(manifest_data) == receipt["sourceManifestSha256"], "manifest identity differs")
        sources = json.loads(manifest_data)["sources"]
        inventories = []
        for file, side in [("declared-inventory.csv", "left"), ("observed-inventory.csv", "right")]:
            data = (directory / file).read_bytes()
            require(digest(data) == result[f"{side}Identity"]["sha256"], "CSV identity differs")
            require(len(data) == result[f"{side}Identity"]["bytes"], "CSV byte count differs")
            rows = list(csv.DictReader(io.StringIO(data.decode())))
            require(len(rows) == len(sources), "inventory rows missing")
            require(len({r["path"] for r in rows}) == len(rows), "inventory duplicate path")
            inventory = {r["path"]: r["sha256"] for r in rows}
            inventories.append(inventory)
        expected, actual = inventories
        require(expected == sources, "declared CSV differs from original manifest")
        for path, value in actual.items():
            data = (ROOT / path).read_bytes()
            require(digest(data) == value, "observed CSV differs from file")
            committed = subprocess.check_output(["git", "show", f"{commit}:{path}"], cwd=ROOT)
            require(data == committed, "source differs from recorded mission commit")
        changed = sorted(path for path in expected if expected[path] != actual[path])
        require(sorted(d["key"] for d in result["differences"]) == changed, "independent exact differences disagree")
        require(result["metrics"]["fieldDifferences"] == len(changed), "field-difference count disagrees")
        require(result["metrics"]["unmatchedRows"] == 0, "unexpected missing row")
        require(result["metrics"]["matchedPairs"] == len(sources), "matched pair count disagrees")
        require(result["resolution"]["automaticallyResolved"] is False, "source approval is not automatic")
        require(workspace["authority"] == "none", "workspace authority must stay empty")
        require(workspace["result"] == result, "workspace result differs")
        require(
            workspace["input"]["leftCsv"].encode() == (directory / "declared-inventory.csv").read_bytes(),
            "workspace declared input differs",
        )
        require(
            workspace["input"]["rightCsv"].encode() == (directory / "observed-inventory.csv").read_bytes(),
            "workspace observed input differs",
        )
        require(
            len(list(csv.DictReader(io.StringIO((directory / "differences.csv").read_text())))) == len(changed),
            "difference export differs",
        )
        require(
            len(list(csv.DictReader(io.StringIO((directory / "action-plan.csv").read_text())))) == len(changed),
            "action export differs",
        )
        require(receipt["connectedExecution"].startswith("NOT RUN"), "local Node cannot qualify connected executor")
        require(len(receipt["unknownCosts"]) >= 6, "unknown full-cost inventory missing")
        methods.add(receipt["retainedMethod"]["methodIdentity"])
        inputs.add(result["leftIdentity"]["sha256"])
    require(len(methods) == 1, "second mission changed executable identity")
    require(len(inputs) == 2, "second mission reused identical input")
    require(report["sourceFilesInspected"] == 32, "scope count differs")
    return {
        "schema": "productive-capability-source-mission-acceptance/v1",
        "accepted": True,
        "checks": checks,
        "failures": 0,
        "sourceCommit": commit,
        "implementation": (
            "Separately implemented Python CSV/hash acceptance; same-session authorship, "
            "not independent organizational custody"
        ),
        "conclusion": (
            "Both fresh manifest inventories reconcile exactly. "
            "Same unchanged guide used on two distinct source closures. "
            "No method superiority, capability expansion, complete monetary cost or connected execution demonstrated."
        ),
    }


if __name__ == "__main__":
    result = verify()
    (HERE / "source-missions-acceptance.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))
