# SPDX-License-Identifier: Apache-2.0
"""Stage a bounded additive public source selection; never call GitHub or git.

This selection deliberately omits large histories, wheels and most inherited
raw production bytes. It cannot substitute for the complete offline companion.
"""

from __future__ import annotations

import argparse
from fnmatch import fnmatchcase
import json
from pathlib import Path
import shutil
import sys

sys.dont_write_bytecode = True
from build_companion import (  # noqa: E402
    STUDY, SEALED_PATH, SEALED_SHA256, collect_inputs, digest, outside_study,
    utcnow, write_new_json,
)


ROOT_NAMES = {"README.md", "LICENSE", "LICENSE.txt", "LICENSE.md", "NOTICE", "NOTICE.md", "CITATION.cff"}
PATTERNS = (
    "protocol/*", "calibration/*", "market/README.md", "market/MODEL.md",
    "market/src/*", "market/tests/*", "market/canonical/*", "market/protocol/*",
    "market/development/*.json", "market/results/primary-command*",
    "market/results/primary-01/summary.csv", "market/results/primary-01/completion.json",
    "market/exploratory/*.mjs", "market/exploratory/*.md", "market/exploratory/*.json",
    "market/exploratory/*.log", "market/exploratory/results-01/summary.csv",
    "market/exploratory/results-01/completion.json",
    "market/exploratory/results-01/descriptive-findings.json",
    "market/exploratory/results-01/pricing-diagnostic-existing-histories.json",
    "market/policy-diagnostic/*.mjs", "market/policy-diagnostic/*.md",
    "market/policy-diagnostic/*.json", "market/policy-diagnostic/*.log",
    "market/policy-diagnostic/results-01/summary.csv",
    "market/policy-diagnostic/results-01/completion.json",
    "market/policy-diagnostic/results-01/descriptive-findings.json",
    "market/policy-diagnostic/results-01/diagnostic-findings.json",
    "market/reporting/*.mjs", "market/reporting/*.py", "market/reporting/*.md",
    "market/reporting/*.json", "market/reporting/*.log",
    "market/reporting/*.diff",
    "market/reporting/results-01/completion.json", "market/reporting/results-01/audit.json",
    "market/deployment-robustness/*.mjs", "market/deployment-robustness/*.py",
    "market/deployment-robustness/*.md", "market/deployment-robustness/*.json",
    "market/deployment-robustness/*.log", "market/deployment-robustness/*.diff",
    "market/deployment-robustness/results-01/summary.csv",
    "market/deployment-robustness/results-01/main-threshold-table.csv",
    "market/deployment-robustness/results-01/adverse-table.csv",
    "market/deployment-robustness/results-01/funding-availability-by-run.csv",
    "market/deployment-robustness/results-01/mechanism-comparisons.json",
    "market/deployment-robustness/results-01/completion.json",
    "market/deployment-robustness/results-01/descriptive-findings.json",
    "review/*.py", "review/*.mjs", "review/*.json", "review/*.md", "review/resources/*",
    "review/demo-qa/result.json", "review/demo-qa/failure-*.json",
    "review/production-relocation/receipt.json", "review/production-relocation/custody.json",
    "review/production-relocation/replay_one.py",
    "publication/*.py", "publication/*.cjs", "publication/*.mjs", "publication/*.js",
    "publication/*.tex", "publication/*.bib", "publication/*.md", "publication/*.json", "publication/*.csv",
    "publication/demo.template.html", "publication/figures/*", "figures/*",
    "deliverables/*.pdf", "deliverables/*.html", "packaging/*.py", "packaging/*.md",
    "tools/measured_run.py", "tools/meter-provenance.json",
    "production/packets/*.zip", "production/export-001/receipt.json",
    "production/export-001/independent-custody.json",
    "production/export-001/AGI_ALPHA_Upgrade_Decision_Packet.zip",
)
UPSTREAM_NOTICES = {
    "vendor/product/LICENSE", "vendor/product/contrib/upgrade_decision/NOTICES.md",
    "vendor/useful-work-v2/canonical/LICENSE.Alpha", "vendor/useful-work-v2/canonical/SOURCE.json",
    "vendor/useful-work-v2/native/LICENSE.Alpha", "vendor/useful-work-v2/native/SOURCE.json",
    "vendor/useful-work-v2/native/examples/build-successor/vendor/agijobs/LICENSE",
    "vendor/useful-work-v2/native/examples/build-successor/vendor/agijobs/provenance.json",
}
MAX_FILE_BYTES = 4 * 1024 * 1024
MAX_TOTAL_BYTES = 20 * 1024 * 1024


def wanted(path, production):
    if path.endswith((".jsonl", ".jsonl.gz", ".whl")):
        return False
    if path == "publication/representative-histories.json":
        return False
    if path in ROOT_NAMES or path in production or path in UPSTREAM_NOTICES or path == SEALED_PATH:
        return True
    # pathlib-style matching here limits * to one directory segment. This keeps
    # a compact review JSON rule from accidentally admitting every raw run.
    parts = path.split("/")
    return any(len(parts) == len(pattern.split("/")) and
               all(fnmatchcase(part, glob) for part, glob in zip(parts, pattern.split("/")))
               for pattern in PATTERNS)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, help="New staging directory outside study")
    parser.add_argument("--plan-only", action="store_true", help="Create only the selection manifest and boundary notice")
    args = parser.parse_args()
    destination = outside_study(args.out, "Public source staging directory")
    files, _ = collect_inputs()
    production = set(json.loads((STUDY / "production/PUBLICATION_SCOPE.json").read_text())["public_new_source_and_selected_evidence"])
    production.add("production/PUBLICATION_SCOPE.json")
    chosen = [row for row in files if wanted(row["path"], production)]
    oversized = [row["path"] for row in chosen if row["bytes"] > MAX_FILE_BYTES]
    if oversized:
        raise ValueError("Review public selection files exceeding 4 MiB: " + ", ".join(oversized))
    total = sum(row["bytes"] for row in chosen)
    if total > MAX_TOTAL_BYTES:
        raise ValueError("Public selection exceeds the declared 20 MiB bound")
    destination.mkdir(parents=True, exist_ok=False)
    if not args.plan_only:
        for row in chosen:
            target = destination / row["path"]
            target.parent.mkdir(parents=True, exist_ok=True)
            with (STUDY / row["path"]).open("rb") as source, target.open("xb") as output:
                shutil.copyfileobj(source, output)
            if digest(target) != {"bytes": row["bytes"], "sha256": row["sha256"]}:
                raise ValueError(f"Public source copy differs: {row['path']}")
    boundary = (
        "# Public source selection — not a standalone offline companion\n\n"
        "This additive research source selection preserves new code, frozen protocols, calibration sources, selected outcomes, paper, demo and upstream copyright notices. It omits the complete campaign cash/event histories, wheel binaries and most inherited raw production evidence. A checkout of this selection alone cannot reproduce the production extension or fully audit all original histories. Use the separately provided complete companion for those operations.\n\n"
        "The self-contained HTML includes the four executed decision packets and works without installation. The market core and tests use the included unchanged canonical modules under installed Node.js. The paper PDF is directly readable; its source rebuild needs the documented TeX toolchain. Original source provenance is preserved, and upstream sources retain their own licenses.\n\n"
        "From this source directory, installed Node.js is sufficient for these controls:\n\n"
        "```sh\nnode market/tests/test_market.mjs\nnode market/deployment-robustness/test-funding.mjs\nnode review/audit.mjs\n```\n\n"
        "The funding helper is a read-only view of supplied account histories. It does not create money, alter the frozen investment policy or admit a second asset. Full campaign replay/audit and production replay require the complete companion's preserved history/input closure, including wheels where applicable. Figure regeneration also needs the complete recorded data; finished figures and the PDF are included here.\n\n"
        "This directory is prepared for review. Creating a GitHub commit or pull request is a separate publication action. It does not replace any repository CI/release requirements and is not permission to run a held deployment or operator profile.\n"
    )
    (destination / "PUBLIC_SOURCE_NOT_OFFLINE_COMPLETE.md").write_text(boundary)
    manifest = {
        "schema": "agialpha-bounded-public-source-selection/v1", "created_at": utcnow(),
        "public_source_is_standalone_offline_companion": False,
        "plan_only": args.plan_only, "selected_files": len(chosen), "selected_bytes": total,
        "limits": {"per_file_bytes": MAX_FILE_BYTES, "total_bytes": MAX_TOTAL_BYTES},
        "sealed_production_manifest_sha256": SEALED_SHA256,
        "upstream_research_commit": "068e276fb9cd457c76ef5f8eaebf91b302d70d24",
        "upstream_product_commit": "269af6f9dd8d511fc387d0cecdff62a88ea96b02",
        "upstream_native_commit": "eb07086ac42799ff45f7b1c946a2f7c514bd3bbc",
        "files": chosen,
        "omitted": ["Full .jsonl/.jsonl.gz campaigns, cash histories, competitor accounting supplement and the 5 MiB publication representative-history export", "Wheels and disposable environments", "Most inherited raw production bytes; immutable source references retained", "Browser screenshots and extraction duplicates"],
        "publication_action_performed": False,
    }
    write_new_json(destination / "PUBLIC_SOURCE_SELECTION.json", manifest)
    print(json.dumps({"staging_directory": str(destination), "plan_only": args.plan_only,
                      "selected_files": len(chosen), "selected_bytes": total,
                      "public_source_is_standalone_offline_companion": False,
                      "publication_action_performed": False}))


if __name__ == "__main__":
    main()
