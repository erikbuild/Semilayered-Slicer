# ABOUTME: Builds a small git repository shaped like the real one, for tests of the rebrand tool.
# ABOUTME: It has an "upstream" branch with product-named files and a "work" branch that adds own files.
from __future__ import annotations

import os
import subprocess
from pathlib import Path
from types import SimpleNamespace
from typing import Dict, Union

from semilayered.rebrand.edits import Edit, Substitution

FIXTURE_TABLE = SimpleNamespace(
    OWN_PATHS=("semilayered/", "plans/", ".github/workflows/semilayered_"),
    VERBATIM_PATHS=("LICENSE.txt",),
    SUBSTITUTIONS=(Substitution("com.example.SemilayeredSlicer", "io.test.SemilayeredSlicer", "app id"),),
    EDITS=(
        Edit(
            "docs/notes.md",
            "Made by Unlayered 3D.",
            "Made by Unlayered 3D and rebuilt by others.",
            reason="attribution",
        ),
    ),
    KEPT_PRODUCT_NAMES=(),
    KEPT_IDENTIFIERS={},
    BRAND_IMAGE_PATHS=(),
)

LOGO_BYTES = b"\x89PNG\r\n\x1a\n\x00\x00Unlayered Slicer\x00\xff\xfe"
# Decodes as UTF-8, but the NUL bytes mark it as binary data all the same.
NUL_PADDED_BYTES = b"\x00\x01Unlayered Slicer\x00"

UPSTREAM_FILES: Dict[str, Union[str, bytes]] = {
    "src/UnlayeredSlicer.cpp": (
        '#include "UnlayeredSlicer.hpp"\n'
        "// Unlayered Slicer entry point\n"
        'const char* update_url = "https://unlayered3d.com/slicer/latest.json";\n'
    ),
    "src/UnlayeredSlicer.hpp": '#define APP_NAME "Unlayered Slicer"\n',
    "docs/notes.md": "Made by Unlayered 3D. See https://unlayered3d.com for Unlayered Slicer.\n",
    "LICENSE.txt": "Unlayered Slicer is licensed under the AGPL.\n",
    "resources/logo.png": LOGO_BYTES,
    "resources/table.bin": NUL_PADDED_BYTES,
    "com.example.UnlayeredSlicer.desktop": "Name=Unlayered Slicer\nId=com.example.UnlayeredSlicer\n",
    "old_only.txt": "A file a later upstream commit deletes.\n",
}

OWN_FILES: Dict[str, str] = {
    "semilayered/README.md": "The fork's own notes, which mention Unlayered Slicer by name.\n",
    "plans/plan.md": "A plan.\n",
    ".github/workflows/semilayered_checks.yml": "name: checks\n",
}


def git(root: Path, *args: str) -> str:
    """Run git in root and return its standard output; raise if it fails."""
    return subprocess.run(["git", *args], cwd=root, check=True, capture_output=True, text=True).stdout


def write(root: Path, path: str, content: Union[str, bytes]) -> None:
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content.encode("utf-8") if isinstance(content, str) else content)


def commit_all(root: Path, message: str) -> str:
    """Stage everything, commit, and return the commit hash."""
    git(root, "add", "-A")
    git(root, "commit", "-qm", message)
    return git(root, "rev-parse", "HEAD").strip()


def make_repo(parent: Path) -> Path:
    """Create the fixture repository under parent, checked out on the "work" branch."""
    root = parent / "repo"
    root.mkdir()
    git(root, "init", "-q", "-b", "upstream")
    git(root, "config", "user.name", "Fixture")
    git(root, "config", "user.email", "fixture@example.invalid")
    git(root, "config", "commit.gpgsign", "false")
    git(root, "config", "core.hooksPath", str(root / ".git" / "no-hooks"))
    for path, content in UPSTREAM_FILES.items():
        write(root, path, content)
    os.symlink("docs/notes.md", root / "link.md")
    os.symlink("no-such-target", root / "dangling")
    commit_all(root, "upstream source 1")
    git(root, "checkout", "-q", "-b", "work")
    for path, content in OWN_FILES.items():
        write(root, path, content)
    commit_all(root, "own files")
    return root


def advance_upstream(root: Path) -> str:
    """Add a second commit to "upstream" (one file added, one deleted); return its hash. Leaves "work" checked out."""
    git(root, "checkout", "-q", "upstream")
    write(root, "src/extra.cpp", "// Added later to Unlayered Slicer\n")
    (root / "old_only.txt").unlink()
    commit = commit_all(root, "upstream source 2")
    git(root, "checkout", "-q", "work")
    return commit


def snapshot(root: Path) -> Dict[str, bytes]:
    """Return every working-tree file's bytes (a symlink's target instead), keyed by relative path."""
    found: Dict[str, bytes] = {}
    for directory, names, files in os.walk(root):
        if ".git" in names:
            names.remove(".git")
        for name in files + [n for n in names if (Path(directory) / n).is_symlink()]:
            full = Path(directory) / name
            relative = full.relative_to(root).as_posix()
            found[relative] = b"-> " + os.readlink(full).encode() if full.is_symlink() else full.read_bytes()
    return found
