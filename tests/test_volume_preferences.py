"""Unit-тесты сохранения громкости в UiPreferences."""

from __future__ import annotations

import pytest
from PySide6.QtCore import QSettings

from quantis.ui.preferences import UiPreferences


@pytest.fixture(autouse=True)
def reset_preferences_singleton():
    from PySide6.QtCore import QSettings

    settings = QSettings("ReallyFun", "Quantis")
    settings.remove("playback/volume")
    settings.sync()
    UiPreferences._instance = None
    yield
    UiPreferences._instance = None


def test_volume_defaults_to_80(qapp) -> None:
    prefs = UiPreferences()
    assert prefs.volume == 80


def test_volume_persists(qapp) -> None:
    prefs = UiPreferences()
    prefs.set_volume(42)
    assert prefs.volume == 42

    stored = QSettings("ReallyFun", "Quantis").value("playback/volume")
    assert int(stored) == 42


def test_volume_clamped(qapp) -> None:
    prefs = UiPreferences()
    prefs.set_volume(150)
    assert prefs.volume == 100
    prefs.set_volume(-10)
    assert prefs.volume == 0
