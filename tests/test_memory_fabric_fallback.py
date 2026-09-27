# SPDX-License-Identifier: Apache-2.0
import importlib
import math
import os
import sys
import unittest
from unittest import mock


class TestMemoryFabricEmbedderFallback(unittest.TestCase):
    def test_hashing_path_when_deps_missing(self) -> None:
        os.environ.pop("OPENAI_API_KEY", None)
        sys.modules.pop("alpha_factory_v1.backend.memory_fabric", None)
        importlib.invalidate_caches()
        with mock.patch.dict(sys.modules, {"openai": None, "sentence_transformers": None}):
            memf = importlib.import_module("alpha_factory_v1.backend.memory_fabric")
            vec = memf._EMBED("text")
        self.assertEqual(len(vec), memf.CFG.VECTOR_DIM)
        norm = math.sqrt(sum(x * x for x in vec))
        self.assertAlmostEqual(norm, 1.0, places=5)


class TestMemoryFabricStorageSelection(unittest.TestCase):
    def test_disabled_remote_storage_never_constructs_a_client(self) -> None:
        memf = importlib.import_module("alpha_factory_v1.backend.memory_fabric")
        graph = mock.Mock()
        postgres = mock.Mock()
        with (
            mock.patch.object(memf.CFG, "NEO4J_URI", ""),
            mock.patch.object(memf.CFG, "PGHOST", ""),
            mock.patch.object(memf, "GraphDatabase", graph, create=True),
            mock.patch.object(memf, "psycopg2", postgres, create=True),
            memf.MemoryFabric() as fabric,
        ):
            self.assertNotEqual(fabric.graph._mode, "neo4j")
            self.assertNotEqual(fabric.vector._mode, "pg")
        graph.driver.assert_not_called()
        postgres.connect.assert_not_called()

    def test_configured_graph_storage_retains_its_existing_connection_path(self) -> None:
        memf = importlib.import_module("alpha_factory_v1.backend.memory_fabric")
        graph = mock.MagicMock()
        with (
            mock.patch.object(memf.CFG, "NEO4J_URI", "bolt://configured.invalid:7687"),
            mock.patch.object(memf, "GraphDatabase", graph, create=True),
        ):
            store = memf._GraphStore()
            self.assertEqual(store._mode, "neo4j")
        graph.driver.assert_called_once_with(
            "bolt://configured.invalid:7687", auth=(memf.CFG.NEO4J_USER, memf.CFG.NEO4J_PASSWORD)
        )
        graph.driver.return_value.session.return_value.__enter__.return_value.run.assert_called_once_with("RETURN 1")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
