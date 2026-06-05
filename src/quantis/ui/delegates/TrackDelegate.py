from PySide6.QtCore import QPoint, QRect, QSize, Qt, Signal, QObject, QModelIndex
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QMenu, QStyledItemDelegate, QStyle, QStyleOptionViewItem
from quantis.utils import get_asset_path
from quantis.ui.qt_models.playlist_model import PlaylistModel


class TrackDelegateSignals(QObject):
    """Делегаты не могут объявлять сигналы напрямую, используем вспомогательный объект."""
    play_requested = Signal(object)
    download_requested = Signal(object)
    context_menu_requested = Signal(object, QPoint)  # track, global_pos


class TrackDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.signals = TrackDelegateSignals()

        # Кэшируем иконки, чтобы не загружать их каждый раз
        self._play_icon = QIcon(get_asset_path("assets/icons/play.svg"))
        self._download_icon = QIcon(get_asset_path("assets/icons/download.svg"))

    def sizeHint(self, option, index) -> QSize:
        # Задаем фиксированную высоту строки — 60px
        return QSize(option.rect.width(), 60)

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex):
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)

        # Достаем данные из модели
        track = index.data(PlaylistModel.TrackRole)
        is_playing = index.data(PlaylistModel.IsPlayingRole)
        is_hovered = bool(option.state & QStyle.State_MouseOver)

        rect = option.rect

        # 1. Рисуем фон при наведении (эффект карточки в стиле Киберпанк/Тёмный неон)
        if is_hovered:
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor("#1a1a24"))  # Твой цвет ховера карточки
            painter.drawRoundedRect(rect.adjusted(4, 2, -4, -2), 8, 8)
        elif is_playing:
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor("#0d1b2a"))  # Цвет фона активного трека
            painter.drawRoundedRect(rect.adjusted(4, 2, -4, -2), 8, 8)

        # 2. Рисуем индекс или иконку "Play" слева
        num_rect = QRect(rect.x() + 10, rect.y(), 30, rect.height())
        if is_playing:
            painter.setPen(QColor("#00f0ff"))  # Киберпанк неон-голубой
            painter.drawText(num_rect, Qt.AlignCenter, "▶")
        else:
            painter.setPen(QColor("#888888"))
            painter.drawText(num_rect, Qt.AlignCenter, str(index.row() + 1))

        # 3. Рисуем Обложку (Заглушку или загруженную)
        cover_rect = QRect(rect.x() + 50, rect.y() + 6, 48, 48)
        # Здесь можно нарисовать твой QPixmap обложки
        painter.setBrush(QColor("#252538"))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(cover_rect, 6, 6)

        # Если навели ховер — рисуем кнопку плей поверх обложки
        if is_hovered:
            painter.setBrush(QColor(0, 0, 0, 120))  # Затемнение
            painter.drawRoundedRect(cover_rect, 6, 6)
            self._play_icon.paint(painter, cover_rect.adjusted(12, 12, -12, -12))

        # 4. Текст: Название и Автор
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPixelSize(14)

        author_font = QFont()
        author_font.setPixelSize(12)

        # Позиции для текста
        text_x = rect.x() + 110
        title_rect = QRect(text_x, rect.y() + 12, rect.width() - text_x - 100, 20)
        author_rect = QRect(text_x, rect.y() + 32, rect.width() - text_x - 100, 16)

        painter.setFont(title_font)
        painter.setPen(QColor("#ffffff") if not is_playing else QColor("#00f0ff"))
        painter.drawText(title_rect, Qt.AlignLeft | Qt.AlignVCenter, track.title)

        painter.setFont(author_font)
        painter.setPen(QColor("#aaaaaa"))
        painter.drawText(author_rect, Qt.AlignLeft | Qt.AlignVCenter, track.author)

        # 5. Кнопка скачивания справа (только при ховере)
        if is_hovered:
            dl_rect = QRect(rect.right() - 40, rect.y() + 16, 28, 28)
            # Сохраняем геометрию кнопки в свойства индекса, чтобы обработать клик
            self._download_btn_rect = dl_rect
            self._download_icon.paint(painter, dl_rect)

        painter.restore()

    # --- Обработка кликов по абстрактным кнопкам внутри области ---
    def editorEvent(self, event, model, option, index) -> bool:
        track = index.data(PlaylistModel.TrackRole)

        # Клик левой кнопкой мыши
        if event.type() == event.Type.MouseButtonPress and event.button() == Qt.LeftButton:
            pos = event.position().toPoint()

            # Проверяем, попал ли клик в область воображаемой кнопки скачивания
            rect = option.rect
            dl_rect = QRect(rect.right() - 40, rect.y() + 16, 28, 28)

            if dl_rect.contains(pos):
                self.signals.download_requested.emit(track)
                return True

            # Иначе — просто запускаем трек
            self.signals.play_requested.emit(track)
            return True

        # Правый клик — контекстное меню
        elif event.type() == event.Type.MouseButtonPress and event.button() == Qt.RightButton:
            self.signals.context_menu_requested.emit(track, event.globalPosition().toPoint())
            return True

        return super().editorEvent(event, model, option, index)