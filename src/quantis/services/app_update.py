"""Проверка новой версии Quantis через GitHub Releases.

Сеть живёт только здесь: UI вызывает ``fetch_latest_release`` через AsyncBridge
и открывает ``html_url`` в браузере. Файлы приложения не скачиваются.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Mapping

import aiohttp

from quantis.version import __version__

GITHUB_REPO = "Really-Fun/Quantis"
GITHUB_LATEST_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
SKIP_ENV = "QUANTIS_SKIP_UPDATE_CHECK"
CHECK_INTERVAL_SECONDS = 24 * 60 * 60
_REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=12)
_TRUTHY = ("1", "true", "yes", "on")


@dataclass(frozen=True, slots=True)
class ReleaseInfo:
    tag: str
    html_url: str
    name: str = ""
    published_at: str = ""


def app_version() -> str:
    return __version__


def display_version(raw: str) -> str:
    """Человекочитаемая версия без префикса ``v``."""
    text = (raw or "").strip()
    if len(text) >= 2 and text[0] in "vV" and text[1].isdigit():
        return text[1:]
    return text


def normalize_version(raw: str) -> tuple[int, ...]:
    """Разбирает ``1.2.3`` / ``v1.2.3`` в кортеж чисел для сравнения."""
    text = display_version(raw)
    parts: list[int] = []
    for chunk in text.split("."):
        digits = ""
        for char in chunk:
            if char.isdigit():
                digits += char
            else:
                break
        parts.append(int(digits) if digits else 0)
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts)


def is_newer(current: str, remote: str) -> bool:
    if not remote.strip():
        return False
    return normalize_version(remote) > normalize_version(current)


def skip_update_check() -> bool:
    return os.environ.get(SKIP_ENV, "").strip().lower() in _TRUTHY


def should_auto_check(
    *,
    last_check_at: float = 0.0,
    now: float,
    enabled: bool = True,
) -> bool:
    if skip_update_check() or not enabled:
        return False
    if last_check_at <= 0:
        return True
    return (now - last_check_at) >= CHECK_INTERVAL_SECONDS


def should_announce(current: str, remote_tag: str, dismissed_tag: str) -> bool:
    """Плашка: remote новее current и этот тег ещё не скрывали."""
    if not is_newer(current, remote_tag):
        return False
    if dismissed_tag and normalize_version(dismissed_tag) == normalize_version(
        remote_tag
    ):
        return False
    return True


def parse_release_payload(data: Mapping[str, Any]) -> ReleaseInfo | None:
    """Собирает ReleaseInfo. Draft/prerelease — ``None`` (не предлагаем)."""
    if data.get("draft") or data.get("prerelease"):
        return None
    tag = str(data.get("tag_name") or "").strip()
    if not tag:
        raise ValueError("GitHub release has no tag_name")
    html_url = str(data.get("html_url") or "").strip()
    if not html_url:
        raise ValueError("GitHub release has no html_url")
    return ReleaseInfo(
        tag=tag,
        html_url=html_url,
        name=str(data.get("name") or "").strip(),
        published_at=str(data.get("published_at") or "").strip(),
    )


async def _download_latest_payload() -> Mapping[str, Any]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": f"Quantis/{app_version()}",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    async with aiohttp.ClientSession(
        timeout=_REQUEST_TIMEOUT, headers=headers
    ) as session:
        async with session.get(GITHUB_LATEST_URL) as response:
            response.raise_for_status()
            payload = await response.json()
    if not isinstance(payload, Mapping):
        raise ValueError("GitHub latest release payload is not an object")
    return payload


async def fetch_latest_release() -> ReleaseInfo | None:
    payload = await _download_latest_payload()
    return parse_release_payload(payload)
