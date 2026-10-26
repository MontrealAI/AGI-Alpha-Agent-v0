# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from typing import Any

from accept_dossier import STUDY, accept, read_dossier


class AcceptanceControls(unittest.TestCase):
    before: dict[str, Any]
    after: dict[str, Any]
    dossier: dict[str, Any]

    @classmethod
    def setUpClass(cls) -> None:
        directory = STUDY / "outputs/development-final-full"
        pack = json.loads((directory / "workbench-pack.json").read_text())
        cls.before = json.loads(pack["spec"]["inputs"]["oldSpec"])
        cls.after = json.loads(pack["spec"]["inputs"]["newSpec"])
        cls.dossier = json.loads((directory / "response-dossier.json").read_text())

    def rejected(self, edited: dict[str, Any]) -> None:
        with self.assertRaises(ValueError):
            accept(self.before, self.after, edited)

    def test_complete_development_dossier(self) -> None:
        result = accept(self.before, self.after, self.dossier)
        self.assertTrue(result["accepted"])
        self.assertEqual([result["oldNodes"], result["newNodes"], result["changes"]], [2408, 2413, 6])

    def test_missing_change(self) -> None:
        value = copy.deepcopy(self.dossier)
        value["changes"].pop()
        self.rejected(value)

    def test_extra_change(self) -> None:
        value = copy.deepcopy(self.dossier)
        extra = copy.deepcopy(value["changes"][0])
        extra["key"] = '["GET /invented 200",[]]'
        value["changes"].append(extra)
        self.rejected(value)

    def test_duplicate_change(self) -> None:
        value = copy.deepcopy(self.dossier)
        value["changes"].append(copy.deepcopy(value["changes"][0]))
        self.rejected(value)

    def test_forged_fact(self) -> None:
        value = copy.deepcopy(self.dossier)
        value["changes"][0]["newFacts"]["type"] = "boolean"
        self.rejected(value)

    def test_forged_pointer(self) -> None:
        value = copy.deepcopy(self.dossier)
        value["changes"][0]["newPointer"] = "#/definitions/unknown"
        self.rejected(value)

    def test_forged_reference_chain(self) -> None:
        value = copy.deepcopy(self.dossier)
        value["changes"][0]["newRefChain"] = []
        self.rejected(value)

    def test_wrong_inventory_count(self) -> None:
        value = copy.deepcopy(self.dossier)
        value["counts"]["new"]["nodes"] += 1
        self.rejected(value)

    def test_wrong_source_digest(self) -> None:
        value = copy.deepcopy(self.dossier)
        value["oldSourceDigest"] = "0" * 64
        self.rejected(value)

    def test_false_added_response(self) -> None:
        value = copy.deepcopy(self.dossier)
        value["addedResponses"].append("GET /invented 200")
        self.rejected(value)

    def test_unassessed_scope_removed(self) -> None:
        value = copy.deepcopy(self.dossier)
        value["unassessed"] = []
        value["counts"]["old"]["warnings"] = value["counts"]["new"]["warnings"] = 0
        self.rejected(value)

    def test_unassessed_location_removed(self) -> None:
        value = copy.deepcopy(self.dossier)
        value["unassessed"] = [row for row in value["unassessed"] if row["responseId"] != "GET /_ping 200"]
        for side in ["old", "new"]:
            value["counts"][side]["warnings"] = sum(row["side"] == side for row in value["unassessed"])
        self.rejected(value)

    def fragments(self, directory: Path) -> dict[str, Any]:
        content = json.dumps(self.dossier, ensure_ascii=False, separators=(",", ":")) + "\n"
        middle = len(content) // 2
        (directory / "dossier-part-1.txt").write_text(content[:middle])
        (directory / "dossier-part-2.txt").write_text(content[middle:])
        index = {
            "encoding": "utf8-json-fragments",
            "digest": hashlib.sha256(content.encode()).hexdigest(),
            "parts": ["dossier-part-1.txt", "dossier-part-2.txt"],
        }
        (directory / "response-dossier-index.json").write_text(json.dumps(index))
        return index

    def test_fragment_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            directory = Path(folder)
            self.fragments(directory)
            actual, files = read_dossier(directory)
            self.assertEqual(actual, self.dossier)
            self.assertEqual(len(files), 3)

    def test_fragment_digest_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            directory = Path(folder)
            self.fragments(directory)
            (directory / "dossier-part-1.txt").write_text(" ")
            with self.assertRaises(ValueError):
                read_dossier(directory)

    def test_missing_fragment(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            directory = Path(folder)
            self.fragments(directory)
            (directory / "dossier-part-2.txt").unlink()
            with self.assertRaises(ValueError):
                read_dossier(directory)

    def test_duplicate_fragment(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            directory = Path(folder)
            index = self.fragments(directory)
            index["parts"][1] = index["parts"][0]
            (directory / "response-dossier-index.json").write_text(json.dumps(index))
            with self.assertRaises(ValueError):
                read_dossier(directory)

    def test_fragment_traversal(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            directory = Path(folder)
            index = self.fragments(directory)
            index["parts"][0] = "../dossier-part-1.txt"
            (directory / "response-dossier-index.json").write_text(json.dumps(index))
            with self.assertRaises(ValueError):
                read_dossier(directory)

    def test_fragment_symlink(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            directory = Path(folder)
            self.fragments(directory)
            target = directory / "dossier-part-1.txt"
            target.unlink()
            target.symlink_to(directory / "dossier-part-2.txt")
            with self.assertRaises(ValueError):
                read_dossier(directory)

    def test_oversized_fragment(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            directory = Path(folder)
            self.fragments(directory)
            (directory / "dossier-part-1.txt").write_text("x" * 175001)
            with self.assertRaises(ValueError):
                read_dossier(directory)

    def test_ambiguous_direct_and_fragmented(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            directory = Path(folder)
            self.fragments(directory)
            (directory / "response-dossier.json").write_text(json.dumps(self.dossier))
            with self.assertRaises(ValueError):
                read_dossier(directory)


if __name__ == "__main__":
    unittest.main()
