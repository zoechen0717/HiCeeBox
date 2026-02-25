# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for HiCeeBox macOS .app bundle.

Run from project root:
    pyinstaller HiCeeBox.spec

Or use the build script:
    ./build_macos.sh [--clean] [--debug]
"""

from pathlib import Path
import sys

# Project root = current working directory (build script runs from project root)
# PyInstaller does not set __file__ when exec'ing the spec
SPEC_DIR = Path.cwd()
sys.path.insert(0, str(SPEC_DIR))

# Import after pathex is set so we find local packages
import hiceebox
import hiceebox_gui

HICEEBOX_ROOT = Path(hiceebox.__file__).resolve().parent
HICEEBOX_GUI_ROOT = Path(hiceebox_gui.__file__).resolve().parent

# --- Runtime hook: set matplotlib backend before any other code ---
RUNTIME_HOOK_MPL = str(HICEEBOX_GUI_ROOT / "rthook_mpl_qt.py")

# --- Data: package trees + default promoter.bed (for Gene name lookup in frozen app) ---
datas = [
    (str(HICEEBOX_ROOT), "hiceebox"),
    (str(HICEEBOX_GUI_ROOT), "hiceebox_gui"),
]
_promoter_bed = SPEC_DIR / "promoter.bed"
if _promoter_bed.exists():
    datas.append((str(_promoter_bed), "."))

# --- Hidden imports: ensure all required modules are collected ---
hiddenimports = [
    # App entry and GUI
    "hiceebox_gui.app",
    "hiceebox_gui.main_window",
    "hiceebox_gui.state",
    "hiceebox_gui.controller",
    "hiceebox_gui.canvas",
    "hiceebox_gui.widgets",
    # Core
    "hiceebox",
    "hiceebox.matrix.base",
    "hiceebox.matrix.hic_provider",
    "hiceebox.matrix.cooler_provider",
    "hiceebox.tracks",
    "hiceebox.tracks.base",
    "hiceebox.tracks.hic_triangle",
    "hiceebox.tracks.hic_genome_view",
    "hiceebox.tracks.bigwig",
    "hiceebox.tracks.bed",
    "hiceebox.tracks.bedpe",
    "hiceebox.tracks.gene",
    "hiceebox.view",
    "hiceebox.view.genome_view",
    "hiceebox.view.layout",
    "hiceebox.utils",
    "hiceebox.utils.config",
    "hiceebox.utils.gtf_to_bed12",
    # Qt + matplotlib (must use QtAgg in frozen app)
    "PySide6",
    "PySide6.QtCore",
    "PySide6.QtGui",
    "PySide6.QtWidgets",
    "matplotlib",
    "matplotlib.pyplot",
    "matplotlib.figure",
    "matplotlib.backends.backend_qtagg",
    "matplotlib.backends.qt_compat",
    # Data / scientific
    "numpy",
    "pandas",
    "yaml",
    "pyBigWig",
    "hicstraw",
    "cooler",
]

# --- Exclude unneeded modules to reduce size and avoid wrong backend ---
# Do not exclude 'unittest' - pyparsing (matplotlib dep) imports it
excludes = [
    "tkinter",
    "pytest",
    "IPython",
    "jupyter",
    "notebook",
    "tornado",
    "sphinx",
    "PIL.ImageTk",
    "matplotlib.backends.backend_macosx",  # Prefer Qt only in frozen app
]

# --- Analysis ---
a = Analysis(
    [str(HICEEBOX_GUI_ROOT / "app.py")],
    pathex=[str(SPEC_DIR)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[RUNTIME_HOOK_MPL],
    excludes=excludes,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data)

# Console: set to True only for debugging (see build_macos.sh --debug)
CONSOLE = False

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="HiCeeBox",
    debug=False,
    strip=False,
    upx=False,  # Disable UPX on macOS to avoid code-sign / runtime issues
    console=CONSOLE,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(SPEC_DIR / "assets" / "icon.icns") if (SPEC_DIR / "assets" / "icon.icns").exists() else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    name="HiCeeBox",
)

icon_path = str(SPEC_DIR / "assets" / "icon.icns") if (SPEC_DIR / "assets" / "icon.icns").exists() else None

app = BUNDLE(
    coll,
    name="HiCeeBox.app",
    icon=icon_path,
    bundle_identifier="com.hiceebox.app",
    version="0.1.0",
    info_plist={
        "NSPrincipalClass": "NSApplication",
        "NSHighResolutionCapable": True,
        "CFBundleName": "HiCeeBox",
        "CFBundleDisplayName": "HiCeeBox",
        "CFBundleIdentifier": "com.hiceebox.app",
        "CFBundleVersion": "0.1.0",
        "CFBundleShortVersionString": "0.1.0",
        "CFBundlePackageType": "APPL",
        "CFBundleSignature": "????",
        "CFBundleExecutable": "HiCeeBox",
        "NSHumanReadableCopyright": "Copyright (c) 2026 HiCeeBox",
        "LSMinimumSystemVersion": "10.15.0",
        "NSRequiresAquaSystemAppearance": False,
        "LSApplicationCategoryType": "public.app-category.education",
        # Fix keyboard input in .app bundle on macOS (use system input)
        "LSEnvironment": {"QT_IM_MODULE": ""},
        "CFBundleDocumentTypes": [
            {
                "CFBundleTypeName": "Hi-C File",
                "CFBundleTypeRole": "Viewer",
                "LSItemContentTypes": ["public.data"],
                "LSHandlerRank": "Default",
                "CFBundleTypeExtensions": ["hic", "mcool", "cool"],
            },
        ],
    },
)
