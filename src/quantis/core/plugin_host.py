"""Узкий контракт для плагинов (без God Object)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from PySide6.QtGui import QIcon

if TYPE_CHECKING:
    from quantis.controllers.playback_controller import PlaybackController
    from quantis.core.async_bridge import AsyncBridge
    from quantis.plugins.event_bus import EventBus
    from quantis.services.music_service import MusicService


@dataclass
class PluginHost:
    event_bus: EventBus
    playback: PlaybackController
    music: MusicService
    async_bridge: AsyncBridge | None = None

    def register_nav_item(
        self,
        item_id: str,
        tooltip: str,
        page_id: int,
        *,
        icon: QIcon | None = None,
        on_click: Callable[[], None] | None = None,
    ) -> None:
        from quantis.ui.ui_extensions import NavExtension, UiExtensionHost

        UiExtensionHost.instance().register_nav_item(
            NavExtension(
                item_id=item_id,
                tooltip=tooltip,
                icon=icon,
                page_id=page_id,
                from_plugin=True,
                on_click=on_click,
            )
        )

    def unregister_nav_item(self, item_id: str) -> None:
        from quantis.ui.ui_extensions import UiExtensionHost

        UiExtensionHost.instance().unregister_nav_item(item_id)

    def register_player_action(
        self,
        action_id: str,
        tooltip: str,
        callback: Callable[[], None],
        *,
        icon: QIcon | None = None,
    ) -> None:
        from quantis.ui.ui_extensions import PlayerActionExtension, UiExtensionHost

        UiExtensionHost.instance().register_player_action(
            PlayerActionExtension(
                action_id=action_id,
                tooltip=tooltip,
                icon=icon,
                callback=callback,
                from_plugin=True,
            )
        )

    def unregister_player_action(self, action_id: str) -> None:
        from quantis.ui.ui_extensions import UiExtensionHost

        UiExtensionHost.instance().unregister_player_action(action_id)
