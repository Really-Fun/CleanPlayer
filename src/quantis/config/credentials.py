"""Сохранение токенов в системном keyring."""

from __future__ import annotations

from keyring import get_password, set_password

from quantis.config.clients import Clients
from quantis.config.constants import SERVICE_NAME_YANDEX, USER


def yandex_token() -> str:
    return get_password(SERVICE_NAME_YANDEX, USER) or ""


def save_yandex_token(token: str) -> None:
    value = token.strip()
    if not value:
        raise ValueError("Токен не может быть пустым")
    set_password(SERVICE_NAME_YANDEX, USER, value)
    Clients().reload_yandex_client()
