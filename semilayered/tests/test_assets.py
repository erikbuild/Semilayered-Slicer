# ABOUTME: Tests for naming a release and collecting its installers from a build run's downloaded artifacts.
# ABOUTME: Works on made-up artifact directories laid out the way `gh run download` leaves them.
import contextlib
import hashlib
import io
import tempfile
import unittest
import zipfile
from pathlib import Path

from semilayered.release.__main__ import main
from semilayered.release.assets import (
    MissingAsset,
    collect,
    expected_assets,
    release_tag,
    release_title,
    upstream_version,
)

EXPECTED_FOR_0_1_10 = [
    ("Semilayered_Slicer_Windows_V0.1.10_x64", "Semilayered_Slicer_Windows_Installer_V0.1.10_x64.exe"),
    ("Semilayered_Slicer_Windows_V0.1.10_arm64", "Semilayered_Slicer_Windows_Installer_V0.1.10_arm64.exe"),
    ("Semilayered_Slicer_Windows_V0.1.10_x64_portable", "Semilayered_Slicer_Windows_V0.1.10_x64_portable.zip"),
    ("Semilayered_Slicer_Windows_V0.1.10_arm64_portable", "Semilayered_Slicer_Windows_V0.1.10_arm64_portable.zip"),
    ("Semilayered_Slicer_Mac_universal_V0.1.10", "Semilayered_Slicer_Mac_universal_V0.1.10.dmg"),
    ("Semilayered_Slicer_Linux_ubuntu_2404_V0.1.10", "Semilayered_Slicer_Linux_AppImage_Ubuntu2404_V0.1.10.AppImage"),
    (
        "Semilayered_Slicer_Linux_ubuntu_2404_aarch64_V0.1.10",
        "Semilayered_Slicer_Linux_AppImage_Ubuntu2404_aarch64_V0.1.10.AppImage",
    ),
]

VERSION_INC = """\
set(SLIC3R_APP_NAME "Semilayered Slicer")
set(UNLAYERED_VERSION "0.1.10")
set(SLIC3R_VERSION "02.08.01.55")
"""


def downloaded_artifacts(parent: Path) -> Path:
    """Lay out one directory per artifact, as `gh run download` does, and return their parent."""
    artifacts = parent / "artifacts"
    for artifact, published in EXPECTED_FOR_0_1_10:
        directory = artifacts / artifact
        directory.mkdir(parents=True)
        if artifact.endswith("_portable"):
            (directory / "semilayered-slicer.exe").write_bytes(b"exe for " + artifact.encode())
            (directory / "resources" / "profiles").mkdir(parents=True)
            (directory / "resources" / "profiles" / "Unlayered.json").write_text("{}")
        else:
            (directory / published).write_bytes(b"installer for " + artifact.encode())
    (artifacts / "PDB").mkdir()
    (artifacts / "PDB" / "symbols.7z").write_bytes(b"not published")
    return artifacts


class NamingTest(unittest.TestCase):
    def test_tag_and_title_carry_the_upstream_version_and_the_build_number(self):
        self.assertEqual(release_tag("0.1.10", 7), "semilayered-0.1.10-b7")
        self.assertEqual(release_title("0.1.10", 7), "Semilayered Slicer 0.1.10 (build 7)")

    def test_version_is_read_from_version_inc(self):
        with tempfile.TemporaryDirectory() as holder:
            (Path(holder) / "version.inc").write_text(VERSION_INC)
            self.assertEqual(upstream_version(Path(holder)), "0.1.10")

    def test_version_inc_without_the_version_is_an_error(self):
        with tempfile.TemporaryDirectory() as holder:
            (Path(holder) / "version.inc").write_text('set(SLIC3R_VERSION "02.08.01.55")\n')
            with self.assertRaises(ValueError):
                upstream_version(Path(holder))

    def test_expected_assets_for_0_1_10(self):
        self.assertEqual(expected_assets("0.1.10"), EXPECTED_FOR_0_1_10)


class CollectTest(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.holder = Path(temp.name)
        self.artifacts = downloaded_artifacts(self.holder)
        self.out = self.holder / "release"

    def test_copies_each_installer_under_its_published_name(self):
        collected = collect(self.artifacts, self.out, "0.1.10")
        self.assertEqual(
            sorted(path.name for path in collected),
            sorted([published for _, published in EXPECTED_FOR_0_1_10] + ["SHA256SUMS"]),
        )
        self.assertEqual(
            (self.out / "Semilayered_Slicer_Mac_universal_V0.1.10.dmg").read_bytes(),
            b"installer for Semilayered_Slicer_Mac_universal_V0.1.10",
        )
        self.assertFalse((self.out / "symbols.7z").exists())

    def test_zips_a_portable_build_under_one_top_folder(self):
        collect(self.artifacts, self.out, "0.1.10")
        with zipfile.ZipFile(self.out / "Semilayered_Slicer_Windows_V0.1.10_x64_portable.zip") as portable:
            self.assertEqual(
                sorted(portable.namelist()),
                ["SemilayeredSlicer/resources/profiles/Unlayered.json", "SemilayeredSlicer/semilayered-slicer.exe"],
            )
            self.assertEqual(
                portable.read("SemilayeredSlicer/semilayered-slicer.exe"),
                b"exe for Semilayered_Slicer_Windows_V0.1.10_x64_portable",
            )

    def test_writes_a_checksum_for_every_file(self):
        collect(self.artifacts, self.out, "0.1.10")
        lines = (self.out / "SHA256SUMS").read_text().splitlines()
        self.assertEqual(len(lines), 7)
        for line in lines:
            digest, name = line.split("  ", 1)
            with self.subTest(name=name):
                self.assertEqual(hashlib.sha256((self.out / name).read_bytes()).hexdigest(), digest)

    def test_names_the_missing_artifact_and_writes_nothing(self):
        missing = "Semilayered_Slicer_Linux_ubuntu_2404_aarch64_V0.1.10"
        for file in (self.artifacts / missing).iterdir():
            file.unlink()
        (self.artifacts / missing).rmdir()
        with self.assertRaises(MissingAsset) as caught:
            collect(self.artifacts, self.out, "0.1.10")
        self.assertIn(missing, str(caught.exception))
        self.assertFalse(self.out.exists() and any(self.out.iterdir()))

    def test_names_an_installer_missing_from_its_artifact(self):
        installer = self.artifacts / EXPECTED_FOR_0_1_10[0][0] / EXPECTED_FOR_0_1_10[0][1]
        installer.rename(installer.with_name("Something_else.exe"))
        with self.assertRaises(MissingAsset) as caught:
            collect(self.artifacts, self.out, "0.1.10")
        self.assertIn(EXPECTED_FOR_0_1_10[0][1], str(caught.exception))

    def test_refuses_an_output_directory_that_is_not_empty(self):
        self.out.mkdir()
        (self.out / "left_over.txt").write_text("from an earlier run")
        with self.assertRaises(ValueError):
            collect(self.artifacts, self.out, "0.1.10")


class CommandTest(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        (self.root / "version.inc").write_text(VERSION_INC)

    def run_main(self, *arguments):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = main(list(arguments), root=self.root)
        return code, out.getvalue(), err.getvalue()

    def test_tag_prints_the_tag_for_a_build(self):
        self.assertEqual(self.run_main("tag", "--build", "12"), (0, "semilayered-0.1.10-b12\n", ""))

    def test_collect_reports_a_missing_artifact_and_exits_1(self):
        artifacts = downloaded_artifacts(self.root)
        (artifacts / "Semilayered_Slicer_Mac_universal_V0.1.10" / "Semilayered_Slicer_Mac_universal_V0.1.10.dmg").unlink()
        code, _, err = self.run_main("collect", "--artifacts", str(artifacts), "--out", str(self.root / "release"))
        self.assertEqual(code, 1)
        self.assertIn("Semilayered_Slicer_Mac_universal_V0.1.10.dmg", err)

    def test_collect_lists_what_it_collected(self):
        artifacts = downloaded_artifacts(self.root)
        code, out, _ = self.run_main("collect", "--artifacts", str(artifacts), "--out", str(self.root / "release"))
        self.assertEqual(code, 0)
        self.assertEqual(len(out.splitlines()), 8)


if __name__ == "__main__":
    unittest.main()
