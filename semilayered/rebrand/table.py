# ABOUTME: The data that turns Unlayered Slicer into Semilayered Slicer, beyond the name pattern itself.
# ABOUTME: Lists the fork's own paths, files kept word for word, tree-wide substitutions and explicit edits.
from __future__ import annotations

from typing import Dict, Tuple

from semilayered.rebrand.edits import Edit, Substitution

VENDOR = "Semilayered Slicer contributors"
RELEASES_URL = "https://github.com/erikbuild/Semilayered-Slicer/releases"

# Path prefixes that exist only in this fork. The tool never changes these files, and a regeneration keeps them.
OWN_PATHS: Tuple[str, ...] = ("semilayered/", "plans/", ".github/workflows/semilayered_")

# Upstream files kept word for word: neither their contents nor their paths are renamed.
# These are legal and policy texts that Unlayered 3D wrote about its own product.
VERBATIM_PATHS: Tuple[str, ...] = (
    "LICENSE.txt",
    "PRIVACY.md",
    "SECURITY.md",
    "resources/web/privacy/slicer-privacy-policy.html",
)

# Replacements of every occurrence, tree-wide, applied after the product name is renamed.
SUBSTITUTIONS: Tuple[Substitution, ...] = (
    Substitution(
        "Unlayered3D/Semilayered-Slicer",
        "erikbuild/Semilayered-Slicer",
        "source, release and issue links, and the source address the app offers under the AGPL, "
        "must lead to the repository these builds come from",
    ),
    Substitution(
        "com.unlayered3d.SemilayeredSlicer",
        "io.github.erikbuild.SemilayeredSlicer",
        "the app ID (macOS bundle, Flatpak, desktop entry) must not sit under Unlayered 3D's domain",
    ),
    Substitution(
        "Unlayered3D.SemilayeredSlicer",
        "erikbuild.SemilayeredSlicer",
        "the MSIX package identity must not name Unlayered 3D as its owner",
    ),
)

README_NOTICE = """\
> **Semilayered Slicer is an unofficial build of Unlayered Slicer.** It is not affiliated with
> or endorsed by Unlayered 3D. This tree is Unlayered Slicer's source with the application
> renamed by the tool in `semilayered/` (first applied 2026-11-12). Two things differ besides
> the name: the application does not update itself, and a few lines are edited where the rename
> alone would be wrong. `semilayered/rebrand/table.py` lists every one. It is provided as is,
> without support. Please do not report problems with it to Unlayered 3D. Everything below is
> Unlayered Slicer's own README with the name replaced."""

README_FIRST_LINES = '<div align="center">\n\n<picture>'

GENERATOR_DEFINITION = """\
// The application name recorded as the generator of G-code and settings files. It matches
// Unlayered Slicer's, so both applications read each other's output.
#define GENERATOR_APP_NAME "Unlayered Slicer\""""

APP_KEY_DEFINITION = '#define SLIC3R_APP_KEY "@SLIC3R_APP_KEY@"'

UPDATE_CHECK_OPENING = "void GUI_App::check_new_version_sf(int by_user)\n{"

UPDATE_CHECK_OFF = f"""\
    // Semilayered Slicer does not update itself. A check the user asks for opens the releases page.
    BOOST_LOG_TRIVIAL(info) << "updater: update checks are off in this build";
    if (by_user != 0)
        wxLaunchDefaultBrowser("{RELEASES_URL}");
    return;"""

ATTRIBUTION = "an unofficial build of Unlayered Slicer, which is developed by Unlayered 3D"

NOT_THE_PUBLISHER = "Unlayered 3D did not publish this build, so it must not be named as its publisher"
GENERATOR_STAYS = "G-code and settings files keep naming the generator upstream's builds name (Erik's decision)"
NO_SELF_UPDATE = "the application does not update itself, so it must not tell people that signing in makes it do so"
PDB_NAME = "the Windows safety check looks for a PDB name this build never produces"
THE_APPLICATION = "here the word names the application, not the company"
KEY_BY_NAME = "it names the 3MF key, which stays upstream's, so the comment or test agrees with the code"

# Exact replacements in single files, applied last and written against the renamed text.
EDITS: Tuple[Edit, ...] = (
    # Who makes this.
    Edit(
        "src/slic3r/GUI/AboutDialog.cpp",
        '_L("Semilayered Slicer is developed by Unlayered 3D.")',
        f'_L("Semilayered Slicer is {ATTRIBUTION}.")',
        reason="the renamed sentence would say Unlayered 3D develops Semilayered Slicer",
    ),
    Edit(
        "src/slic3r/GUI/AboutDialog.cpp",
        "Semilayered Slicer is developed by Unlayered 3D and builds on the open-source slicers before it",
        f"Semilayered Slicer is {ATTRIBUTION} and builds on the open-source slicers before it",
        reason="the renamed sentence would say Unlayered 3D develops Semilayered Slicer",
    ),
    Edit(
        "README.md",
        README_FIRST_LINES,
        README_NOTICE + "\n\n" + README_FIRST_LINES,
        reason="the AGPL asks a modified version to say prominently that it was modified, and when",
    ),
    Edit(
        "README.md",
        "Semilayered Slicer is Unlayered 3D's fork of [OrcaSlicer]",
        "Semilayered Slicer is an unofficial build of Unlayered Slicer, which is Unlayered 3D's fork of [OrcaSlicer]",
        reason="the renamed sentence would call Semilayered Slicer Unlayered 3D's own fork",
    ),
    # Who publishes this.
    Edit(
        "CMakeLists.txt",
        'set (CPACK_PACKAGE_VENDOR "Unlayered 3D")',
        f'set (CPACK_PACKAGE_VENDOR "{VENDOR}")',
        reason=NOT_THE_PUBLISHER,
    ),
    Edit(
        "src/slic3r/GUI/GUI_App.cpp",
        'L"Software\\\\Unlayered 3D\\\\Semilayered Slicer"',
        f'L"Software\\\\{VENDOR}\\\\Semilayered Slicer"',
        reason="the application reads the registry key the installer writes, which is named after the vendor",
    ),
    Edit(
        "src/dev-utils/platform/msw/SemilayeredSlicer.rc.in",
        'VALUE "CompanyName", "Unlayered 3D"',
        f'VALUE "CompanyName", "{VENDOR}"',
        reason=NOT_THE_PUBLISHER,
    ),
    Edit(
        "src/dev-utils/platform/msw/SemilayeredSlicer-gcodeviewer.rc.in",
        'VALUE "CompanyName", "Unlayered 3D"',
        f'VALUE "CompanyName", "{VENDOR}"',
        reason=NOT_THE_PUBLISHER,
    ),
    Edit(
        "scripts/msix/build_msix.ps1",
        '[string]$Publisher = "CN=38F7EA55-C73B-4072-B3B2-C8E0EA15BB82"',
        f'[string]$Publisher = "CN={VENDOR}"',
        reason="that is Unlayered 3D's Microsoft Store publisher ID",
    ),
    Edit(
        "scripts/msix/build_msix.ps1",
        '[string]$PublisherDisplayName = "Unlayered 3D"',
        f'[string]$PublisherDisplayName = "{VENDOR}"',
        reason=NOT_THE_PUBLISHER,
    ),
    Edit(
        ".github/workflows/build_slicer.yml",
        "vars.ORCA_MSIX_PUBLISHER || 'CN=Unlayered 3D'",
        f"vars.ORCA_MSIX_PUBLISHER || 'CN={VENDOR}'",
        reason=NOT_THE_PUBLISHER,
    ),
    Edit(
        ".github/workflows/build_slicer.yml",
        "vars.ORCA_MSIX_PUBLISHER_DISPLAY_NAME || 'Unlayered 3D'",
        f"vars.ORCA_MSIX_PUBLISHER_DISPLAY_NAME || '{VENDOR}'",
        reason=NOT_THE_PUBLISHER,
    ),
    Edit(
        "scripts/flatpak/io.github.erikbuild.SemilayeredSlicer.metainfo.xml",
        '<developer id="com.unlayered3d">',
        '<developer id="io.github.erikbuild">',
        reason=NOT_THE_PUBLISHER,
    ),
    Edit(
        "scripts/flatpak/io.github.erikbuild.SemilayeredSlicer.metainfo.xml",
        "<name>Unlayered 3D</name>",
        f"<name>{VENDOR}</name>",
        reason=NOT_THE_PUBLISHER,
    ),
    # The generator name in output files stays upstream's.
    Edit(
        "src/libslic3r/libslic3r_version.h.in",
        APP_KEY_DEFINITION,
        APP_KEY_DEFINITION + "\n" + GENERATOR_DEFINITION,
        reason=GENERATOR_STAYS,
    ),
    Edit(
        "src/libslic3r/utils.cpp",
        'return std::string(SLIC3R_APP_NAME " " UNLAYERED_VERSION);',
        'return std::string(GENERATOR_APP_NAME " " UNLAYERED_VERSION);',
        reason=GENERATOR_STAYS,
    ),
    Edit(
        "src/libslic3r/Config.cpp",
        "orcaslicer_gcode_header += SLIC3R_APP_NAME;",
        "orcaslicer_gcode_header += GENERATOR_APP_NAME;",
        reason=GENERATOR_STAYS,
    ),
    Edit(
        "src/libslic3r/GCode/GCodeProcessor.cpp",
        "{ EProducer::OrcaSlicer, SLIC3R_APP_NAME },",
        "{ EProducer::OrcaSlicer, GENERATOR_APP_NAME },",
        reason=GENERATOR_STAYS,
    ),
    Edit(
        "src/libslic3r/GCode/GCodeStatistics.cpp",
        '{ "generator", std::string(SLIC3R_APP_NAME) + " " + UNLAYERED_VERSION }',
        '{ "generator", std::string(GENERATOR_APP_NAME) + " " + UNLAYERED_VERSION }',
        reason=GENERATOR_STAYS,
    ),
    Edit(
        "src/slic3r/Utils/UltiMaker.cpp",
        '"; generated by " SLIC3R_APP_NAME',
        '"; generated by " GENERATOR_APP_NAME',
        reason=GENERATOR_STAYS,
    ),
    # The key that records this fork's version in 3MF project files stays upstream's.
    Edit(
        "src/libslic3r/Format/bbs_3mf.cpp",
        'SEMILAYEREDSLICER_TAG               = "SemilayeredSlicer";',
        'SEMILAYEREDSLICER_TAG               = "UnlayeredSlicer";',
        reason="project files written by either application must stay readable by the other",
    ),
    Edit(
        "src/libslic3r/Format/bbs_3mf.hpp",
        'the "SemilayeredSlicer" tag',
        'the "UnlayeredSlicer" tag',
        count=2,
        reason="the comments describe the tag the code above keeps",
    ),
    Edit(
        "src/SemilayeredSlicer.cpp",
        "// SemilayeredSlicer tag (see unlayered_3mf_version)",
        "// UnlayeredSlicer tag (see unlayered_3mf_version)",
        reason=KEY_BY_NAME,
    ),
    Edit(
        "src/slic3r/GUI/Plater.cpp",
        "// SemilayeredSlicer tag record the OrcaSlicer version",
        "// UnlayeredSlicer tag record the OrcaSlicer version",
        reason=KEY_BY_NAME,
    ),
    # Upstream's tests of that key name it literally; every use of the name in these two files is the key.
    Edit("tests/libslic3r/test_3mf.cpp", "SemilayeredSlicer", "UnlayeredSlicer", count=7, reason=KEY_BY_NAME),
    Edit("tests/cli/test_cli_project_version.sh", "SemilayeredSlicer", "UnlayeredSlicer", count=9, reason=KEY_BY_NAME),
    # No self-updating.
    Edit(
        "src/slic3r/GUI/GUI_App.cpp",
        UPDATE_CHECK_OPENING,
        UPDATE_CHECK_OPENING + "\n" + UPDATE_CHECK_OFF,
        reason="upstream's updater would install Unlayered's build over this one (Erik's decision)",
    ),
    Edit(
        "src/slic3r/GUI/AutoUpdater.cpp",
        '%s then keeps itself up to date and offers "',
        '%s then offers "',
        reason=NO_SELF_UPDATE,
    ),
    Edit(
        "src/slic3r/GUI/AutoUpdater.cpp",
        '%s will stop updating itself until you "',
        '%s will stop offering configuration updates for your printers until you "',
        reason=NO_SELF_UPDATE,
    ),
    Edit(
        "src/slic3r/GUI/MainFrame.cpp",
        '_L("Sign in so the slicer can update itself")',
        '_L("Sign in to get configuration updates for your printers")',
        count=2,
        reason=NO_SELF_UPDATE,
    ),
    Edit(
        "src/slic3r/GUI/WebGuideDialog.cpp",
        'Semilayered Slicer then keeps itself up to date "',
        'Semilayered Slicer then "',
        reason=NO_SELF_UPDATE,
    ),
    Edit(
        "src/slic3r/GUI/WebGuideDialog.cpp",
        '"and offers configuration updates for your printers."',
        '"offers configuration updates for your printers."',
        reason=NO_SELF_UPDATE,
    ),
    # The Windows safety check.
    Edit("scripts/check_exception_throw_info.ps1", "OrcaSlicer.pdb", "SemilayeredSlicer.pdb", count=3, reason=PDB_NAME),
    Edit("scripts/check_exception_throw_info.ps1", "OrcaSlicer.dll", "SemilayeredSlicer.dll", reason=PDB_NAME),
    Edit("scripts/test_check_exception_throw_info.ps1", "OrcaSlicer.pdb", "SemilayeredSlicer.pdb", count=3, reason=PDB_NAME),
    Edit(
        "src/slic3r/GUI/Actions/PreferenceActions.cpp",
        '"Check the Unlayered update site for a newer version of the slicer now?"',
        '"Open the Semilayered Slicer releases page to look for a newer version?"',
        reason="a check the user asks for opens the releases page; it no longer asks Unlayered's update site",
    ),
    # Where the bare company name means the application. Consent and privacy wording is never touched.
    Edit(
        "src/slic3r/GUI/Plater.cpp",
        "Unlayered prepares the print.",
        "Semilayered Slicer prepares the print.",
        reason=THE_APPLICATION,
    ),
    Edit(
        "src/slic3r/GUI/Plater.cpp",
        "In Unlayered, slice, then choose",
        "In Semilayered Slicer, slice, then choose",
        reason=THE_APPLICATION,
    ),
    Edit(
        "src/slic3r/GUI/Plater.cpp",
        "Unlayered uses it to send prints to your Bambu printer.",
        "Semilayered Slicer uses it to send prints to your Bambu printer.",
        reason=THE_APPLICATION,
    ),
)

# Places where the product name stays on purpose, as (path, exact text, reason). The checks allow these only.
KEPT_PRODUCT_NAMES: Tuple[Tuple[str, str, str], ...] = (
    ("src/libslic3r/libslic3r_version.h.in", GENERATOR_DEFINITION, GENERATOR_STAYS),
    ("src/libslic3r/Format/bbs_3mf.cpp", '= "UnlayeredSlicer";', "the 3MF key both applications read"),
    ("src/libslic3r/Format/bbs_3mf.hpp", 'the "UnlayeredSlicer" tag', "the 3MF key both applications read"),
    ("src/SemilayeredSlicer.cpp", "// UnlayeredSlicer tag", KEY_BY_NAME),
    ("src/slic3r/GUI/Plater.cpp", "// UnlayeredSlicer tag", KEY_BY_NAME),
    ("tests/libslic3r/test_3mf.cpp", "UnlayeredSlicer", KEY_BY_NAME),
    ("tests/cli/test_cli_project_version.sh", "UnlayeredSlicer", KEY_BY_NAME),
    ("src/slic3r/GUI/AboutDialog.cpp", ATTRIBUTION, "says whose work this is a build of"),
    ("README.md", README_NOTICE, "says whose work this is a build of"),
    ("README.md", "an unofficial build of Unlayered Slicer, which is", "says whose work this is a build of"),
)

# Text that must survive the rebrand, mapped to how much the edits above change its count (0 for most).
KEPT_IDENTIFIERS: Dict[str, int] = {
    "unlayered3d.com": 0,
    # Eight publisher fields stop naming it; the README notice names it twice.
    "Unlayered 3D": -6,
    "Unlayered3D/RepRapFirmware": 0,
    "X-Unlayered-": 0,
    "UNLAYERED_NO_TELEMETRY": 0,
    "UNLAYERED_VERSION": 0,
    "UNLAYERED_MOD": 0,
    "UnlayeredAccount": 0,
    "unlayered-sys.json": 0,
    "UnlayeredWebControl": 0,
    "Unlayered 5 Axis Printer": 0,
    "fdm_process_unlayered": 0,
    "Sign in to Unlayered": 0,
}

# Upstream paths, as upstream names them, of every image that shows Unlayered's mark or wordmark.
# Images that show OrcaSlicer's logo (the document icons, studio_logo.svg, logo2.png, the MSIX
# assets, UnlayeredSlicer_gradient_circle.svg) are upstream's inheritance from OrcaSlicer and stay.
BRAND_IMAGE_PATHS: Tuple[str, ...] = (
    "resources/Icon.icns",
    "resources/images/UnlayeredSlicer-mac_128px.png",
    "resources/images/UnlayeredSlicer-mac_256px.ico",
    "resources/images/UnlayeredSlicer.ico",
    "resources/images/UnlayeredSlicer.png",
    "resources/images/UnlayeredSlicer.svg",
    "resources/images/UnlayeredSlicerTitle.ico",
    "resources/images/UnlayeredSlicerTitle.png",
    "resources/images/UnlayeredSlicer_128px.png",
    "resources/images/UnlayeredSlicer_154.png",
    "resources/images/UnlayeredSlicer_154_title.png",
    "resources/images/UnlayeredSlicer_192px.png",
    "resources/images/UnlayeredSlicer_192px_grayscale.png",
    "resources/images/UnlayeredSlicer_192px_transparent.png",
    "resources/images/UnlayeredSlicer_32px.png",
    "resources/images/UnlayeredSlicer_64.png",
    "resources/images/UnlayeredSlicer_about.svg",
    "resources/images/UnlayeredSlicer_about_dark.svg",
    "resources/images/UnlayeredSlicer_gradient.svg",
    "resources/images/UnlayeredSlicer_gradient_narrow.svg",
    "resources/images/UnlayeredSlicer_gray.svg",
    "resources/images/UnlayeredSlicer_horizontal_dark.svg",
    "resources/images/UnlayeredSlicer_horizontal_light.svg",
    "resources/images/splash_logo.svg",
    "resources/images/splash_logo_dark.svg",
    "resources/web/image/logo.png",
)
