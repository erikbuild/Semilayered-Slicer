# ABOUTME: Reads the format facts of an image file from its bytes: pixel sizes, icon entries, SVG geometry.
# ABOUTME: Used by the artwork tests to compare each replacement image with the upstream image it replaces.
from __future__ import annotations

import re
import struct
from typing import List, Optional, Set, Tuple

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"

# Pixel size of the icon each ICNS entry type holds. Mask, contents and metadata entries are not listed.
ICNS_PIXELS = {
    "is32": 16, "icp4": 16, "ic04": 16,
    "il32": 32, "icp5": 32, "ic05": 32, "ic11": 32,
    "ih32": 48,
    "icp6": 64, "ic12": 64,
    "ic07": 128,
    "ic08": 256, "ic13": 256,
    "ic09": 512, "ic14": 512,
    "ic10": 1024,
}  # fmt: skip


def png_size(data: bytes) -> Tuple[int, int]:
    if not data.startswith(PNG_SIGNATURE) or data[12:16] != b"IHDR":
        raise ValueError("not a PNG image")
    return struct.unpack(">II", data[16:24])


def ico_entries(data: bytes) -> List[Tuple[int, int, str]]:
    """Return (width, height, encoding) for each icon in an ICO file; encoding is "png" or "bmp"."""
    reserved, kind, count = struct.unpack("<HHH", data[:6])
    if reserved != 0 or kind != 1:
        raise ValueError("not an ICO image")
    entries = []
    for index in range(count):
        width, height, _, _, _, _, size, offset = struct.unpack("<BBBBHHII", data[6 + 16 * index : 22 + 16 * index])
        image = data[offset : offset + size]
        if len(image) != size:
            raise ValueError("an ICO entry points outside the file")
        entries.append((width or 256, height or 256, "png" if image.startswith(PNG_SIGNATURE) else "bmp"))
    return entries


def icns_pixel_sizes(data: bytes) -> Set[int]:
    """Return the pixel sizes an ICNS file holds icons for."""
    if data[:4] != b"icns" or struct.unpack(">I", data[4:8])[0] != len(data):
        raise ValueError("not an ICNS image")
    sizes, offset = set(), 8
    while offset < len(data):
        kind = data[offset : offset + 4].decode("latin-1")
        length = struct.unpack(">I", data[offset + 4 : offset + 8])[0]
        if length < 8:
            raise ValueError("a malformed ICNS entry")
        if kind in ICNS_PIXELS:
            sizes.add(ICNS_PIXELS[kind])
        offset += length
    return sizes


def svg_geometry(text: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """Return the (viewBox, width, height) attributes of an SVG's root element."""
    root = re.search(r"<svg\b[^>]*>", text, re.S)
    if not root:
        raise ValueError("not an SVG image")

    def attribute(name: str) -> Optional[str]:
        found = re.search(rf'\s{name}="([^"]*)"', root.group(0))
        return found.group(1) if found else None

    return attribute("viewBox"), attribute("width"), attribute("height")
