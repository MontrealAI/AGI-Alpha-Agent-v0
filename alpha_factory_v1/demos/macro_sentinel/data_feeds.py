# SPDX-License-Identifier: Apache-2.0
# alpha_factory_v1/demos/macro_sentinel/data_feeds.py
# © 2025 MONTREAL.AI Apache-2.0 License
"""
Macro-Sentinel — Data Feeds
───────────────────────────
Bridges offline CSV snapshots *and* real-time APIs into a single async
generator that emits uniformly-shaped macro-events for the Orchestrator agent.

Highlights
----------
● Graceful degrade: zero-config offline mode falls back on CSVs bundled in
  `offline_samples/`.
● Multi-source live polling (FRED, Fed RSS, Etherscan, CME futures).
● Async HTTP via *aiohttp* to avoid blocking the agent loop.
● Optional publish hooks: TimescaleDB, Redis Streams, Qdrant vector store.
● All credentials pulled from `config.env`; no secrets in code.
"""

from __future__ import annotations

import asyncio
import csv
import ipaddress
import os
import pathlib
import datetime as dt
import re
from types import SimpleNamespace

try:  # aiohttp optional at test time
    import aiohttp
except ModuleNotFoundError:  # pragma: no cover - offline fallback
    aiohttp = None
try:  # feedparser optional at test time
    import feedparser
except ModuleNotFoundError:  # pragma: no cover - offline fallback
    feedparser = SimpleNamespace(parse=lambda _url: SimpleNamespace(entries=()))
from typing import AsyncIterator, Dict, Any, Optional, cast
from collections import deque
from urllib.parse import urlsplit
from urllib.request import urlopen

# Source snapshot revision for offline CSVs
# Update to match `DEMO_ASSETS_REV` in run_macro_demo.sh when refreshing
# offline samples.
DEMO_ASSETS_REV = os.getenv("DEMO_ASSETS_REV", "90fe9b623b3a0ae5475cf4fa8693d43cb5ba9ac5")

# ───────────────────────── Config from env ──────────────────────────
_DEFAULT_DATA_DIR = pathlib.Path(__file__).parent / "offline_samples"


def _data_dir() -> pathlib.Path:
    """Return offline CSV directory from env or default."""
    return pathlib.Path(os.getenv("OFFLINE_DATA_DIR", str(_DEFAULT_DATA_DIR)))


DATA_DIR = _data_dir()

FRED_KEY = os.getenv("FRED_API_KEY")
ETHERSCAN_KEY = os.getenv("ETHERSCAN_API_KEY")
RSS_URL = os.getenv("FED_RSS_URL", "https://www.federalreserve.gov/feeds/press_speeches.htm")
FRED_3M = os.getenv("FRED_SERIES_3M", "DTB3")
FRED_10Y = os.getenv("FRED_SERIES_10Y", "DGS10")
STABLE_TOKEN = os.getenv("STABLE_TOKEN", "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606e48")  # USDC
CME_SYMBOL = os.getenv("CME_SYMBOL", "ES")  # S&P 500 futures

# optional sinks
DB_URL = os.getenv("DATABASE_URL")  # Timescale/Postgres
REDIS_URL = os.getenv("REDIS_URL")
VEC_URL = os.getenv("VECTOR_HOST")  # Qdrant

# ───────────────────────── Helpers / offline CSV ────────────────────
OFFLINE_URLS = {
    "fed_speeches.csv": f"https://raw.githubusercontent.com/MontrealAI/demo-assets/{DEMO_ASSETS_REV}/fed_speeches.csv",
    "yield_curve.csv": f"https://raw.githubusercontent.com/MontrealAI/demo-assets/{DEMO_ASSETS_REV}/yield_curve.csv",
    "stable_flows.csv": f"https://raw.githubusercontent.com/MontrealAI/demo-assets/{DEMO_ASSETS_REV}/stable_flows.csv",
    "cme_settles.csv": f"https://raw.githubusercontent.com/MontrealAI/demo-assets/{DEMO_ASSETS_REV}/cme_settles.csv",
}

_DEFAULT_ROWS = {
    "fed_speeches.csv": {"text": "No speech"},
    "yield_curve.csv": {"3m": "4.5", "10y": "4.4"},
    "stable_flows.csv": {"usd_mn": "25"},
    "cme_settles.csv": {"settle": "5000"},
}


def _ensure_offline() -> None:
    offline_dir = _data_dir()
    offline_dir.mkdir(parents=True, exist_ok=True)
    for name, url in OFFLINE_URLS.items():
        path = offline_dir / name
        if path.exists():
            continue
        try:
            with urlopen(url, timeout=5) as r, open(path, "wb") as f:
                f.write(r.read())
        except Exception:
            # Create a minimal placeholder when the download fails
            row = _DEFAULT_ROWS[name]
            with open(path, "w", newline="") as f:
                writer = csv.DictWriter(f, row.keys())
                writer.writeheader()
                writer.writerow(row)


def _csv(name: str) -> list[dict[str, str]]:
    """Return rows from an offline CSV file."""
    with open(_data_dir() / name, newline="") as f:
        return list(csv.DictReader(f))


_ensure_offline()

OFF_FED = _csv("fed_speeches.csv")
OFF_YIELD = _csv("yield_curve.csv")
OFF_FLOW = _csv("stable_flows.csv")
OFF_CME = _csv("cme_settles.csv")  # snapshot of ES settles

# ───────────────────────── Async HTTP helpers ───────────────────────
_SESSION: Optional[aiohttp.ClientSession] = None


async def _session() -> aiohttp.ClientSession:
    """Return a shared aiohttp session or raise when unavailable."""
    global _SESSION
    if aiohttp is None:
        if os.getenv("LIVE_FEED", "0") == "1":
            raise RuntimeError("LIVE_FEED=1 requires the aiohttp package")
        raise RuntimeError("aiohttp is required for live mode")
    if _SESSION is None:
        _SESSION = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5))
    return _SESSION


async def _http_json(url: str) -> Any:
    """Return JSON from ``url`` using the shared session.

    Args:
        url: HTTP endpoint.

    Returns:
        Parsed JSON payload.
    """
    s = await _session()
    async with s.get(url) as r:
        r.raise_for_status()
        return await r.json()


async def _http_text(url: str) -> str:
    """Return raw text from ``url`` using the shared session."""
    s = await _session()
    async with s.get(url) as r:
        r.raise_for_status()
        return str(await r.text())


# ───────────────────────── Live fetchers ─────────────────────────────
async def _fred_latest(series: str) -> Optional[float]:
    """Return the most recent FRED observation for ``series``."""
    if not FRED_KEY:
        return None
    url = (
        "https://api.stlouisfed.org/fred/series/observations"
        f"?series_id={series}&api_key={FRED_KEY}&file_type=json"
        "&sort_order=desc&limit=1"
    )
    j = await _http_json(url)
    val = j["observations"][0]["value"]
    return float(val) if val not in {"", "."} else None


_CACHE_SPEECH: deque[str] = deque(maxlen=10)


async def _latest_fed_speech() -> Optional[str]:
    """Return the latest Fed speech title or ``None`` if unchanged."""
    await _session()  # early check so RuntimeError propagates when aiohttp is missing
    try:
        feed = feedparser.parse(RSS_URL)
        title = cast(Optional[str], feed.entries[0].title) if feed.entries else None
        if title and title not in _CACHE_SPEECH:
            _CACHE_SPEECH.append(title)
            return title
    except Exception:
        return None
    return None


async def _latest_stable_flow() -> Optional[float]:
    """Return USD transferred in the latest stablecoin transaction."""
    if not ETHERSCAN_KEY:
        return None
    url = (
        f"https://api.etherscan.io/api?module=account&action=tokentx"
        f"&contractaddress={STABLE_TOKEN}&page=1&offset=1&sort=desc"
        f"&apikey={ETHERSCAN_KEY}"
    )
    j = await _http_json(url)
    val = j["result"][0]["value"]
    return float(val) / 1e6


async def _latest_cme_settle() -> Optional[float]:
    """Return the latest futures price via the Deribit fallback."""
    # Deribit free endpoint as CME fallback
    try:
        url = f"https://www.deribit.com/api/v2/public/ticker?instrument_name={CME_SYMBOL}-PERPETUAL"
        j = await _http_json(url)
        return float(j["result"]["last_price"])
    except Exception:
        return None


# ───────────────────────── Optional fan-out sinks ────────────────────
def _safe(f: Any, *a: Any, **kw: Any) -> None:
    try:
        f(*a, **kw)
    except Exception:
        pass


def _push_db(evt: Dict[str, Any]) -> None:
    """Persist ``evt`` to TimescaleDB when configured."""
    if not DB_URL:
        return
    import psycopg2

    with psycopg2.connect(DB_URL) as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO macro_events " "(ts,speech,y10y,y3m,stable_flow,es_settle)" "VALUES (%s,%s,%s,%s,%s,%s)",
            (
                evt["timestamp"],
                evt["fed_speech"],
                evt["yield_10y"],
                evt["yield_3m"],
                evt["stable_flow"],
                evt["es_settle"],
            ),
        )


def _push_redis(evt: Dict[str, Any]) -> None:
    """Publish ``evt`` to a Redis stream when configured."""
    if not REDIS_URL:
        return
    import redis
    import json as _j

    r = redis.from_url(REDIS_URL)
    r.xadd("macro_stream", {"json": _j.dumps(evt)}, maxlen=10000)


def _qdrant_endpoint(target: str) -> str:
    """Validate an origin; bare external hosts use HTTPS, literal loopback HTTP.

    ``VECTOR_HOST`` accepts a host with an optional port or an HTTP(S) origin
    without a path, user information, query or fragment. Plain HTTP is limited
    to literal loopback addresses and exact ``localhost`` for local development.
    Hostnames are never resolved to grant the plaintext exception.
    """
    if (
        not target
        or len(target) > 2048
        or any(ord(char) <= 32 or ord(char) >= 127 for char in target)
        or any(char in target for char in "\\%?#@")
    ):
        raise ValueError("Invalid Qdrant target")
    try:
        parsed = urlsplit(target if "://" in target else "//" + target)
        host, port = parsed.hostname, parsed.port
    except ValueError as exc:
        raise ValueError("Invalid Qdrant target") from exc
    if (
        parsed.scheme not in {"", "http", "https"}
        or not parsed.netloc
        or not host
        or parsed.path
        or parsed.query
        or parsed.fragment
        or parsed.username is not None
        or parsed.password is not None
        or parsed.netloc.endswith(":")
        or port is not None
        and not 1 <= port <= 65535
    ):
        raise ValueError("Invalid Qdrant origin")
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        if (
            len(host) > 253
            or "[" in parsed.netloc
            or "]" in parsed.netloc
            or re.fullmatch(r"[0-9.]+", host)
            or any(not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label) for label in host.split("."))
        ):
            raise ValueError("Invalid Qdrant hostname") from None
        loopback = host == "localhost"
        authority = host
    else:
        if address.version == 6 and not re.fullmatch(r"\[[0-9a-fA-F:.]+\](?::[0-9]+)?", parsed.netloc):
            raise ValueError("Invalid Qdrant IPv6 authority")
        loopback = (
            address in ipaddress.ip_network("127.0.0.0/8")
            if address.version == 4
            else address == ipaddress.ip_address("::1")
        )
        authority = f"[{address.compressed}]" if address.version == 6 else str(address)
    scheme = parsed.scheme or ("http" if loopback else "https")
    if scheme == "http" and not loopback:
        raise ValueError("Qdrant HTTP requires a literal loopback target")
    if port is not None:
        authority += f":{port}"
    return f"{scheme}://{authority}/collections/macro/points"


def _push_qdrant(evt: Dict[str, Any]) -> None:
    """Insert ``evt`` into a validated Qdrant origin without following redirects.

    Transports that cannot disable redirects fail closed before sending.
    """
    if not VEC_URL:
        return
    endpoint = _qdrant_endpoint(VEC_URL)
    import af_requests as requests
    import hashlib
    import json as _j

    vec = hashlib.sha256(evt["fed_speech"].encode()).digest()[:8]
    payload = {"points": [{"id": evt["timestamp"], "vector": list(vec), "payload": evt}]}
    response = requests.put(
        endpoint,
        data=_j.dumps(payload),
        headers={"Content-Type": "application/json"},
        timeout=5,
        allow_redirects=False,
    )
    if 300 <= response.status_code < 400:
        raise ValueError("Qdrant redirects are refused")
    response.raise_for_status()


def _fanout(evt: Dict[str, Any]) -> None:
    """Send ``evt`` to all configured output sinks."""
    _safe(_push_db, evt)
    _safe(_push_redis, evt)
    _safe(_push_qdrant, evt)


# ───────────────────────── Main async generator ──────────────────────
async def stream_macro_events(live: bool = False) -> AsyncIterator[Dict[str, Any]]:
    """Yield macro events from offline CSVs or live APIs.

    Args:
        live: Pull from network sources when ``True``.

    Yields:
        Event dictionaries with timestamp, speech, yields, stable flow and ES settle.
    """
    idx = 0
    poll = float(os.getenv("POLL_INTERVAL_SEC", "15" if live else "1"))
    while True:
        evt: Dict[str, Any] = {"timestamp": dt.datetime.now(dt.timezone.utc).isoformat()}
        if live:
            speech = await _latest_fed_speech() or OFF_FED[idx]["text"]
            y10 = await _fred_latest(FRED_10Y) or float(OFF_YIELD[idx]["10y"])
            y3 = await _fred_latest(FRED_3M) or float(OFF_YIELD[idx]["3m"])
            flow = await _latest_stable_flow() or float(OFF_FLOW[idx]["usd_mn"])
            es = await _latest_cme_settle() or float(OFF_CME[idx]["settle"])
        else:
            speech = OFF_FED[idx]["text"]
            y10, y3 = float(OFF_YIELD[idx]["10y"]), float(OFF_YIELD[idx]["3m"])
            flow = float(OFF_FLOW[idx]["usd_mn"])
            es = float(OFF_CME[idx]["settle"])

        evt.update({"fed_speech": speech, "yield_10y": y10, "yield_3m": y3, "stable_flow": flow, "es_settle": es})
        _fanout(evt)
        yield evt
        idx = (idx + 1) % len(OFF_FED)
        await asyncio.sleep(poll)
