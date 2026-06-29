# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file for Bookkeeping App
# Build with: pyinstaller build.spec

import os
import sys

APP_DIR = os.path.dirname(os.path.abspath(SPECPATH))
PYTHON_DIR = os.path.dirname(sys.executable)

a = Analysis(
    ['main.py'],
    pathex=[APP_DIR],
    binaries=[
        (os.path.join(PYTHON_DIR, 'vcruntime140.dll'), '.'),
        (os.path.join(PYTHON_DIR, 'vcruntime140_1.dll'), '.'),
        (os.path.join(PYTHON_DIR, 'python314.dll'), '.'),
    ],
    datas=[
        ('app_icon.ico', '.'),
        ('app_icon.png', '.'),
    ],
    hiddenimports=[
        'pgeocode',
        'pdfplumber',
        'openpyxl',
        'ofxparse',
        'reportlab',
        'xlsxwriter',
        'tkcalendar',
        'babel.numbers',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='5StarBookKeeping',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='app_icon.ico',
)
