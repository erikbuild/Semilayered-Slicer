# The Semilayered tools

Semilayered Slicer is Unlayered Slicer's source with the application renamed. Nobody renames it by
hand. The tools in this directory regenerate the whole tree from an upstream commit, so the tree in
git is always:

    rebrand(an upstream commit) + the fork's own files

The fork's own files are this directory, `plans/`, and `.github/workflows/semilayered_*.yml`.
Everything else comes from upstream through the tool. To change an upstream file, change the tool or
its table in `rebrand/table.py` and regenerate; an edit made by hand is overwritten by the next
regeneration.

## Taking a new source drop

    git fetch upstream
    python3 -m semilayered.rebrand regenerate upstream/main
    python3 -m semilayered.rebrand check
    git status
    git commit

`regenerate` needs a clean working tree. It replaces the tree with upstream's, puts the own files
back, renames the product, applies the explicit edits, installs the artwork, and stages the result.
It never commits. When the upstream commit is new to this branch it leaves a merge in progress, so
the commit you make records which source drop the tree came from. The commit it used is written to
`semilayered/upstream_commit`.

If it stops with an error, nothing has changed: the new tree is built in a temporary worktree first
and replaces this one only when it is complete. The error names what did not match, which is usually
an explicit edit whose text upstream has changed. Fix the table, commit, and run it again.

`check` proves the tree is a pure regeneration. It fails if the product name is still somewhere it
should not be, if text that must stay as upstream wrote it has changed, if one of upstream's brand
images is still in the tree, or if any file differs from what regenerating produces. It builds a
fresh copy in a temporary worktree to compare against, and changes nothing in this one.

## How a push becomes a release

A push to `main` runs `Semilayered build on push`: it checks the tree, starts upstream's `Build all`
on `main`, waits for it, and then starts `Semilayered publish release` for that run. The publish
workflow refuses a run that is not a finished `Build all` on `main`, a run with a failure that is
not in `release/known_upstream_failures.txt`, a run with an installer missing, and a build that
already has a release.

To publish a finished run by hand, without rebuilding:

    gh workflow run semilayered_publish_release.yml -f run_id=<the number in the run's URL>

## After changing the tool or the table

    python3 -m semilayered.rebrand regenerate

With no argument it regenerates from the recorded upstream commit.

## Tests

    python3 -m unittest discover -s semilayered/tests -t .
