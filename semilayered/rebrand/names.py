# ABOUTME: Renames the product name "Unlayered Slicer", in each of its spellings, in text and in paths.
# ABOUTME: Also finds spellings the rename does not handle, so a tree that still holds one can be rejected.
from __future__ import annotations

import re

_FIRST_WORD = {
    "Unlayered": "Semilayered",
    "unlayered": "semilayered",
    "UNLAYERED": "SEMILAYERED",
}

# The first word of the product name, wherever "slicer" follows it directly or after one separator.
# The word on its own names the company, its printers and its services, and is left alone.
_RENAMEABLE = re.compile(r"(Unlayered|unlayered|UNLAYERED)(?=[ \-_.]?(?i:slicer))")

# Any way of writing the two words close together, including ones the rename does not handle:
# other casings, a line break between the words, an HTML or URL-encoded space.
_ANY_FORM = re.compile(r"unlayered(?:&nbsp;|&#160;|%20|[^a-z0-9]){0,12}slicer", re.IGNORECASE)


def rename_text(text: str) -> str:
    """Return text with every handled spelling of the product name renamed."""
    return _RENAMEABLE.sub(lambda match: _FIRST_WORD[match.group(1)], text)


def rename_path(path: str) -> str:
    """Return a slash-separated path with the product name renamed in each component."""
    return "/".join(rename_text(component) for component in path.split("/"))


def find_product_names(text: str) -> list[tuple[int, str]]:
    """Return (line number, matched text) for every occurrence of the product name in any form."""
    return [(text.count("\n", 0, match.start()) + 1, match.group(0)) for match in _ANY_FORM.finditer(text)]
