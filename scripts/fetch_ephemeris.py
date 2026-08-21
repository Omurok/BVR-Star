#!/usr/bin/env python3
"""Download the two pinned Swiss Ephemeris files used by BVR-Star."""

from __future__ import annotations

import argparse
import hashlib
import os
import tempfile
import urllib.request
from pathlib import Path

FILES = {
    "sepl_18.se1": (
        "https://raw.githubusercontent.com/aloistr/swisseph/master/ephe/sepl_18.se1",
        "ca1393ceab3a44fbc895887cf789c68819ae6a1cbc9b22225872dbe4ccd99a66",
    ),
    "semo_18.se1": (
        "https://raw.githubusercontent.com/aloistr/swisseph/master/ephe/semo_18.se1",
        "1ca07bd67c24374d77226180c20a4f9996cba013697894810518e7eb582ca4f7",
    ),
}


def digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def fetch(target_dir: Path) -> None:
    target_dir.mkdir(parents=True, exist_ok=True)
    for filename, (url, expected) in FILES.items():
        target = target_dir / filename
        if target.is_file() and digest(target) == expected:
            continue
        descriptor, temporary_name = tempfile.mkstemp(prefix=f".{filename}.", dir=target_dir)
        os.close(descriptor)
        temporary = Path(temporary_name)
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "BVR-Star/0.1"})
            with urllib.request.urlopen(request, timeout=60) as response, temporary.open("wb") as out:
                while block := response.read(1024 * 1024):
                    out.write(block)
            actual = digest(temporary)
            if actual != expected:
                raise RuntimeError(f"SHA-256 mismatch for {filename}: {actual}")
            temporary.replace(target)
        finally:
            temporary.unlink(missing_ok=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("destination", nargs="?", type=Path)
    parser.add_argument("--output", dest="output", type=Path)
    arguments = parser.parse_args()
    destination = arguments.output or arguments.destination or Path("ephe")
    fetch(destination)
