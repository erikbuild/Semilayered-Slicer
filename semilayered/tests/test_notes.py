# ABOUTME: Tests for the release notes: what every release has to tell the person downloading it.
# ABOUTME: Checks the statements the design requires, not the exact wording around them.
import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from semilayered.release.__main__ import main
from semilayered.release.failures import Failure
from semilayered.release.notes import release_notes

UPSTREAM = "0eb63cfa46c84bd01143cb78c9557384b6a6dff7"
KNOWN = {
    Failure("test", "Linux x86_64 / Unit Tests", "Each cube's raft is its support, centered below it"),
    Failure("test", "macOS arm64 / Unit Tests", "Each cube's raft is its support, centered below it"),
    Failure("slice", "Slice check (Linux aarch64)", "Unlayered / Unlayered 5 Axis Printer 0.4 nozzle"),
    Failure("job", "Flatpak (x86_64, ubuntu-24.04)", "Run flatpak/flatpak-github-actions/flatpak-builder@master"),
}


class ReleaseNotesTest(unittest.TestCase):
    def setUp(self):
        self.notes = release_notes("0.1.10", 7, UPSTREAM, KNOWN)

    def test_say_what_this_build_is_and_is_not(self):
        for statement in (
            "unofficial build of Unlayered Slicer",
            "not affiliated with or endorsed by Unlayered 3D",
            "provided as is, without support",
            "does not update itself",
        ):
            with self.subTest(statement=statement):
                self.assertIn(statement, self.notes)

    def test_name_the_upstream_commit_the_build_comes_from(self):
        self.assertIn(UPSTREAM, self.notes)

    def test_tell_each_system_how_to_open_an_unsigned_build(self):
        self.assertIn("xattr -dr com.apple.quarantine", self.notes)
        self.assertIn("chmod +x", self.notes)
        self.assertIn("SmartScreen", self.notes)

    def test_list_every_known_failing_check_once(self):
        self.assertEqual(self.notes.count("Each cube's raft is its support, centered below it"), 1)
        self.assertIn("Unlayered / Unlayered 5 Axis Printer 0.4 nozzle", self.notes)
        self.assertIn("Flatpak (x86_64, ubuntu-24.04)", self.notes)

    def test_name_the_platforms_a_test_fails_on(self):
        line = next(line for line in self.notes.splitlines() if "Each cube's raft" in line)
        self.assertIn("Linux x86_64", line)
        self.assertIn("macOS arm64", line)

    def test_without_known_failures_say_nothing_about_them(self):
        self.assertNotIn("fail", release_notes("0.1.10", 7, UPSTREAM, set()).lower())


class NotesCommandTest(unittest.TestCase):
    def test_notes_are_written_for_the_tree_they_are_run_in(self):
        with tempfile.TemporaryDirectory() as holder:
            root = Path(holder)
            (root / "version.inc").write_text('set(UNLAYERED_VERSION "0.1.11")\n')
            (root / "semilayered").mkdir()
            (root / "semilayered" / "upstream_commit").write_text(UPSTREAM + "\n")
            known = root / "known.txt"
            known.write_text("job\tFlatpak (x86_64, ubuntu-24.04)\tbuild\n")
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = main(["notes", "--build", "3", "--known", str(known)], root=root)
        self.assertEqual(code, 0)
        self.assertIn("Unlayered Slicer 0.1.11", out.getvalue())
        self.assertIn(UPSTREAM, out.getvalue())
        self.assertIn("Flatpak (x86_64, ubuntu-24.04)", out.getvalue())


if __name__ == "__main__":
    unittest.main()
