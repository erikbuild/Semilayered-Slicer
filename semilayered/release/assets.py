# ABOUTME: Names a release and collects its installers from the downloaded artifacts of a finished "Build all" run.
# ABOUTME: A missing installer stops the release, so nothing is published from a partial build.
from __future__ import annotations

import hashlib
import re
import shutil
import zipfile
from pathlib import Path
from typing import List, Tuple

CHECKSUMS_FILE = "SHA256SUMS"
# The folder a portable Windows build unpacks to.
PORTABLE_FOLDER = "SemilayeredSlicer"

# Each published file: the artifact "Build all" uploads it in, its name, and whom it is for.
# {v} is the upstream version with a leading V, as upstream's workflows name things.
_ASSETS = [
    ("Semilayered_Slicer_Windows_{v}_x64", "Semilayered_Slicer_Windows_Installer_{v}_x64.exe", "Windows, 64-bit Intel or AMD: installer"),
    ("Semilayered_Slicer_Windows_{v}_arm64", "Semilayered_Slicer_Windows_Installer_{v}_arm64.exe", "Windows on ARM: installer"),
    ("Semilayered_Slicer_Windows_{v}_x64_portable", "Semilayered_Slicer_Windows_{v}_x64_portable.zip", "Windows, 64-bit Intel or AMD: runs without installing"),
    ("Semilayered_Slicer_Windows_{v}_arm64_portable", "Semilayered_Slicer_Windows_{v}_arm64_portable.zip", "Windows on ARM: runs without installing"),
    ("Semilayered_Slicer_Mac_universal_{v}", "Semilayered_Slicer_Mac_universal_{v}.dmg", "macOS, Apple silicon or Intel"),
    ("Semilayered_Slicer_Linux_ubuntu_2404_{v}", "Semilayered_Slicer_Linux_AppImage_Ubuntu2404_{v}.AppImage", "Linux, 64-bit Intel or AMD"),
    ("Semilayered_Slicer_Linux_ubuntu_2404_aarch64_{v}", "Semilayered_Slicer_Linux_AppImage_Ubuntu2404_aarch64_{v}.AppImage", "Linux on ARM"),
]  # fmt: skip


class MissingAsset(Exception):
    """The build run did not produce a file the release needs."""


def upstream_version(root: Path) -> str:
    """Return the upstream release this tree is built from, as version.inc records it."""
    found = re.search(r'set\(UNLAYERED_VERSION "([^"]+)"\)', (root / "version.inc").read_text(encoding="utf-8"))
    if not found:
        raise ValueError(f"{root / 'version.inc'} does not set UNLAYERED_VERSION")
    return found.group(1)


def release_tag(version: str, build: int) -> str:
    return f"semilayered-{version}-b{build}"


def release_title(version: str, build: int) -> str:
    return f"Semilayered Slicer {version} (build {build})"


def expected_assets(version: str) -> List[Tuple[str, str]]:
    """Return (artifact name, published file name) for every file a release carries."""
    return [(artifact.format(v=f"V{version}"), published.format(v=f"V{version}")) for artifact, published, _ in _ASSETS]


def asset_descriptions(version: str) -> List[Tuple[str, str]]:
    """Return (published file name, whom it is for) for every file a release carries."""
    return [(published.format(v=f"V{version}"), description) for _, published, description in _ASSETS]


def collect(artifacts_dir: Path, out_dir: Path, version: str) -> List[Path]:
    """Gather the release's files into out_dir from artifacts laid out one directory per artifact.

    Installers are copied, portable builds are zipped, and SHA256SUMS lists a checksum for each.
    Raises MissingAsset, before writing anything, if the run did not produce one of them.
    """
    if out_dir.exists() and any(out_dir.iterdir()):
        raise ValueError(f"{out_dir} is not empty; collect into a new directory")
    assets = expected_assets(version)
    for artifact, published in assets:
        directory = artifacts_dir / artifact
        if not directory.is_dir():
            raise MissingAsset(f"the run has no artifact named {artifact}")
        if _is_portable(artifact):
            if not any(path.is_file() for path in directory.rglob("*")):
                raise MissingAsset(f"artifact {artifact} is empty")
        elif not (directory / published).is_file():
            raise MissingAsset(f"{published} is not in artifact {artifact}")

    out_dir.mkdir(parents=True, exist_ok=True)
    collected = []
    for artifact, published in assets:
        if _is_portable(artifact):
            _zip_directory(artifacts_dir / artifact, out_dir / published)
        else:
            shutil.copyfile(artifacts_dir / artifact / published, out_dir / published)
        collected.append(out_dir / published)
    checksums = out_dir / CHECKSUMS_FILE
    checksums.write_text("".join(f"{_sha256(path)}  {path.name}\n" for path in sorted(collected)), encoding="utf-8")
    return collected + [checksums]


def _is_portable(artifact: str) -> bool:
    return artifact.endswith("_portable")


def _zip_directory(directory: Path, archive: Path) -> None:
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as output:
        for path in sorted(directory.rglob("*")):
            if path.is_file():
                output.write(path, f"{PORTABLE_FOLDER}/{path.relative_to(directory).as_posix()}")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as content:
        for block in iter(lambda: content.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()
