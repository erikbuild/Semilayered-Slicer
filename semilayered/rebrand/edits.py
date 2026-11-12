# ABOUTME: Explicit edits to upstream's files: exact replacements for what the name pattern cannot decide.
# ABOUTME: An edit that does not find its text the expected number of times fails instead of being skipped.
from __future__ import annotations

from dataclasses import dataclass


class EditMismatch(Exception):
    """An explicit edit did not find the text it replaces the expected number of times."""


@dataclass(frozen=True)
class Edit:
    """One exact replacement in one file, written against the text as it reads after renaming."""

    path: str
    old: str
    new: str
    count: int = 1
    reason: str = ""

    def __post_init__(self) -> None:
        if not self.new or self.new in self.old:
            raise ValueError(
                f"{self.path}: the new text must not be empty or part of the old text, "
                "or an applied edit could not be told from an unapplied one"
            )


@dataclass(frozen=True)
class Substitution:
    """A replacement of every occurrence, tree-wide, in file contents and in path components."""

    old: str
    new: str
    reason: str = ""

    def __post_init__(self) -> None:
        if not self.old or self.old in self.new:
            raise ValueError(
                f"{self.old!r}: the old text must not be empty or part of the new text, "
                "or the substitution would apply again on every run"
            )


def apply_edit(text: str, edit: Edit) -> str:
    """Return text with the edit applied, or unchanged if it already was. Raise EditMismatch otherwise."""
    edited = text.count(edit.new)
    # An insertion keeps its old text inside the new text; those occurrences are not waiting to be edited.
    unedited = text.count(edit.old) - edited * edit.new.count(edit.old)
    if unedited == 0 and edited >= edit.count:
        return text
    if unedited == edit.count and edited == 0:
        return text.replace(edit.old, edit.new)
    raise EditMismatch(
        f"{edit.path}: expected {edit.count} of {edit.old!r}, found {unedited} "
        f"(and {edited} already edited). This edit exists because: {edit.reason}"
    )


def substitute(text: str, substitution: Substitution) -> tuple[str, int]:
    """Return text with every occurrence replaced, and how many there were."""
    return text.replace(substitution.old, substitution.new), text.count(substitution.old)
