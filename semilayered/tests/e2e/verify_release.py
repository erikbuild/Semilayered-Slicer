# ABOUTME: Verifies a release of Semilayered Slicer from the outside, on macOS: downloads, checksums, identity, behaviour.
# ABOUTME: Usage: python3 semilayered/tests/e2e/verify_release.py (<release tag> | --dir <directory of release files>)
from __future__ import annotations

import hashlib
import plistlib
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path
from typing import Callable, List, Tuple

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPOSITORY_ROOT))

from semilayered.release.assets import CHECKSUMS_FILE, expected_assets, upstream_version  # noqa: E402
from semilayered.tests.e2e.behaviour_checks import generator_name, no_update_check  # noqa: E402

DOWNLOADS = "https://github.com/erikbuild/Semilayered-Slicer/releases/download"
APP_NAME = "Semilayered Slicer"
APP_ID = "io.github.erikbuild.SemilayeredSlicer"
WINDOWS_FILES = ("semilayered-slicer.exe", "SemilayeredSlicer.dll")

Result = Tuple[bool, str]


def download(tag: str, names: List[str], into: Path) -> Result:
    """Fetch every file of the release the way a visitor would: no login, no token."""
    for name in names:
        try:
            with urllib.request.urlopen(f"{DOWNLOADS}/{tag}/{name}") as response, open(into / name, "wb") as target:
                shutil.copyfileobj(response, target)
        except OSError as problem:
            return False, f"could not download {name} without credentials: {problem}"
    return True, f"{len(names)} files downloaded without credentials"


def checksums(directory: Path, names: List[str]) -> Result:
    """Every file must be listed in SHA256SUMS with the checksum it actually has."""
    listed = dict(reversed(line.split("  ", 1)) for line in (directory / CHECKSUMS_FILE).read_text().splitlines())
    for name in names:
        if name not in listed:
            return False, f"{name} is not listed in {CHECKSUMS_FILE}"
        digest = hashlib.sha256()
        with open(directory / name, "rb") as content:
            for block in iter(lambda: content.read(1 << 20), b""):
                digest.update(block)
        if digest.hexdigest() != listed[name]:
            return False, f"{name} does not match its checksum"
    return True, f"{len(names)} files match {CHECKSUMS_FILE}"


def copy_app_out_of(dmg: Path, into: Path) -> Path:
    """Mount the disk image, copy its application into a directory, and return the copy."""
    mount = into / "mount"
    mount.mkdir()
    attach = ["hdiutil", "attach", str(dmg), "-nobrowse", "-readonly", "-noautoopen", "-mountpoint", str(mount)]
    subprocess.run(attach, check=True, capture_output=True)
    try:
        app = next(mount.glob("*.app"))
        copy = into / app.name
        subprocess.run(["ditto", str(app), str(copy)], check=True, capture_output=True)
    finally:
        subprocess.run(["hdiutil", "detach", str(mount), "-quiet"], capture_output=True)
    return copy


def macos_identity(app: Path) -> Result:
    with open(app / "Contents" / "Info.plist", "rb") as plist:
        info = plistlib.load(plist)
    found = (info.get("CFBundleName"), info.get("CFBundleIdentifier"))
    if found != (APP_NAME, APP_ID):
        return False, f"the app calls itself {found}; expected {(APP_NAME, APP_ID)}"
    return True, f"the app is {APP_NAME} ({APP_ID})"


def windows_identity(installer: Path) -> Result:
    if not shutil.which("7zz"):
        return False, "7zz is needed to look inside the Windows installer (brew install sevenzip)"
    listing = subprocess.run(["7zz", "l", str(installer)], capture_output=True, text=True, errors="replace").stdout
    missing = [name for name in WINDOWS_FILES if name not in listing]
    if missing:
        return False, f"the Windows installer does not contain {', '.join(missing)}"
    return True, f"the Windows installer contains {' and '.join(WINDOWS_FILES)}"


def main() -> int:
    arguments = sys.argv[1:]
    from_directory = len(arguments) == 2 and arguments[0] == "--dir"
    tagged = len(arguments) == 1 and re.fullmatch(r"semilayered-(?P<version>.+)-b\d+", arguments[0])
    if not (from_directory or tagged):
        print("usage: verify_release.py (<release tag> | --dir <directory of release files>)", file=sys.stderr)
        return 2

    version = tagged.group("version") if tagged else upstream_version(REPOSITORY_ROOT)
    names = [published for _, published in expected_assets(version)]
    dmg = next(name for name in names if name.endswith(".dmg"))
    installer = next(name for name in names if name.endswith("_x64.exe"))
    passed = True

    def report(name: str, check: Callable[[], Result]) -> bool:
        nonlocal passed
        ok, detail = check()
        passed = passed and ok
        print(f"{'PASS' if ok else 'FAIL'} {name}: {detail}")
        return ok

    with tempfile.TemporaryDirectory(prefix="semilayered-verify-") as holder:
        work = Path(holder)
        files = Path(arguments[1]) if from_directory else work / "files"
        if tagged:
            files.mkdir()
            if not report("download", lambda: download(arguments[0], names + [CHECKSUMS_FILE], files)):
                return 1
        if not report("checksums", lambda: checksums(files, names)):
            return 1
        app = copy_app_out_of(files / dmg, work)
        report("macos_identity", lambda: macos_identity(app))
        report("windows_identity", lambda: windows_identity(files / installer))
        report("no_update_check", lambda: no_update_check(app))
        report("generator_name", lambda: generator_name(app))
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
