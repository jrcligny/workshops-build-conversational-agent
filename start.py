#!/usr/bin/env python3
"""Cross-platform bootstrap: stdlib only, works before the kit is installed."""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main(argv=None):
    parser = argparse.ArgumentParser(description="Install and start all workshop services.")
    parser.add_argument("--port-offset", type=int, default=0, help="Shift all six default ports")
    parser.add_argument("--reset-data", action="store_true", help="Discard existing business data and rebuild the index")
    args = parser.parse_args(argv)
    if not 0 <= args.port_offset <= 57455:
        parser.error("--port-offset must be between 0 and 57455")
    uv = shutil.which("uv")
    if uv is None:
        print("uv is required. Install it from https://docs.astral.sh/uv/", file=sys.stderr)
        return 1
    # Do not let an unrelated active environment influence project selection.
    env = {key: value for key, value in os.environ.items() if key != "VIRTUAL_ENV"}
    commands = [
        [uv, "sync", "--extra", "dev", "--locked"],
        [uv, "run", "--no-sync", "workshop", "serve", "--port-offset", str(args.port_offset)],
    ]
    if args.reset_data:
        commands[-1].append("--reset-data")
    try:
        for command in commands:
            result = subprocess.run(command, cwd=ROOT, env=env, check=False)
            if result.returncode:
                return result.returncode
    except KeyboardInterrupt:
        # The foreground launcher also receives Ctrl+C and stops its services.
        return 130
    except OSError as exc:
        print(f"Cannot start the workshop: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())