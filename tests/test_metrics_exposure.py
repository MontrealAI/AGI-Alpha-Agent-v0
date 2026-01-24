# SPDX-License-Identifier: Apache-2.0
import contextlib
import importlib
import os
from typing import Any, AsyncIterator, cast

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

os.environ.setdefault("API_TOKEN", "test-token")
os.environ.setdefault("API_RATE_LIMIT", "1000")
os.environ.setdefault("AGI_INSIGHT_ALLOW_INSECURE", "1")
os.environ.setdefault("NO_LLM", "1")

from alpha_factory_v1.core.interface import api_server as api_server


def test_new_metrics_present() -> None:
    api = importlib.reload(api_server)

    @contextlib.asynccontextmanager
    async def _noop_lifespan(_: Any) -> AsyncIterator[None]:
        yield

    api.app.router.lifespan_context = _noop_lifespan
    with TestClient(cast(Any, api.app)) as client:
        resp = client.get("/metrics")
        assert resp.status_code == 200
        text = resp.text
        assert "dgm_parents_selected_total" in text
        assert "dgm_children_admitted_total" in text
        assert "dgm_revives_total" in text
