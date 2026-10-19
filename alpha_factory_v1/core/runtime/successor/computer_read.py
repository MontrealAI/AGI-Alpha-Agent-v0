# SPDX-License-Identifier: Apache-2.0
"""Credential-free, disposable public-document reader supervised by the native parent."""

from __future__ import annotations

import base64
import ipaddress
import json
import socket
import sys
from typing import Any
from urllib.parse import urlsplit

import httpx


def read_public(url: str, method: str, maximum: int) -> dict[str, Any]:
    """Keep public-IP pinning, TLS verification and byte accounting inside one disposable process."""
    received = 0
    try:
        parts = urlsplit(url)
        if (
            method not in {"GET", "HEAD"}
            or parts.scheme != "https"
            or not parts.hostname
            or parts.username
            or parts.password
            or parts.fragment
            or parts.port not in {None, 443}
            or len(url) > 2048
            or any(ord(character) < 33 or character == "\\" for character in url)
            or type(maximum) is not int  # noqa: E721
            or not 0 < maximum <= 1_500_000
        ):
            raise ValueError("unsupported public read")
        addresses = sorted({row[4][0] for row in socket.getaddrinfo(parts.hostname, 443, type=socket.SOCK_STREAM)})
        if not addresses or any(not ipaddress.ip_address(address).is_global for address in addresses):
            raise ValueError("private or nonpublic network destination")
        address = str(addresses[0])
        host = f"[{address}]" if ":" in address else address
        target = url.replace(parts.netloc, host, 1)
        with httpx.Client(timeout=8, trust_env=False, follow_redirects=False) as client:
            with client.stream(
                method, target, headers={"Host": parts.hostname}, extensions={"sni_hostname": parts.hostname}
            ) as response:
                if response.status_code != 200:
                    raise ValueError("public read requires an exact 200 response")
                content = bytearray()
                for part in response.iter_bytes(chunk_size=65_536):
                    received += len(part)
                    if received > maximum:
                        raise ValueError("network byte budget exhausted")
                    content.extend(part)
                content_type = response.headers.get("content-type", "application/octet-stream")
                if len(content_type) > 1024:
                    raise ValueError("network content-type exceeds its bound")
                return {
                    "bytes_read": received,
                    "response": {
                        "status": 200,
                        "content_type": content_type,
                        "body": base64.b64encode(content).decode("ascii"),
                    },
                }
    except Exception:
        return {"bytes_read": received, "error": "public read refused or failed"}


def main() -> None:
    """Accept one bounded parent request without inheriting tasks, profiles or credentials."""
    try:
        raw = sys.stdin.buffer.read(16_385)
        if len(raw) > 16_384:
            raise ValueError("oversized read request")
        value = json.loads(raw)
        if not isinstance(value, dict) or set(value) != {"url", "method", "maximum"}:
            raise ValueError("invalid read request")
        result = read_public(value["url"], value["method"], value["maximum"])
    except Exception:
        result = {"bytes_read": 0, "error": "public read refused or failed"}
    sys.stdout.write(json.dumps(result, separators=(",", ":")))


if __name__ == "__main__":
    main()
