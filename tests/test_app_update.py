"""Проверка обновлений: semver, payload GitHub, throttle — без сети."""

from __future__ import annotations

import pytest

from quantis.services.app_update import (
    CHECK_INTERVAL_SECONDS,
    SKIP_ENV,
    app_version,
    display_version,
    fetch_latest_release,
    is_newer,
    normalize_version,
    parse_release_payload,
    should_announce,
    should_auto_check,
    skip_update_check,
)
from quantis.version import __version__


@pytest.fixture(autouse=True)
def _clear_skip_env(monkeypatch) -> None:
    monkeypatch.delenv(SKIP_ENV, raising=False)


def test_app_version_matches_package_constant() -> None:
    assert app_version() == __version__
    assert __version__ == "0.1.1"


def test_display_version_strips_v_prefix() -> None:
    assert display_version("v0.2.0") == "0.2.0"
    assert display_version("V1.0") == "1.0"
    assert display_version("0.1.1") == "0.1.1"


def test_normalize_and_compare_versions() -> None:
    assert normalize_version("v0.2.0") == (0, 2, 0)
    assert normalize_version("0.1.1") == (0, 1, 1)
    assert is_newer("0.1.1", "v0.2.0")
    assert is_newer("0.1.1", "0.1.2")
    assert not is_newer("0.1.1", "0.1.1")
    assert not is_newer("0.1.1", "v0.1.1")
    assert not is_newer("0.2.0", "0.1.9")
    assert not is_newer("0.1.1", "")
    assert is_newer("0.9.0", "0.10.0")


def test_parse_release_payload_ok() -> None:
    info = parse_release_payload(
        {
            "tag_name": "v0.2.0",
            "html_url": "https://github.com/Really-Fun/Quantis/releases/tag/v0.2.0",
            "name": "Quantis 0.2.0",
            "published_at": "2026-09-04T00:00:00Z",
            "prerelease": False,
            "draft": False,
        }
    )
    assert info is not None
    assert info.tag == "v0.2.0"
    assert info.html_url.endswith("/v0.2.0")
    assert info.name == "Quantis 0.2.0"


def test_parse_release_ignores_prerelease_and_draft() -> None:
    assert (
        parse_release_payload(
            {
                "tag_name": "v0.3.0-rc1",
                "html_url": "https://example.com/rc",
                "prerelease": True,
            }
        )
        is None
    )
    assert (
        parse_release_payload(
            {
                "tag_name": "v0.3.0",
                "html_url": "https://example.com/draft",
                "draft": True,
            }
        )
        is None
    )


def test_parse_release_requires_tag_and_url() -> None:
    with pytest.raises(ValueError, match="tag_name"):
        parse_release_payload({"html_url": "https://example.com"})
    with pytest.raises(ValueError, match="html_url"):
        parse_release_payload({"tag_name": "v0.2.0"})


def test_should_announce_respects_dismissed_tag() -> None:
    assert should_announce("0.1.1", "v0.2.0", "")
    assert not should_announce("0.1.1", "v0.2.0", "0.2.0")
    assert not should_announce("0.1.1", "v0.2.0", "v0.2.0")
    assert should_announce("0.1.1", "v0.3.0", "v0.2.0")
    assert not should_announce("0.1.1", "0.1.1", "")
    assert not should_announce("0.1.1", "", "")


def test_should_auto_check_throttle() -> None:
    now = 1_000_000.0
    assert should_auto_check(last_check_at=0, now=now)
    assert not should_auto_check(
        last_check_at=now - 60,
        now=now,
    )
    assert should_auto_check(
        last_check_at=now - CHECK_INTERVAL_SECONDS,
        now=now,
    )
    assert not should_auto_check(last_check_at=0, now=now, enabled=False)


def test_skip_env_disables_auto_check(monkeypatch) -> None:
    monkeypatch.delenv(SKIP_ENV, raising=False)
    assert not skip_update_check()
    monkeypatch.setenv(SKIP_ENV, "1")
    assert skip_update_check()
    assert not should_auto_check(last_check_at=0, now=1.0)


@pytest.mark.asyncio
async def test_fetch_latest_release_uses_parser(monkeypatch) -> None:
    async def fake_download():
        return {
            "tag_name": "v0.2.0",
            "html_url": "https://github.com/Really-Fun/Quantis/releases/tag/v0.2.0",
            "prerelease": False,
        }

    monkeypatch.setattr(
        "quantis.services.app_update._download_latest_payload",
        fake_download,
    )
    info = await fetch_latest_release()
    assert info is not None
    assert info.tag == "v0.2.0"


def test_update_preferences_roundtrip(qapp) -> None:
    from PySide6.QtCore import QSettings

    from quantis.ui.preferences import UiPreferences

    settings = QSettings("ReallyFun", "Quantis")
    for key in (
        "updates/last_check_at",
        "updates/last_tag",
        "updates/last_html_url",
        "updates/dismissed_tag",
        "updates/check_on_startup",
    ):
        settings.remove(key)
    settings.sync()
    UiPreferences._instance = None

    prefs = UiPreferences()
    assert prefs.update_check_on_startup is True
    assert prefs.update_last_check_at == 0.0
    assert prefs.update_last_tag == ""

    prefs.set_update_check_on_startup(False)
    prefs.set_update_last_check_at(1_700_000_000)
    prefs.set_update_last_tag("v0.2.0")
    prefs.set_update_last_html_url("https://example.com/rel")
    prefs.set_update_dismissed_tag("v0.2.0")

    assert prefs.update_check_on_startup is False
    assert prefs.update_last_check_at == 1_700_000_000.0
    assert prefs.update_last_tag == "v0.2.0"
    assert prefs.update_last_html_url == "https://example.com/rel"
    assert prefs.update_dismissed_tag == "v0.2.0"

    UiPreferences._instance = None


def test_settings_page_shows_current_version(qapp) -> None:
    from PySide6.QtCore import QSettings

    from quantis.ui.preferences import UiPreferences
    from quantis.ui.views.settings_page import SettingsPage

    settings = QSettings("ReallyFun", "Quantis")
    settings.remove("updates/last_tag")
    settings.remove("updates/last_check_at")
    settings.remove("updates/last_html_url")
    settings.sync()
    UiPreferences._instance = None

    page = SettingsPage()
    assert app_version() in page._version_label.text()
    assert page._update_status.text() == "Ещё не проверяли"
    assert not page._update_open_btn.isEnabled()

    UiPreferences._instance = None
