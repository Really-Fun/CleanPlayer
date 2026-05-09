"""Шина событий приложения.

Построена на базе Qt Signals. 
Обеспечивает потокобезопасность и автоматическое удаление подписок 
при удалении объектов (никаких утечек памяти).
"""

from PySide6.QtCore import QObject, Signal

class EventBus(QObject):
    """Центральная шина событий приложения."""
    
    track_changed = Signal(object)     # Передает объект Track
    playback_paused = Signal()
    playback_resumed = Signal()
    playback_stopped = Signal()
    track_finished = Signal()
    
    next_requested = Signal()
    previous_requested = Signal()
    
    theme_changed = Signal(str)        # Передает 'dark' или 'light'
    plugin_loaded = Signal(str)        # Передает plugin_id
    plugin_unloaded = Signal(str)      # Передает plugin_id
    error_occurred = Signal(str)       # Передает текст ошибки для показа в UI

    def __init__(self) -> None:
        super().__init__()