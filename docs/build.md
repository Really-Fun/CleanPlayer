# Сборка Quantis

Собираются два варианта приложения — они отличаются только медиадвижком.

| Сборка | Движок | Артефакт |
|--------|--------|----------|
| **qt** | Qt Multimedia (FFmpeg) | `dist\Quantis\Quantis.exe` |
| **vlc** | libVLC (`python-vlc`) | `dist\Quantis-VLC\Quantis-VLC.exe` |

## Windows

```bat
REM Qt (по умолчанию)
poetry install --with dev
poetry run python scripts/build_exe.py qt

REM VLC — нужен установленный VideoLAN VLC (для libvlc.dll + plugins)
poetry install --with dev,vlc
set VLC_HOME=C:\Program Files\VideoLAN\VLC
poetry run python scripts/build_exe.py vlc
```

То же через PowerShell:

```powershell
.\scripts\build.ps1 -Backend qt
.\scripts\build.ps1 -Backend vlc -VlcHome "C:\Program Files\VideoLAN\VLC"
```

Каталог VLC можно передать и аргументом, минуя переменную окружения:

```bat
poetry run python scripts/build_exe.py vlc --vlc-home "C:\Program Files\VideoLAN\VLC"
```

`scripts/build_exe.py` — тонкая обёртка над PyInstaller: выставляет
`QUANTIS_MEDIA_BACKEND`, запускает `main.spec` и раскладывает результат по
`dist/` (рабочие файлы — в `build/pyi-<backend>/`). Выбор движка на этапе
сборки читают rthook'и из `packaging/`.

## Переключение движка без пересборки

Для разработки движок задаётся переменной окружения:

```bat
set QUANTIS_MEDIA_BACKEND=vlc
poetry install --with vlc
poetry run quantis
```

## Что создаётся рядом с exe

При первом запуске приложение само создаёт свои каталоги в папке с exe:

- `plugins_dir/` — плагины приложения
- `background/user/` — пользовательские обои
- `music/`, `covers/`, `player_history.db` — данные плеера

В сборку **Quantis-VLC** дополнительно копируются `libvlc.dll` и `plugins/`
из `VLC_HOME`.
