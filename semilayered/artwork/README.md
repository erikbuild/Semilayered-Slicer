# Semilayered Slicer artwork

Upstream's application icon, splash logo and wordmarks show Unlayered 3D's mark and name, which are
its trademarks. The rebrand replaces each of those images with the one at the same path under
`tree/`. `semilayered/rebrand/table.py` lists the upstream images (`BRAND_IMAGE_PATHS`).

What is here now is a placeholder: a dark rounded square holding three layers, the top one half
printed, and the name set in NanumGothic Bold (shipped in `resources/fonts`, SIL Open Font
Licence), converted to outlines.

## Regenerating the placeholder

On macOS, from the repository root:

    swift semilayered/artwork/generate.swift
    python3 -m unittest semilayered.tests.test_artwork

`generate.swift` holds the whole design as code and writes every file under `tree/`.

## Replacing it with real artwork

Put the new images in `tree/`, each under the same name as the file it replaces. The tests require
every replacement to have the format and size of the upstream image: the same pixel size for a
PNG, the same icon sizes for an ICO or ICNS, the same `viewBox`, `width` and `height` for an SVG.
SVGs may use only filled paths and basic shapes, because the application's SVG renderer draws no
text, styles, filters or masks. Then regenerate the tree:

    python3 -m semilayered.rebrand regenerate
