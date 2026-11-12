# ABOUTME: Command line for the release tooling, run from the checkout a release is made from.
# ABOUTME: Usage: python3 -m semilayered.release gate|artifacts|collect|notes|tag|title ...   (each takes --help)
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import List, Optional

from semilayered.rebrand.regenerate import recorded_upstream_commit
from semilayered.release import assets, failures
from semilayered.release.notes import release_notes

REPOSITORY = "erikbuild/Semilayered-Slicer"
REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def main(arguments: Optional[List[str]] = None, root: Optional[Path] = None, run_failures=failures.run_failures) -> int:
    parser = argparse.ArgumentParser(prog="python3 -m semilayered.release")
    commands = parser.add_subparsers(dest="command", required=True)

    gate = commands.add_parser("gate", help="fail if a run has a failure that is not on the known-failure list")
    gate.add_argument("--run", required=True, help='id of a finished "Build all" run')
    gate.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY", REPOSITORY), help="owner/name on GitHub")

    collect = commands.add_parser("collect", help="gather a release's files from a run's downloaded artifacts")
    collect.add_argument("--artifacts", type=Path, required=True, help="directory holding one directory per artifact")
    collect.add_argument("--out", type=Path, required=True, help="empty or new directory to put the release's files in")

    commands.add_parser("artifacts", help="print the name of each artifact a release is made from")
    notes = commands.add_parser("notes", help="print the release notes for a build")
    tag = commands.add_parser("tag", help="print the release tag for a build")
    title = commands.add_parser("title", help="print the release title for a build")
    for command in (notes, tag, title):
        command.add_argument("--build", type=int, required=True, help='the run number of the "Build all" run')
    for command in (gate, notes):
        command.add_argument("--known", type=Path, default=failures.KNOWN_FAILURES_FILE, help="the known-failure list")

    options = parser.parse_args(arguments)
    root = root or REPOSITORY_ROOT
    if options.command == "gate":
        return _gate(options, run_failures)
    if options.command == "collect":
        return _collect(options, root)
    version = assets.upstream_version(root)
    if options.command == "artifacts":
        for artifact, _published in assets.expected_assets(version):
            print(artifact)
    elif options.command == "tag":
        print(assets.release_tag(version, options.build))
    elif options.command == "title":
        print(assets.release_title(version, options.build))
    else:
        known = failures.load_known(options.known)
        print(release_notes(version, options.build, recorded_upstream_commit(root), known), end="")
    return 0


def _gate(options, run_failures) -> int:
    known = failures.load_known(options.known)
    found = run_failures(options.run, options.repo)
    new = sorted(failures.unlisted(found, known))
    gone = sorted(failures.now_passing(found, known))
    if gone:
        print(f"Listed, but did not fail in this run ({len(gone)}):")
        for failure in gone:
            print(f"  {failure}")
    if new:
        print(f"Not on the known-failure list ({len(new)}):")
        for failure in new:
            print(f"  {failure}")
        return 1
    print(f"{len(found & known)} known failures occurred; nothing failed beyond the list.")
    return 0


def _collect(options, root: Path) -> int:
    try:
        collected = assets.collect(options.artifacts, options.out, assets.upstream_version(root))
    except (assets.MissingAsset, ValueError) as problem:
        print(f"collect failed: {problem}", file=sys.stderr)
        return 1
    for path in collected:
        print(path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
