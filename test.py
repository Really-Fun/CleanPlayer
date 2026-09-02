import sys
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QBrush, QPen
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QSlider, QScrollArea, QFrame, QLineEdit,
    QListWidget, QListWidgetItem, QSizePolicy, QGridLayout, QGraphicsDropShadowEffect
)

# --- ПАЛИТРА ТЕМЫ "AURORA" ---
BG_COLOR = "#0B0D12"
SURFACE_COLOR = "#141821"
SURFACE_HOVER = "#1C212D"
TEXT_MAIN = "#F2F4F8"
TEXT_DIM = "#8A92A6"
ACCENT_COLOR = "#6C5CE7"
YT_COLOR = "#FF4E45"
YA_COLOR = "#FFDB4D"

QSS = f"""
QMainWindow, QWidget#MainContainer {{
    background-color: {BG_COLOR};
    color: {TEXT_MAIN};
    font-family: 'JetBrains Mono', 'Segoe UI', sans-serif;
}}

/* Сайдбар */
QFrame#Sidebar {{
    background-color: {BG_COLOR};
    border-right: 1px solid rgba(255, 255, 255, 0.05);
}}
QPushButton#NavBtn {{
    background-color: transparent;
    color: {TEXT_DIM};
    text-align: left;
    padding: 12px 16px;
    border-radius: 12px;
    font-size: 14px;
    font-weight: 600;
    border: none;
}}
QPushButton#NavBtn:hover {{
    background-color: {SURFACE_COLOR};
    color: {TEXT_MAIN};
}}
QPushButton#NavBtn[active="true"] {{
    background-color: {SURFACE_HOVER};
    color: {TEXT_MAIN};
}}

/* Поиск */
QLineEdit#SearchBar {{
    background-color: {SURFACE_COLOR};
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 14px;
    padding: 12px 18px;
    color: {TEXT_MAIN};
    font-size: 14px;
}}
QLineEdit#SearchBar:focus {{
    border: 1px solid {ACCENT_COLOR};
}}

/* Карточка трека */
QFrame#TrackRow {{
    background-color: {SURFACE_COLOR};
    border-radius: 12px;
    border: 1px solid transparent;
}}
QFrame#TrackRow:hover {{
    background-color: {SURFACE_HOVER};
    border: 1px solid rgba(255, 255, 255, 0.05);
}}
QLabel#TrackTitle {{
    color: {TEXT_MAIN};
    font-size: 14px;
    font-weight: bold;
}}
QLabel#TrackArtist {{
    color: {TEXT_DIM};
    font-size: 12px;
}}

/* Бейджи площадок */
QLabel#BadgeYT {{
    background-color: {YT_COLOR};
    color: #FFFFFF;
    font-size: 10px;
    font-weight: bold;
    border-radius: 6px;
    padding: 2px 6px;
}}
QLabel#BadgeYA {{
    background-color: {YA_COLOR};
    color: #000000;
    font-size: 10px;
    font-weight: bold;
    border-radius: 6px;
    padding: 2px 6px;
}}

/* Нижний плеер */
QFrame#PlayerBar {{
    background-color: {SURFACE_COLOR};
    border-top: 1px solid rgba(255, 255, 255, 0.08);
}}
QPushButton#ControlBtn {{
    background-color: transparent;
    color: {TEXT_MAIN};
    border-radius: 18px;
    font-size: 16px;
    border: none;
}}
QPushButton#ControlBtn:hover {{
    background-color: {SURFACE_HOVER};
}}
QPushButton#PlayBtn {{
    background-color: {ACCENT_COLOR};
    color: #FFFFFF;
    border-radius: 22px;
    font-size: 18px;
    border: none;
}}
QPushButton#PlayBtn:hover {{
    background-color: #7D6EEA;
}}
QSlider::groove:horizontal {{
    height: 4px;
    background: rgba(255, 255, 255, 0.1);
    border-radius: 2px;
}}
QSlider::sub-page:horizontal {{
    background: {ACCENT_COLOR};
    border-radius: 2px;
}}
QSlider::handle:horizontal {{
    background: {TEXT_MAIN};
    width: 12px;
    margin-top: -4px;
    margin-bottom: -4px;
    border-radius: 6px;
}}
"""

class TrackRow(QFrame):
    """Компонент строки трека с индикацией источника (YouTube / Яндекс)"""
    def __init__(self, title, artist, duration, source="YT", cover_color="#2C3E50"):
        super().__init__()
        self.setObjectName("TrackRow")
        self.setFixedHeight(64)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 16, 8)
        layout.setSpacing(14)
        
        # Имитация обложки трека с динамическим цветом
        cover = QFrame()
        cover.setFixedSize(48, 48)
        cover.setStyleSheet(f"background-color: {cover_color}; border-radius: 8px;")
        
        # Бейдж источника поверх или рядом
        badge = QLabel("YT" if source == "YT" else "YA")
        badge.setObjectName("BadgeYT" if source == "YT" else "BadgeYA")
        badge.setFixedSize(24, 16)
        badge.setAlignment(Qt.AlignCenter)
        
        # Информация о треке
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
        info_layout.setContentsMargins(0, 2, 0, 2)
        
        title_label = QLabel(title)
        title_label.setObjectName("TrackTitle")
        
        artist_layout = QHBoxLayout()
        artist_layout.setSpacing(6)
        artist_label = QLabel(artist)
        artist_label.setObjectName("TrackArtist")
        
        artist_layout.addWidget(artist_label)
        artist_layout.addWidget(badge)
        artist_layout.addStretch()
        
        info_layout.addWidget(title_label)
        info_layout.addLayout(artist_layout)
        
        # Длительность и действия
        duration_label = QLabel(duration)
        duration_label.setStyleSheet(f"color: {TEXT_DIM}; font-size: 13px;")
        
        like_btn = QPushButton("❤")
        like_btn.setObjectName("ControlBtn")
        like_btn.setFixedSize(32, 32)
        
        layout.addWidget(cover)
        layout.addLayout(info_layout)
        layout.addStretch()
        layout.addWidget(like_btn)
        layout.addWidget(duration_label)

class Sidebar(QFrame):
    """Боковая панель навигации со слотами под плагины"""
    def __init__(self):
        super().__init__()
        self.setObjectName("Sidebar")
        self.setFixedWidth(240)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 24, 16, 24)
        layout.setSpacing(6)
        
        # Логотип
        logo = QLabel("QUANTIS")
        logo.setStyleSheet(f"color: {TEXT_MAIN}; font-size: 20px; font-weight: 800; letter-spacing: 2px; margin-bottom: 20px;")
        layout.addWidget(logo)
        
        # Основная навигация
        self.add_nav_btn(layout, "🏠  Главная", active=True)
        self.add_nav_btn(layout, "🔍  Поиск и Микс")
        self.add_nav_btn(layout, "📚  Моя медиатека")
        
        layout.addSpacing(20)
        
        # Секция плагинов (Интеграция сторонних модулей)
        plugins_header = QLabel("ПЛАГИНЫ")
        plugins_header.setStyleSheet(f"color: {TEXT_DIM}; font-size: 11px; font-weight: bold; margin-left: 16px; margin-bottom: 4px;")
        layout.addWidget(plugins_header)
        
        self.add_nav_btn(layout, "🧩  Маркетплейс")
        self.add_nav_btn(layout, "⚡  YouTube Source")
        self.add_nav_btn(layout, "💛  Yandex Source")
        
        layout.addStretch()
        
        # Настройки
        self.add_nav_btn(layout, "⚙️  Настройки")

    def add_nav_btn(self, layout, text, active=False):
        btn = QPushButton(text)
        btn.setObjectName("NavBtn")
        if active:
            btn.setProperty("active", "true")
        layout.addWidget(btn)

class PlayerBar(QFrame):
    """Нижняя зафиксированная панель воспроизведения"""
    def __init__(self):
        super().__init__()
        self.setObjectName("PlayerBar")
        self.setFixedHeight(84)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(24, 0, 24, 0)
        
        # Левая часть: Текущий трек
        left_layout = QHBoxLayout()
        left_layout.setSpacing(12)
        
        cover = QFrame()
        cover.setFixedSize(52, 52)
        cover.setStyleSheet(f"background-color: #6C5CE7; border-radius: 8px;")
        
        track_info = QVBoxLayout()
        track_info.setAlignment(Qt.AlignVCenter)
        t_title = QLabel("Everything In Its Right Place")
        t_title.setStyleSheet("font-weight: bold; font-size: 14px;")
        t_artist = QLabel("Radiohead · 🔴 YouTube")
        t_artist.setStyleSheet(f"color: {TEXT_DIM}; font-size: 12px;")
        track_info.addWidget(t_title)
        track_info.addWidget(t_artist)
        
        left_layout.addWidget(cover)
        left_layout.addLayout(track_info)
        
        # Центральная часть: Управление и прогресс
        center_layout = QVBoxLayout()
        center_layout.setAlignment(Qt.AlignCenter)
        
        controls = QHBoxLayout()
        controls.setSpacing(16)
        
        shuffle_btn = QPushButton("🔀")
        prev_btn = QPushButton("⏮")
        play_btn = QPushButton("⏸")
        next_btn = QPushButton("⏭")
        repeat_btn = QPushButton("🔁")
        
        for btn in [shuffle_btn, prev_btn, next_btn, repeat_btn]:
            btn.setObjectName("ControlBtn")
            btn.setFixedSize(36, 36)
            
        play_btn.setObjectName("PlayBtn")
        play_btn.setFixedSize(44, 44)
        
        controls.addWidget(shuffle_btn)
        controls.addWidget(prev_btn)
        controls.addWidget(play_btn)
        controls.addWidget(next_btn)
        controls.addWidget(repeat_btn)
        
        progress_layout = QHBoxLayout()
        t_curr = QLabel("1:24")
        t_curr.setStyleSheet(f"color: {TEXT_DIM}; font-size: 11px;")
        slider = QSlider(Qt.Horizontal)
        slider.setValue(35)
        slider.setFixedWidth(360)
        t_total = QLabel("4:11")
        t_total.setStyleSheet(f"color: {TEXT_DIM}; font-size: 11px;")
        
        progress_layout.addWidget(t_curr)
        progress_layout.addWidget(slider)
        progress_layout.addWidget(t_total)
        
        center_layout.addLayout(controls)
        center_layout.addLayout(progress_layout)
        
        # Правая часть: Громкость и инструменты
        right_layout = QHBoxLayout()
        right_layout.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        
        lyrics_btn = QPushButton("🎙")
        queue_btn = QPushButton("☰")
        vol_btn = QPushButton("🔊")
        
        for btn in [lyrics_btn, queue_btn, vol_btn]:
            btn.setObjectName("ControlBtn")
            btn.setFixedSize(36, 36)
            right_layout.addWidget(btn)
            
        vol_slider = QSlider(Qt.Horizontal)
        vol_slider.setValue(80)
        vol_slider.setFixedWidth(80)
        right_layout.addWidget(vol_slider)
        
        # Сборка сетки плеера
        layout.addLayout(left_layout, 1)
        layout.addLayout(center_layout, 2)
        layout.addLayout(right_layout, 1)

class QuantisMainWindow(QMainWindow):
    """Главное окно приложения"""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Quantis — Multi-Source Audio Aggregator")
        self.resize(1200, 760)
        self.setMinimumSize(900, 600)
        
        # Главный контейнер
        main_widget = QWidget()
        main_widget.setObjectName("MainContainer")
        self.setCentralWidget(main_widget)
        
        root_layout = QVBoxLayout(main_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)
        
        # Верхняя зона: Сайдбар + Контент
        top_area = QHBoxLayout()
        top_area.setSpacing(0)
        
        self.sidebar = Sidebar()
        top_area.addWidget(self.sidebar)
        
        # Зона контента
        content_area = QWidget()
        content_layout = QVBoxLayout(content_area)
        content_layout.setContentsMargins(32, 24, 32, 24)
        content_layout.setSpacing(20)
        
        # Поисковая строка с поддержкой фильтров по источникам
        search_bar = QLineEdit()
        search_bar.setObjectName("SearchBar")
        search_bar.setPlaceholderText("Поиск треков, альбомов или артистов (YouTube, Яндекс.Музыка)...")
        content_layout.addWidget(search_bar)
        
        # Заголовок секции
        section_title = QLabel("Мульти-лента и Рекомендации")
        section_title.setStyleSheet("font-size: 22px; font-weight: 800; margin-top: 10px;")
        content_layout.addWidget(section_title)
        
        # Скролл со списком треков
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(8)
        
        # Демонстрационные данные из разных источников
        tracks_data = [
            ("Everything In Its Right Place", "Radiohead", "4:11", "YT", "#2C3E50"),
            ("На заре", "Альянс", "5:44", "YA", "#8E44AD"),
            ("Let Happen", "Tame Impala", "4:18", "YT", "#D35400"),
            ("Звезда по имени Солнце", "Кино", "3:45", "YA", "#27AE60"),
            ("Instant Crush", "Daft Punk ft. Julian Casablancas", "5:37", "YT", "#2980B9"),
            ("Танцы на стёклах", "Максим Фадеев", "4:12", "YA", "#C0392B"),
            ("Midnight City", "M83", "4:03", "YT", "#16A085"),
            ("Крошка моя", "Руки Вверх", "4:09", "YA", "#E67E22"),
        ]
        
        for title, artist, duration, source, color in tracks_data:
            scroll_layout.addWidget(TrackRow(title, artist, duration, source, color))
            
        scroll_layout.addStretch()
        scroll.setWidget(scroll_content)
        content_layout.addWidget(scroll)
        
        top_area.addWidget(content_area, 1)
        root_layout.addLayout(top_area, 1)
        
        # Нижняя панель воспроизведения (всегда снизу)
        self.player_bar = PlayerBar()
        root_layout.addWidget(self.player_bar)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyleSheet(QSS)
    
    window = QuantisMainWindow()
    window.show()
    sys.exit(app.exec())
