# SPDX-License-Identifier: Apache-2.0
"""Read-only archive navigation audit, supplementary to the frozen endpoint."""
from pathlib import Path
import argparse
import hashlib
import json
import re


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--study", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    study = args.study.resolve()
    rows = []
    for tid in ["F01", "F02", "F03", "F04"]:
        for arm in "ABC":
            folder = study / "results/followup" / tid / arm
            pack = json.loads((folder / "workbench-pack.json").read_text())
            source_ref = next(json.loads(row["content"]) for row in pack["result"]["artifacts"] if row["name"] == "captured-source-reference.json")
            source_path = folder / source_ref["fullTask"]
            result_path = folder / source_ref["fullLocalResult"]
            reports = []
            for lang in ["en", "fr"]:
                report = folder / "delivery" / f"report-{lang}.md"
                for link in re.findall(r"\]\(([^)]+)\)", report.read_text()):
                    if "://" not in link and not link.startswith("#"):
                        reports.append({"language": lang, "link": link, "existsRelativeToReport": (report.parent / link).is_file()})
            raw = json.loads((folder / "delivery/raw-task.json").read_text())
            licenses = [{"locator": row["file"], "existsRelativeToAcquisitionCorpus": (study / "acceptance-followup" / row["file"]).is_file(),
                         "sha256Matches": hashlib.sha256((study / "acceptance-followup" / row["file"]).read_bytes()).hexdigest() == row["sha256"]}
                        for row in raw["licenseRecords"]]
            rows.append({"task": tid, "arm": arm, "workbenchInputLocator": source_ref["fullTask"],
                         "existsRelativeToWorkbenchPack": source_path.is_file(),
                         "resolvesWithinArchiveTo": str(source_path.resolve().relative_to(study)),
                         "workbenchLocalResultLocatorExists": result_path.is_file(),
                         "deliveryRawTaskExists": (folder / "delivery/raw-task.json").is_file(),
                         "deliveryRawTaskMatchesFrozenTask": raw == json.loads((study / "acceptance-followup/tasks" / f"{tid}.json").read_text()),
                         "reportLinks": reports, "licenseRecords": licenses})
    result = {"schema": "alpha-transfer-post-oracle-portability-audit/v1", "rows": rows,
              "brokenWorkbenchInputLocators": sum(not r["existsRelativeToWorkbenchPack"] for r in rows),
              "brokenCustomerReportLinks": sum(not link["existsRelativeToReport"] for r in rows for link in r["reportLinks"]),
              "missingOrChangedArchivedLicenses": sum(not x["existsRelativeToAcquisitionCorpus"] or not x["sha256Matches"] for r in rows for x in r["licenseRecords"]),
              "frozenCheckerCheckedAuxiliaryWorkbenchLocator": False,
              "effectOnFrozenEndpoint": "Frozen mechanical scores stay unchanged. The broader all-artifact-navigation claim is qualified; these same twelve auxiliary locator failures must be disclosed.",
              "strictEveryLocalReferenceAcceptance": {"A": 0, "B": 0, "C": 0},
              "completeCustomerInputUnavailable": False,
              "interpretation": "Consumer source is attached and all customer report links resolve. The auxiliary Workbench input pointer is one parent traversal short. This is a navigation defect, not changed source evidence or a changed binding verdict. No output or candidate repaired.",
              "licenseLocatorBase": "acceptance-followup; acquisition metadata locators are not standalone delivery-directory links",
              "absoluteMeterCommands": "Historical execution provenance. They are not portable commands to replay verbatim; use the repo-relative frozen runtime/evaluator entry points.",
              "originalOutputsModified": False}
    text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.out:
        with args.out.open("x") as handle:
            handle.write(text)
    else:
        print(text, end="")


if __name__ == "__main__":
    main()
