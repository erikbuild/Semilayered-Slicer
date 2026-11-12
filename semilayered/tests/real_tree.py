# ABOUTME: Helpers for tests that look at the real repository and the upstream commit it was generated from.
# ABOUTME: Such tests are skipped in a clone where that upstream commit is not available.
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Optional

from semilayered.rebrand.regenerate import UPSTREAM_COMMIT_FILE

ROOT = Path(__file__).resolve().parents[2]


def upstream_commit() -> Optional[str]:
    """Return the upstream commit the tree comes from (or will come from), or None if this clone lacks it."""
    recorded = ROOT / UPSTREAM_COMMIT_FILE
    ref = recorded.read_text().strip() if recorded.is_file() else "upstream/main"
    found = subprocess.run(
        ["git", "rev-parse", "--verify", "--quiet", ref + "^{commit}"], cwd=ROOT, capture_output=True, text=True
    )
    return found.stdout.strip() or None


def upstream_file(commit: str, path: str) -> bytes:
    """Return a file's content as it is in the upstream commit."""
    return subprocess.run(["git", "show", f"{commit}:{path}"], cwd=ROOT, capture_output=True, check=True).stdout
