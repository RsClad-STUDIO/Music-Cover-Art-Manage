# -*- mode: python ; coding: utf-8 -*-
import os

PROJECT_ROOT = os.path.abspath(os.path.join(SPECPATH, ".."))
SRC_ROOT = os.path.join(PROJECT_ROOT, "src")
ICON_PATH = os.path.join(PROJECT_ROOT, "assets", "icon.ico")

a = Analysis(
    [os.path.join(PROJECT_ROOT, "main.py")],
    pathex=[SRC_ROOT],
    binaries=[],
    datas=[(ICON_PATH, "assets")],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [], exclude_binaries=True,
    name="Music Cover Art Manage CLI", debug=False,
    bootloader_ignore_signals=False, strip=False, upx=False,
    console=True, disable_windowed_traceback=False,
    argv_emulation=False, target_arch=None,
    codesign_identity=None, entitlements_file=None,
    icon=[ICON_PATH],
)
coll = COLLECT(
    exe, a.binaries, a.datas, strip=False, upx=False,
    upx_exclude=[], name="Music Cover Art Manage",
)
