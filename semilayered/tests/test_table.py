# ABOUTME: Checks the real table against the real upstream tree, regenerated once in a scratch worktree.
# ABOUTME: Skipped when the upstream commit is not available in this clone.
import re
import subprocess
import unittest

from semilayered.rebrand import table
from semilayered.rebrand.checks import kept_identifier_drift, leftover_product_names, upstream_brand_images
from semilayered.rebrand.regenerate import scratch_regeneration
from semilayered.rebrand.tree import excluding_own_paths
from semilayered.tests.real_tree import ROOT, upstream_commit, upstream_file

# Text the design says must survive the rebrand exactly as upstream has it.
PROTECTED = {
    "unlayered3d.com",
    "Unlayered 3D",
    "Unlayered3D/RepRapFirmware",
    "X-Unlayered-",
    "UNLAYERED_NO_TELEMETRY",
    "UNLAYERED_VERSION",
    "UNLAYERED_MOD",
    "UnlayeredAccount",
    "unlayered-sys.json",
    "UnlayeredWebControl",
    "Unlayered 5 Axis Printer",
    "fdm_process_unlayered",
    "Sign in to Unlayered",
}

LEGAL_TEXTS = ("LICENSE.txt", "PRIVACY.md", "SECURITY.md", "resources/web/privacy/slicer-privacy-policy.html")


class RegeneratedUpstreamTreeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.commit = upstream_commit()
        if cls.commit is None:
            raise unittest.SkipTest("the upstream commit is not available in this clone")
        scratch = scratch_regeneration(ROOT, cls.commit)
        cls.tree = scratch.__enter__()
        cls.addClassCleanup(scratch.__exit__, None, None, None)

    def text(self, path: str) -> str:
        return (self.tree / path).read_text(encoding="utf-8")

    def assertAbsent(self, needle: str, path: str) -> None:
        self.assertEqual(self.text(path).count(needle), 0, f"{needle!r} is still in {path}")

    def assertPresent(self, needle: str, path: str) -> None:
        self.assertGreater(self.text(path).count(needle), 0, f"{needle!r} is not in {path}")

    def files_mentioning(self, needle: str) -> list:
        """Upstream files, other than the legal texts and the fork's own files, that contain needle."""
        exclusions = [f":(exclude){path}" for path in LEGAL_TEXTS] + excluding_own_paths(table)
        found = subprocess.run(
            ["git", "grep", "-l", "-I", "-F", "-e", needle, "--", ".", *exclusions],
            cwd=self.tree,
            capture_output=True,
            text=True,
        )
        return found.stdout.splitlines()

    def test_no_product_name_is_left(self):
        self.assertEqual(leftover_product_names(self.tree), [])

    def test_none_of_upstreams_brand_images_is_left(self):
        self.assertEqual(upstream_brand_images(self.tree, self.commit), [])

    def test_protected_text_keeps_its_count(self):
        self.assertEqual(kept_identifier_drift(self.tree, self.commit), [])

    def test_everything_the_design_protects_is_in_the_table(self):
        self.assertEqual(PROTECTED - set(table.KEPT_IDENTIFIERS), set())

    def test_legal_texts_are_word_for_word_upstreams(self):
        for path in LEGAL_TEXTS:
            with self.subTest(path=path):
                self.assertEqual((self.tree / path).read_bytes(), upstream_file(self.commit, path))

    def test_app_id_is_the_forks_everywhere(self):
        self.assertEqual(self.files_mentioning("com.unlayered3d"), [])
        self.assertPresent("io.github.erikbuild.SemilayeredSlicer", "src/dev-utils/platform/osx/Info.plist.in")
        for path in (
            "src/dev-utils/platform/unix/io.github.erikbuild.SemilayeredSlicer.desktop",
            "scripts/flatpak/io.github.erikbuild.SemilayeredSlicer.yml",
            "scripts/flatpak/io.github.erikbuild.SemilayeredSlicer.metainfo.xml",
        ):
            with self.subTest(path=path):
                self.assertTrue((self.tree / path).is_file())

    def test_source_links_point_at_the_fork(self):
        self.assertEqual(self.files_mentioning("Unlayered3D/Unlayered-Slicer"), [])
        self.assertEqual(self.files_mentioning("Unlayered3D/Semilayered-Slicer"), [])
        self.assertPresent("https://github.com/erikbuild/Semilayered-Slicer", "src/slic3r/GUI/WebAppBridge.cpp")

    def test_firmware_source_still_points_at_unlayered(self):
        self.assertPresent("Unlayered3D/RepRapFirmware", "README.md")

    def test_nothing_says_unlayered_3d_made_this_build(self):
        self.assertAbsent("Semilayered Slicer is developed by Unlayered 3D", "src/slic3r/GUI/AboutDialog.cpp")
        self.assertAbsent("Semilayered Slicer is Unlayered 3D's fork", "README.md")
        self.assertAbsent('CPACK_PACKAGE_VENDOR "Unlayered 3D"', "CMakeLists.txt")
        for path in (
            "src/dev-utils/platform/msw/SemilayeredSlicer.rc.in",
            "src/dev-utils/platform/msw/SemilayeredSlicer-gcodeviewer.rc.in",
            "scripts/msix/build_msix.ps1",
            ".github/workflows/build_slicer.yml",
        ):
            with self.subTest(path=path):
                self.assertAbsent('"Unlayered 3D"', path)
                self.assertAbsent("'Unlayered 3D'", path)
                self.assertAbsent("CN=Unlayered 3D", path)

    def test_readme_opens_by_saying_what_this_is(self):
        self.assertTrue(
            self.text("README.md").startswith("> **Semilayered Slicer is an unofficial build of Unlayered Slicer.**")
        )

    def test_about_still_credits_unlayered_3d(self):
        about = self.text("src/slic3r/GUI/AboutDialog.cpp")
        self.assertEqual(about.count("an unofficial build of Unlayered Slicer, which is developed by Unlayered 3D"), 2)
        self.assertPresent("Modifications Copyright(C) 2026 Unlayered 3D", "src/slic3r/GUI/AboutDialog.cpp")

    def test_installer_and_application_agree_on_the_registry_key(self):
        vendor = re.search(r'set \(CPACK_PACKAGE_VENDOR "([^"]+)"\)', self.text("CMakeLists.txt")).group(1)
        self.assertPresent(f'L"Software\\\\{vendor}\\\\Semilayered Slicer"', "src/slic3r/GUI/GUI_App.cpp")

    def test_nothing_a_user_can_reach_promises_self_updating(self):
        self.assertAbsent("keeps itself up to date", "src/slic3r/GUI/AutoUpdater.cpp")
        self.assertAbsent("keeps itself up to date", "src/slic3r/GUI/WebGuideDialog.cpp")
        self.assertAbsent("will stop updating itself", "src/slic3r/GUI/AutoUpdater.cpp")
        self.assertAbsent("so the slicer can update itself", "src/slic3r/GUI/MainFrame.cpp")
        self.assertAbsent("Check the Unlayered update site", "src/slic3r/GUI/Actions/PreferenceActions.cpp")

    def test_where_the_bare_name_meant_the_application_it_names_this_one(self):
        for upstream_wording in ("Unlayered prepares the print", "In Unlayered, slice", "Unlayered uses it to send"):
            with self.subTest(upstream_wording=upstream_wording):
                self.assertAbsent(upstream_wording, "src/slic3r/GUI/Plater.cpp")

    def test_consent_wording_is_left_as_upstream_wrote_it(self):
        self.assertPresent("Unlayered asks before uploading any model", "src/slic3r/GUI/ModelUploadConsentDialog.cpp")
        self.assertPresent("Unlayered asks you separately, for each model", "src/slic3r/GUI/Preferences.cpp")


if __name__ == "__main__":
    unittest.main()
