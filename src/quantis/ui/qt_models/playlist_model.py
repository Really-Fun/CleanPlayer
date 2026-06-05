from PySide6.QtCore import QAbstractListModel, QModelIndex, Qt
from quantis.models import Track

class PlaylistModel(QAbstractListModel):
    # Кастомные роли для делегата
    TrackRole = Qt.ItemDataRole.UserRole + 1
    IsPlayingRole = Qt.ItemDataRole.UserRole + 2

    def __init__(self, playlist, parent=None):
        super().__init__(parent)
        self._playlist = playlist
        self._current_track_id = None  # Храним ID играющего трека здесь

    def rowCount(self, parent=QModelIndex()) -> int:
        return len(self._playlist)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None

        track = self._playlist.get_track(index.row())

        if role == PlaylistModel.TrackRole:
            return track
        elif role == PlaylistModel.IsPlayingRole:
            return getattr(track, 'track_id', None) == self._current_track_id

        return None

    def set_current_track_id(self, track_id: str):
        self._current_track_id = track_id
        self.dataChanged.emit(self.index(0, 0), self.index(self.rowCount() - 1, 0))