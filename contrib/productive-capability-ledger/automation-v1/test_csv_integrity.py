from __future__ import annotations

import csv
import hashlib
import importlib.util
import io
import json
import shutil
import tempfile
import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
FIXTURE = HERE.parent / "completion-v4/runs/inventory-repair-replication"


def load_verifier(path: Path) -> Any:
    loader = SourceFileLoader("csv_integrity_verifier", str(path))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


VERIFIER = load_verifier(HERE / "verify-run.py")


def read_json(path: Path) -> Any:
    return json.loads(path.read_bytes())


def save_json(path: Path, value: Any) -> str:
    raw = (json.dumps(value) + "\n").encode()
    path.write_bytes(raw)
    return hashlib.sha256(raw).hexdigest()


def rehash(directory: Path, filenames: list[str]) -> None:
    complete = read_json(directory / "COMPLETE.json")
    for filename in filenames:
        digest = hashlib.sha256((directory / filename).read_bytes()).hexdigest()
        complete["artifacts"][filename] = digest
        for trace in complete["stages"]:
            if filename in trace["artifacts"]:
                trace["artifacts"][filename] = digest
                stage_name = "stage-" + trace["stage"] + ".json"
                complete["artifacts"][stage_name] = save_json(directory / stage_name, trace)
    save_json(directory / "COMPLETE.json", complete)


def mutate_csv(directory: Path, filename: str, field: str) -> None:
    with (directory / filename).open(newline="") as handle:
        reader = csv.DictReader(handle)
        fields = reader.fieldnames
        rows = list(reader)
    assert fields is not None and rows
    rows[0][field] = "incorrect-exported-value"
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=fields, quoting=csv.QUOTE_ALL, lineterminator="\r\n")
    writer.writeheader()
    writer.writerows(rows)
    (directory / filename).write_bytes(output.getvalue().encode())
    rehash(directory, [filename])


class CsvIntegrityTests(unittest.TestCase):
    def test_original_complete_fixture_still_passes(self) -> None:
        self.assertTrue(VERIFIER.verify(FIXTURE)["accepted"])

    def test_all_difference_export_fields_refuse_rehashed_corruption(self) -> None:
        fields = [
            "id",
            "occurrence",
            "action",
            "key",
            "kind",
            "leftRow",
            "rightRow",
            "field",
            "leftValue",
            "rightValue",
        ]
        for field in fields:
            with self.subTest(field=field), tempfile.TemporaryDirectory() as temporary:
                directory = Path(temporary) / "run"
                shutil.copytree(FIXTURE, directory)
                mutate_csv(directory, "differences.csv", field)
                with self.assertRaisesRegex(ValueError, "Download differs from independently reconstructed"):
                    VERIFIER.verify(directory)

    def test_all_action_export_fields_refuse_rehashed_corruption(self) -> None:
        fields = [
            "action",
            "exact_key",
            "type",
            "left_data_rows",
            "right_data_rows",
            "original_review_occurrences",
            "next_step",
        ]
        for field in fields:
            with self.subTest(field=field), tempfile.TemporaryDirectory() as temporary:
                directory = Path(temporary) / "run"
                shutil.copytree(FIXTURE, directory)
                mutate_csv(directory, "action-plan.csv", field)
                with self.assertRaisesRegex(ValueError, "Download differs from independently reconstructed"):
                    VERIFIER.verify(directory)

    def test_result_evidence_refs_cannot_be_laundered_with_a_matching_workspace(self) -> None:
        for target, field in [
            ("difference", "leftRow"),
            ("difference", "action"),
            ("action", "occurrences"),
            ("action", "leftRows"),
        ]:
            with self.subTest(target=target, field=field), tempfile.TemporaryDirectory() as temporary:
                directory = Path(temporary) / "run"
                shutil.copytree(FIXTURE, directory)
                result = read_json(directory / "result.json")
                row = result["differences"][0] if target == "difference" else result["resolution"]["actions"][0]
                row[field] = [999] if isinstance(row[field], list) else 999
                workspace = read_json(directory / "workspace.json")
                workspace["result"] = result
                save_json(directory / "result.json", result)
                save_json(directory / "workspace.json", workspace)
                rehash(directory, ["result.json", "workspace.json"])
                with self.assertRaisesRegex(ValueError, "Independent source"):
                    VERIFIER.verify(directory)

    def test_retained_embedded_action_csv_is_independently_reconstructed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary) / "run"
            shutil.copytree(FIXTURE, directory)
            result = read_json(directory / "result.json")
            result["resolution"]["actionsCsv"] = "unverified-retained-action-export\n"
            workspace = read_json(directory / "workspace.json")
            workspace["result"] = result
            save_json(directory / "result.json", result)
            save_json(directory / "workspace.json", workspace)
            rehash(directory, ["result.json", "workspace.json"])
            with self.assertRaisesRegex(ValueError, "Retained action CSV differs"):
                VERIFIER.verify(directory)


if __name__ == "__main__":
    unittest.main()
