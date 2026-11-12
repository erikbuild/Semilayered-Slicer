# ABOUTME: Tests for renaming the product name in text and in paths.
# ABOUTME: Covers every spelling, the uses of "Unlayered" that must stay, and finding leftovers.
import unittest

from semilayered.rebrand.names import find_product_names, rename_path, rename_text

RENAMED = {
    "Unlayered Slicer": "Semilayered Slicer",
    "UnlayeredSlicer": "SemilayeredSlicer",
    "unlayered-slicer.exe": "semilayered-slicer.exe",
    "Unlayered-Slicer/build": "Semilayered-Slicer/build",
    "Unlayered_Slicer_Mac_universal_": "Semilayered_Slicer_Mac_universal_",
    "unlayered_slicer_main": "semilayered_slicer_main",
    "unlayeredslicer://open": "semilayeredslicer://open",
    " Unlayered.Slicer.1": " Semilayered.Slicer.1",
    "UNLAYEREDSLICER_TAG": "SEMILAYEREDSLICER_TAG",
    "OtherUnlayeredSlicerInstanceMessage": "OtherSemilayeredSlicerInstanceMessage",
    "Unlayered Slicer G-code Viewer": "Semilayered Slicer G-code Viewer",
    "Unlayered3D/Unlayered-Slicer": "Unlayered3D/Semilayered-Slicer",
}

UNTOUCHED = [
    "Unlayered 3D",
    "Unlayered3D/RepRapFirmware",
    "https://unlayered3d.com/slicer/latest.json",
    "UNLAYERED_VERSION",
    "UNLAYERED_MOD",
    "UNLAYERED_NO_TELEMETRY",
    "UnlayeredAccount",
    "X-Unlayered-Install",
    "0:/sys/unlayered-sys.json",
    "Sign in to Unlayered",
    "Unlayered 5 Axis Printer",
    "fdm_process_unlayered_common",
    "UnlayeredWebControl-SD.zip",
    "when an Unlayered\nprinter is found",
    "Unlayered 3D slicer settings",
]

# Spellings the rename does not handle. Each must still be found, so a tree holding one is rejected.
UNHANDLED_FORMS = [
    'Unlayered "\n"Slicer',
    "Unlayered\n// Slicer",
    "Unlayered&nbsp;Slicer",
    "Unlayered%20Slicer",
    "UnLayered Slicer",
]


class RenameTextTest(unittest.TestCase):
    def test_every_spelling_is_renamed(self):
        for before, after in RENAMED.items():
            with self.subTest(before=before):
                self.assertEqual(rename_text(before), after)

    def test_other_uses_of_the_word_are_untouched(self):
        for text in UNTOUCHED:
            with self.subTest(text=text):
                self.assertEqual(rename_text(text), text)
                self.assertEqual(find_product_names(text), [])

    def test_renaming_twice_changes_nothing(self):
        for before, after in RENAMED.items():
            with self.subTest(before=before):
                self.assertEqual(rename_text(after), after)

    def test_name_inside_longer_text_is_renamed_in_place(self):
        self.assertEqual(
            rename_text('title = "Unlayered Slicer - " + name; // by Unlayered 3D\nexe = unlayered-slicer'),
            'title = "Semilayered Slicer - " + name; // by Unlayered 3D\nexe = semilayered-slicer',
        )


class RenamePathTest(unittest.TestCase):
    def test_file_name_is_renamed(self):
        self.assertEqual(rename_path("src/UnlayeredSlicer_app_msvc.cpp"), "src/SemilayeredSlicer_app_msvc.cpp")

    def test_directory_names_are_renamed(self):
        self.assertEqual(
            rename_path("build/UnlayeredSlicer/UnlayeredSlicer.app/Contents"),
            "build/SemilayeredSlicer/SemilayeredSlicer.app/Contents",
        )

    def test_path_naming_the_printer_is_untouched(self):
        path = "resources/profiles/Unlayered/machine/Unlayered 5 Axis Printer.json"
        self.assertEqual(rename_path(path), path)


class FindProductNamesTest(unittest.TestCase):
    def test_reports_line_number_and_matched_text(self):
        self.assertEqual(
            find_product_names("first line\nsecond has Unlayered Slicer in it\nthird"),
            [(2, "Unlayered Slicer")],
        )

    def test_unhandled_forms_are_found_after_renaming(self):
        for form in UNHANDLED_FORMS:
            with self.subTest(form=form):
                found = find_product_names(rename_text("first line\n" + form))
                self.assertEqual(len(found), 1)
                self.assertEqual(found[0][0], 2)

    def test_nothing_is_left_after_an_ordinary_rename(self):
        for before in RENAMED:
            with self.subTest(before=before):
                self.assertEqual(find_product_names(rename_text(before)), [])


if __name__ == "__main__":
    unittest.main()
