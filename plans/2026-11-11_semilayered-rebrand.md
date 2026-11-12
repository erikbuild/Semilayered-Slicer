# Semilayered Slicer Rebrand and Automatic Builds Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn upstream's Unlayered Slicer tree into Semilayered Slicer with a re-runnable tool, and publish account-free installers for Windows, macOS and Linux as a GitHub Release on every push to `main`.

**Architecture:** A Python package, `semilayered.rebrand`, regenerates the whole tree from an upstream commit: rename the product name, apply a table of explicit edits, install replacement artwork. The committed tree always equals that output plus the fork's own files, and a check proves it. A second package, `semilayered.release`, judges a finished "Build all" run against a list of upstream's known failures, collects the installers and writes release notes; two small workflows call it.

**Tech Stack:** Python 3.9+ standard library and `unittest`; `git` and `gh` as subprocesses; GitHub Actions; Swift (macOS only) for the artwork generator.

**Spec:** `plans/2026-11-11_semilayered-rebrand_design.md`. Read it first; this plan argues from it.

## Global Constraints

- Only Erik commits and pushes. A "Commit" step means: stop, show `git status`, propose the message, and wait. No `Co-Authored-By` or "Generated with" trailers.
- Upstream's files are never edited by hand. Every change to them comes from running the tool.
- Own files are exactly: `semilayered/`, `plans/`, `.github/workflows/semilayered_*.yml`.
- New name: `Semilayered Slicer`. App ID: `io.github.erikbuild.SemilayeredSlicer`. Repository: `erikbuild/Semilayered-Slicer`. Vendor and publisher text: `Semilayered Slicer contributors`. Releases page: `https://github.com/erikbuild/Semilayered-Slicer/releases`.
- Every code file starts with two comment lines beginning `ABOUTME: `.
- Names and comments describe what the code does now. No "new", "old", "legacy", "wrapper", no history.
- Python: 3.9-compatible, standard library only. Tests run with `python3 -m unittest discover -s semilayered/tests -t .` from the repository root and print nothing but the unittest summary.
- Tests use real git repositories in temporary directories and real log excerpts. No mocks of the code under test.
- Steps marked **(Erik's OK)** touch his machine or his GitHub account: installing packages, launching apps, dispatching workflows, creating releases. Ask at that step.
- Stop and bring the options to Erik if: the Windows safety check fails once it runs; a CI failure is neither on the known-failure list nor explained by the rename; the local build fails for a reason that is not the rename.
- Debugging any failure follows superpowers:systematic-debugging: cause first, one fix at a time.

## Review Focus

1. A later source drop writes the product name in a form the rename pattern misses (wrapped across lines, `Unlayered&nbsp;Slicer`, `Unlayered%20Slicer`). Expected: `check` fails and names the file and line. Pinned in Task 1.
2. A renamed path collides with a path that already exists. Expected: the tool stops with both paths in the message and overwrites nothing. Pinned in Task 3.
3. The name sits in a file that is not UTF-8 text (UTF-16 resource script, binary). Expected: `check` reports the file instead of passing silently. Pinned in Task 4.
4. An explicit edit's text is gone or appears a different number of times after upstream changes it. Expected: the tool fails naming the entry and the count found, and a second run of a successful regeneration changes nothing. Pinned in Tasks 2 and 3.
5. "Build all" finishes on another branch, is re-run, or produces a build number that was already released. Expected: nothing is published twice and nothing is published from a branch other than `main`. Pinned in Tasks 11 and 12.

## File Structure

| Path | Responsibility |
|---|---|
| `semilayered/__init__.py`, `semilayered/README.md` | Package marker; how to take a source drop and what each command does |
| `semilayered/rebrand/names.py` | The product-name pattern: rename text and paths, find leftovers |
| `semilayered/rebrand/edits.py` | `Edit` and `Substitution` types and how one is applied or rejected |
| `semilayered/rebrand/table.py` | Data only: own paths, verbatim files, substitutions, edits, allowed leftovers, kept identifiers, brand image paths |
| `semilayered/rebrand/tree.py` | Walk tracked files and apply names, substitutions, path renames, edits and artwork to a tree |
| `semilayered/rebrand/regenerate.py` | Rebuild a working tree from an upstream commit plus own files; record the upstream commit |
| `semilayered/rebrand/checks.py` | The invariants: leftovers, kept identifiers, upstream brand images, reproducibility |
| `semilayered/rebrand/__main__.py` | CLI: `regenerate [ref]`, `check` |
| `semilayered/upstream_commit` | One line: the upstream commit the tree was generated from |
| `semilayered/artwork/generate.swift`, `semilayered/artwork/src/` | Artwork sources and generator (macOS only) |
| `semilayered/artwork/tree/` | Generated images at the repository-relative paths they are installed to |
| `semilayered/release/failures.py` | Read a run's failures; compare with the known list |
| `semilayered/release/known_upstream_failures.txt` | The known-failure list for the current source drop |
| `semilayered/release/assets.py` | Version, tag, expected installers, collection, checksums |
| `semilayered/release/notes.py` | Release notes text |
| `semilayered/release/__main__.py` | CLI: `gate`, `collect`, `notes`, `tag` |
| `semilayered/tests/` | Unit and integration tests and log fixtures |
| `semilayered/tests/e2e/behaviour_checks.py`, `semilayered/tests/e2e/verify_release.py` | Checks on a built app; checks on a published release |
| `.github/workflows/semilayered_build_on_push.yml` | On push to `main`: run checks, then start "Build all" |
| `.github/workflows/semilayered_publish_release.yml` | When "Build all" completes on `main`: gate, collect, publish |

---

## Phase 1: the rebrand tool (no changes to upstream's files yet)

### Task 1: Product-name renaming

**Files:**
- Create: `semilayered/__init__.py`, `semilayered/rebrand/__init__.py`, `semilayered/rebrand/names.py`
- Test: `semilayered/tests/__init__.py`, `semilayered/tests/test_names.py`

**Interfaces:**
- Produces: `rename_text(text: str) -> str`; `rename_path(path: str) -> str` (each path component renamed); `find_product_names(text: str) -> list[tuple[int, str]]` returning `(line number, matched text)` for every occurrence, including forms `rename_text` does not handle.

- [ ] **Step 1: Write the failing tests**

```python
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
    "Unlayered 3D", "Unlayered3D/RepRapFirmware", "https://unlayered3d.com/slicer/latest.json",
    "UNLAYERED_VERSION", "UNLAYERED_MOD", "UNLAYERED_NO_TELEMETRY", "UnlayeredAccount",
    "X-Unlayered-Install", "0:/sys/unlayered-sys.json", "Sign in to Unlayered",
    "Unlayered 5 Axis Printer", "fdm_process_unlayered_common", "UnlayeredWebControl-SD.zip",
    "when an Unlayered\nprinter is found", "Unlayered 3D slicer settings",
]
# test_every_spelling_is_renamed: rename_text(k) == v for each pair
# test_other_uses_of_the_word_are_untouched: rename_text(s) == s and find_product_names(s) == [] for each
# test_renaming_twice_changes_nothing: rename_text(rename_text(k)) == rename_text(k)
# test_paths: rename_path("src/UnlayeredSlicer_app_msvc.cpp") == "src/SemilayeredSlicer_app_msvc.cpp"
#             rename_path("resources/profiles/Unlayered/machine/Unlayered 5 Axis Printer.json") unchanged
# test_leftovers_found_after_renaming (Review Focus 1): for each of
#   'Unlayered "\n"Slicer', "Unlayered\n// Slicer", "Unlayered&nbsp;Slicer", "Unlayered%20Slicer"
#   find_product_names(rename_text(s)) has one entry with the right line number
# test_nothing_left_after_ordinary_rename: find_product_names(rename_text(k)) == [] for each RENAMED key
```

- [ ] **Step 2: Run** `python3 -m unittest semilayered.tests.test_names -v`. Expected: import error.
- [ ] **Step 3: Implement.** `rename_text` replaces the first word in its three casings (`Unlayered`, `unlayered`, `UNLAYERED`) when it is followed by at most one of space, `-`, `_`, `.` and then `slicer` in any case; the separator and second word are left as they are. `find_product_names` is deliberately looser, case-insensitive: `unlayered`, then up to 12 joiners, then `slicer`, where a joiner is any character that is not a letter or digit, or one of `&nbsp;`, `&#160;`, `%20`.
- [ ] **Step 4: Run again.** Expected: all pass.
- [ ] **Step 5: Commit** (Erik): `Add product-name renaming for the rebrand tool`.

### Task 2: Explicit edits

**Files:**
- Create: `semilayered/rebrand/edits.py`
- Test: `semilayered/tests/test_edits.py`

**Interfaces:**
- Produces:
  - `Edit(path: str, old: str, new: str, count: int = 1, reason: str = "")`: exact replacement in one file, written against the text as it reads after renaming.
  - `Substitution(old: str, new: str, reason: str = "")`: every occurrence, in contents and in path components, tree-wide.
  - `EditMismatch(Exception)`.
  - `apply_edit(text: str, edit: Edit) -> str`.
  - `substitute(text: str, sub: Substitution) -> tuple[str, int]` returning the new text and the number of replacements.

- [ ] **Step 1: Write the failing tests**

```python
# test_edit_replaces_exactly_count_occurrences
# test_edit_whose_text_is_missing_fails_naming_the_entry (Review Focus 4):
#   with assertRaises(EditMismatch) as e: apply_edit("abc", Edit("f.cpp", "x", "y", reason="why"))
#   "f.cpp" in str(e.exception) and "why" in str(e.exception) and "found 0" in str(e.exception)
# test_edit_matching_more_often_than_count_fails: apply_edit("x x", Edit("f", "x", "y")) raises, "found 2"
# test_edit_already_applied_is_left_alone: apply_edit("y", Edit("f", "x", "y")) == "y"
# test_insertion_is_not_applied_twice: e = Edit("f", "void f()\n{", "void f()\n{\n    return;")
#   apply_edit(apply_edit("void f()\n{\n}", e), e) == "void f()\n{\n    return;\n}"
# test_substitute_counts: substitute("a b a", Substitution("a", "c")) == ("c b c", 2)
```

- [ ] **Step 2: Run** `python3 -m unittest semilayered.tests.test_edits -v`. Expected: import error.
- [ ] **Step 3: Implement.** An edit counts as already applied when `new` occurs at least `count` times; otherwise `old` must occur exactly `count` times.
- [ ] **Step 4: Run again.** Expected: all pass.
- [ ] **Step 5: Commit** (Erik): `Add explicit edits that fail when upstream's text changes`.

### Task 3: Applying to a tree, and regenerating from an upstream commit

**Files:**
- Create: `semilayered/rebrand/table.py` (empty lists for now plus `OWN_PATHS`), `semilayered/rebrand/tree.py`, `semilayered/rebrand/regenerate.py`, `semilayered/rebrand/__main__.py`, `semilayered/README.md`
- Test: `semilayered/tests/repo_fixture.py` (builds a small git repository in a temp dir with an `upstream` branch), `semilayered/tests/test_tree.py`, `semilayered/tests/test_regenerate.py`

**Interfaces:**
- Consumes: Task 1 and Task 2 names.
- Produces:
  - `table.OWN_PATHS = ("semilayered/", "plans/", ".github/workflows/semilayered_")`; `table.VERBATIM_PATHS`, `table.SUBSTITUTIONS`, `table.EDITS` (filled in Task 6).
  - `tree.apply(root: Path, table=table) -> None`.
  - `tree.PathCollision(Exception)`.
  - `regenerate.regenerate(root: Path, upstream_ref: Optional[str] = None) -> str` returning the upstream commit used. With no ref it uses the one in `semilayered/upstream_commit`.
  - `regenerate.scratch_regeneration(root: Path, upstream_commit: str)`: context manager yielding a temporary `git worktree` that holds the regenerated tree built with the own files as they are in `root` now.
  - CLI `python3 -m semilayered.rebrand regenerate [ref]`.

`apply` order: rename and substitute contents of every tracked UTF-8 text file that is not own or verbatim; rename and substitute paths with `git mv`, deepest first; apply `EDITS`; copy every file under `semilayered/artwork/tree/` over the tracked file at the same relative path. Symlinks are never read or written.

`regenerate` order: require a clean working tree; resolve the ref to a commit; if that commit is not an ancestor of `HEAD`, start `git merge -s ours --no-commit` so the result records the merge; replace index and working tree with the upstream tree (`git read-tree --reset -u`); restore own paths from `HEAD`; write `semilayered/upstream_commit`; run `apply`; `git add -A`. It never commits.

- [ ] **Step 1: Write the failing tests** against the fixture repository (files `src/UnlayeredSlicer.cpp` including `"UnlayeredSlicer.hpp"`, `src/UnlayeredSlicer.hpp`, `docs/notes.md` mentioning Unlayered 3D and unlayered3d.com, `LICENSE.txt` listed as verbatim and containing the product name, a binary file, a symlink):

```python
# test_contents_and_paths_are_renamed_together: after apply, src/SemilayeredSlicer.cpp exists,
#   includes "SemilayeredSlicer.hpp", and `git ls-files` has no old path
# test_own_and_verbatim_files_are_untouched: byte-identical before and after
# test_binary_files_and_symlinks_are_untouched
# test_second_apply_changes_nothing (Review Focus 4): `git status --porcelain` identical after a second apply
# test_colliding_rename_stops (Review Focus 2): with src/SemilayeredSlicer.hpp already tracked,
#   apply raises PathCollision naming both paths; `git status --porcelain` shows no renames
# test_substitution_applies_to_paths_and_contents
# test_regenerate_from_upstream_ref: on a branch with own files committed, regenerate(root, "upstream")
#   leaves a staged tree with renamed files, own files intact, semilayered/upstream_commit == upstream sha
# test_regenerate_records_a_merge_when_upstream_moved: after committing, add a commit to `upstream`,
#   regenerate again, commit; `git rev-list --parents -n1 HEAD` lists the new upstream commit as a parent
# test_regenerate_refuses_a_dirty_tree
# test_file_deleted_upstream_disappears: a file removed on `upstream` is gone after regenerate
# test_scratch_regeneration_leaves_the_real_tree_alone: `git status --porcelain` of root unchanged,
#   and the worktree is removed on exit
```

- [ ] **Step 2: Run** `python3 -m unittest semilayered.tests.test_tree semilayered.tests.test_regenerate -v`. Expected: import errors.
- [ ] **Step 3: Implement** `tree.py`, `regenerate.py`, the CLI command, and `semilayered/README.md` (what the tool is; "to take a source drop: `git fetch upstream`, `python3 -m semilayered.rebrand regenerate upstream/main`, `python3 -m semilayered.rebrand check`, review, commit").
- [ ] **Step 4: Run again.** Expected: all pass.
- [ ] **Step 5: Commit** (Erik): `Add tree regeneration from an upstream commit`.

### Task 4: The checks

**Files:**
- Create: `semilayered/rebrand/checks.py`; extend `__main__.py` with `check`
- Modify: `semilayered/rebrand/table.py` (add `KEPT_PRODUCT_NAMES`, `KEPT_IDENTIFIERS`, `BRAND_IMAGE_PATHS`, empty for now)
- Test: `semilayered/tests/test_checks.py`

**Interfaces:**
- Consumes: `tree.apply`, `regenerate.scratch_regeneration`, `names.find_product_names`.
- Produces:
  - `leftover_product_names(root) -> list[str]`: `path:line: text` for every product name in a tracked file or path that is not own, verbatim, or listed in `table.KEPT_PRODUCT_NAMES` (`(path, literal, reason)` triples).
  - `kept_identifier_drift(root, upstream_commit) -> list[str]`: for each `table.KEPT_IDENTIFIERS` entry (`identifier -> allowed difference`), a line when its count in the tree differs from its count in the upstream commit by anything else.
  - `upstream_brand_images(root, upstream_commit) -> list[str]`: tracked files whose content equals the upstream content of any `table.BRAND_IMAGE_PATHS` entry.
  - `reproduces(root, upstream_commit) -> bool`: compares the tree hash of a `scratch_regeneration` with the tree hash of the current working tree.
  - CLI `python3 -m semilayered.rebrand check`: reads the commit from `semilayered/upstream_commit`, runs all four, prints each finding, exits 1 if any.

- [ ] **Step 1: Write the failing tests** on the Task 3 fixture:

```python
# test_clean_regenerated_tree_passes: all four return empty / True
# test_leftover_in_text_is_reported_with_path_and_line
# test_leftover_in_utf16_file_is_reported (Review Focus 3): a tracked file holding
#   "Unlayered Slicer".encode("utf-16-le") is reported by leftover_product_names
# test_leftover_in_a_path_is_reported
# test_listed_leftover_is_allowed: same text listed in KEPT_PRODUCT_NAMES is not reported
# test_kept_identifier_that_was_renamed_is_reported: changing "unlayered3d.com" in one file reports drift
# test_upstream_brand_image_left_in_place_is_reported
# test_hand_edit_to_an_upstream_file_breaks_reproduction: reproduces(...) is False after editing docs/notes.md
```

- [ ] **Step 2: Run** `python3 -m unittest semilayered.tests.test_checks -v`. Expected: import error.
- [ ] **Step 3: Implement.** Files that are not UTF-8 text are searched as bytes, in UTF-8 and UTF-16-LE, for each spelling `rename_text` handles.
- [ ] **Step 4: Run again**, then the whole suite. Expected: all pass, output is only the unittest summary.
- [ ] **Step 5: Commit** (Erik): `Add checks that the tree is a pure regeneration`.

---

## Phase 2: content for the real tree

### Task 5: Behaviour checks, seen against upstream's own build first

**Files:**
- Create: `semilayered/tests/e2e/behaviour_checks.py`

**Interfaces:**
- Produces: `python3 semilayered/tests/e2e/behaviour_checks.py <path to .app>` (macOS). Prints one PASS or FAIL line per check; exits 0 only if both pass.
  - `no_update_check`: requires that the app's executable does not contain the text the update request logs (`updater: checking `) and does contain the text logged in its place (`updater: update checks are off in this build`). Launching the app cannot show this unattended: a first launch stops at the setup wizard and several one-time questions before it would check for updates, and the public tree has no way to answer them automatically.
  - `generator_name`: slices a model from `tests/data` with the app's command line and requires the first `; generated by` line of the G-code to start with `; generated by Unlayered Slicer <version> on `, with `<version>` read from `version.inc`.

These are the tests for the two behaviour decisions (updater off, generator name unchanged). Writing them now means the first is seen failing before the edit that fixes it exists.

- [ ] **Step 1: Write the script.** Find the data-directory and slicing options from the app's `--help`.
- [ ] **Step 2: Run it against upstream's build (Erik's OK: it runs an unsigned app from the command line).** Download artifact `Unlayered_Slicer_Mac_universal_V0.1.10` from run 43108415857 with `gh run download`, mount the DMG, copy the app to a temp directory. Expected: `no_update_check` FAIL, `generator_name` PASS. If `no_update_check` passes here, the check is not observing the update check; fix the check before going on.
- [ ] **Step 3: Commit** (Erik): `Add checks for update and generator-name behaviour of a built app`.

### Task 6: The table for Unlayered Slicer 0.1.10

**Files:**
- Modify: `semilayered/rebrand/table.py`
- Test: `semilayered/tests/test_table.py`

**Interfaces:**
- Consumes: `Edit`, `Substitution`, `scratch_regeneration`.
- Produces: the filled table. Later tasks rely on `GENERATOR_APP_NAME` existing in `src/libslic3r/libslic3r.h` and on the Windows PDB being `SemilayeredSlicer.pdb`.

Entries, each with a `reason`. `old` text is copied from the tree as it reads after renaming; find each with `git grep` in a scratch regeneration.

- `VERBATIM_PATHS`: `LICENSE.txt`, `PRIVACY.md`, `resources/web/privacy/slicer-privacy-policy.html`.
- `SUBSTITUTIONS`:
  - `Unlayered3D/Semilayered-Slicer` to `erikbuild/Semilayered-Slicer`
  - `com.unlayered3d.SemilayeredSlicer` to `io.github.erikbuild.SemilayeredSlicer`
  - `Unlayered3D.SemilayeredSlicer` to `erikbuild.SemilayeredSlicer` (MSIX identity)
- `EDITS`:
  - **Attribution.** `src/slic3r/GUI/AboutDialog.cpp`: `Semilayered Slicer is developed by Unlayered 3D.` becomes `Semilayered Slicer is an unofficial build of Unlayered Slicer, which is developed by Unlayered 3D.`
  - **README notice.** Inserted above the first line of `README.md`:

    ```
    > **Semilayered Slicer is an unofficial build of Unlayered Slicer.** It is not affiliated with
    > or endorsed by Unlayered 3D. This tree is Unlayered Slicer's source with the application
    > renamed by the tool in `semilayered/` (first applied 2026-11-12). Two things differ besides
    > the name: the application does not update itself, and a few lines are edited where the rename
    > alone would be wrong. `semilayered/rebrand/table.py` lists every one. It is provided as is,
    > without support. Please do not report problems with it to Unlayered 3D. Everything below is
    > Unlayered Slicer's own README with the name replaced.
    ```
  - **Vendor fields** to `Semilayered Slicer contributors`: `CPACK_PACKAGE_VENDOR` in `CMakeLists.txt`; `CompanyName` in both `src/dev-utils/platform/msw/*.rc.in`; the `PublisherDisplayName` default in `scripts/msix/build_msix.ps1` and its fallback in `.github/workflows/build_slicer.yml`; the `CN=Unlayered 3D` fallback there becomes `CN=Semilayered Slicer contributors`; `<developer id="com.unlayered3d">` in the metainfo becomes `io.github.erikbuild` and its name the vendor text.
  - **Generator name pinned** (five sites plus one definition). After the `GCODEVIEWER_BUILD_ID` line in `src/libslic3r/libslic3r.h` insert:

    ```cpp
    // The application name recorded as the generator of G-code and settings files. It matches
    // Unlayered Slicer's, so both applications read each other's output.
    #define GENERATOR_APP_NAME "Unlayered Slicer"
    ```
    and replace `SLIC3R_APP_NAME` with `GENERATOR_APP_NAME` in `header_slic3r_generated()` (`src/libslic3r/utils.cpp`), the G-code header match in `src/libslic3r/Config.cpp`, the first `Producers` entry in `src/libslic3r/GCode/GCodeProcessor.cpp`, the `"generator"` value in `src/libslic3r/GCode/GCodeStatistics.cpp`, and the `; generated by` test in `src/slic3r/Utils/UltiMaker.cpp`.
  - **3MF key kept.** `src/libslic3r/Format/bbs_3mf.cpp`: the value of `SEMILAYEREDSLICER_TAG` goes back to `"UnlayeredSlicer"`; the two comments in `bbs_3mf.hpp` that name the tag go back to naming `"UnlayeredSlicer"`.
  - **Updater off.** `src/slic3r/GUI/GUI_App.cpp`, immediately inside `void GUI_App::check_new_version_sf(int by_user)`:

    ```cpp
        // Semilayered Slicer does not update itself. A check the user asks for opens the releases page.
        BOOST_LOG_TRIVIAL(info) << "updater: update checks are off in this build";
        if (by_user != 0)
            wxLaunchDefaultBrowser("https://github.com/erikbuild/Semilayered-Slicer/releases");
        return;
    ```
    The log line is what `behaviour_checks.py` looks for in the built executable, and what a real first launch leaves in the log.
  - **Windows safety check.** `OrcaSlicer.pdb` becomes `SemilayeredSlicer.pdb` in `scripts/check_exception_throw_info.ps1` (3 places) and `scripts/test_check_exception_throw_info.ps1` (3 places); `OrcaSlicer.dll` in the script's comment becomes `SemilayeredSlicer.dll`.
  - **Bare "Unlayered" meaning the application.** `Unlayered prepares the print.` becomes `Semilayered Slicer prepares the print.` Rule for the audit in Step 3: change a sentence only when "Unlayered" is the application doing something, and never inside privacy or consent text.
- `KEPT_PRODUCT_NAMES`: the `GENERATOR_APP_NAME` definition; the 3MF key and its two comments; the About sentence; the README notice.
- `KEPT_IDENTIFIERS`, each with the difference the edits above cause (0 for most; the vendor edits and the README notice change the count of `Unlayered 3D`): `unlayered3d.com`, `Unlayered 3D`, `Unlayered3D/RepRapFirmware`, `X-Unlayered-`, `UNLAYERED_NO_TELEMETRY`, `UNLAYERED_VERSION`, `UNLAYERED_MOD`, `UnlayeredAccount`, `unlayered-sys.json`, `UnlayeredWebControl`, `Unlayered 5 Axis Printer`, `fdm_process_unlayered`, `Sign in to Unlayered`.
- `BRAND_IMAGE_PATHS`: filled in Task 7.

- [ ] **Step 1: Write the failing test.** `test_table.py` opens a `scratch_regeneration` of the commit in `semilayered/upstream_commit`, or of `upstream/main` when that file does not exist yet (skipped with a message if neither is available), and asserts `leftover_product_names` and `kept_identifier_drift` are empty there.
- [ ] **Step 2: Run it.** Expected: fails. With the table still empty, the product name inside the three verbatim files is reported as a leftover.
- [ ] **Step 3: Fill the table**, then audit. Produce two lists for Erik in the task report: every string literal in `src/` containing bare "Unlayered" with the decision taken under the rule above; and every sentence in the regenerated tree where "Semilayered Slicer" sits within one sentence of "Unlayered 3D", "official", "support", "contact" or "warranty", with the decision. A sentence the rename made false gets an edit.
- [ ] **Step 4: Run the test and the suite.** Expected: pass.
- [ ] **Step 5: Commit** (Erik): `Add the rebrand table for Unlayered Slicer 0.1.10`.

### Task 7: Placeholder artwork

**Files:**
- Create: `semilayered/artwork/src/mark.svg`, `semilayered/artwork/src/wordmark.svg`, `semilayered/artwork/generate.swift`, `semilayered/artwork/README.md`, `semilayered/artwork/tree/**`
- Modify: `semilayered/rebrand/table.py` (`BRAND_IMAGE_PATHS`)
- Test: `semilayered/tests/test_artwork.py`

**Interfaces:**
- Consumes: `tree.apply` installs `semilayered/artwork/tree/`.
- Produces: `table.BRAND_IMAGE_PATHS`: upstream paths (before renaming) of every image carrying Unlayered's mark or wordmark.

The mark: a rounded square, background `#1F2933`, three horizontal rounded bars in `#2DD4BF`, the top bar half the length of the others. The wordmark: "Semilayered Slicer" in `resources/fonts/Sarabun-SemiBold.ttf` (SIL Open Font Licence; confirm against the licence files beside it), converted to outlines. SVG output uses only `path` and `rect` with flat fills, because the app's SVG renderer draws no text.

- [ ] **Step 1: Inventory.** View every candidate and list the ones that show Unlayered's mark or name: the 24 `resources/images/UnlayeredSlicer*` files, `resources/images/splash_logo*.svg`, `resources/images/studio_logo.svg`, `resources/web/image/logo*.png`, images under `resources/web/unlayered/` and `resources/web/guide/4unlayered/`, `scripts/msix/` assets, any `.ico`/`.icns` under `src/dev-utils/platform/`. `resources/profiles/Unlayered/` (the printer's own bed texture) is not brand artwork of the application and stays. Put the list in `BRAND_IMAGE_PATHS`.
- [ ] **Step 2: Write the failing tests** (pure Python readers for PNG, ICO, ICNS headers and SVG `viewBox`):

```python
# test_every_brand_image_has_a_replacement: {rename_path(p) for p in BRAND_IMAGE_PATHS}
#   == set of files under semilayered/artwork/tree/
# test_replacements_match_upstream_dimensions: for each pair, same format, same pixel size
#   (PNG IHDR; every ICO entry size; every ICNS icon type), same SVG viewBox
# test_svgs_contain_no_text_elements
# test_no_replacement_equals_the_upstream_image (bytes differ)
```

- [ ] **Step 3: Run** `python3 -m unittest semilayered.tests.test_artwork -v`. Expected: fails, no replacements.
- [ ] **Step 4: Write the sources and `generate.swift`**, run it, and view each kind of output (mark at 32 px and 192 px, wordmark light and dark, the About image) before going on.
- [ ] **Step 5: Run the tests and the suite.** Expected: pass.
- [ ] **Step 6: Show Erik** the mark and the wordmark, then **Commit** (Erik): `Add placeholder artwork for Semilayered Slicer`.

---

## Phase 3: apply, build, converge

### Task 8: Known-failure gate

**Files:**
- Create: `semilayered/release/__init__.py`, `semilayered/release/failures.py`, `semilayered/release/__main__.py`, `semilayered/release/known_upstream_failures.txt`
- Test: `semilayered/tests/test_failures.py`, `semilayered/tests/fixtures/unit_tests_linux.log`, `semilayered/tests/fixtures/slice_check.log` (trimmed from baseline run 43108415857)

**Interfaces:**
- Produces:
  - `Failure(kind: str, job: str, item: str)` with `kind` one of `job`, `test`, `slice`.
  - `parse_failed_tests(log: str) -> list[str]`; `parse_failed_slices(log: str) -> list[str]`.
  - `run_failures(run_id: str, repo: str) -> set[Failure]` (uses `gh api` for jobs and `gh run view --log-failed` for logs).
  - `load_known(path) -> set[Failure]`; `unlisted(found, known) -> set[Failure]`; `now_passing(found, known) -> set[Failure]`.
  - CLI `python3 -m semilayered.release gate --run <id> [--repo owner/name]`: prints unlisted failures and listed ones that now pass; exits 1 if any are unlisted.

A failed unit-test or slice-check job yields one `test` or `slice` failure per item parsed from its log; if nothing can be parsed it yields a `job` failure, as does any other failed job (item: the failed step). The list file is tab-separated `kind`, `job`, `item`, with `#` comments.

- [ ] **Step 1: Write the failing tests**

```python
# test_failed_tests_are_read_from_ctest_output: parse_failed_tests(fixture) == [
#   "release_targets_platform: other platforms only is not an update here",
#   "Nonplanar layers: hold back holds the safe part of a wall joined to a rim beside the top's highest point",
#   "Each cube's raft is its support, centered below it"]
# test_failed_slices_are_read: three "Unlayered / Unlayered 5 Axis Printer 0.N nozzle" entries
# test_log_without_a_failure_block_gives_no_tests
# test_unlisted_and_now_passing: set arithmetic on small sets
# test_known_file_round_trip: comments and blank lines ignored; a line with the wrong field count raises naming the line number
```

- [ ] **Step 2: Run** `python3 -m unittest semilayered.tests.test_failures -v`. Expected: import error.
- [ ] **Step 3: Implement**, and write the list: the two Flatpak jobs and `Test Results` as `job`; the three tests under `Linux x86_64 / Unit Tests` and `Linux aarch64 / Unit Tests`; the two under `macOS arm64 / Unit Tests`; the three slice entries under `Slice check (Linux aarch64)`.
- [ ] **Step 4: Run the tests.** Then check against reality: `python3 -m semilayered.release gate --run 43108415857 --repo erikbuild/Semilayered-Slicer`. Expected: exactly two unlisted failures, the two Windows `Check exception throw info Win` steps, and nothing reported as now passing.
- [ ] **Step 5: Commit** (Erik): `Add the known-upstream-failure gate`.

### Task 9: Regenerate the real tree

**Files:** every upstream file the tool touches; `semilayered/upstream_commit`.

- [ ] **Step 1:** With Tasks 1 to 8 committed and the tree clean: `python3 -m semilayered.rebrand regenerate upstream/main`.
- [ ] **Step 2:** `python3 -m semilayered.rebrand check`. Expected: no findings, exit 0. A finding is fixed in the table or the tool with a test first, never by hand in the tree.
- [ ] **Step 3:** `python3 -m unittest discover -s semilayered/tests -t .`. Expected: all pass.
- [ ] **Step 4:** Report to Erik: `git diff --cached --stat | tail -1`, the count of renamed paths, and the full diff of the files with explicit edits only.
- [ ] **Step 5: Commit** (Erik): `Regenerate as Semilayered Slicer from Unlayered Slicer 0.1.10`.

### Task 10: Build and converge

**Files:** none by hand. Fixes go through the table or tool.

- [ ] **Step 1: Local macOS build (Erik's OK).** It gives a compile-and-test loop that needs no commit or push. Needs `brew install automake texinfo libtool pkgconf yasm nasm` for whatever is missing, about 15 GB of disk and roughly an hour and a half the first time. Commands, from upstream's CI: `./build_release_macos.sh -dx -a arm64 -t 10.15`, then `ORCA_TESTS_BUILD_ONLY=1 ./build_release_macos.sh -s -n -x -a arm64 -t 10.15 -T`, then the unit tests the way `.github/workflows/unit_tests.yml` runs them, then `behaviour_checks.py` on the built app. Expected: builds; the only failing unit tests are the two listed for macOS; both behaviour checks pass. If Erik declines, or the toolchain fails for a reason that is not the rename, go on with CI only.
- [ ] **Step 2: First CI run (Erik pushes `wip/semilayered-rebrand`; Erik's OK to dispatch):** `gh workflow run build_all.yml --ref wip/semilayered-rebrand`. Dependencies rebuild, so allow about three hours.
- [ ] **Step 3: Judge it:** `python3 -m semilayered.release gate --run <id>`. Expected: exit 0, and the two Windows unit-test jobs ran.
- [ ] **Step 4:** For each unlisted failure, find the cause. If the rename caused it, add a failing test to the tool's suite, fix the table or tool, regenerate, check, and ask Erik to commit and push. If it is a Windows unit test that fails the same way as on the other platforms, add it to the list with that note. If the Windows safety check fails, stop.
- [ ] **Step 5:** Repeat Steps 2 to 4 until the gate exits 0 and the run has all seven installer artifacts. Then run `behaviour_checks.py` on the app from that run's DMG **(Erik's OK)**. Expected: both pass.

---

## Phase 4: publishing

### Task 11: Assets, tag and notes

**Files:**
- Create: `semilayered/release/assets.py`, `semilayered/release/notes.py`; extend `semilayered/release/__main__.py`
- Test: `semilayered/tests/test_assets.py`, `semilayered/tests/test_notes.py`

**Interfaces:**
- Produces:
  - `upstream_version(root) -> str` (reads `UNLAYERED_VERSION` from `version.inc`).
  - `release_tag(version: str, build: int) -> str`; `release_title(version, build) -> str`.
  - `expected_assets(version) -> list[tuple[str, str]]` (artifact name, published file name).
  - `MissingAsset(Exception)`; `collect(artifacts_dir: Path, out_dir: Path, version: str) -> list[Path]`.
  - `release_notes(version, build, upstream_commit, known: set[Failure]) -> str`.
  - CLI `collect --artifacts DIR --out DIR`, `notes --build N`, `tag --build N`.

- [ ] **Step 1: Write the failing tests**

```python
# test_tag_and_title (Review Focus 5): release_tag("0.1.10", 7) == "semilayered-0.1.10-b7"
#                     release_title("0.1.10", 7) == "Semilayered Slicer 0.1.10 (build 7)"
# test_version_is_read_from_version_inc (temp file with the real line)
# test_expected_assets_for_0_1_10 == [
#  ("Semilayered_Slicer_Windows_V0.1.10_x64", "Semilayered_Slicer_Windows_Installer_V0.1.10_x64.exe"),
#  ("Semilayered_Slicer_Windows_V0.1.10_arm64", "Semilayered_Slicer_Windows_Installer_V0.1.10_arm64.exe"),
#  ("Semilayered_Slicer_Windows_V0.1.10_x64_portable", "Semilayered_Slicer_Windows_V0.1.10_x64_portable.zip"),
#  ("Semilayered_Slicer_Windows_V0.1.10_arm64_portable", "Semilayered_Slicer_Windows_V0.1.10_arm64_portable.zip"),
#  ("Semilayered_Slicer_Mac_universal_V0.1.10", "Semilayered_Slicer_Mac_universal_V0.1.10.dmg"),
#  ("Semilayered_Slicer_Linux_ubuntu_2404_V0.1.10", "Semilayered_Slicer_Linux_AppImage_Ubuntu2404_V0.1.10.AppImage"),
#  ("Semilayered_Slicer_Linux_ubuntu_2404_aarch64_V0.1.10", "Semilayered_Slicer_Linux_AppImage_Ubuntu2404_aarch64_V0.1.10.AppImage")]
# test_collect_copies_files_zips_portable_directories_and_writes_checksums: on a fake artifacts dir;
#   portable zip has one top folder "SemilayeredSlicer/"; SHA256SUMS has one line per file and verifies
# test_collect_names_the_missing_asset: remove one artifact dir -> MissingAsset with its name
# test_collect_refuses_an_out_dir_that_is_not_empty
# test_notes_say_what_this_is: text contains "unofficial build of Unlayered Slicer",
#   "not affiliated with or endorsed by Unlayered 3D", "provided as is, without support",
#   the upstream commit, each known failure's item, "does not update itself",
#   "xattr -dr com.apple.quarantine", "chmod +x"
```

- [ ] **Step 2: Run** `python3 -m unittest semilayered.tests.test_assets semilayered.tests.test_notes -v`. Expected: import errors.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run the suite.** Then collect from the converged Task 10 run: `gh run download <id>` for the seven artifacts into a scratch directory, `python3 -m semilayered.release collect ...`. Expected: seven files and `SHA256SUMS`. Correct `expected_assets` here if the real artifact contents differ, test first.
- [ ] **Step 5: Commit** (Erik): `Add release asset collection and notes`.

### Task 12: The two workflows

**Files:**
- Create: `.github/workflows/semilayered_build_on_push.yml`, `.github/workflows/semilayered_publish_release.yml`

**Interfaces:**
- Consumes: both CLIs.

`semilayered_build_on_push.yml`: on `push` to `main` and `workflow_dispatch`; permissions `contents: read`, `actions: write`. Job `checks` on `ubuntu-24.04`: checkout; `git fetch --depth 1 https://github.com/Unlayered3D/Unlayered-Slicer.git "$(cat semilayered/upstream_commit)"`; the unittest suite; `python3 -m semilayered.rebrand check`. Job `start_build` needs `checks`: `gh workflow run build_all.yml --ref main`.

`semilayered_publish_release.yml`: on `workflow_run` of `Build all`, type `completed`; permissions `contents: write`, `actions: read`. One job on `ubuntu-24.04`, run only when `github.event.workflow_run.head_branch == 'main'` and `github.event.workflow_run.event == 'workflow_dispatch'` (Review Focus 5). Steps: checkout `github.event.workflow_run.head_sha`; `gate --run`; stop with a clear message if the tag from `tag --build ${{ github.event.workflow_run.run_number }}` already has a release (a re-run); `gh run download`; `collect`; make the x86_64 AppImage executable, run it with `--appimage-extract '*.desktop'`, and require a line `Name=Semilayered Slicer`; `notes`; `gh release create <tag> --target <head_sha> --title ... --notes-file ... <files>`.

- [ ] **Step 1: Write both files.**
- [ ] **Step 2: Dry run by hand (Erik's OK), before they reach `main`:** run the publish job's commands locally against the converged Task 10 run, ending in `gh release create ... --draft`. Expected: a draft release with eight files. Run the "tag already has a release" step again. Expected: it stops. Delete the draft.
- [ ] **Step 3: Commit** (Erik): `Build on push to main and publish a GitHub Release`.

### Task 13: First release and end-to-end verification

**Files:**
- Create: `semilayered/tests/e2e/verify_release.py`

**Interfaces:**
- Consumes: `behaviour_checks.py`.
- Produces: `python3 semilayered/tests/e2e/verify_release.py (<tag> | --dir DIR)` (macOS; needs `hdiutil` and `7zz`), exit 0 only if every check passes.

With a tag it downloads every asset with no credentials; with `--dir` it uses files already collected. It verifies `SHA256SUMS`; mounts the DMG and requires `CFBundleName` `Semilayered Slicer` and `CFBundleIdentifier` `io.github.erikbuild.SemilayeredSlicer`; lists the Windows x64 installer with `7zz` and requires `semilayered-slicer.exe` and `SemilayeredSlicer.dll`; then runs `behaviour_checks.py` on the app from the DMG.

- [ ] **Step 1: Write the script and run it with `--dir` on the files Task 11 collected (Erik's OK to launch the app).** Expected: exit 0.
- [ ] **Step 2:** Erik merges `wip/semilayered-rebrand` into `main` and pushes.
- [ ] **Step 3:** Watch `Semilayered build on push`, then `Build all`, then `Semilayered publish release`. Expected: a public release tagged `semilayered-0.1.10-b<N>` with eight files. If the publish workflow never starts, apply the fallback in the spec's Risks (one workflow that starts the build, waits, then publishes) as its own task.
- [ ] **Step 4:** `python3 semilayered/tests/e2e/verify_release.py semilayered-0.1.10-b<N>`. Expected: exit 0.
- [ ] **Step 5:** Erik opens the app from the DMG, answers the first-run questions, and confirms the name in the menu bar, the About text, and that Help ▸ Check for Updates opens the releases page. Then read that launch's log: it must contain `updater: update checks are off in this build` and no `updater: checking`.
- [ ] **Step 6:** Delete the baseline run's artifacts (Erik's OK), and update `semilayered/README.md` with anything the first drop taught. **Commit** (Erik).
