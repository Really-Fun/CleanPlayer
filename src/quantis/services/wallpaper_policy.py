"""Политика видео-фона: стримим любой длины, на диск — только короткие клипы."""

from __future__ import annotations

# Часовой mp4 в кэш не качаем: это сотни МБ, стрима хватает.
WALLPAPER_CACHE_MAX_SEC = 15 * 60
WALLPAPER_MAX_LOCAL_BYTES = 40 * 1024 * 1024
WALLPAPER_SYNC_INTERVAL_MS = 1200
WALLPAPER_SYNC_DRIFT_MS = 1500
# Если видео стабильно не догоняет, порог растёт: лучше лёгкий рассинхрон,
# чем перемотка HTTP-потока каждую секунду.
WALLPAPER_MAX_DRIFT_MS = 6000
WALLPAPER_QUALITY_CHOICES = (360, 480, 720)
WALLPAPER_FPS_CHOICES = (5, 10, 15, 24, 30)
WALLPAPER_DEFAULT_QUALITY = 360
WALLPAPER_DEFAULT_FPS = 10
_DECODE_MAX_SIDE = {360: 640, 480: 854, 720: 1280}
_FORMAT_FALLBACK_HEIGHT = {360: 480, 480: 720, 720: 720}


def should_play_local_wallpaper(size_bytes: int) -> bool:
    return 0 < size_bytes <= WALLPAPER_MAX_LOCAL_BYTES


def wallpaper_positions_drifted(
    audio_ms: int, video_ms: int, *, tolerance_ms: int = WALLPAPER_SYNC_DRIFT_MS
) -> bool:
    if audio_ms <= 0 or video_ms < 0:
        return False
    return abs(audio_ms - video_ms) > max(WALLPAPER_SYNC_DRIFT_MS, tolerance_ms)


def wallpaper_next_drift_tolerance(current_ms: int) -> int:
    return min(WALLPAPER_MAX_DRIFT_MS, max(WALLPAPER_SYNC_DRIFT_MS, current_ms) * 2)


def wallpaper_duration_filter(info: dict, *, incomplete: bool = False) -> str | None:
    """Фильтр yt-dlp: не качать час видео в кэш обоев."""
    duration = int(info.get("duration") or 0)
    if duration > WALLPAPER_CACHE_MAX_SEC:
        return f"too long for wallpaper cache ({duration}s)"
    return None


def clamp_wallpaper_quality(value: int) -> int:
    if value in WALLPAPER_QUALITY_CHOICES:
        return value
    return min(WALLPAPER_QUALITY_CHOICES, key=lambda height: abs(height - value))


def clamp_wallpaper_fps(value: int) -> int:
    if value in WALLPAPER_FPS_CHOICES:
        return value
    return min(WALLPAPER_FPS_CHOICES, key=lambda fps: abs(fps - value))


def wallpaper_decode_max_side(height: int) -> int:
    return _DECODE_MAX_SIDE[clamp_wallpaper_quality(height)]


def wallpaper_yt_dlp_format(height: int) -> str:
    h = clamp_wallpaper_quality(height)
    return f"best[vcodec!=none][height<={h}]/best[height<={h}]/18"


def wallpaper_yt_dlp_android_format(height: int) -> str:
    h = clamp_wallpaper_quality(height)
    if h <= 360:
        return "18/best[height<=360]/best[height<=480]"
    extra = _FORMAT_FALLBACK_HEIGHT[h]
    return f"best[height<={h}][vcodec!=none]/best[height<={h}]/best[height<={extra}]/18"


def wallpaper_cache_format(height: int) -> str:
    h = clamp_wallpaper_quality(height)
    return (
        f"best[ext=mp4][vcodec!=none][height<={h}]/"
        f"best[ext=mp4][height<={h}]/"
        f"18/best[height<={h}]"
    )
