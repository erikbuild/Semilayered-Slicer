# ABOUTME: Tests for applying the rebrand to a working tree, run against a real git repository in a temp dir.
# ABOUTME: Covers renaming contents and paths together, what is left alone, collisions, edits and artwork.
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from semilayered.rebrand.edits import Edit, EditMismatch, Substitution
from semilayered.rebrand.tree import ArtworkWithoutTarget, PathCollision, apply
from semilayered.tests.repo_fixture import (
    FIXTURE_TABLE,
    LOGO_BYTES,
    NUL_PADDED_BYTES,
    OWN_FILES,
    commit_all,
    git,
    make_repo,
    snapshot,
    write,
)


def table_with(**changes):
    return SimpleNamespace(**{**vars(FIXTURE_TABLE), **changes})


class ApplyTest(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = make_repo(Path(temp.name))

    def tracked(self):
        return git(self.root, "ls-files").splitlines()

    def test_contents_and_paths_are_renamed_together(self):
        apply(self.root, FIXTURE_TABLE)
        self.assertIn('#include "SemilayeredSlicer.hpp"', (self.root / "src/SemilayeredSlicer.cpp").read_text())
        self.assertIn("// Semilayered Slicer entry point", (self.root / "src/SemilayeredSlicer.cpp").read_text())
        tracked = self.tracked()
        self.assertIn("src/SemilayeredSlicer.hpp", tracked)
        self.assertNotIn("src/UnlayeredSlicer.cpp", tracked)
        self.assertNotIn("src/UnlayeredSlicer.hpp", tracked)
        self.assertFalse((self.root / "src/UnlayeredSlicer.cpp").exists())

    def test_other_uses_of_the_word_keep_their_text(self):
        apply(self.root, FIXTURE_TABLE)
        self.assertIn("https://unlayered3d.com/slicer/latest.json", (self.root / "src/SemilayeredSlicer.cpp").read_text())
        self.assertIn("Unlayered 3D", (self.root / "docs/notes.md").read_text())

    def test_own_and_verbatim_files_are_untouched(self):
        before = snapshot(self.root)
        apply(self.root, FIXTURE_TABLE)
        after = snapshot(self.root)
        for path in list(OWN_FILES) + ["LICENSE.txt"]:
            with self.subTest(path=path):
                self.assertEqual(after[path], before[path])

    def test_binary_files_and_symlinks_are_untouched(self):
        apply(self.root, FIXTURE_TABLE)
        self.assertEqual((self.root / "resources/logo.png").read_bytes(), LOGO_BYTES)
        self.assertEqual((self.root / "resources/table.bin").read_bytes(), NUL_PADDED_BYTES)
        self.assertTrue((self.root / "link.md").is_symlink())
        self.assertEqual(os.readlink(self.root / "link.md"), "docs/notes.md")
        self.assertEqual(os.readlink(self.root / "dangling"), "no-such-target")

    def test_second_apply_changes_nothing(self):
        apply(self.root, FIXTURE_TABLE)
        files_after_first = snapshot(self.root)
        status_after_first = git(self.root, "status", "--porcelain")
        apply(self.root, FIXTURE_TABLE)
        self.assertEqual(snapshot(self.root), files_after_first)
        self.assertEqual(git(self.root, "status", "--porcelain"), status_after_first)

    def test_colliding_rename_stops_before_changing_anything(self):
        write(self.root, "src/SemilayeredSlicer.hpp", "// already here\n")
        commit_all(self.root, "a file where a rename wants to land")
        before = snapshot(self.root)
        with self.assertRaises(PathCollision) as caught:
            apply(self.root, FIXTURE_TABLE)
        self.assertIn("src/UnlayeredSlicer.hpp", str(caught.exception))
        self.assertIn("src/SemilayeredSlicer.hpp", str(caught.exception))
        self.assertEqual(snapshot(self.root), before)
        self.assertEqual(git(self.root, "status", "--porcelain"), "")

    def test_substitution_applies_to_paths_and_contents(self):
        apply(self.root, FIXTURE_TABLE)
        self.assertEqual(
            (self.root / "io.test.SemilayeredSlicer.desktop").read_text(),
            "Name=Semilayered Slicer\nId=io.test.SemilayeredSlicer\n",
        )
        self.assertNotIn("com.example.UnlayeredSlicer.desktop", self.tracked())

    def test_substitution_that_matches_nothing_fails(self):
        table = table_with(SUBSTITUTIONS=(Substitution("no-such-text", "anything", "left over from an older upstream"),))
        with self.assertRaises(EditMismatch) as caught:
            apply(self.root, table)
        self.assertIn("no-such-text", str(caught.exception))

    def test_explicit_edit_is_applied_to_the_renamed_tree(self):
        apply(self.root, FIXTURE_TABLE)
        self.assertEqual(
            (self.root / "docs/notes.md").read_text(),
            "Made by Unlayered 3D and rebuilt by others. See https://unlayered3d.com for Semilayered Slicer.\n",
        )

    def test_edit_to_a_file_that_is_gone_fails_naming_the_entry(self):
        table = table_with(EDITS=(Edit("src/removed.cpp", "a", "b", reason="gone upstream"),))
        with self.assertRaises(EditMismatch) as caught:
            apply(self.root, table)
        self.assertIn("src/removed.cpp", str(caught.exception))
        self.assertIn("gone upstream", str(caught.exception))

    def test_artwork_replaces_the_tracked_image_at_the_same_path(self):
        write(self.root, "semilayered/artwork/tree/resources/logo.png", b"replacement image")
        commit_all(self.root, "artwork")
        apply(self.root, FIXTURE_TABLE)
        self.assertEqual((self.root / "resources/logo.png").read_bytes(), b"replacement image")

    def test_artwork_for_a_path_that_is_not_tracked_fails(self):
        write(self.root, "semilayered/artwork/tree/resources/no_such_image.png", b"replacement image")
        commit_all(self.root, "artwork with nowhere to go")
        with self.assertRaises(ArtworkWithoutTarget) as caught:
            apply(self.root, FIXTURE_TABLE)
        self.assertIn("resources/no_such_image.png", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
