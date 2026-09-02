# quantis.py
# pip install PySide6
import sys
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QLineEdit,
    QScrollArea,
    QFrame,
    QSlider,
    QGridLayout,
    QSizePolicy,
    QStackedWidget,
    QGraphicsDropShadowEffect,
)
from PySide6.QtCore import Qt, QSize, QTimer
from PySide6.QtGui import QColor, QPainter, QBrush, QPixmap, QFont, QLinearGradient

# ---------- Тема ----------
BG = "#0B0D12"
SURFACE = "#141821"
SURFACE2 = "#1C212D"
TEXT = "#F2F4F8"
TEXT_DIM = "#8A92A6"
ACCENT = "#6C5CE7"
YT = "#FF4E45"
YA = "#FFDB4D"

FONT = "Segoe UI"

# ---------- Демо-данные ----------
TRACKS = [
    ("Midnight City", "M83", "yt", "3:42", "#3A2E5C"),
    ("Blinding Lights", "The Weeknd", "ya", "3:20", "#5C2E2E"),
    ("Instant Crush", "Daft Punk", "yt", "5:37", "#2E4A5C"),
    ("Redbone", "Childish Gambino", "ya", "5:26", "#5C4A2E"),
    ("Nightcall", "Kavinsky", "yt", "4:18", "#2E2E5C"),
    ("Tadow", "Masego", "ya", "5:04", "#2E5C4A"),
    ("Nikes", "Frank Ocean", "yt", "5:14", "#5C2E4A"),
    ("Sunflower", "Post Malone", "ya", "2:38", "#5C5C2E"),
]

MIXES = [
    ("Ночной драйв", "#3A2E5C"),
    ("Фокус", "#2E4A5C"),
    ("Тренировка", "#5C2E3A"),
    ("Чил", "#2E5C4A"),
    ("Новинки", "#5C4A2E"),
]


def circle_pixmap(size, color):
    """Круглая обложка-заглушка с градиентом."""
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    grad = QLinearGradient(0, 0, size, size)
    c = QColor(color)
    grad.setColorAt(0, c.lighter(140))
    grad.setColorAt(1, c.darker(120))
    p.setBrush(QBrush(grad))
    p.setPen(Qt.NoPen)
    p.drawRoundedRect(0, 0, size, size, 12, 12)
    p.end()
    return pm


def source_dot(kind, d=16):
    pm = QPixmap(d, d)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    color = QColor(YT) if kind == "yt" else QColor(YA)
    p.setBrush(QBrush(color))
    p.setPen(Qt.NoPen)
    p.drawEllipse(0, 0, d, d)
    p.setPen(QColor("#0B0D12"))
    f = QFont(FONT, 8, QFont.Bold)
    p.setFont(f)
    p.drawText(pm.rect(), Qt.AlignCenter, "Y" if kind == "yt" else "Я")
    p.end()
    return pm


# ---------- Виджеты ----------
class CoverLabel(QLabel):
    def __init__(self, size, color, source=None):
        super().__init__()
        self.setFixedSize(size, size)
        base = circle_pixmap(size, color)
        if source:
            p = QPainter(base)
            p.setRenderHint(QPainter.Antialiasing)
            dot = source_dot("yt" if source == "yt" else "ya", 18)
            p.drawPixmap(size - 20, size - 20, dot)
            p.end()
        self.setPixmap(base)


class MixCard(QFrame):
    def __init__(self, title, color):
        super().__init__()
        self.setObjectName("mixCard")
        self.setFixedSize(160, 190)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(10)
        cover = CoverLabel(136, color)
        lay.addWidget(cover)
        t = QLabel(title)
        t.setStyleSheet(f"color:{TEXT}; font-weight:600; font-size:14px;")
        lay.addWidget(t)
        lay.addStretch()

        sh = QGraphicsDropShadowEffect(self)
        sh.setBlurRadius(24)
        sh.setColor(QColor(0, 0, 0, 120))
        sh.setOffset(0, 6)
        self.setGraphicsEffect(sh)


class TrackRow(QFrame):
    def __init__(self, idx, title, artist, source, dur, color, on_play):
        super().__init__()
        self.setObjectName("trackRow")
        self.setFixedHeight(64)
        self.on_play = on_play
        self.data = (title, artist, source, color)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 6, 16, 6)
        lay.setSpacing(14)

        num = QLabel(str(idx))
        num.setFixedWidth(20)
        num.setStyleSheet(f"color:{TEXT_DIM}; font-size:14px;")
        lay.addWidget(num)

        cover = CoverLabel(48, color, source)
        lay.addWidget(cover)

        info = QVBoxLayout()
        info.setSpacing(2)
        t = QLabel(title)
        t.setStyleSheet(f"color:{TEXT}; font-weight:600; font-size:14px;")
        src = "🔴 YouTube" if source == "yt" else "🟡 Яндекс"
        a = QLabel(f"{artist} · {src}")
        a.setStyleSheet(f"color:{TEXT_DIM}; font-size:12px;")
        info.addWidget(t)
        info.addWidget(a)
        lay.addLayout(info)
        lay.addStretch()

        dl = QPushButton("⬇")
        heart = QPushButton("♡")
        for b in (dl, heart):
            b.setObjectName("iconBtn")
            b.setFixedSize(32, 32)
            b.setCursor(Qt.PointingHandCursor)
        lay.addWidget(heart)
        lay.addWidget(dl)

        d = QLabel(dur)
        d.setStyleSheet(f"color:{TEXT_DIM}; font-size:13px;")
        d.setFixedWidth(40)
        d.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        lay.addWidget(d)

    def mousePressEvent(self, e):
        self.on_play(*self.data)


class SidebarButton(QPushButton):
    def __init__(self, icon, text):
        super().__init__(f"  {icon}   {text}")
        self.setObjectName("navBtn")
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(44)


# ---------- Главное окно ----------
class Quantis(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Quantis")
        self.resize(1240, 820)
        self.setMinimumSize(1000, 680)

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # верхняя часть: sidebar + content
        top = QHBoxLayout()
        top.setContentsMargins(0, 0, 0, 0)
        top.setSpacing(0)
        top.addWidget(self.build_sidebar())
        top.addWidget(self.build_content(), 1)
        top_w = QWidget()
        top_w.setLayout(top)
        root.addWidget(top_w, 1)

        # плеер
        root.addWidget(self.build_player())

        # прогресс-таймер (демо-анимация)
        self.progress = 0
        self.timer = QTimer()
        self.timer.timeout.connect(self.tick)

        self.apply_style()

    # ---- Sidebar ----
    def build_sidebar(self):
        bar = QFrame()
        bar.setObjectName("sidebar")
        bar.setFixedWidth(230)
        lay = QVBoxLayout(bar)
        lay.setContentsMargins(18, 22, 14, 18)
        lay.setSpacing(6)

        logo = QLabel("◆ Quantis")
        logo.setStyleSheet(f"color:{TEXT}; font-size:22px; font-weight:800;")
        lay.addWidget(logo)
        lay.addSpacing(18)

        btns = [
            ("🏠", "Главная"),
            ("🔍", "Поиск"),
            ("🎧", "Микс"),
            ("📚", "Медиатека"),
            ("⬇", "Загрузки"),
        ]
        self.nav_group = []
        for icon, text in btns:
            b = SidebarButton(icon, text)
            b.clicked.connect(lambda _, x=b: self.select_nav(x))
            lay.addWidget(b)
            self.nav_group.append(b)
        self.nav_group[0].setChecked(True)

        lay.addSpacing(16)
        sep = QLabel("ПЛАГИНЫ")
        sep.setStyleSheet(
            f"color:{TEXT_DIM}; font-size:11px; font-weight:700; letter-spacing:1px;"
        )
        lay.addWidget(sep)
        for icon, text in [
            ("🧩", "Sponsorblock"),
            ("🧩", "Lyrics+"),
            ("➕", "Магазин"),
        ]:
            b = SidebarButton(icon, text)
            b.clicked.connect(lambda _, x=b: self.select_nav(x))
            lay.addWidget(b)
            self.nav_group.append(b)

        lay.addStretch()
        settings = SidebarButton("⚙", "Настройки")
        settings.clicked.connect(lambda _, x=settings: self.select_nav(x))
        lay.addWidget(settings)
        self.nav_group.append(settings)
        return bar

    def select_nav(self, btn):
        for b in self.nav_group:
            b.setChecked(b is btn)

    # ---- Content ----
    def build_content(self):
        scroll = QScrollArea()
        scroll.setObjectName("content")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        wrap = QWidget()
        lay = QVBoxLayout(wrap)
        lay.setContentsMargins(32, 26, 32, 40)
        lay.setSpacing(22)

        # Поиск
        search = QLineEdit()
        search.setObjectName("search")
        search.setPlaceholderText("🔍  Искать во всех источниках…")
        search.setFixedHeight(46)
        lay.addWidget(search)

        # Чипы-фильтры
        chips = QHBoxLayout()
        chips.setSpacing(8)
        for name in ["Всё", "YouTube", "Яндекс", "Треки", "Плейлисты", "Альбомы"]:
            c = QPushButton(name)
            c.setObjectName("chip")
            c.setCheckable(True)
            c.setCursor(Qt.PointingHandCursor)
            if name == "Всё":
                c.setChecked(True)
            chips.addWidget(c)
        chips.addStretch()
        lay.addLayout(chips)

        # Заголовок Миксы
        h1 = QLabel("Твои миксы")
        h1.setStyleSheet(f"color:{TEXT}; font-size:22px; font-weight:800;")
        lay.addWidget(h1)

        mix_row = QHBoxLayout()
        mix_row.setSpacing(16)
        for title, color in MIXES:
            mix_row.addWidget(MixCard(title, color))
        mix_row.addStretch()
        lay.addLayout(mix_row)

        # Заголовок треки
        h2 = QLabel("Популярное сейчас")
        h2.setStyleSheet(f"color:{TEXT}; font-size:22px; font-weight:800;")
        lay.addWidget(h2)

        list_frame = QFrame()
        list_frame.setObjectName("listFrame")
        ll = QVBoxLayout(list_frame)
        ll.setContentsMargins(8, 8, 8, 8)
        ll.setSpacing(2)
        for i, (title, artist, src, dur, color) in enumerate(TRACKS, 1):
            ll.addWidget(TrackRow(i, title, artist, src, dur, color, self.play_track))
        lay.addWidget(list_frame)

        lay.addStretch()
        scroll.setWidget(wrap)
        return scroll

    # ---- Player ----
    def build_player(self):
        bar = QFrame()
        bar.setObjectName("player")
        bar.setFixedHeight(84)
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(20, 0, 20, 0)
        lay.setSpacing(20)

        # Левый блок: обложка + инфо
        left = QHBoxLayout()
        left.setSpacing(14)
        self.p_cover = CoverLabel(56, "#3A2E5C", "yt")
        left.addWidget(self.p_cover)
        info = QVBoxLayout()
        info.setSpacing(2)
        self.p_title = QLabel("Midnight City")
        self.p_title.setStyleSheet(f"color:{TEXT}; font-weight:700; font-size:14px;")
        self.p_artist = QLabel("M83 · 🔴 YouTube")
        self.p_artist.setStyleSheet(f"color:{TEXT_DIM}; font-size:12px;")
        info.addWidget(self.p_title)
        info.addWidget(self.p_artist)
        left.addLayout(info)
        heart = QPushButton("♡")
        heart.setObjectName("iconBtn")
        heart.setFixedSize(34, 34)
        heart.setCursor(Qt.PointingHandCursor)
        left.addWidget(heart)
        left_w = QWidget()
        left_w.setLayout(left)
        left_w.setFixedWidth(300)
        lay.addWidget(left_w)

        # Центр: контролы + прогресс
        center = QVBoxLayout()
        center.setSpacing(6)
        ctr = QHBoxLayout()
        ctr.setSpacing(14)
        ctr.addStretch()
        for icon, name in [("🔀", "shuffle"), ("⏮", "prev")]:
            b = QPushButton(icon)
            b.setObjectName("ctrlBtn")
            b.setFixedSize(36, 36)
            b.setCursor(Qt.PointingHandCursor)
            ctr.addWidget(b)
        self.play_btn = QPushButton("▶")
        self.play_btn.setObjectName("playBtn")
        self.play_btn.setFixedSize(48, 48)
        self.play_btn.setCursor(Qt.PointingHandCursor)
        self.play_btn.clicked.connect(self.toggle_play)
        ctr.addWidget(self.play_btn)
        for icon, name in [("⏭", "next"), ("🔁", "repeat")]:
            b = QPushButton(icon)
            b.setObjectName("ctrlBtn")
            b.setFixedSize(36, 36)
            b.setCursor(Qt.PointingHandCursor)
            ctr.addWidget(b)
        ctr.addStretch()
        center.addLayout(ctr)

        prog = QHBoxLayout()
        prog.setSpacing(10)
        self.cur_time = QLabel("0:00")
        self.cur_time.setStyleSheet(f"color:{TEXT_DIM}; font-size:11px;")
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setObjectName("progress")
        self.slider.setRange(0, 100)
        self.tot_time = QLabel("3:42")
        self.tot_time.setStyleSheet(f"color:{TEXT_DIM}; font-size:11px;")
        prog.addWidget(self.cur_time)
        prog.addWidget(self.slider)
        prog.addWidget(self.tot_time)
        center.addLayout(prog)

        center_w = QWidget()
        center_w.setLayout(center)
        lay.addWidget(center_w, 1)  # 1 = stretch, чтобы центр занимал максимум места

        # Правый блок: инструменты и громкость
        right = QHBoxLayout()
        right.setSpacing(10)
        right.addStretch()
        for icon in ["🎙", "☰", "🔊"]:
            b = QPushButton(icon)
            b.setObjectName("iconBtn")
            b.setFixedSize(32, 32)
            b.setCursor(Qt.PointingHandCursor)
            right.addWidget(b)

        vol_slider = QSlider(Qt.Horizontal)
        vol_slider.setObjectName("progress")
        vol_slider.setRange(0, 100)
        vol_slider.setValue(75)
        vol_slider.setFixedWidth(80)
        right.addWidget(vol_slider)

        right_w = QWidget()
        right_w.setLayout(right)
        right_w.setFixedWidth(260)
        lay.addWidget(right_w)

        return bar

    # ---- Логика плеера (Демо) ----
    def toggle_play(self):
        if self.timer.isActive():
            self.timer.stop()
            self.play_btn.setText("▶")
        else:
            self.timer.start(1000)
            self.play_btn.setText("⏸")

    def tick(self):
        self.progress += 1
        if self.progress > 100:
            self.progress = 0
            self.toggle_play()
        self.slider.setValue(self.progress)
        self.cur_time.setText(f"{self.progress // 60}:{self.progress % 60:02d}")

    def play_track(self, title, artist, source, color):
        # Обновляем инфо в плеере
        self.p_title.setText(title)
        src = "🔴 YouTube" if source == "yt" else "🟡 Яндекс"
        self.p_artist.setText(f"{artist} · {src}")

        # Обновляем обложку
        pm = circle_pixmap(56, color)
        p = QPainter(pm)
        p.setRenderHint(QPainter.Antialiasing)
        dot = source_dot("yt" if source == "yt" else "ya", 18)
        p.drawPixmap(56 - 20, 56 - 20, dot)
        p.end()
        self.p_cover.setPixmap(pm)

        # Сбрасываем прогресс и запускаем
        self.progress = 0
        self.slider.setValue(0)
        self.cur_time.setText("0:00")
        if not self.timer.isActive():
            self.toggle_play()

    # ---- Стилизация (QSS) ----
    def apply_style(self):
        qss = f"""
        QMainWindow, QWidget {{
            background-color: {BG};
            color: {TEXT};
            font-family: "{FONT}";
        }}
        
        /* Скроллбары */
        QScrollArea {{ border: none; background: transparent; }}
        QScrollBar:vertical {{
            border: none; background: transparent;
            width: 8px; margin: 0px;
        }}
        QScrollBar::handle:vertical {{
            background: rgba(255, 255, 255, 0.15);
            min-height: 30px; border-radius: 4px;
        }}
        QScrollBar::handle:vertical:hover {{
            background: rgba(255, 255, 255, 0.3);
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}

        /* Сайдбар */
        QFrame#sidebar {{
            background-color: {BG};
        }}
        QPushButton#navBtn {{
            background-color: transparent;
            color: {TEXT_DIM};
            text-align: left;
            border-radius: 10px;
            font-size: 14px;
            font-weight: 600;
            border: none;
            padding-left: 12px;
        }}
        QPushButton#navBtn:hover {{
            background-color: {SURFACE};
            color: {TEXT};
        }}
        QPushButton#navBtn:checked {{
            background-color: {SURFACE2};
            color: {TEXT};
        }}

        /* Контент и Поиск */
        QLineEdit#search {{
            background-color: {SURFACE};
            border: 1px solid rgba(255, 255, 255, 0.04);
            border-radius: 12px;
            padding: 0 16px;
            font-size: 14px;
        }}
        QLineEdit#search:focus {{
            border: 1px solid {ACCENT};
        }}
        
        QPushButton#chip {{
            background-color: {SURFACE};
            color: {TEXT_DIM};
            border: none; border-radius: 16px;
            padding: 6px 16px; font-size: 13px; font-weight: 600;
        }}
        QPushButton#chip:hover {{
            background-color: {SURFACE2}; color: {TEXT};
        }}
        QPushButton#chip:checked {{
            background-color: {TEXT}; color: {BG};
        }}

        /* Списки и карточки */
        QFrame#mixCard {{
            background-color: {SURFACE};
            border-radius: 16px;
        }}
        QFrame#mixCard:hover {{
            background-color: {SURFACE2};
        }}
        QFrame#listFrame {{ background: transparent; }}
        QFrame#trackRow {{ background-color: {BG}; border-radius: 12px; }}
        QFrame#trackRow:hover {{ background-color: {SURFACE}; }}

        /* Плеер */
        QFrame#player {{
            background-color: {SURFACE};
            border-top: 1px solid rgba(255, 255, 255, 0.05);
        }}
        QPushButton#iconBtn, QPushButton#ctrlBtn {{
            background-color: transparent; color: {TEXT_DIM};
            border: none; border-radius: 16px; font-size: 16px;
        }}
        QPushButton#iconBtn:hover, QPushButton#ctrlBtn:hover {{
            color: {TEXT}; background-color: rgba(255, 255, 255, 0.05);
        }}
        QPushButton#playBtn {{
            background-color: {TEXT}; color: {BG};
            border-radius: 24px; border: none; font-size: 18px;
            padding-left: 2px; /* Выравнивание треугольника */
        }}
        QPushButton#playBtn:hover {{
            background-color: {ACCENT}; color: {TEXT};
        }}

        /* Слайдеры */
        QSlider#progress::groove:horizontal {{
            height: 4px; background: rgba(255, 255, 255, 0.1); border-radius: 2px;
        }}
        QSlider#progress::sub-page:horizontal {{
            background: {TEXT}; border-radius: 2px;
        }}
        QSlider#progress::handle:horizontal {{
            background: {TEXT}; width: 12px;
            margin-top: -4px; margin-bottom: -4px; border-radius: 6px;
        }}
        QSlider#progress::handle:horizontal:hover {{
            background: {ACCENT}; transform: scale(1.2);
        }}
        """
        self.setStyleSheet(qss)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = Quantis()
    window.show()
    sys.exit(app.exec())
