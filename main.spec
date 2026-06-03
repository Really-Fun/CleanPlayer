# -*- mode: python ; coding: utf-8 -*-
import os
import sys

# Находим путь к активному виртуальному окружению Poetry
venv_path = os.environ.get('VIRTUAL_ENV') or os.path.join(os.getcwd(), '.venv')
site_packages = os.path.join(venv_path, 'lib', f'python{sys.version_info.major}.{sys.version_info.minor}', 'site-packages')

# Динамически собираем путь к локалям ytmusicapi из .venv
ytm_locales_src = os.path.join(site_packages, 'ytmusicapi', 'locales', 'ru')
ytm_ru_locale = (ytm_locales_src, 'ytmusicapi/locales/ru') if os.path.exists(ytm_locales_src) else (os.path.abspath('.'), 'ytmusicapi/locales/ru')

a = Analysis(
    ['src/quantis/main.py'],
    pathex=['src'],
    binaries=[],
    datas=[
        ytm_ru_locale,
        ('src/quantis/assets/icons/exe_logo.png', '.')
    ],
    hiddenimports=[
        'qasync',
        'aiosqlite',
        'mpris_server'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=1,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='Quantis',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='src/quantis/assets/icons/exe_logo.png',
)