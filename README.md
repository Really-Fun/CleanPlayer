<p align="center">
  <img src="readme/logo.svg" alt="Quantis" width="720">
</p>

<p align="center">
  <strong>Десктопный музыкальный плеер для RU/CIS</strong><br>
  Яндекс.Музыка · YouTube · Офлайн
</p>

<p align="center">
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/Python-3.13%20%7C%203.14-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-GPL--3.0-blue?style=flat-square" alt="License"></a>
  <a href="https://github.com/Really-Fun/Quantis"><img src="https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-2ea043?style=flat-square" alt="Platform"></a>
  <a href="https://github.com/Really-Fun/Quantis/releases"><img src="https://img.shields.io/github/v/release/Really-Fun/Quantis?style=flat-square" alt="Release"></a>
  <img src="https://img.shields.io/badge/Qt-PySide6-41cd52?style=flat-square&logo=qt" alt="PySide6">
</p>

<p align="center">
  <a href="#скриншоты">Скриншоты</a> ·
  <a href="#возможности">Возможности</a> ·
  <a href="#темы">Темы</a> ·
  <a href="#быстрый-старт">Быстрый старт</a> ·
  <a href="#разработка">Разработка</a> ·
  <a href="#поддержать-проект">Поддержать</a>
</p>

---

## О проекте

**Quantis** — асинхронный кроссплатформенный плеер на **PySide6** и **asyncio**.
Одно окно для поиска, прослушивания и скачивания музыки с **Яндекс.Музыки** и
**YouTube**: история с возобновлением с места остановки, «Моя волна», радио по
треку и нативная интеграция с медиа-клавишами ОС.

Воспроизведение работает через **Qt Multimedia** или **VLC (libvlc)** — это две
отдельные сборки exe.

## Скриншоты

<table>
<tr>
<td width="50%"><img src="readme/home.png" alt="Главная"></td>
<td width="50%"><img src="readme/search.png" alt="Поиск"></td>
</tr>
<tr>
<td align="center"><sub>Главная — библиотека и плейлисты</sub></td>
<td align="center"><sub>Поиск — Яндекс и YouTube в одной выдаче</sub></td>
</tr>
</table>

<p align="center">
  <img src="readme/playlist.png" alt="Плейлист" width="820">
</p>

## Возможности

| | |
|---|---|
| **Поиск** | Параллельно по Яндекс.Музыке и YouTube, debounce, прогрессивная выдача по источникам, ленивые списки без прогрузки всего каталога |
| **Воспроизведение** | Qt Multimedia или VLC, seek/громкость, автопереход к следующему треку |
| **Радио и волна** | «Моя волна» (Yandex rotor), радио по любому треку через YouTube Watch Playlist |
| **Библиотека** | Любимые треки, свои плейлисты, «Недавно прослушанные», «Скачанные» |
| **Офлайн** | Скачивание треков и обложек в `Музыка/Quantis`, статус загрузки на карточке |
| **История** | SQLite: недавно прослушанное и продолжение с сохранённой позиции |
| **Интерфейс** | MVVM, `EventBus`, QSS-темы, панель «Сейчас играет», обои |
| **Интеграция** | Медиа-клавиши ОС: SMTC (Windows) и MPRIS (Linux), keyring для токенов |
| **Расширяемость** | Плагины из `plugins_dir/` со своими страницами в UI |

## Темы

Переключаются в **Настройки → Тема**.

| Тема | Характер |
|------|----------|
| **Aurora** | Cyan + magenta, свечение, тема по умолчанию |
| **Glass** | Стекло поверх обоев, включает фон автоматически |
| **Редакционная** | Georgia + mono, cyan/red, акцент на панель «Сейчас» |
| **Классическая** | Спокойный тёмный steel-blue |
| **Светлая** | Приглушённый светлый режим |
| **Тёмно-жёлтая** | Тёплый amber-акцент |

## Быстрый старт

Нужны Python **3.13 или 3.14** и [Poetry](https://python-poetry.org/docs/#installation).

```bash
git clone https://github.com/Really-Fun/Quantis.git
cd Quantis
poetry install
poetry run quantis
```

### Аккаунты

Без токенов работают поиск и воспроизведение **YouTube**. Всё остальное
подключается во вкладке **Member**:

- **Yandex Music** — OAuth-токен, хранится в keyring (там же виден статус Яндекс Плюс)
- **YouTube Music** — cookies в файле `credentials/youtube_cookies.txt` внутри [каталога данных](docs/build.md#каталоги-данных) (keyring на Windows не принимает большие blob'ы)

<details>
<summary>Прописать токен Яндекса вручную</summary>

```python
import keyring

keyring.set_password("YANDEX_TOKEN_NEON_APP", "NEON_APP", "<ваш_oauth_токен>")
```

</details>

## Сборка и архитектура

- **Сборка exe и установщик** (варианты `qt`/`vlc`, Inno Setup, каталоги данных) — [docs/build.md](docs/build.md)
- **Слои, поток воспроизведения, структура каталогов** — [docs/architecture.md](docs/architecture.md)
- **Карта интерфейса** (страницы, сигналы `EventBus`) — [docs/ui-map.md](docs/ui-map.md)

## Разработка

```bash
# тесты (сетевые помечены @pytest.mark.network)
poetry run pytest tests/ -q

# линтеры
poetry run ruff check src tests
poetry run black --check src tests
```

Отключить системный медиа-адаптер при отладке — `QUANTIS_ENABLE_ADAPTER=0`.
Подробнее о процессе и code style — в [CONTRIBUTING.md](CONTRIBUTING.md).

## Дорожная карта

- [ ] Android-клиент
- [ ] Spotify / VK / SoundCloud
- [ ] Горячие клавиши (Space, Ctrl+←/→)
- [ ] Визуализатор
- [ ] Пользовательские темы и фоны

## Поддержать проект

Quantis бесплатный и с открытым исходным кодом. Если он вам пригодился — можно
поддержать разработку через CloudTips: это идёт на серверы, тестовые устройства
и кофе.

<p align="center">
  <a href="https://pay.cloudtips.ru/p/c8c0b13b">
    <img src="https://img.shields.io/badge/CloudTips-Поддержать_проект-F5426C?style=for-the-badge&labelColor=1f2430" alt="Поддержать через CloudTips">
  </a>
</p>


<p align="center">
  <img src="readme/qr.jpg" alt="QR для донатов CloudTips" width="180">
</p>


## Лицензия

[GNU GPL v3](LICENSE) · © [Really-Fun](https://github.com/Really-Fun)

<p align="center">
  <sub>Если Quantis полезен - поставьте звезду на GitHub. Это правда помогает.</sub>
</p>
