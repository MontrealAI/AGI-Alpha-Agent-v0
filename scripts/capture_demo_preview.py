#!/usr/bin/env python
# SPDX-License-Identifier: Apache-2.0
"""Record a short preview video of a demo using pyvirtualdisplay and ffmpeg."""
from __future__ import annotations

import argparse
import subprocess
import time
from pathlib import Path
import shlex
import sys

from pyvirtualdisplay import Display


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Capture demo preview")
    parser.add_argument(
        "demo",
        help="Path to the demo shell script or command to execute",
    )
    parser.add_argument(
        "-o",
        "--output",
        required=True,
        help="Output file (.mp4 or .gif)",
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=15,
        help="Duration to record in seconds (default: 15)",
    )
    parser.add_argument(
        "--size",
        default="1280x720",
        help="Virtual display size WxH (default: 1280x720)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    width, height = (int(x) for x in args.size.split("x", maxsplit=1))
    output = Path(args.output)

    temp_mp4 = output if output.suffix != ".gif" else output.with_suffix(".mp4")

    with Display(visible=False, size=(width, height)) as disp:
        display_var = f":{disp.display}"
        ffmpeg_cmd = [
            "ffmpeg",
            "-y",
            "-video_size",
            args.size,
            "-f",
            "x11grab",
            "-i",
            display_var,
            "-codec:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            str(temp_mp4),
        ]
        # Start ffmpeg first so it captures the entire run
        ffmpeg_proc = subprocess.Popen(ffmpeg_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            demo_cmd = shlex.split(args.demo)
        except ValueError as exc:
            print(f"Failed to parse demo command: {exc}", file=sys.stderr)
            ffmpeg_proc.terminate()
            ffmpeg_proc.wait()
            return 1
        try:
            demo_proc = subprocess.Popen(
                demo_cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except FileNotFoundError as exc:
            print(f"Failed to run demo: {exc}", file=sys.stderr)
            ffmpeg_proc.terminate()
            ffmpeg_proc.wait()
            return 1
        try:
            time.sleep(args.duration)
        finally:
            demo_proc.terminate()
            ffmpeg_proc.terminate()
            demo_proc.wait()
            ffmpeg_proc.wait()

    if output.suffix == ".gif":
        subprocess.run(["ffmpeg", "-y", "-i", str(temp_mp4), str(output)], check=True)
        temp_mp4.unlink(missing_ok=True)

    print(f"Saved preview to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
