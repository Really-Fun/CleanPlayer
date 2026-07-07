"""UI model списка треков с ленивой подгрузкой строк."""

from __future__ import annotations

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt

from quantis.models.track import Track


class TrackListModel(QAbstractTableModel):
    TrackRole = Qt.ItemDataRole.UserRole + 1
    IndexRole = Qt.ItemDataRole.UserRole + 2
    IsPlayingRole = Qt.ItemDataRole.UserRole + 3

    _BATCH_SIZE = 40

    def __init__(self, tracks: list[Track] | None = None, parent=None):
        super().__init__(parent)
        self._tracks: list[Track] = list(tracks or [])
        self._loaded_count = min(len(self._tracks), self._BATCH_SIZE)
        self._playing_track: Track | None = None

    def roleNames(self) -> dict[int, bytes]:
        return {
            self.TrackRole: b"track",
            self.IndexRole: b"index",
            self.IsPlayingRole: b"isPlaying",
        }

    def rowCount(self, parent=QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return self._loaded_count

    def columnCount(self, parent=QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return 1

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> object:
        if not index.isValid() or not (0 <= index.row() < self._loaded_count):
            return None

        track = self._tracks[index.row()]

        if role == self.TrackRole:
            return track
        if role == Qt.ItemDataRole.DisplayRole:
            return f"{track.title} — {track.author}"
        if role == self.IndexRole:
            return index.row() + 1
        if role == self.IsPlayingRole:
            return self._playing_track is not None and track == self._playing_track
        return None

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable

    def canFetchMore(self, parent: QModelIndex) -> bool:
        if parent.isValid():
            return False
        return self._loaded_count < len(self._tracks)

    def fetchMore(self, parent: QModelIndex) -> None:
        if parent.isValid():
            return
        remaining = len(self._tracks) - self._loaded_count
        if remaining <= 0:
            return
        count = min(remaining, self._BATCH_SIZE)
        start = self._loaded_count
        end = start + count - 1
        self.beginInsertRows(QModelIndex(), start, end)
        self._loaded_count += count
        self.endInsertRows()

    def set_tracks(self, tracks: list[Track]) -> None:
        self.beginResetModel()
        self._tracks = list(tracks)
        self._loaded_count = min(len(self._tracks), self._BATCH_SIZE)
        self.endResetModel()

    def all_tracks(self) -> list[Track]:
        return list(self._tracks)

    def get_track(self, index: int) -> Track | None:
        if 0 <= index < len(self._tracks):
            return self._tracks[index]
        return None

    def remove_track(self, index: int) -> bool:
        if not (0 <= index < len(self._tracks)):
            return False

        was_visible = index < self._loaded_count
        if was_visible:
            self.beginRemoveRows(QModelIndex(), index, index)
        self._tracks.pop(index)
        if was_visible:
            self._loaded_count = max(0, self._loaded_count - 1)
            self.endRemoveRows()
        return True

    def set_playing_track(self, track: Track | None) -> None:
        self._playing_track = track
        if self.rowCount() == 0:
            return
        self.dataChanged.emit(
            self.index(0, 0), self.index(self.rowCount() - 1, 0), [self.IsPlayingRole]
        )
