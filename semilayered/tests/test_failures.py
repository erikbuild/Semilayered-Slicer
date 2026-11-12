# ABOUTME: Tests for reading a finished CI run's failures and comparing them with the known-failure list.
# ABOUTME: Uses the job list and log excerpts of the real baseline run (43108415857) as fixtures.
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from semilayered.release.__main__ import main
from semilayered.release.failures import (
    KNOWN_FAILURES_FILE,
    Failure,
    failures_from,
    load_known,
    now_passing,
    parse_failed_slices,
    parse_failed_tests,
    unlisted,
)

FIXTURES = Path(__file__).parent / "fixtures"

LINUX_UNIT_TESTS_JOB = 130879325266
SLICE_CHECK_JOB = 130879325148

FAILED_TESTS = [
    "release_targets_platform: other platforms only is not an update here",
    "Nonplanar layers: hold back holds the safe part of a wall joined to a rim beside the top's highest point",
    "Each cube's raft is its support, centered below it",
]
FAILED_SLICES = [
    "Unlayered / Unlayered 5 Axis Printer 0.4 nozzle",
    "Unlayered / Unlayered 5 Axis Printer 0.6 nozzle",
    "Unlayered / Unlayered 5 Axis Printer 0.8 nozzle",
]
WINDOWS_BUILD = "Build Windows {} / Build Deps / Build Unlayered Slicer / Build Unlayered Slicer"
FLATPAK_STEP = "Run flatpak/flatpak-github-actions/flatpak-builder@master"


def fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def log_line(text: str) -> str:
    """One line as `gh run view --log-failed` prints it: job, step, then a timestamped message."""
    return f"Some job\tUNKNOWN STEP\t2026-11-12T00:26:34.8440371Z {text}\n"


class ParseLogsTest(unittest.TestCase):
    def test_failed_tests_are_read_from_ctest_output(self):
        self.assertEqual(parse_failed_tests(fixture("unit_tests_linux_log.txt")), FAILED_TESTS)

    def test_failed_slices_are_read(self):
        self.assertEqual(parse_failed_slices(fixture("slice_check_log.txt")), FAILED_SLICES)

    def test_log_without_a_failure_block_gives_no_tests(self):
        log = log_line("100% tests passed, 0 tests failed out of 3") + log_line("\t7 - Skipped earlier (Skipped)")
        self.assertEqual(parse_failed_tests(log), [])

    def test_names_with_brackets_and_other_outcomes_are_read_whole(self):
        log = (
            log_line("The following tests FAILED:")
            + log_line("\t12 - Scales (a) and (b) alike (Timeout)")
            + log_line("\t13 - Crashes on load (SEGFAULT) Geometry")
            + log_line("\t14 - Aborts (Subprocess aborted) Slicing Fast")
            + log_line("Errors while running CTest")
            + log_line("\t99 - Printed after the block (Failed)")
        )
        self.assertEqual(parse_failed_tests(log), ["Scales (a) and (b) alike", "Crashes on load", "Aborts"])


class FailuresFromJobsTest(unittest.TestCase):
    def setUp(self):
        jobs = json.loads(fixture("baseline_jobs.json"))
        logs = {LINUX_UNIT_TESTS_JOB: fixture("unit_tests_linux_log.txt"), SLICE_CHECK_JOB: fixture("slice_check_log.txt")}
        self.found = failures_from(jobs, lambda job_id: logs.get(job_id, ""))

    def test_each_failed_unit_test_is_its_own_failure(self):
        for name in FAILED_TESTS:
            with self.subTest(name=name):
                self.assertIn(Failure("test", "Linux x86_64 / Unit Tests", name), self.found)

    def test_each_failed_slice_is_its_own_failure(self):
        for printer in FAILED_SLICES:
            with self.subTest(printer=printer):
                self.assertIn(Failure("slice", "Slice check (Linux aarch64)", printer), self.found)

    def test_other_failed_jobs_are_reported_with_their_failed_step(self):
        self.assertIn(Failure("job", "Flatpak (x86_64, ubuntu-24.04)", FLATPAK_STEP), self.found)
        self.assertIn(Failure("job", WINDOWS_BUILD.format("x64"), "Check exception throw info Win"), self.found)
        self.assertIn(Failure("job", "Test Results", ""), self.found)

    def test_test_job_whose_log_names_no_test_is_reported_as_a_job(self):
        self.assertIn(Failure("job", "Linux aarch64 / Unit Tests", "Unpackage and Run Unit Tests"), self.found)
        self.assertNotIn(Failure("job", "Linux x86_64 / Unit Tests", "Unpackage and Run Unit Tests"), self.found)

    def test_jobs_that_did_not_fail_are_not_reported(self):
        self.assertEqual(len(self.found), 13)


class UnfinishedJobsTest(unittest.TestCase):
    """A run that was cancelled or timed out has not passed its checks, whatever its logs say."""

    def found(self, conclusion):
        jobs = [
            {"id": 1, "name": "Linux x86_64 / Unit Tests", "conclusion": conclusion, "steps": []},
            {"id": 2, "name": "Build macOS Universal", "conclusion": "success", "steps": []},
            {"id": 3, "name": "Publish dev build", "conclusion": "skipped", "steps": []},
        ]
        return failures_from(jobs, lambda job_id: fixture("unit_tests_linux_log.txt"))

    def test_cancelled_job_is_a_failure_of_the_job(self):
        self.assertEqual(self.found("cancelled"), {Failure("job", "Linux x86_64 / Unit Tests", "cancelled")})

    def test_timed_out_job_is_a_failure_of_the_job(self):
        self.assertEqual(self.found("timed_out"), {Failure("job", "Linux x86_64 / Unit Tests", "timed_out")})

    def test_job_that_has_not_finished_is_a_failure_of_the_job(self):
        self.assertEqual(self.found(None), {Failure("job", "Linux x86_64 / Unit Tests", "not finished")})


class KnownListTest(unittest.TestCase):
    def load(self, text: str):
        with tempfile.TemporaryDirectory() as holder:
            path = Path(holder) / "known.txt"
            path.write_text(text, encoding="utf-8")
            return load_known(path)

    def test_comments_and_blank_lines_are_ignored(self):
        known = self.load("# why this list exists\n\ntest\tLinux x86_64 / Unit Tests\tA test, with a comma\n")
        self.assertEqual(known, {Failure("test", "Linux x86_64 / Unit Tests", "A test, with a comma")})

    def test_a_dash_stands_for_no_item(self):
        self.assertEqual(self.load("job\tTest Results\t-\n"), {Failure("job", "Test Results", "")})

    def test_line_with_the_wrong_number_of_fields_is_named(self):
        with self.assertRaises(ValueError) as caught:
            self.load("# comment\njob\tFlatpak\tstep\ntest\tonly two fields\n")
        self.assertIn("line 3", str(caught.exception))

    def test_line_with_an_unknown_kind_is_named(self):
        with self.assertRaises(ValueError) as caught:
            self.load("build\tFlatpak\tstep\n")
        self.assertIn("line 1", str(caught.exception))

    def test_the_shipped_list_reads_cleanly(self):
        known = load_known(KNOWN_FAILURES_FILE)
        self.assertIn(Failure("test", "macOS arm64 / Unit Tests", FAILED_TESTS[2]), known)
        self.assertIn(Failure("job", "Test Results", ""), known)

    def test_unlisted_and_now_passing(self):
        listed, new, gone = Failure("job", "A", "x"), Failure("test", "B", "y"), Failure("slice", "C", "z")
        self.assertEqual(unlisted({listed, new}, {listed, gone}), {new})
        self.assertEqual(now_passing({listed, new}, {listed, gone}), {gone})


class GateCommandTest(unittest.TestCase):
    def gate(self, found):
        with tempfile.TemporaryDirectory() as holder:
            known = Path(holder) / "known.txt"
            known.write_text("job\tFlatpak\tbuild\ntest\tUnit Tests\tOld failure\n", encoding="utf-8")
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = main(["gate", "--run", "7", "--known", str(known)], run_failures=lambda run, repo: found)
            return code, out.getvalue()

    def test_passes_when_every_failure_is_listed(self):
        code, out = self.gate({Failure("job", "Flatpak", "build"), Failure("test", "Unit Tests", "Old failure")})
        self.assertEqual(code, 0)
        self.assertIn("2 known", out)

    def test_fails_and_names_a_failure_that_is_not_listed(self):
        code, out = self.gate({Failure("job", "Flatpak", "build"), Failure("test", "Unit Tests", "Brand new failure")})
        self.assertEqual(code, 1)
        self.assertIn("Brand new failure", out)

    def test_reports_a_listed_failure_that_did_not_happen_without_failing(self):
        code, out = self.gate({Failure("job", "Flatpak", "build")})
        self.assertEqual(code, 0)
        self.assertIn("Old failure", out)


if __name__ == "__main__":
    unittest.main()
