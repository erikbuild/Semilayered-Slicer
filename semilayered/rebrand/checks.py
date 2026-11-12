# ABOUTME: Checks that a tree is exactly what the rebrand tool produces from its upstream commit.
# ABOUTME: Reports leftover product names, kept identifiers that changed, upstream brand images, and hand edits.
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Dict, Iterator, List, Tuple

from semilayered.rebrand import table as default_table
from semilayered.rebrand.names import find_product_names
from semilayered.rebrand.regenerate import scratch_regeneration
from semilayered.rebrand.tree import excluding_own_paths, git, is_own, read_text, tracked_files


def leftover_product_names(root: Path, table=default_table) -> List[str]:
    """Return one line per product name still in an upstream file or path, apart from the listed kept ones."""
    kept: Dict[str, List[str]] = {}
    for path, literal, _reason in table.KEPT_PRODUCT_NAMES:
        kept.setdefault(path, []).append(literal)
    tracked = tracked_files(root)
    findings = [
        f"{path}: kept text is no longer there: {literal!r}"
        for path, literals in kept.items()
        if path not in tracked
        for literal in literals
    ]
    for path in tracked:
        if is_own(path, table):
            continue
        findings += [f"{path}: the path itself contains {match!r}" for _line, match in find_product_names(path)]
        if path in table.VERBATIM_PATHS or (root / path).is_symlink():
            continue
        text = read_text(root / path)
        if text is not None:
            searched, missing = _without_kept(text, kept.get(path, []))
            findings += [f"{path}: kept text is no longer there: {literal!r}" for literal in missing]
            findings += [f"{path}:{line}: {match}" for line, match in find_product_names(searched)]
        else:
            findings += _leftovers_in_binary(path, (root / path).read_bytes(), kept.get(path, []))
    return findings


def kept_identifier_drift(root: Path, upstream_commit: str, table=default_table) -> List[str]:
    """Return one line per kept identifier whose count differs from upstream's by more than the table allows."""
    findings = []
    for identifier, allowed in table.KEPT_IDENTIFIERS.items():
        before = _occurrences(root, identifier, table, upstream_commit)
        after = _occurrences(root, identifier, table)
        if after - before != allowed:
            findings.append(
                f"{identifier!r} occurs {before} times upstream and {after} times here; "
                f"the table allows a difference of {allowed}"
            )
    return findings


def upstream_brand_images(root: Path, upstream_commit: str, table=default_table) -> List[str]:
    """Return one line per file in the tree whose content is one of upstream's brand images."""
    if not table.BRAND_IMAGE_PATHS:
        return []
    upstream = dict(_blobs(git(root, "ls-tree", "-r", "-z", upstream_commit)))
    findings = [
        f"{path}: listed as a brand image, but upstream has no such file"
        for path in table.BRAND_IMAGE_PATHS
        if path not in upstream
    ]
    brand = {upstream[path]: path for path in table.BRAND_IMAGE_PATHS if path in upstream}
    with _working_tree_index(root) as environment:
        staged = _git_with(root, environment, "ls-files", "-s", "-z")
    for path, blob in _blobs(staged):
        if blob in brand:
            findings.append(f"{path}: still upstream's image (the same content as {brand[blob]})")
    return findings


def differences_from_regeneration(root: Path, upstream_commit: str, table=default_table) -> List[str]:
    """Return one line per path where the working tree differs from a fresh regeneration."""
    with scratch_regeneration(root, upstream_commit, table) as scratch:
        regenerated = git(scratch, "write-tree").strip()
        with _working_tree_index(root) as environment:
            current = _git_with(root, environment, "write-tree").strip()
        if regenerated == current:
            return []
        changes = git(root, "diff-tree", "-r", "-z", "--name-status", regenerated, current).split("\0")
    meaning = {
        "M": "differs from the regenerated file",
        "A": "is not produced by regenerating",
        "D": "is produced by regenerating but is missing here",
    }
    return [
        f"{path}: {meaning.get(status, status)}" for status, path in zip(changes[0::2], changes[1::2]) if path
    ]


def reproduces(root: Path, upstream_commit: str, table=default_table) -> bool:
    """Say whether regenerating from the upstream commit yields exactly the working tree."""
    return not differences_from_regeneration(root, upstream_commit, table)


def _without_kept(text: str, literals: List[str]) -> Tuple[str, List[str]]:
    """Return text with each kept literal blanked out (line numbers preserved), and the literals not found."""
    missing = []
    for literal in literals:
        if literal in text:
            # A digit cannot join two words into a match the way a space or punctuation could.
            text = text.replace(literal, "0" + "\n" * literal.count("\n"))
        else:
            missing.append(literal)
    return text, missing


def _leftovers_in_binary(path: str, data: bytes, kept: List[str]) -> List[str]:
    """Search data that is not UTF-8 text for the name as single-byte text and as UTF-16 at either alignment."""
    decodings = [data.decode("latin-1"), data.decode("utf-16-le", "ignore"), data[1:].decode("utf-16-le", "ignore")]
    findings = [
        f"{path}: kept text is no longer there: {literal!r}"
        for literal in kept
        if not any(literal in decoded for decoded in decodings)
    ]
    for decoded in decodings:
        matches = find_product_names(_without_kept(decoded, kept)[0])
        if matches:
            findings.append(f"{path}: binary file contains {matches[0][1]!r}")
            break
    return findings


def _occurrences(root: Path, text: str, table, commit: str = "") -> int:
    """Count occurrences of text in upstream files, in the working tree or in a commit."""
    command = ["git", "grep", "-I", "-o", "-F", "-e", text] + ([commit] if commit else [])
    command += ["--", ".", *excluding_own_paths(table)]
    result = subprocess.run(command, cwd=root, capture_output=True, text=True, errors="replace")
    if result.returncode not in (0, 1):
        raise RuntimeError(f"git grep failed: {result.stderr.strip()}")
    return len(result.stdout.splitlines())


def _blobs(listing: str) -> List[Tuple[str, str]]:
    """Read (path, blob hash) pairs from NUL-separated `git ls-tree` or `git ls-files -s` output."""
    pairs = []
    for entry in listing.split("\0"):
        if entry:
            fields, path = entry.split("\t", 1)
            pairs.append((path, fields.split()[2] if fields.split()[1] == "blob" else fields.split()[1]))
    return pairs


@contextmanager
def _working_tree_index(root: Path) -> Iterator[Dict[str, str]]:
    """Yield an environment in which git sees an index holding the working tree as it is now."""
    with tempfile.TemporaryDirectory(prefix="semilayered-index-") as holder:
        index = Path(holder) / "index"
        real = Path(git(root, "rev-parse", "--git-path", "index").strip())
        real = real if real.is_absolute() else root / real
        if real.exists():
            shutil.copy2(real, index)
        environment = {**os.environ, "GIT_INDEX_FILE": str(index)}
        _git_with(root, environment, "add", "-A")
        yield environment


def _git_with(root: Path, environment: Dict[str, str], *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=root, env=environment, check=True, capture_output=True, text=True
    ).stdout
