"""Fetch the official CorefUD scorer at the revision pinned by this project."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

REPOSITORY = "https://github.com/ufal/corefud-scorer.git"
REVISION = "4fd7b0e0c661aeeff88bc60c19ef507b84d1b590"


def main() -> int:
    """Clone or verify the external scorer and check out the pinned revision."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", type=Path, default=Path("vendor/corefud-scorer"))
    args = parser.parse_args()
    target = args.target.resolve()
    if not target.exists():
        subprocess.run(["git", "clone", REPOSITORY, str(target)], check=True)
    subprocess.run(["git", "-C", str(target), "fetch", "--depth", "1", "origin", REVISION], check=True)
    subprocess.run(["git", "-C", str(target), "checkout", "--detach", REVISION], check=True)
    actual = subprocess.check_output(
        ["git", "-C", str(target), "rev-parse", "HEAD"], text=True
    ).strip()
    if actual != REVISION:
        raise RuntimeError(f"Expected {REVISION}, received {actual}")
    print(f"CorefUD scorer ready at {target} ({actual})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
