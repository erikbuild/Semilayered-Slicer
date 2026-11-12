# ABOUTME: Command line for the rebrand tool, run from anywhere inside the repository.
# ABOUTME: Usage: python3 -m semilayered.rebrand regenerate [upstream-ref] | check
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import List, Optional

from semilayered.rebrand import table as default_table
from semilayered.rebrand.checks import (
    differences_from_regeneration,
    kept_identifier_drift,
    leftover_product_names,
    upstream_brand_images,
)
from semilayered.rebrand.edits import EditMismatch
from semilayered.rebrand.regenerate import DirtyTree, recorded_upstream_commit, regenerate
from semilayered.rebrand.tree import ArtworkWithoutTarget, PathCollision

# A broken tree can produce thousands of findings; the first ones are enough to see what is wrong.
FINDINGS_SHOWN = 100


def repository_root() -> Path:
    found = subprocess.run(["git", "rev-parse", "--show-toplevel"], check=True, capture_output=True, text=True)
    return Path(found.stdout.strip())


def main(arguments: Optional[List[str]] = None, root: Optional[Path] = None, table=default_table) -> int:
    parser = argparse.ArgumentParser(prog="python3 -m semilayered.rebrand")
    commands = parser.add_subparsers(dest="command", required=True)
    regenerate_command = commands.add_parser(
        "regenerate", help="rebuild the working tree from an upstream commit; stages everything, commits nothing"
    )
    regenerate_command.add_argument(
        "ref", nargs="?", help="upstream commit or ref; defaults to the one the tree was last generated from"
    )
    commands.add_parser("check", help="verify that the tree is exactly what regenerate produces")
    options = parser.parse_args(arguments)

    root = root or repository_root()
    if options.command == "regenerate":
        return _regenerate(root, options.ref, table)
    return _check(root, table)


def _regenerate(root: Path, ref: Optional[str], table) -> int:
    try:
        commit = regenerate(root, ref, table)
    except (DirtyTree, EditMismatch, PathCollision, ArtworkWithoutTarget) as problem:
        print(f"regenerate failed: {problem}", file=sys.stderr)
        return 1
    print(f"Regenerated from upstream commit {commit}.")
    print("Everything is staged and nothing is committed. Review with: git status; git diff --cached --stat")
    return 0


def _check(root: Path, table) -> int:
    try:
        commit = recorded_upstream_commit(root)
    except FileNotFoundError:
        print("check failed: semilayered/upstream_commit does not exist yet; run regenerate first", file=sys.stderr)
        return 1
    sections = [
        ("Product name left in the tree", leftover_product_names(root, table)),
        ("Kept identifiers whose count changed", kept_identifier_drift(root, commit, table)),
        ("Upstream brand images still in the tree", upstream_brand_images(root, commit, table)),
        ("Differences from a fresh regeneration", differences_from_regeneration(root, commit, table)),
    ]
    failed = False
    for title, findings in sections:
        if not findings:
            continue
        failed = True
        print(f"{title} ({len(findings)}):")
        for finding in findings[:FINDINGS_SHOWN]:
            print(f"  {finding}")
        if len(findings) > FINDINGS_SHOWN:
            print(f"  ... and {len(findings) - FINDINGS_SHOWN} more")
    if failed:
        return 1
    print(f"The tree is a pure regeneration of upstream commit {commit}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
