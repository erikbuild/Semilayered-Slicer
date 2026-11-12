# ABOUTME: Applies the rebrand to a git working tree: file contents, paths, explicit edits, then artwork.
# ABOUTME: Works on tracked files only, and never changes the fork's own files, verbatim files or symlinks.
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Dict, List, Optional

from semilayered.rebrand import table as default_table
from semilayered.rebrand.edits import EditMismatch, apply_edit, substitute
from semilayered.rebrand.names import rename_path, rename_text

# Replacement images live here, each at the repository-relative path of the image it replaces.
ARTWORK_TREE = "semilayered/artwork/tree"


class PathCollision(Exception):
    """Renaming a path would land it on a path that is already taken."""


class ArtworkWithoutTarget(Exception):
    """A replacement image has no tracked file at its path to replace."""


def git(root: Path, *args: str) -> str:
    """Run git in root and return its standard output; raise if it fails."""
    return subprocess.run(["git", *args], cwd=root, check=True, capture_output=True, text=True).stdout


def tracked_files(root: Path) -> List[str]:
    return [path for path in git(root, "ls-files", "-z").split("\0") if path]


def is_own(path: str, table) -> bool:
    return any(path.startswith(prefix) for prefix in table.OWN_PATHS)


def excluding_own_paths(table) -> List[str]:
    """Return git pathspecs that leave the fork's own files out of a command run over the whole tree."""
    return [f":(exclude){prefix}" if prefix.endswith("/") else f":(exclude,glob){prefix}*" for prefix in table.OWN_PATHS]


def read_text(path: Path) -> Optional[str]:
    """Return the file's text, or None when it is a symlink or is not UTF-8 text."""
    if path.is_symlink():
        return None
    data = path.read_bytes()
    if b"\0" in data:
        return None
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return None


def write_text(path: Path, text: str) -> None:
    path.write_bytes(text.encode("utf-8"))


def apply(root: Path, table=default_table) -> None:
    """Rebrand the working tree at root in place. Meant for a tree as upstream wrote it, which is what regenerate gives it."""
    upstream_files = [
        path for path in tracked_files(root) if not is_own(path, table) and path not in table.VERBATIM_PATHS
    ]
    renames = _planned_renames(root, upstream_files, table)
    seen = _rewrite_contents(root, upstream_files, table)
    for path in upstream_files:
        path_after = rename_path(path)
        for substitution in table.SUBSTITUTIONS:
            seen[substitution] += path_after.count(substitution.old) + path_after.count(substitution.new)
    _move(root, renames)
    for substitution in table.SUBSTITUTIONS:
        if seen[substitution] == 0:
            raise EditMismatch(
                f"substitution {substitution.old!r} -> {substitution.new!r} matched nothing in the tree. "
                f"It exists because: {substitution.reason}"
            )
    _apply_edits(root, table)
    _install_artwork(root)


def _planned_renames(root: Path, paths: List[str], table) -> Dict[str, str]:
    """Return old path -> new path for every path that changes, or raise before anything is touched."""
    taken = set(tracked_files(root))
    renames: Dict[str, str] = {}
    for path in paths:
        renamed = rename_path(path)
        for substitution in table.SUBSTITUTIONS:
            renamed = renamed.replace(substitution.old, substitution.new)
        if renamed == path:
            continue
        if renamed in taken:
            raise PathCollision(f"{path} would be renamed to {renamed}, which already exists")
        taken.add(renamed)
        renames[path] = renamed
    return renames


def _rewrite_contents(root: Path, paths: List[str], table) -> Dict[object, int]:
    """Rename and substitute inside every text file; return how often each substitution's text was seen."""
    seen = {substitution: 0 for substitution in table.SUBSTITUTIONS}
    for path in paths:
        text = read_text(root / path)
        if text is None:
            continue
        changed = rename_text(text)
        for substitution in table.SUBSTITUTIONS:
            changed, replaced = substitute(changed, substitution)
            seen[substitution] += replaced + changed.count(substitution.new)
        if changed != text:
            write_text(root / path, changed)
    return seen


def _move(root: Path, renames: Dict[str, str]) -> None:
    for old, new in renames.items():
        (root / new).parent.mkdir(parents=True, exist_ok=True)
        git(root, "mv", "--", old, new)
    for old in renames:
        directory = (root / old).parent
        while directory != root and directory.is_dir() and not any(directory.iterdir()):
            directory.rmdir()
            directory = directory.parent


def _apply_edits(root: Path, table) -> None:
    for edit in table.EDITS:
        text = read_text(root / edit.path) if (root / edit.path).is_file() else None
        if text is None:
            raise EditMismatch(f"{edit.path}: no such text file in the tree. This edit exists because: {edit.reason}")
        changed = apply_edit(text, edit)
        if changed != text:
            write_text(root / edit.path, changed)


def _install_artwork(root: Path) -> None:
    listed = git(root, "ls-files", "-z", "--cached", "--others", "--exclude-standard", "--", ARTWORK_TREE)
    tracked = set(tracked_files(root))
    for source in sorted(path for path in listed.split("\0") if path):
        if not (root / source).is_file():
            continue
        target = source[len(ARTWORK_TREE) + 1 :]
        if target not in tracked:
            raise ArtworkWithoutTarget(f"{source} has no tracked file at {target} to replace")
        image = (root / source).read_bytes()
        if (root / target).read_bytes() != image:
            (root / target).write_bytes(image)
