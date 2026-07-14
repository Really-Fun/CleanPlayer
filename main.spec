# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec для Quantis (Windows onedir → dist/Quantis/Quantis.exe).

Сборка:
    poetry install --with dev
    poetry run pyinstaller main.spec --noconfirm
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_data_files, collect_submodules

# SPECPATH — каталог со .spec (не путь к файлу)
try:
    ROOT = Path(SPECPATH).resolve()
except NameError:
    ROOT = Path.cwd()

SRC = ROOT / "src"
QUANTIS = SRC / "quantis"

_venv = Path(os.environ.get("VIRTUAL_ENV") or (ROOT / ".venv"))
if sys.platform == "win32":
    SITE = _venv / "Lib" / "site-packages"
else:
    SITE = (
        _venv
        / "lib"
        / f"python{sys.version_info.major}.{sys.version_info.minor}"
        / "site-packages"
    )

datas: list = []
binaries: list = []
hiddenimports: list[str] = []

# Ресурсы приложения
if (QUANTIS / "assets").is_dir():
    datas.append((str(QUANTIS / "assets"), "quantis/assets"))
    datas.append((str(QUANTIS / "assets"), "assets"))
if (QUANTIS / "styles").is_dir():
    datas.append((str(QUANTIS / "styles"), "quantis/styles"))

# Опциональный фон из корня репозитория
repo_bg = ROOT / "assets" / "background"
if repo_bg.is_dir():
    datas.append((str(repo_bg), "assets/background"))

# ytmusicapi локали
if (SITE / "ytmusicapi").is_dir():
    try:
        datas += collect_data_files("ytmusicapi", includes=["locales/**"])
    except Exception:
        pass

# Тяжёлые зависимости с нативными бинарниками
for pkg in ("PySide6", "shiboken6", "yt_dlp", "certifi"):
    try:
        pkg_datas, pkg_binaries, pkg_hidden = collect_all(pkg)
        datas += pkg_datas
        binaries += pkg_binaries
        hiddenimports += pkg_hidden
    except Exception:
        pass

if sys.platform == "win32":
    for pkg in (
        "winrt",
        "winrt.windows.foundation",
        "winrt.windows.media",
        "winrt.windows.media.playback",
    ):
        try:
            hiddenimports += collect_submodules(pkg)
        except Exception:
            hiddenimports.append(pkg)

hiddenimports += [
    "qasync",
    "aiosqlite",
    "aiohttp",
    "aiofiles",
    "keyring",
    "keyring.backends",
    "keyring.backends.Windows",
    "yandex_music",
    "ytmusicapi",
    "quantis",
    "quantis.main",
    "quantis.adapter",
    "quantis.adapter.clean_adapter",
    "quantis.adapter.windows_adapter",
    "PySide6.QtCore",
    "PySide6.QtGui",
    "PySide6.QtWidgets",
    "PySide6.QtMultimedia",
    "PySide6.QtMultimediaWidgets",
    "PySide6.QtNetwork",
    "PySide6.QtSvg",
]

icon_path = QUANTIS / "assets" / "icons" / "logo.png"
icon = str(icon_path) if icon_path.is_file() else None

a = Analysis(
    [str(QUANTIS / "main.py")],
    pathex=[str(SRC)],
    binaries=binaries,
    datas=datas,
    hiddenimports=sorted(set(hiddenimports)),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter",
        "matplotlib",
        "numpy",
        "pandas",
        "scipy",
        "IPython",
        "notebook",
        "pytest",
        "mpris_server",
    ],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Quantis",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="Quantis",
)
