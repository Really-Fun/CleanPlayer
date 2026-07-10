from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


class HomeSection(QWidget):
    """Секция главной: заголовок + горизонтальная лента контента."""

    def __init__(
        self,
        title: str,
        subtitle: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("homeSection")

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(10)

        header = QVBoxLayout()
        header.setSpacing(2)
        self._title = QLabel(title)
        self._title.setObjectName("homeSectionTitle")
        header.addWidget(self._title)
        self._subtitle = QLabel(subtitle)
        self._subtitle.setObjectName("homeSectionSubtitle")
        self._subtitle.setVisible(bool(subtitle))
        header.addWidget(self._subtitle)
        root.addLayout(header)

        self._scroll = QScrollArea()
        self._scroll.setObjectName("homeSectionScroll")
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setFrameShape(QScrollArea.Shape.NoFrame)

        self._strip = QWidget()
        self._strip.setObjectName("homeSectionStrip")
        self._strip_layout = QHBoxLayout(self._strip)
        self._strip_layout.setContentsMargins(0, 0, 0, 0)
        self._strip_layout.setSpacing(12)
        self._strip_layout.addStretch()
        self._scroll.setWidget(self._strip)
        root.addWidget(self._scroll)

    def set_subtitle(self, text: str) -> None:
        self._subtitle.setText(text)
        self._subtitle.setVisible(bool(text))

    def clear_items(self) -> None:
        while self._strip_layout.count():
            item = self._strip_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self._strip_layout.addStretch()

    def add_item(self, widget: QWidget, *, stretch: bool = False) -> None:
        if stretch:
            self._strip_layout.addStretch()
        self._strip_layout.insertWidget(self._strip_layout.count() - 1, widget)

    def add_widget_block(self, widget: QWidget) -> None:
        """Вставляет блок на всю ширину (например таблица недавних)."""
        self._scroll.setWidget(widget)
        widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
