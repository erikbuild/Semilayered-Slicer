# ABOUTME: Rebuilds the working tree from an upstream commit: upstream's files, the fork's own files, the rebrand.
# ABOUTME: Records which upstream commit the tree came from, and can build the same tree in a scratch worktree.
from __future__ import annotations

import shutil
import subprocess
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, List, Optional

from semilayered.rebrand import table as default_table
from semilayered.rebrand.tree import apply, git, is_own

# One line: the upstream commit the tree was generated from.
UPSTREAM_COMMIT_FILE = "semilayered/upstream_commit"


class DirtyTree(Exception):
    """The working tree has changes that a regeneration would destroy."""


def recorded_upstream_commit(root: Path) -> str:
    return (root / UPSTREAM_COMMIT_FILE).read_text().strip()


def regenerate(root: Path, upstream_ref: Optional[str] = None, table=default_table) -> str:
    """Replace the working tree with the rebranded upstream tree plus the own files; return the upstream commit.

    Everything is staged and nothing is committed. When the upstream commit is not yet part of
    this branch's history, a merge is left in progress so that the commit records it.
    """
    if git(root, "status", "--porcelain"):
        raise DirtyTree("the working tree has uncommitted changes; commit or stash them first")
    commit = git(root, "rev-parse", "--verify", (upstream_ref or recorded_upstream_commit(root)) + "^{commit}").strip()
    if not _is_ancestor(root, commit, "HEAD"):
        git(root, "merge", "--quiet", "-s", "ours", "--no-commit", "--no-ff", commit)
    own_files = [path for path in git(root, "ls-tree", "-r", "-z", "--name-only", "HEAD").split("\0") if path and is_own(path, table)]
    git(root, "read-tree", "--reset", "-u", commit)
    for start in range(0, len(own_files), 200):
        git(root, "checkout", "HEAD", "--", *own_files[start : start + 200])
    (root / UPSTREAM_COMMIT_FILE).parent.mkdir(parents=True, exist_ok=True)
    (root / UPSTREAM_COMMIT_FILE).write_text(commit + "\n")
    apply(root, table)
    git(root, "add", "-A")
    return commit


@contextmanager
def scratch_regeneration(root: Path, upstream_commit: str, table=default_table) -> Iterator[Path]:
    """Yield a temporary worktree holding the regenerated tree, built with the own files as they are in root now."""
    holder = Path(tempfile.mkdtemp(prefix="semilayered-scratch-"))
    scratch = holder / "tree"
    git(root, "worktree", "add", "--quiet", "--detach", str(scratch), upstream_commit)
    try:
        for path in _own_files_in_working_tree(root, table):
            if (root / path).is_file():
                (scratch / path).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(root / path, scratch / path)
        apply(scratch, table)
        git(scratch, "add", "-A")
        yield scratch
    finally:
        git(root, "worktree", "remove", "--force", str(scratch))
        shutil.rmtree(holder, ignore_errors=True)


def _is_ancestor(root: Path, commit: str, of: str) -> bool:
    return subprocess.run(["git", "merge-base", "--is-ancestor", commit, of], cwd=root).returncode == 0


def _own_files_in_working_tree(root: Path, table) -> List[str]:
    listed = git(root, "ls-files", "-z", "--cached", "--others", "--exclude-standard")
    return [path for path in listed.split("\0") if path and is_own(path, table)]
