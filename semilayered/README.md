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

If it stops with an error, nothing is lost: `git merge --abort` (when a merge was in progress) or
`git reset --hard` returns to where you started. The error names what did not match, which is
usually an explicit edit whose text upstream has changed.

`check` proves the tree is a pure regeneration. It fails if the product name is still somewhere it
should not be, if text that must stay as upstream wrote it has changed, if one of upstream's brand
images is still in the tree, or if any file differs from what regenerating produces. It builds a
fresh copy in a temporary worktree to compare against, and changes nothing in this one.

## After changing the tool or the table

    python3 -m semilayered.rebrand regenerate

With no argument it regenerates from the recorded upstream commit.

## Tests

    python3 -m unittest discover -s semilayered/tests -t .
