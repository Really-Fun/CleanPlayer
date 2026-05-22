import os
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon, QPixmap
# Импортируем твою функцию get_asset_path
from quantis.utils import get_asset_path

class CustomTitleBar(QWidget):
    def __init__(self, parent, title="Quantis"):
        # Передаем parent, чтобы виджет знал, к какому окну он привязан
        super().__init__(parent)
        self.parent_window = parent 
        
        # --- Настройки самого виджета заголовка ---
        # 1. ВКЛЮЧАЕМ ПРОЗРАЧНОСТЬ ФОНА ДЛЯ ЭТОГО ВИДЖЕТА
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedHeight(30) # Чуть более аккуратная высота
        
        # 2. Глобальный стиль: ЯВНО отключить рамки у QLabel и QPushButton
        self.setStyleSheet("""
            QWidget { background: transparent; border: none; }
            QLabel { background: transparent; border: none; }
            QPushButton { background: transparent; border: none; }
        """)
        
        # Настраиваем Layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 0, 0)
        layout.setSpacing(0)
        
        # ─── Инициализация элементов ───────────────────────────────────

        # Пути к иконкам (предполагаем, что они у тебя есть)
        logo_path = get_asset_path("assets/icons/logo_title.png") # Уменьшенная версия твоего лого
        min_icon_path = get_asset_path("assets/icons/minimize.svg")
        close_icon_path = get_asset_path("assets/icons/close.svg")

        # 1. Логотип (опционально, но делает интерфейс богаче)
        if os.path.exists(logo_path):
            self.icon_label = QLabel()
            pm = QPixmap(logo_path).scaled(18, 18, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.icon_label.setPixmap(pm)
            self.icon_label.setFixedSize(18, 18)
            layout.addWidget(self.icon_label)
            layout.addSpacing(8) # Отступ от лого до текста

        # 2. Текст заголовка (Quantis)
        self.title_label = QLabel(title)
        # Явный цвет и стиль, никаких рамок!
        self.title_label.setStyleSheet("color: #fdfdfd; font-size: 13px; font-weight: bold;")
        layout.addWidget(self.title_label)
        
        # Пружина (растравливает заголовок и кнопки по краям)
        layout.addStretch()

        # 3. Кнопка "Свернуть" с иконкой
        self.btn_minimize = QPushButton()
        if os.path.exists(min_icon_path):
            self.btn_minimize.setIcon(QIcon(min_icon_path))
            self.btn_minimize.setIconSize(QSize(18, 18))
        else:
            self.btn_minimize.setText("—") # Запасной вариант, если нет иконки
            self.btn_minimize.setStyleSheet("color: #999999;")

        self.btn_minimize.setFixedSize(40, 30)
        self.btn_minimize.setStyleSheet(self._button_style())
        self.btn_minimize.clicked.connect(self.parent_window.showMinimized)
        layout.addWidget(self.btn_minimize)
        
        # 4. Кнопка "Закрыть" с иконкой
        self.btn_close = QPushButton()
        if os.path.exists(close_icon_path):
            self.btn_close.setIcon(QIcon(close_icon_path))
            self.btn_close.setIconSize(QSize(18, 18))
        else:
            self.btn_close.setText("✕")
            self.btn_close.setStyleSheet("color: #999999;")

        self.btn_close.setFixedSize(40, 30)
        # Для крестика особый ховер цвет
        self.btn_close.setStyleSheet(self._button_style(hover_color="#c41c30"))
        self.btn_close.clicked.connect(self.parent_window.close)
        layout.addWidget(self.btn_close)
        
        self.drag_pos = None

    # Вспомогательный метод для стилизации кнопок
    def _button_style(self, hover_color="#3a3a3a"):
        # Убираем все отступы и делаем фон прозрачным
        return f"""
            QPushButton {{
                background-color: transparent;
                border: none;
                margin: 0px;
                padding: 0px;
            }}
            QPushButton:hover {{
                background-color: {hover_color};
            }}
        """

    # --- Логика перетаскивания окна ---
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if self.drag_pos is not None:
            # Считаем разницу и двигаем родительское (главное) окно
            delta = event.globalPosition().toPoint() - self.drag_pos
            self.parent_window.move(self.parent_window.pos() + delta)
            self.drag_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        self.drag_pos = None