#!/usr/bin/env python3
"""Сборка Quantis.exe с выбранным медиадвижком.

Примеры:
    python scripts/build_exe.py qt
    python scripts/build_exe.py vlc
    python scripts/build_exe.py vlc --vlc-home "C:\\Program Files\\VideoLAN\\VLC"
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description="Сборка Quantis (qt | vlc)")
    parser.add_argument(
        "backend",
        choices=("qt", "vlc"),
        help="Медиадвижок: qt = Qt Multimedia, vlc = python-vlc/libVLC",
    )
    parser.add_argument(
        "--vlc-home",
        default=os.environ.get("VLC_HOME", ""),
        help="Каталог установки VLC (для bundling libvlc.dll + plugins)",
    )
    parser.add_argument(
        "--noconfirm",
        action="store_true",
        default=True,
        help="Перезаписать dist без вопросов (по умолчанию)",
    )
    args = parser.parse_args()

    env = os.environ.copy()
    env["QUANTIS_MEDIA_BACKEND"] = args.backend
    if args.backend == "vlc" and args.vlc_home:
        env["VLC_HOME"] = args.vlc_home

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        str(ROOT / "main.spec"),
        "--noconfirm",
        "--distpath",
        str(ROOT / "dist"),
        "--workpath",
        str(ROOT / "build" / f"pyi-{args.backend}"),
    ]

    print(f"==> Building Quantis backend={args.backend}")
    if args.backend == "vlc":
        print(f"    VLC_HOME={env.get('VLC_HOME') or '(auto)'}")
    print("   ", " ".join(cmd))
    result = subprocess.run(cmd, cwd=ROOT, env=env, check=False)
    if result.returncode == 0:
        name = "Quantis" if args.backend == "qt" else "Quantis-VLC"
        print(f"==> OK: dist/{name}/{name}.exe")
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
