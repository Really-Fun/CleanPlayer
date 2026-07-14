from __future__ import annotations

from PySide6.QtWidgets import QLabel, QSizePolicy, QVBoxLayout, QWidget


class HomeSection(QWidget):
    """Секция главной: заголовок + контент без вложенного скролла."""

    def __init__(
        self,
        title: str,
        subtitle: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("homeSection")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(12)

        header = QVBoxLayout()
        header.setSpacing(3)
        self._title = QLabel(title)
        self._title.setObjectName("homeSectionTitle")
        header.addWidget(self._title)
        self._subtitle = QLabel(subtitle)
        self._subtitle.setObjectName("homeSectionSubtitle")
        self._subtitle.setVisible(bool(subtitle))
        header.addWidget(self._subtitle)
        root.addLayout(header)

        self._body = QWidget()
        self._body.setObjectName("homeSectionBody")
        self._body.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Maximum,
        )
        self._body_layout = QVBoxLayout(self._body)
        self._body_layout.setContentsMargins(0, 0, 0, 0)
        self._body_layout.setSpacing(0)
        root.addWidget(self._body)

    def set_subtitle(self, text: str) -> None:
        self._subtitle.setText(text)
        self._subtitle.setVisible(bool(text))

    def add_widget_block(self, widget: QWidget) -> None:
        """Контент секции на всю ширину (сетка / таблица)."""
        while self._body_layout.count():
            item = self._body_layout.takeAt(0)
            old = item.widget()
            if old is not None:
                old.deleteLater()
        widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        self._body_layout.addWidget(widget)
