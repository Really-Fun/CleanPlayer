"""Страница менеджера плагинов."""

from __future__ import annotations

import asyncio
import shutil
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QCursor
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QFrame,
    QSizePolicy,
    QSpacerItem,
    QFileDialog,
    QMessageBox,
)

from plugins.registry import PluginInfo, PluginRegistry
from plugins.loader import PLUGIN_DIR


class PluginCard(QFrame):
    """Визуальная карточка отдельного плагина."""

    def __init__(
        self,
        info: PluginInfo,
        registry: PluginRegistry,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._info = info
        self._registry = registry

        self.setFixedHeight(120)
        self.setObjectName("PluginCardFrame")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 15, 20, 15)
        layout.setSpacing(15)

        # Иконка
        icon = QLabel("🧩")
        icon.setObjectName("PluginIcon")
        icon.setFont(QFont("Arial", 36))
        icon.setFixedSize(60, 60)
        icon.setAlignment(Qt.AlignCenter)
        layout.addWidget(icon)

        # Текст
        text_layout = QVBoxLayout()
        text_layout.setSpacing(5)

        self.title_label = QLabel(info.meta.name)
        self.title_label.setObjectName("PluginTitle")

        self.desc_label = QLabel(info.meta.description or "Нет описания")
        self.desc_label.setObjectName("PluginDesc")
        self.desc_label.setWordWrap(True)

        self.meta_label = QLabel(
            f"Версия: {info.meta.version}  •  Автор: {info.meta.author}"
        )
        self.meta_label.setObjectName("PluginMeta")

        self.error_label = QLabel("")
        self.error_label.setObjectName("PluginError")
        self.error_label.setWordWrap(True)
        self.error_label.setVisible(False)

        text_layout.addWidget(self.title_label)
        text_layout.addWidget(self.desc_label)
        text_layout.addWidget(self.meta_label)
        text_layout.addWidget(self.error_label)
        text_layout.addStretch()
        layout.addLayout(text_layout)

        # Кнопки
        action_layout = QVBoxLayout()
        action_layout.setSpacing(8)

        self.btn_toggle = QPushButton()
        self.btn_toggle.setObjectName("BtnTogglePlugin")
        self.btn_toggle.setFixedWidth(110)
        self.btn_toggle.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_toggle.clicked.connect(self._toggle)

        self.btn_delete = QPushButton("Удалить")
        self.btn_delete.setObjectName("BtnDeletePlugin")
        self.btn_delete.setFixedWidth(110)
        self.btn_delete.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_delete.clicked.connect(self._delete)

        action_layout.addWidget(self.btn_toggle)
        action_layout.addWidget(self.btn_delete)
        action_layout.addStretch()
        layout.addLayout(action_layout)

        self._refresh_state()

        # Подписываемся на изменения реестра
        self._registry.plugin_changed.connect(self._on_registry_changed)

    # ── Внутренние методы ─────────────────────────────────────────────────────

    def _refresh_state(self) -> None:
        is_active = self._info.is_active
        self.btn_toggle.setText("Включён ✓" if is_active else "Выключен")
        self.btn_toggle.setProperty("active", str(is_active).lower())
        self.btn_toggle.style().unpolish(self.btn_toggle)
        self.btn_toggle.style().polish(self.btn_toggle)

        has_error = bool(self._info.error)
        self.error_label.setVisible(has_error)
        self.error_label.setText(f"⚠ {self._info.error}" if has_error else "")

    def _toggle(self) -> None:
        plugin_id = self._info.meta.plugin_id
        if self._info.is_active:
            asyncio.ensure_future(self._registry.disable(plugin_id))
        else:
            asyncio.ensure_future(self._registry.enable(plugin_id))

    def _delete(self) -> None:
        plugin_id = self._info.meta.plugin_id
        reply = QMessageBox.question(
            self,
            "Удаление плагина",
            f"Удалить плагин «{self._info.meta.name}»?\nЭто действие необратимо.",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        if self._info.is_active:
            asyncio.ensure_future(self._registry.disable(plugin_id))
        try:
            shutil.rmtree(self._info.meta.path)
        except OSError as e:
            QMessageBox.warning(self, "Ошибка", f"Не удалось удалить: {e}")

    def _on_registry_changed(self, plugin_id: str) -> None:
        if plugin_id == self._info.meta.plugin_id:
            self._refresh_state()


class PluginsManagerPage(QWidget):
    """Страница менеджера плагинов — показывает реальные плагины из PluginRegistry."""

    def __init__(self, context, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("PluginsManagerSection")

        root = QVBoxLayout(self)
        root.setContentsMargins(30, 30, 30, 30)
        root.setSpacing(20)

        # Шапка
        header = QHBoxLayout()

        title = QLabel("Управление плагинами")
        title.setObjectName("PluginPageTitle")
        header.addWidget(title)
        header.addStretch()

        btn_install = QPushButton("+ Установить из файла")
        btn_install.setObjectName("BtnInstallPlugin")
        btn_install.setCursor(QCursor(Qt.PointingHandCursor))
        btn_install.clicked.connect(self._install_from_folder)
        header.addWidget(btn_install)

        root.addLayout(header)

        # Зона скроллинга
        self.scroll_area = QScrollArea()
        self.scroll_area.setObjectName("PluginScrollArea")
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.scroll_content = QWidget()
        self.scroll_content.setObjectName("PluginScrollContent")
        self.plugins_layout = QVBoxLayout(self.scroll_content)
        self.plugins_layout.setContentsMargins(0, 0, 15, 0)
        self.plugins_layout.setSpacing(8)
        self.scroll_area.setWidget(self.scroll_content)
        root.addWidget(self.scroll_area)

        # Надпись "нет плагинов"
        self._empty_label = QLabel(
            "Плагины не установлены.\nНажми «+ Установить из файла» чтобы добавить."
        )
        self._empty_label.setAlignment(Qt.AlignCenter)
        self._empty_label.setObjectName("PluginEmptyLabel")
        self.plugins_layout.addWidget(self._empty_label)
        self.plugins_layout.addSpacerItem(
            QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)
        )

        self._registry_connected = False

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if not self._registry_connected:
            self._connect_registry()
            self._registry_connected = True

    def _connect_registry(self) -> None:
        registry = PluginRegistry.instance()
        registry.plugin_changed.connect(self._refresh)
        self._refresh()

    def _refresh(self, _plugin_id: str = "") -> None:
        """Перестраивает список карточек из реестра."""
        registry = PluginRegistry.instance()
        infos = registry.get_all()
        print(infos)

        # Удаляем старые карточки (кроме лейбла и spacer)
        while self.plugins_layout.count() > 2:
            item = self.plugins_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self._empty_label.setVisible(not infos)

        for info in infos:
            card = PluginCard(info, registry, self.scroll_content)
            self.plugins_layout.insertWidget(self.plugins_layout.count() - 1, card)

    def _install_from_folder(self) -> None:
        """Открывает диалог выбора папки плагина и копирует её в plugins_dir."""
        source = QFileDialog.getExistingDirectory(
            self,
            "Выберите папку плагина",
            str(Path.home()),
        )
        if not source:
            return
        source_path = Path(source)
        plugin_id = source_path.name
        dest = PLUGIN_DIR / plugin_id

        if dest.exists():
            QMessageBox.warning(
                self,
                "Плагин уже установлен",
                f"Плагин с ID «{plugin_id}» уже установлен.\n"
                "Удалите существующий перед установкой.",
            )
            return

        try:
            PLUGIN_DIR.mkdir(parents=True, exist_ok=True)
            shutil.copytree(source_path, dest)
        except OSError as e:
            QMessageBox.critical(self, "Ошибка установки", str(e))
            return

        QMessageBox.information(
            self,
            "Плагин установлен",
            f"Плагин «{plugin_id}» установлен.\n"
            "Перезапустите приложение для его активации.",
        )
