# ABOUTME: Reads which checks failed in a finished "Build all" run and compares them with the known-failure list.
# ABOUTME: Upstream's own tree fails some of its checks; only a failure that is not on the list blocks a release.
from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Iterator, List, Set

KNOWN_FAILURES_FILE = Path(__file__).with_name("known_upstream_failures.txt")

# What a failure is about: a whole job (item: its failed steps), one unit test, or one printer's test slice.
KINDS = ("job", "test", "slice")

_TIMESTAMP = re.compile(r"^﻿?\d{4}-\d\d-\d\dT[\d:.]+Z ?")
# A line of ctest's list of failed tests: number, name, outcome in brackets, then the test's labels.
_FAILED_TEST = re.compile(r"^\s*\d+ - (?P<name>.+) \([^()]+\)(?:\s.*)?$")
_FAILED_SLICE = re.compile(r"^\[error\]\s+\[(?P<printer>[^\]]+)\]")


@dataclass(frozen=True, order=True)
class Failure:
    kind: str
    job: str
    item: str

    def __str__(self) -> str:
        return f"[{self.kind}] {self.job}" + (f": {self.item}" if self.item else "")


def parse_failed_tests(log: str) -> List[str]:
    """Return the names ctest lists under "The following tests FAILED:" in a job's log."""
    names: List[str] = []
    listing = False
    for message in _messages(log):
        if not listing:
            listing = message.strip() == "The following tests FAILED:"
            continue
        entry = _FAILED_TEST.match(message)
        if not entry:
            break
        names.append(entry.group("name"))
    return names


def parse_failed_slices(log: str) -> List[str]:
    """Return the "vendor / printer" of each test slice the slice check reports as an error."""
    printers: List[str] = []
    for message in _messages(log):
        entry = _FAILED_SLICE.match(message)
        if entry and entry.group("printer") not in printers:
            printers.append(entry.group("printer"))
    return printers


def failures_from(jobs: Iterable[dict], log_for: Callable[[int], str]) -> Set[Failure]:
    """Return the failures of a run, given its jobs and a way to fetch a failed job's log.

    A failed unit-test or slice-check job becomes one failure per test or printer its log names.
    Any other failed job, and one of those whose log names nothing, is a failure of the job itself.
    So is a job that ended any other way than passing or being skipped: cancelled, timed out,
    or not finished. Its checks did not pass, whatever its log says.
    """
    found: Set[Failure] = set()
    for job in jobs:
        conclusion = job.get("conclusion")
        if conclusion in ("success", "skipped"):
            continue
        name = job["name"]
        if conclusion != "failure":
            found.add(Failure("job", name, conclusion or "not finished"))
            continue
        kind, items = "job", []
        if name.endswith("/ Unit Tests"):
            kind, items = "test", parse_failed_tests(log_for(job["id"]))
        elif name.startswith("Slice check"):
            kind, items = "slice", parse_failed_slices(log_for(job["id"]))
        if items:
            found.update(Failure(kind, name, item) for item in items)
        else:
            failed_steps = [step["name"] for step in job.get("steps", []) if step.get("conclusion") == "failure"]
            found.add(Failure("job", name, "; ".join(failed_steps)))
    return found


def run_failures(run_id: str, repository: str) -> Set[Failure]:
    """Return the failures of a finished run on GitHub, read with the gh command."""
    listing = _gh(
        "api",
        "--paginate",
        f"repos/{repository}/actions/runs/{run_id}/jobs?per_page=100",
        "--jq",
        ".jobs[] | {id, name, conclusion, steps: [.steps[]? | {name, conclusion}]}",
    )
    jobs = [json.loads(line) for line in listing.splitlines() if line.strip()]
    return failures_from(
        jobs, lambda job_id: _gh("run", "view", str(run_id), "--repo", repository, "--job", str(job_id), "--log-failed")
    )


def load_known(path: Path) -> Set[Failure]:
    """Read the known-failure list: tab-separated kind, job and item per line; "-" for no item; "#" comments."""
    known: Set[Failure] = set()
    for number, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        fields = line.split("\t")
        if len(fields) != 3 or fields[0] not in KINDS:
            raise ValueError(f"{path}, line {number}: expected kind, job and item separated by tabs, with kind one of {KINDS}")
        known.add(Failure(fields[0], fields[1], "" if fields[2] == "-" else fields[2]))
    return known


def unlisted(found: Set[Failure], known: Set[Failure]) -> Set[Failure]:
    """The failures that are not on the list. Any of these blocks a release."""
    return found - known


def now_passing(found: Set[Failure], known: Set[Failure]) -> Set[Failure]:
    """The listed failures that did not happen, so the list can be trimmed."""
    return known - found


def _messages(log: str) -> Iterator[str]:
    """Yield each log line's message, without the job, step and timestamp gh puts before it."""
    for line in log.splitlines():
        yield _TIMESTAMP.sub("", line.split("\t", 2)[-1])


def _gh(*arguments: str) -> str:
    result = subprocess.run(["gh", *arguments], capture_output=True, text=True, errors="replace")
    if result.returncode != 0:
        raise RuntimeError(f"gh {' '.join(arguments[:3])} failed: {result.stderr.strip()}")
    return result.stdout
