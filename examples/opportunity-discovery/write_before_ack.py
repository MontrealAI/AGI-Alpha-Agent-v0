# SPDX-License-Identifier: Apache-2.0
"""Authored local fault fixture: durable effect, deliberately lost acknowledgement."""

import json
import os
import sys
from pathlib import Path

request = json.loads(sys.stdin.read(16_385))
if set(request) != {"output", "content"} or len(request["content"].encode()) > 4096:
    raise ValueError("bounded authored fixture required")
with Path(request["output"]).open("xb") as stream:
    stream.write(request["content"].encode())
    stream.flush()
    os.fsync(stream.fileno())
os._exit(23)
