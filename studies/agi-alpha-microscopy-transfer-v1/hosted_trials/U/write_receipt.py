#!/usr/bin/env python3
"""Write the honest receipt for the completed hosted trial execution."""
import json
from datetime import datetime, timezone
from pathlib import Path

out = Path(__file__).parent
started = datetime.fromisoformat("2026-10-27T17:42:18.110083+00:00")
finished = datetime.now(timezone.utc)
receipt = {
    "task": "Independent quantitative microscopy delivery",
    "configuration": "U",
    "started_utc": started.isoformat(),
    "finished_utc": finished.isoformat(),
    "observed_elapsed_seconds": (finished - started).total_seconds(),
    "tool_invocations": {
        "functions.exec_calls": 4,
        "nested_exec_command_calls": 4,
        "description": "Four execution batches, each with one functions.exec wrapper and one exec_command call. Eight calls if wrappers and nested calls are both counted."
    },
    "work_performed": [
        "Read only the supplied input inventory, TASK.md and cases.json.",
        "Read all 12 contracts; loaded every supplied array with NumPy; computed exact file SHA-256, actual label counts and coordinate summaries.",
        "Wrote and executed solve.py to generate answers.json. Wrote and executed verify.py using independent 70-digit Decimal calculations; all checks passed. Receipt creation then failed because the orchestration snippet lacked an import of json.",
        "Added the missing json import in a saved receipt writer, generated receipt.json and checked all required deliverables. No measurement outputs required correction."
    ],
    "correction_count": 1,
    "corrections_performed": [
        {"error": "NameError: name 'json' is not defined in the initial receipt-writing orchestration snippet.",
         "fix": "Created write_receipt.py with an explicit import json and executed it.",
         "affected_output": "receipt.json only; answers.json and verification.json had already been successfully generated."}
    ],
    "validation": json.loads((out / "verification.json").read_text()),
    "scientific_conventions": [
        "Every nonzero signed label ID is one region; zero is background.",
        "Index is voxel center; no half-voxel centroid offset.",
        "Spacing and origin converted per axis into micrometers.",
        "Native measure is voxel count times product of micrometer spacing.",
        "Mapped measure is native measure times absolute determinant of the linear affine block.",
        "Native centroids follow source_axes; mapped centroids follow target_axes without an extra permutation.",
        "Empty foreground accepted; unavailable metrics and unsupported mission semantics are not fabricated."
    ],
    "costs": {"tokens": None, "billing": None,
              "reason": "Token counts and billing are unavailable in this trial; neither was estimated."},
    "external_resources_used": [],
    "subagents_used": 0,
    "artifacts": ["answers.json", "solve.py", "verify.py", "verification.json", "write_receipt.py", "receipt.json"]
}
(out / "receipt.json").write_text(json.dumps(receipt, indent=2, allow_nan=False) + "\n")
for name in receipt["artifacts"]:
    path = out / name
    assert path.is_file() and path.stat().st_size > 0
    if path.suffix == ".json":
        json.loads(path.read_text())
    elif path.suffix == ".py":
        compile(path.read_text(), str(path), "exec")
print(json.dumps({"receipt_written": str(out / "receipt.json"),
                  "elapsed_seconds": receipt["observed_elapsed_seconds"],
                  "deliverable_files": receipt["artifacts"],
                  "validation": receipt["validation"]}))
