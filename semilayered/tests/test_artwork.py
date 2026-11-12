# ABOUTME: Tests that every upstream brand image has a replacement of the same format and size.
# ABOUTME: Compares the generated artwork with the images in the upstream commit; skipped without that commit.
import unittest

from semilayered.rebrand import table
from semilayered.rebrand.names import rename_path
from semilayered.rebrand.tree import ARTWORK_TREE
from semilayered.tests.image_info import ico_entries, icns_pixel_sizes, png_size, svg_geometry
from semilayered.tests.real_tree import ROOT, upstream_commit, upstream_file

ARTWORK = ROOT / ARTWORK_TREE

# Elements the application's SVG renderer does not draw.
UNDRAWN_SVG_ELEMENTS = ("<text", "<style", "<filter", "<mask", "<clipPath", "<image", "<use")


class ArtworkTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.commit = upstream_commit()
        if cls.commit is None:
            raise unittest.SkipTest("the upstream commit is not available in this clone")

    def pairs(self):
        """Yield (upstream path, upstream bytes, replacement bytes) for every brand image."""
        for path in table.BRAND_IMAGE_PATHS:
            yield path, upstream_file(self.commit, path), (ARTWORK / rename_path(path)).read_bytes()

    def test_every_brand_image_has_a_replacement_and_nothing_else_does(self):
        expected = {rename_path(path) for path in table.BRAND_IMAGE_PATHS}
        actual = {file.relative_to(ARTWORK).as_posix() for file in ARTWORK.rglob("*") if file.is_file()}
        self.assertEqual(len(expected), 26)
        self.assertEqual(actual, expected)

    def test_replacements_have_the_format_and_size_of_the_image_they_replace(self):
        for path, theirs, ours in self.pairs():
            with self.subTest(path=path):
                if path.endswith(".png"):
                    self.assertEqual(png_size(ours), png_size(theirs))
                elif path.endswith(".ico"):
                    self.assertEqual(ico_entries(ours), ico_entries(theirs))
                elif path.endswith(".icns"):
                    self.assertEqual(icns_pixel_sizes(theirs) - icns_pixel_sizes(ours), set())
                elif path.endswith(".svg"):
                    self.assertEqual(svg_geometry(ours.decode("utf-8")), svg_geometry(theirs.decode("utf-8")))
                else:
                    self.fail("an image format these tests do not know how to compare")

    def test_svgs_use_only_what_the_application_draws(self):
        for path, _theirs, ours in self.pairs():
            if path.endswith(".svg"):
                for element in UNDRAWN_SVG_ELEMENTS:
                    with self.subTest(path=path, element=element):
                        self.assertNotIn(element, ours.decode("utf-8"))

    def test_no_replacement_is_the_upstream_image(self):
        for path, theirs, ours in self.pairs():
            with self.subTest(path=path):
                self.assertNotEqual(ours, theirs)


if __name__ == "__main__":
    unittest.main()
