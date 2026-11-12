# ABOUTME: Writes the notes published with each release of Semilayered Slicer.
# ABOUTME: They say what the build is, which upstream commit it comes from, how to open it, and which checks it fails.
from __future__ import annotations

from typing import Dict, List, Set

from semilayered.release.assets import asset_descriptions
from semilayered.release.failures import Failure

_UNIT_TESTS_SUFFIX = " / Unit Tests"


def release_notes(version: str, build: int, upstream_commit: str, known: Set[Failure]) -> str:
    """Return the notes, in Markdown, for one build of one upstream version."""
    files = "\n".join(f"| {description} | `{published}` |" for published, description in asset_descriptions(version))
    notes = f"""\
**Semilayered Slicer {version} (build {build}) is an unofficial build of Unlayered Slicer {version}.** It is not affiliated with or endorsed by Unlayered 3D. It is provided as is, without support. Please do not report problems with it to Unlayered 3D.

This is Unlayered Slicer's source at commit `{upstream_commit}` with the application renamed. Two things differ besides the name: the application does not update itself, and a few lines are edited where the rename alone would be wrong. `semilayered/rebrand/table.py` at this release's tag lists every one. Come back to this page for newer builds.

## Which file

| For | File |
|---|---|
{files}

`SHA256SUMS` holds the checksum of every file.

## Opening an unsigned build

None of these files is signed, so each system asks before running them.

- **macOS:** copy the app to Applications, run `xattr -dr com.apple.quarantine /Applications/SemilayeredSlicer.app` in Terminal, then open it as usual.
- **Windows:** when SmartScreen appears, choose *More info*, then *Run anyway*.
- **Linux:** `chmod +x` the AppImage, then run it.
"""
    checks = _failing_checks(known)
    if checks:
        listed = "\n".join(f"- {check}" for check in checks)
        notes += f"""
## Known failing checks

Unlayered Slicer {version}'s own source fails some of the checks in its own test suite. This build fails the same ones and no others:

{listed}
"""
    return notes


def _failing_checks(known: Set[Failure]) -> List[str]:
    """Describe each known failure once, naming every platform a unit test fails on."""
    platforms: Dict[str, List[str]] = {}
    slices: List[str] = []
    jobs: List[str] = []
    for failure in sorted(known):
        if failure.kind == "test":
            platform = failure.job[: -len(_UNIT_TESTS_SUFFIX)] if failure.job.endswith(_UNIT_TESTS_SUFFIX) else failure.job
            platforms.setdefault(failure.item, []).append(platform)
        elif failure.kind == "slice":
            slices.append(failure.item)
        else:
            jobs.append(failure.job)
    return (
        [f'Unit test "{name}" ({", ".join(where)})' for name, where in platforms.items()]
        + [f"Test slice for {printer}" for printer in slices]
        + [f'Job "{job}"' for job in jobs]
    )
