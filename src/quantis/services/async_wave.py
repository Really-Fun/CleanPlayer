"""Моя волна — персональное радио (Yandex rotor / позже YouTube)."""

from __future__ import annotations

import logging
from typing import Any

from quantis.config.clients import Clients
from quantis.config.credentials import yandex_token
from quantis.models import YandexTrack
from quantis.models.playlist import WavePlaylist
from quantis.services.async_finder import _yandex_track_from_api

logger = logging.getLogger(__name__)

YANDEX_USER_WAVE_STATION = "user:onyourwave"
_WAVE_FROM = "mobile-home-quantis-wave"


class AsyncWaveService:
    """Персональная волна: сейчас — Yandex ``user:onyourwave``."""

    async def start_yandex_wave(self) -> WavePlaylist | None:
        if not yandex_token():
            logger.info("Моя волна: нет токена Yandex")
            return None
        client = Clients().get_yandex_client()
        if client is None:
            logger.warning("Моя волна: клиент Yandex недоступен")
            return None
        try:
            result = await client.rotor_station_tracks(
                YANDEX_USER_WAVE_STATION,
                settings2=True,
            )
        except Exception:
            logger.exception("Моя волна: не удалось получить треки станции")
            return None
        if result is None:
            return None

        tracks = self._tracks_from_sequence(getattr(result, "sequence", None))
        if not tracks:
            logger.warning("Моя волна: пустая последовательность треков")
            return None

        batch_id = getattr(result, "batch_id", None)
        try:
            await client.rotor_station_feedback_radio_started(
                YANDEX_USER_WAVE_STATION,
                _WAVE_FROM,
                batch_id=batch_id,
            )
        except Exception:
            logger.debug("Моя волна: radioStarted feedback не отправлен", exc_info=True)

        if tracks:
            try:
                await client.rotor_station_feedback_track_started(
                    YANDEX_USER_WAVE_STATION,
                    track_id=tracks[0].track_id,
                    batch_id=batch_id,
                )
            except Exception:
                logger.debug(
                    "Моя волна: trackStarted feedback не отправлен",
                    exc_info=True,
                )

        return WavePlaylist(
            name="Моя волна",
            tracks=tracks,
            source="yandex",
            station=YANDEX_USER_WAVE_STATION,
            batch_id=batch_id,
        )

    async def fetch_more_yandex(
        self,
        *,
        queue_track_id: str | int,
        batch_id: str | None = None,
    ) -> list[YandexTrack]:
        """Продолжение цепочки волны (следующий батч)."""
        client = Clients().get_yandex_client()
        if client is None or not yandex_token():
            return []
        try:
            result = await client.rotor_station_tracks(
                YANDEX_USER_WAVE_STATION,
                settings2=True,
                queue=queue_track_id,
            )
        except Exception:
            logger.exception("Моя волна: не удалось продлить цепочку")
            return []
        if result is None:
            return []
        return self._tracks_from_sequence(getattr(result, "sequence", None))

    @staticmethod
    def _tracks_from_sequence(sequence: Any) -> list[YandexTrack]:
        if not sequence:
            return []
        tracks: list[YandexTrack] = []
        for item in sequence:
            track = getattr(item, "track", None)
            if track is None:
                continue
            try:
                tracks.append(_yandex_track_from_api(track))
            except Exception:
                logger.debug("Моя волна: пропуск трека в sequence", exc_info=True)
        return tracks
