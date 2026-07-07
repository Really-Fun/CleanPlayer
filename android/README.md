# Quantis Android

Нативный Android-клиент Quantis на **Kotlin + Jetpack Compose**. Логика поиска и стриминга портирована с десктопного Python (`async_finder`, `async_streamer`, `async_recommendation`).

## Возможности

- **Главная** — рекомендации YouTube Music (home feed)
- **Поиск** — Яндекс.Музыка (OAuth) + YouTube Music
- **Радио** — долгое нажатие на трек (watch playlist, как на десктопе)
- **Плеер** — Media3 ExoPlayer + **MediaSession** (управление из шторки)
- Очередь: следующий / предыдущий трек
- Тёмная editorial-тема

## Требования

- Android Studio Ladybug или новее
- JDK 17
- Android SDK 35
- Устройство/эмулятор API 26+

## Сборка

1. Откройте папку `android/` в Android Studio.
2. Дождитесь синхронизации Gradle.
3. **Run** на эмуляторе или телефоне.

При первом запуске разрешите уведомления (Android 13+) — без них медиа-контролы в шторке могут не отображаться.

## Токен Яндекс.Музыки

**Настройки → Yandex OAuth token** — тот же токен, что в десктопном Quantis.

## Управление

| Действие | Жест |
|----------|------|
| Воспроизвести | Тап по треку |
| Радио по треку | Долгое нажатие |
| Пауза / play | Плеер внизу или шторка |
| Следующий / предыдущий | Кнопки в плеере или шторке |

## Архитектура

```
ui/              Compose, ViewModel
domain/          MusicRepository, PlaybackCoordinator
data/
  yandex/        REST api.music.yandex.net
  youtube/       InnerTube (home, search, next, player)
player/          PlaybackService (MediaSessionService), PlayerController
```

## Ограничения

- YouTube: часть треков может не отдавать прямой URL (cipher)
- Радио для Яндекс-треков ищет эквивалент на YouTube
- Нет офлайна и библиотеки

## Дорожная карта

- [ ] Обложки в уведомлении
- [ ] Офлайн-загрузки
- [ ] Яндекс-рекомендации при наличии токена
