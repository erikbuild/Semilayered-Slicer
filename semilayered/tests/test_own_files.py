# ABOUTME: Tests that the fork's own files can all be committed.
# ABOUTME: Upstream's .gitignore has broad patterns (such as *.log); an own file matching one would silently stay behind.
import subprocess
import unittest

from semilayered.rebrand import table
from semilayered.tests.real_tree import ROOT


class OwnFilesTest(unittest.TestCase):
    def test_no_own_file_is_ignored_by_git(self):
        own_directories = [prefix for prefix in table.OWN_PATHS if prefix.endswith("/")]
        listing = subprocess.run(
            ["git", "status", "--porcelain", "--ignored", "--", *own_directories],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        ignored = [
            line[3:]
            for line in listing.splitlines()
            if line.startswith("!! ") and "__pycache__" not in line and not line.endswith(".pyc")
        ]
        self.assertEqual(ignored, [])


if __name__ == "__main__":
    unittest.main()
