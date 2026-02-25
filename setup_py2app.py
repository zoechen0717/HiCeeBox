"""
py2app setup script for HiCeeBox macOS application.

Usage:
    # Development mode (aliased app)
    python setup_py2app.py py2app -A
    
    # Production build
    python setup_py2app.py py2app
"""

from setuptools import setup

APP = ['hiceebox_gui/app.py']
DATA_FILES = []

OPTIONS = {
    'argv_emulation': False,
    'iconfile': 'assets/icon.icns',  # If available
    'plist': {
        'CFBundleName': 'HiCeeBox',
        'CFBundleDisplayName': 'HiCeeBox',
        'CFBundleIdentifier': 'com.hiceebox.app',
        'CFBundleVersion': '0.1.0',
        'CFBundleShortVersionString': '0.1.0',
        'NSHumanReadableCopyright': 'Copyright © 2026 HiCeeBox',
        'LSMinimumSystemVersion': '10.15.0',
        'NSHighResolutionCapable': True,
        'LSApplicationCategoryType': 'public.app-category.education',
    },
    'packages': [
        'hiceebox',
        'hiceebox_gui',
        'PySide6',
        'matplotlib',
        'numpy',
    ],
    'includes': [
        'hiceebox.matrix.hic_provider',
        'hiceebox.matrix.cooler_provider',
        'hiceebox.tracks.hic_triangle',
        'hiceebox.tracks.bigwig',
        'hiceebox.tracks.bed',
        'hiceebox.tracks.bedpe',
        'hiceebox.tracks.gene',
        'matplotlib.backends.backend_qtagg',
    ],
    'excludes': [
        'tkinter',
        'unittest',
        'pytest',
        'IPython',
        'jupyter',
    ],
    'strip': True,
    'optimize': 2,
}

setup(
    name='HiCeeBox',
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)

