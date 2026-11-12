# ABOUTME: Tests for the checks that a tree is a pure regeneration, against a real git repository.
# ABOUTME: Covers leftover product names, kept identifiers, upstream brand images and reproducibility.
import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from semilayered.rebrand.__main__ import main
from semilayered.rebrand.checks import (
    differences_from_regeneration,
    kept_identifier_drift,
    leftover_product_names,
    reproduces,
    upstream_brand_images,
)
from semilayered.rebrand.regenerate import regenerate
from semilayered.tests.repo_fixture import FIXTURE_TABLE, LOGO_BYTES, commit_all, git, make_repo, write

CHECKED_TABLE = SimpleNamespace(
    **{
        **vars(FIXTURE_TABLE),
        "KEPT_PRODUCT_NAMES": (("resources/table.bin", "Unlayered Slicer", "data another program reads"),),
        "KEPT_IDENTIFIERS": {"unlayered3d.com": 0, "Unlayered 3D": 0},
        "BRAND_IMAGE_PATHS": ("resources/logo.png",),
    }
)


def table_with(**changes):
    return SimpleNamespace(**{**vars(CHECKED_TABLE), **changes})


class ChecksTest(unittest.TestCase):
    """Each test starts from a committed, cleanly regenerated tree."""

    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = make_repo(Path(temp.name))
        write(self.root, "semilayered/artwork/tree/resources/logo.png", b"replacement image")
        commit_all(self.root, "artwork")
        self.upstream = regenerate(self.root, "upstream", CHECKED_TABLE)
        commit_all(self.root, "regenerated")

    def add(self, path, content):
        write(self.root, path, content)
        git(self.root, "add", path)

    def test_clean_regenerated_tree_passes_every_check(self):
        self.assertEqual(leftover_product_names(self.root, CHECKED_TABLE), [])
        self.assertEqual(kept_identifier_drift(self.root, self.upstream, CHECKED_TABLE), [])
        self.assertEqual(upstream_brand_images(self.root, self.upstream, CHECKED_TABLE), [])
        self.assertEqual(differences_from_regeneration(self.root, self.upstream, CHECKED_TABLE), [])
        self.assertTrue(reproduces(self.root, self.upstream, CHECKED_TABLE))

    def test_leftover_in_text_is_reported_with_path_and_line(self):
        self.add("docs/more.md", "line one\nabout Unlayered Slicer\n")
        self.assertEqual(leftover_product_names(self.root, CHECKED_TABLE), ["docs/more.md:2: Unlayered Slicer"])

    def test_leftover_in_a_utf16_file_is_reported(self):
        for name, prefix in (("aligned.rc", b""), ("offset.rc", b"\x01")):
            with self.subTest(name=name):
                self.add("resources/" + name, prefix + "Unlayered Slicer".encode("utf-16-le"))
                found = leftover_product_names(self.root, CHECKED_TABLE)
                self.assertEqual(len([line for line in found if line.startswith("resources/" + name)]), 1)

    def test_leftover_in_a_path_is_reported(self):
        self.add("docs/UnlayeredSlicer-notes.txt", "nothing in here\n")
        found = leftover_product_names(self.root, CHECKED_TABLE)
        self.assertEqual(len(found), 1)
        self.assertIn("docs/UnlayeredSlicer-notes.txt", found[0])

    def test_listed_leftover_is_allowed_only_in_its_own_file(self):
        sentence = "An unofficial build of Unlayered Slicer.\n"
        self.add("docs/credit.md", sentence)
        self.add("docs/elsewhere.md", sentence)
        table = table_with(
            KEPT_PRODUCT_NAMES=CHECKED_TABLE.KEPT_PRODUCT_NAMES
            + (("docs/credit.md", "An unofficial build of Unlayered Slicer.", "attribution"),)
        )
        self.assertEqual(leftover_product_names(self.root, table), ["docs/elsewhere.md:1: Unlayered Slicer"])

    def test_kept_text_that_is_gone_is_reported(self):
        table = table_with(
            KEPT_PRODUCT_NAMES=CHECKED_TABLE.KEPT_PRODUCT_NAMES
            + (("docs/notes.md", "Unlayered Slicer is credited here", "attribution"),)
        )
        found = leftover_product_names(self.root, table)
        self.assertEqual(len(found), 1)
        self.assertIn("docs/notes.md", found[0])
        self.assertIn("Unlayered Slicer is credited here", found[0])

    def test_kept_identifier_that_was_renamed_is_reported(self):
        source = self.root / "src/SemilayeredSlicer.cpp"
        source.write_text(source.read_text().replace("unlayered3d.com", "example.com"))
        drift = kept_identifier_drift(self.root, self.upstream, CHECKED_TABLE)
        self.assertEqual(len(drift), 1)
        self.assertIn("unlayered3d.com", drift[0])
        self.assertIn("2", drift[0])
        self.assertIn("1", drift[0])

    def test_kept_identifier_may_change_by_its_allowed_difference(self):
        self.add("docs/credit.md", "Not affiliated with Unlayered 3D.\n")
        self.assertEqual(len(kept_identifier_drift(self.root, self.upstream, CHECKED_TABLE)), 1)
        allowed = table_with(KEPT_IDENTIFIERS={"unlayered3d.com": 0, "Unlayered 3D": 1})
        self.assertEqual(kept_identifier_drift(self.root, self.upstream, allowed), [])

    def test_upstream_brand_image_left_in_place_is_reported(self):
        (self.root / "resources/logo.png").write_bytes(LOGO_BYTES)
        found = upstream_brand_images(self.root, self.upstream, CHECKED_TABLE)
        self.assertEqual(len(found), 1)
        self.assertIn("resources/logo.png", found[0])

    def test_brand_image_path_that_upstream_does_not_have_is_reported(self):
        table = table_with(BRAND_IMAGE_PATHS=("resources/logo.png", "resources/gone.png"))
        found = upstream_brand_images(self.root, self.upstream, table)
        self.assertEqual(len(found), 1)
        self.assertIn("resources/gone.png", found[0])

    def test_hand_edit_to_an_upstream_file_breaks_reproduction(self):
        with open(self.root / "docs/notes.md", "a") as notes:
            notes.write("edited by hand\n")
        self.assertFalse(reproduces(self.root, self.upstream, CHECKED_TABLE))
        differences = differences_from_regeneration(self.root, self.upstream, CHECKED_TABLE)
        self.assertEqual(len(differences), 1)
        self.assertIn("docs/notes.md", differences[0])

    def test_checking_does_not_disturb_the_index_or_the_tree(self):
        with open(self.root / "docs/notes.md", "a") as notes:
            notes.write("edited by hand\n")
        status_before = git(self.root, "status", "--porcelain")
        reproduces(self.root, self.upstream, CHECKED_TABLE)
        self.assertEqual(git(self.root, "status", "--porcelain"), status_before)


class CheckCommandTest(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = make_repo(Path(temp.name))
        write(self.root, "semilayered/artwork/tree/resources/logo.png", b"replacement image")
        commit_all(self.root, "artwork")

    def run_main(self, *arguments):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = main(list(arguments), root=self.root, table=CHECKED_TABLE)
        return code, out.getvalue(), err.getvalue()

    def test_check_passes_on_a_regenerated_tree(self):
        self.assertEqual(self.run_main("regenerate", "upstream")[0], 0)
        commit_all(self.root, "regenerated")
        code, out, _ = self.run_main("check")
        self.assertEqual(code, 0, out)

    def test_check_fails_and_prints_each_finding(self):
        self.run_main("regenerate", "upstream")
        commit_all(self.root, "regenerated")
        write(self.root, "docs/more.md", "about Unlayered Slicer\n")
        git(self.root, "add", "docs/more.md")
        code, out, _ = self.run_main("check")
        self.assertEqual(code, 1)
        self.assertIn("docs/more.md:1: Unlayered Slicer", out)

    def test_check_before_anything_was_regenerated_says_so(self):
        code, _, err = self.run_main("check")
        self.assertEqual(code, 1)
        self.assertIn("regenerate", err)


if __name__ == "__main__":
    unittest.main()
