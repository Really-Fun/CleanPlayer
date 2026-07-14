"""Сохранение токенов и cookies.

Yandex OAuth — в системном keyring (короткий секрет).
YouTube cookies — в локальный файл: Windows CredWrite не принимает
большие blob'ы (ошибка 1783).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from keyring import delete_password, get_password, set_password
from keyring.errors import KeyringError, PasswordDeleteError

from quantis.config.clients import Clients
from quantis.config.constants import (
    SERVICE_NAME_YANDEX,
    SERVICE_NAME_YOUTUBE_COOKIE,
    USER,
)
from quantis.utils.resource_path import app_dir

logger = logging.getLogger(__name__)


def _youtube_cookie_path() -> Path:
    folder = app_dir() / "credentials"
    folder.mkdir(parents=True, exist_ok=True)
    return folder / "youtube_cookies.txt"


def _validate_youtube_auth(value: str) -> str:
    """Проверяет формат auth для ytmusicapi (JSON headers или путь к файлу)."""
    text = value.strip()
    if not text:
        raise ValueError("Cookie не может быть пустым")
    path = Path(text)
    if path.is_file():
        return text
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(
            "Нужен JSON от ytmusicapi (oauth/browser) или путь к файлу auth"
        ) from exc
    if not isinstance(parsed, dict):
        raise ValueError("Auth должен быть JSON-объектом (headers) или путём к файлу")
    return text


def yandex_token() -> str:
    return get_password(SERVICE_NAME_YANDEX, USER) or ""


def yotube_cookie() -> str:
    path = _youtube_cookie_path()
    if path.is_file():
        try:
            return path.read_text(encoding="utf-8").strip()
        except OSError:
            logger.exception("Не удалось прочитать YouTube cookies из %s", path)
    # Миграция со старого keyring (если когда-то сохраняли короткий blob)
    try:
        legacy = get_password(SERVICE_NAME_YOUTUBE_COOKIE, USER) or ""
    except KeyringError:
        legacy = ""
    if legacy:
        try:
            path.write_text(legacy, encoding="utf-8")
            try:
                delete_password(SERVICE_NAME_YOUTUBE_COOKIE, USER)
            except (KeyringError, PasswordDeleteError):
                pass
        except OSError:
            logger.exception("Не удалось мигрировать YouTube cookies в файл")
        return legacy
    return ""


def youtube_cookie() -> str:
    """Алиас без опечатки для yotube_cookie()."""
    return yotube_cookie()


def save_yandex_token(token: str) -> None:
    value = token.strip()
    if not value:
        raise ValueError("Токен не может быть пустым")
    set_password(SERVICE_NAME_YANDEX, USER, value)
    Clients().reload_yandex_client()


def save_youtube_cookie(cookie: str) -> None:
    value = _validate_youtube_auth(cookie)
    path = _youtube_cookie_path()
    try:
        path.write_text(value, encoding="utf-8")
    except OSError as exc:
        raise RuntimeError(f"Не удалось сохранить cookies: {exc}") from exc
    # Убрать устаревшую запись keyring, если была
    try:
        delete_password(SERVICE_NAME_YOUTUBE_COOKIE, USER)
    except (KeyringError, PasswordDeleteError):
        pass
    Clients().reload_youtube_client()
