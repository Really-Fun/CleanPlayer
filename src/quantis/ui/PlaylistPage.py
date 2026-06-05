from PySide6.QtWidgets import QListView, QMainWindow, QMenu
from quantis.ui.qt_models.playlist_model import PlaylistModel
from quantis.ui.delegates.TrackDelegate import TrackDelegate

class PlaylistPage(QListView):
    def __init__(self, playlist, parent=None):
        super().__init__(parent)

        self.setItemDelegate(TrackDelegate(self))
        self.setMouseTracking(True)

        self.playlist_model = PlaylistModel(playlist)
        self.setModel(self.playlist_model)

        self.itemDelegate().signals.play_requested.connect(self.handle_play)
        self.itemDelegate().signals.download_requested.connect(self.handle_download)
        self.itemDelegate().signals.context_menu_requested.connect(self._show_menu)

    def handle_play(self, track):
        print(f"Плеер, играй: {track.title}")
        self.playlist_model.set_current_track_id(track.track_id)

    def handle_download(self, track):
        print(f"Сервис скачивания, качай: {track.track_id}")

    def _show_menu(self, track, global_pos):
        menu = QMenu(self)
        menu.addAction("Добавить в очередь")
        menu.addAction("Удалить")
        menu.exec(global_pos)