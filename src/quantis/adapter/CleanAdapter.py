'''Определяет и подключает подходящий к операционной системе Remote Control API (Media Control API)
Linux - MPRIS
Windows - SMTC
'''
from __future__ import annotations

import platform
from asyncio import AbstractEventLoop

from quantis.core import AppContext
from quantis.player.player import Player


class CleanAdapter:
    """Создаём нужный адаптер в зависимости от ОС пользователя"""

    def __init__(self, context: AppContext) -> None:
        current_os = platform.system()

        match current_os:
            case "Linux":
                self.start_mpris(player=context.player, event_bus=context.event_bus, path_provider=context.path_provider)

            case "Windows":
                self.start_smtc(player=context.player, loop=context.loop, event_bus=context.event_bus)

    def start_mpris(self, player: Player, event_bus, path_provider) -> None:
        """Запускаем MPRIS для линукс
        """
        from mpris_server.server import Server

        from .MprisAdapter import QuantisAppAdapter, QuantisEventHandler

        mpris_adapter = QuantisAppAdapter(player, event_bus, path_provider)
        mpris = Server("Quantis", mpris_adapter)
        event_handler = QuantisEventHandler(mpris.root, mpris.player)
        mpris_adapter.set_event_handler(event_handler)
        mpris.publish()

    def start_smtc(self, player: Player, loop: AbstractEventLoop, event_bus) -> None:
        """Запускаем SMTC для Windows
        """
        from .windows_adapter import WindowsSMTCAdapter

        WindowsSMTCAdapter(player, loop, event_bus)