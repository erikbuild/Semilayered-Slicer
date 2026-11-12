# ABOUTME: Tests for rebuilding the working tree from an upstream commit, against a real git repository.
# ABOUTME: Covers the first regeneration, a later source drop recorded as a merge, and scratch regenerations.
import contextlib
import io
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from semilayered.rebrand.__main__ import main
from semilayered.rebrand.edits import Edit, EditMismatch
from semilayered.rebrand.regenerate import DirtyTree, regenerate, scratch_regeneration
from semilayered.tests.repo_fixture import FIXTURE_TABLE, OWN_FILES, advance_upstream, commit_all, git, make_repo, write

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


class RegenerateTest(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = make_repo(Path(temp.name))
        self.upstream = git(self.root, "rev-parse", "upstream").strip()

    def test_regenerates_from_an_upstream_ref(self):
        used = regenerate(self.root, "upstream", FIXTURE_TABLE)
        self.assertEqual(used, self.upstream)
        self.assertEqual((self.root / "semilayered/upstream_commit").read_text(), self.upstream + "\n")
        self.assertEqual((self.root / "src/SemilayeredSlicer.hpp").read_text(), '#define APP_NAME "Semilayered Slicer"\n')
        for path, content in OWN_FILES.items():
            with self.subTest(path=path):
                self.assertEqual((self.root / path).read_text(), content)

    def test_everything_is_staged_and_nothing_is_committed(self):
        head_before = git(self.root, "rev-parse", "HEAD")
        regenerate(self.root, "upstream", FIXTURE_TABLE)
        self.assertEqual(git(self.root, "rev-parse", "HEAD"), head_before)
        status = git(self.root, "status", "--porcelain").splitlines()
        self.assertTrue(status)
        self.assertEqual([line for line in status if line[1] != " "], [])

    def test_later_source_drop_is_recorded_as_a_merge(self):
        regenerate(self.root, "upstream", FIXTURE_TABLE)
        commit_all(self.root, "regenerated from upstream source 1")
        newer = advance_upstream(self.root)
        self.assertEqual(regenerate(self.root, "upstream", FIXTURE_TABLE), newer)
        git(self.root, "commit", "-qm", "regenerated from upstream source 2")
        parents = git(self.root, "rev-list", "--parents", "-n1", "HEAD").split()[1:]
        self.assertEqual(len(parents), 2)
        self.assertEqual(parents[1], newer)
        self.assertEqual((self.root / "src/extra.cpp").read_text(), "// Added later to Semilayered Slicer\n")

    def test_file_deleted_upstream_disappears(self):
        regenerate(self.root, "upstream", FIXTURE_TABLE)
        commit_all(self.root, "regenerated from upstream source 1")
        self.assertTrue((self.root / "old_only.txt").exists())
        advance_upstream(self.root)
        regenerate(self.root, "upstream", FIXTURE_TABLE)
        self.assertFalse((self.root / "old_only.txt").exists())
        self.assertNotIn("old_only.txt", git(self.root, "ls-files").splitlines())

    def test_without_a_ref_it_uses_the_recorded_commit(self):
        regenerate(self.root, "upstream", FIXTURE_TABLE)
        commit_all(self.root, "regenerated from upstream source 1")
        advance_upstream(self.root)
        changed = SimpleNamespace(
            **{**vars(FIXTURE_TABLE), "EDITS": (Edit("docs/notes.md", "Made by Unlayered 3D.", "Made by Unlayered 3D, built elsewhere."),)}
        )
        self.assertEqual(regenerate(self.root, None, changed), self.upstream)
        self.assertIn("built elsewhere", (self.root / "docs/notes.md").read_text())
        self.assertFalse((self.root / "src/extra.cpp").exists())

    def test_failed_regeneration_leaves_the_checkout_as_it_was(self):
        regenerate(self.root, "upstream", FIXTURE_TABLE)
        commit_all(self.root, "regenerated from upstream source 1")
        advance_upstream(self.root)
        head_before = git(self.root, "rev-parse", "HEAD")
        stale = SimpleNamespace(
            **{**vars(FIXTURE_TABLE), "EDITS": (Edit("docs/notes.md", "text upstream has since removed", "anything"),)}
        )
        with self.assertRaises(EditMismatch):
            regenerate(self.root, "upstream", stale)
        self.assertEqual(git(self.root, "status", "--porcelain"), "")
        self.assertEqual(git(self.root, "rev-parse", "HEAD"), head_before)
        self.assertFalse((self.root / ".git" / "MERGE_HEAD").exists())
        self.assertEqual(len(git(self.root, "worktree", "list").splitlines()), 1)
        self.assertTrue((self.root / "src/SemilayeredSlicer.cpp").exists())

    def test_refuses_a_dirty_tree(self):
        write(self.root, "docs/notes.md", "work in progress\n")
        with self.assertRaises(DirtyTree):
            regenerate(self.root, "upstream", FIXTURE_TABLE)
        self.assertEqual((self.root / "docs/notes.md").read_text(), "work in progress\n")

    def test_command_regenerates_and_reports_the_commit(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = main(["regenerate", "upstream"], root=self.root, table=FIXTURE_TABLE)
        self.assertEqual(code, 0)
        self.assertIn(self.upstream, out.getvalue())
        self.assertTrue((self.root / "src/SemilayeredSlicer.cpp").exists())

    def test_command_reports_a_dirty_tree_and_exits_1(self):
        write(self.root, "docs/notes.md", "work in progress\n")
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            code = main(["regenerate", "upstream"], root=self.root, table=FIXTURE_TABLE)
        self.assertEqual(code, 1)
        self.assertIn("uncommitted changes", err.getvalue())

    def test_module_runs_as_a_command(self):
        result = subprocess.run(
            [sys.executable, "-m", "semilayered.rebrand", "--help"],
            cwd=self.root,
            env={**os.environ, "PYTHONPATH": str(REPOSITORY_ROOT)},
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("regenerate", result.stdout)


class ScratchRegenerationTest(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = make_repo(Path(temp.name))
        self.upstream = git(self.root, "rev-parse", "upstream").strip()

    def test_builds_the_regenerated_tree_somewhere_else(self):
        with scratch_regeneration(self.root, self.upstream, FIXTURE_TABLE) as scratch:
            self.assertNotEqual(scratch, self.root)
            self.assertEqual((scratch / "src/SemilayeredSlicer.hpp").read_text(), '#define APP_NAME "Semilayered Slicer"\n')

    def test_leaves_the_real_tree_alone_and_cleans_up(self):
        status_before = git(self.root, "status", "--porcelain")
        with scratch_regeneration(self.root, self.upstream, FIXTURE_TABLE) as scratch:
            where = scratch
        self.assertEqual(git(self.root, "status", "--porcelain"), status_before)
        self.assertTrue((self.root / "src/UnlayeredSlicer.cpp").exists())
        self.assertFalse(where.exists())
        self.assertEqual(len(git(self.root, "worktree", "list").splitlines()), 1)

    def test_uses_the_own_files_as_they_are_now(self):
        write(self.root, "semilayered/README.md", "edited but not committed\n")
        write(self.root, "semilayered/added.txt", "not even tracked\n")
        with scratch_regeneration(self.root, self.upstream, FIXTURE_TABLE) as scratch:
            self.assertEqual((scratch / "semilayered/README.md").read_text(), "edited but not committed\n")
            self.assertEqual((scratch / "semilayered/added.txt").read_text(), "not even tracked\n")


if __name__ == "__main__":
    unittest.main()
