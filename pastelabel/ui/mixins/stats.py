"""Label statistics behavior for the main window."""


class StatsMixin:
    def _get_session_labels(self):
        """收集当前打开文件夹中用于共享色板的全部标签。"""
        labels = [box.get('label', '') for boxes in self.detection_boxes_dict.values() for box in boxes]
        labels.extend(box.get('label', '') for box in self.detection_boxes)
        labels.extend(item[2] for item in self.canvas_items)
        labels.extend(
            item[2] for idx, items in self.canvas_items_dict.items()
            if idx != self.current_background_index for item in items
        )
        return labels

    def _get_session_paste_stats(self):
        """按图片聚合当前会话的贴图标签。"""
        stats = {}
        for idx in range(len(self.background_images)):
            items = self.canvas_items if idx == self.current_background_index else self.canvas_items_dict.get(idx, [])
            for _, _, label in items:
                if label:
                    stats[label] = stats.get(label, 0) + 1
        return stats

    def _collect_bg_stats_for_dialog(self):
        """Background label counts: reuse full-dataset cache when fresh, else seed disk+memory."""
        cached = getattr(self, '_cached_bg_label_stats', None) or []
        current_path = getattr(self, '_memory_background_path', '') or ''
        cache_path = getattr(self, '_cached_bg_label_stats_path', '') or ''
        scan_done = getattr(self, '_background_label_scan_completed', False)
        dirty = getattr(self, '_dataset_stats_dirty', False)
        if not (cached and scan_done and not dirty and cache_path == current_path):
            if hasattr(self, 'label_manager') and hasattr(self.label_manager, '_seed_stats_cache_from_disk_and_memory'):
                self.label_manager._seed_stats_cache_from_disk_and_memory()
            self._dataset_stats_dirty = False
            cached = getattr(self, '_cached_bg_label_stats', None) or []
        current_path = getattr(self, '_memory_background_path', '') or ''
        # Prefer any non-empty live cache (renames/canvas edits update it without path).
        if cached:
            bg_stats = {}
            for item in cached:
                if not isinstance(item, dict):
                    continue
                label = str(item.get('label', '') or '').strip()
                if not label:
                    continue
                try:
                    count = max(0, int(item.get('count', 0) or 0))
                except (TypeError, ValueError):
                    count = 0
                bg_stats[label] = count
                color = str(item.get('color', '') or '').strip()
                if color and hasattr(self, 'label_color_map'):
                    self.label_color_map.setdefault(label, color)
            if bg_stats:
                return bg_stats

        from ...engine.image_loader import collect_background_label_counts
        bg_stats = collect_background_label_counts(list(self.background_images or []))
        for lbl in getattr(self, 'background_dataset_labels', set()) or set():
            bg_stats.setdefault(lbl, 0)
        for lbl in self.global_labels:
            if lbl in bg_stats or lbl in (getattr(self, 'background_dataset_labels', set()) or set()):
                bg_stats.setdefault(lbl, 0)
        self._cached_bg_label_stats = [
            {'label': label, 'count': count, 'color': self.get_label_color(label)}
            for label, count in sorted(bg_stats.items(), key=lambda x: (-x[1], x[0]))
        ]
        self._cached_bg_label_stats_path = current_path
        return bg_stats

    def _show_label_stats(self):
        """显示标签统计弹窗"""
        from PyQt5.QtWidgets import (
            QDialog, QVBoxLayout, QLabel, QTableWidget, QTableWidgetItem,
            QHeaderView, QPushButton, QWidget, QAbstractItemView,
        )
        from PyQt5.QtCore import Qt, Qt as QtCore
        from ..dialog_helpers import center_on_parent
        from ..theme import ThemeManager
        from .. import i18n
        tr = i18n.t

        class _StatsDialog(QDialog):
            def showEvent(self, event):
                super().showEvent(event)
                center_on_parent(self, self.parent())

        t = ThemeManager.get_theme()
        dialog = _StatsDialog(self)
        dialog.setWindowTitle(tr("标签统计"))
        dialog.setMinimumSize(540, 600)
        from PyQt5.QtCore import QTimer
        def _sync():
            hwnd = int(dialog.winId())
            from ..dwm import set_titlebar_dark
            set_titlebar_dark(hwnd, is_dark)
        is_dark = ThemeManager.get_mode().value == "dark"
        QTimer.singleShot(30, _sync)
        dialog.setStyleSheet(f"""
            QDialog {{ background-color: {t['widget_bg']}; color: {t['text_primary']}; }}
            QTableWidget {{ background-color: {t['widget_bg']}; color: {t['text_primary']};
                border: 1px solid {t['border_color']}; gridline-color: {t['border_color']}; }}
            QTableWidget::item {{ padding: 4px; }}
            QTableWidget::item:selected {{ background-color: {t['accent_light']}; color: {t['accent']}; }}
            QHeaderView::section {{ background-color: {t['panel_bg']}; color: {t['text_primary']};
                border: 1px solid {t['border_color']}; padding: 4px; font-weight: bold; }}
            QTableWidget QTableCornerButton::section {{ background-color: {t['panel_bg']};
                border: 1px solid {t['border_color']}; }}
        """)
        layout = QVBoxLayout(dialog)
        bg_header = QPushButton(f"▼  {tr('背景图标签')}")
        bg_header.setFlat(True)
        bg_header.setCursor(Qt.PointingHandCursor)
        bg_header.setStyleSheet("border: none; text-align: left; font-weight: bold; font-size: 13px; padding: 2px 0;")
        bg_header.setFixedHeight(24)
        layout.addWidget(bg_header)
        bg_stats = self._collect_bg_stats_for_dialog()
        bg_table = QTableWidget(len(bg_stats), 3)
        bg_table.setHorizontalHeaderLabels([tr("类别"), tr("数量"), tr("颜色")])
        bg_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        bg_table.setEditTriggers(QAbstractItemView.DoubleClicked | QAbstractItemView.EditKeyPressed | QAbstractItemView.SelectedClicked)
        for row, (label, count) in enumerate(sorted(bg_stats.items(), key=lambda x: -x[1])):
            label_item = QTableWidgetItem(label)
            label_item.setFlags(label_item.flags() | QtCore.ItemIsEditable)
            label_item.setData(QtCore.UserRole, label)
            bg_table.setItem(row, 0, label_item)
            count_item = QTableWidgetItem(str(count))
            count_item.setFlags(count_item.flags() & ~QtCore.ItemIsEditable)
            bg_table.setItem(row, 1, count_item)
            color_button = QPushButton()
            self._set_label_color_button(color_button, self.get_label_color(label))
            color_button.clicked.connect(lambda _, value=label, button=color_button: self._change_label_color(value, dialog, button))
            bg_table.setCellWidget(row, 2, color_button)

        def _on_bg_label_changed(item):
            if item is None or item.column() != 0:
                return
            old_label = item.data(QtCore.UserRole) or ''
            new_label = (item.text() or '').strip()
            if not old_label:
                return
            if not new_label or new_label == old_label:
                bg_table.blockSignals(True)
                item.setText(old_label)
                bg_table.blockSignals(False)
                return
            existing = {
                (bg_table.item(r, 0).text() if bg_table.item(r, 0) else '')
                for r in range(bg_table.rowCount()) if r != item.row()
            }
            if new_label in existing:
                bg_table.blockSignals(True)
                item.setText(old_label)
                bg_table.blockSignals(False)
                return
            if self.label_manager.rename_detection_label(old_label, new_label):
                item.setData(QtCore.UserRole, new_label)
                self._reload_stats_bg_table(bg_table, dialog)
                if hasattr(self, 'update_label_list'):
                    self.update_label_list()
                if (hasattr(self, '_processing_panel') and self._processing_panel
                        and self._processing_panel.isVisible()):
                    self._update_processing_panel_labels()
                self.canvas.update()
            else:
                bg_table.blockSignals(True)
                item.setText(old_label)
                bg_table.blockSignals(False)

        bg_table.itemChanged.connect(_on_bg_label_changed)
        dialog._bg_table = bg_table
        dialog._on_bg_label_changed = _on_bg_label_changed
        bg_container = QWidget()
        bg_cl = QVBoxLayout(bg_container)
        bg_cl.setContentsMargins(0, 0, 0, 0)
        bg_cl.addWidget(bg_table)
        layout.addWidget(bg_container)
        bg_expanded = True
        def _toggle_bg():
            nonlocal bg_expanded
            bg_expanded = not bg_expanded
            bg_container.setVisible(bg_expanded)
            bg_header.setText(f"{'▼' if bg_expanded else '▶'}  {tr('背景图标签')}")
        bg_header.clicked.connect(_toggle_bg)
        paste_header = QPushButton(f"▼  {tr('贴图标签_list')}")
        paste_header.setFlat(True)
        paste_header.setCursor(Qt.PointingHandCursor)
        paste_header.setStyleSheet("border: none; text-align: left; font-weight: bold; font-size: 13px; padding: 2px 0;")
        paste_header.setFixedHeight(24)
        layout.addWidget(paste_header)
        paste_stats = self._get_session_paste_stats()
        paste_table = QTableWidget(len(paste_stats), 3)
        paste_table.setHorizontalHeaderLabels([tr("类别"), tr("数量"), tr("颜色")])
        paste_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        paste_table.setEditTriggers(QAbstractItemView.DoubleClicked | QAbstractItemView.EditKeyPressed | QAbstractItemView.SelectedClicked)
        for row, (label, count) in enumerate(sorted(paste_stats.items(), key=lambda x: -x[1])):
            label_item = QTableWidgetItem(label)
            label_item.setFlags(label_item.flags() | QtCore.ItemIsEditable)
            label_item.setData(QtCore.UserRole, label)
            paste_table.setItem(row, 0, label_item)
            count_item = QTableWidgetItem(str(count))
            count_item.setFlags(count_item.flags() & ~QtCore.ItemIsEditable)
            paste_table.setItem(row, 1, count_item)
            color_button = QPushButton()
            self._set_label_color_button(color_button, self.get_label_color(label))
            color_button.clicked.connect(lambda _, value=label, button=color_button: self._change_label_color(value, dialog, button))
            paste_table.setCellWidget(row, 2, color_button)

        def _on_paste_label_changed(item):
            if item is None or item.column() != 0:
                return
            old_label = item.data(QtCore.UserRole) or ''
            new_label = (item.text() or '').strip()
            if not old_label:
                return
            if not new_label or new_label == old_label:
                paste_table.blockSignals(True)
                item.setText(old_label)
                paste_table.blockSignals(False)
                return
            existing = {
                (paste_table.item(r, 0).text() if paste_table.item(r, 0) else '')
                for r in range(paste_table.rowCount()) if r != item.row()
            }
            if new_label in existing:
                paste_table.blockSignals(True)
                item.setText(old_label)
                paste_table.blockSignals(False)
                return
            if self.label_manager.rename_paste_label(old_label, new_label):
                item.setData(QtCore.UserRole, new_label)
                color_btn = paste_table.cellWidget(item.row(), 2)
                if color_btn is not None:
                    try:
                        color_btn.clicked.disconnect()
                    except TypeError:
                        pass
                    color_btn.clicked.connect(lambda _, value=new_label, button=color_btn: self._change_label_color(value, dialog, button))
                    self._set_label_color_button(color_btn, self.get_label_color(new_label))
                self.canvas.update()
            else:
                paste_table.blockSignals(True)
                item.setText(old_label)
                paste_table.blockSignals(False)

        paste_table.itemChanged.connect(_on_paste_label_changed)
        paste_container = QWidget()
        paste_cl = QVBoxLayout(paste_container)
        paste_cl.setContentsMargins(0, 0, 0, 0)
        paste_cl.addWidget(paste_table)
        layout.addWidget(paste_container)
        paste_expanded = True
        def _toggle_paste():
            nonlocal paste_expanded
            paste_expanded = not paste_expanded
            paste_container.setVisible(paste_expanded)
            paste_header.setText(f"{'▼' if paste_expanded else '▶'}  {tr('贴图标签_list')}")
        paste_header.clicked.connect(_toggle_paste)
        total = QLabel(
            f"{tr('总计')}: {tr('背景图标签')} {sum(bg_stats.values())} {tr('个')} | "
            f"{tr('贴图标签_list')} {sum(paste_stats.values())} {tr('个')}"
        )
        total.setStyleSheet("font-size: 12px; margin-top: 8px;")
        layout.addWidget(total)
        dialog.exec_()

    def _reload_stats_bg_table(self, bg_table, dialog):
        """Rebuild stats dialog background table from live cache after rename/color."""
        from PyQt5.QtWidgets import QTableWidgetItem, QPushButton
        from PyQt5.QtCore import Qt as QtCore
        bg_stats = self._collect_bg_stats_for_dialog()
        rows = sorted(bg_stats.items(), key=lambda x: (-x[1], x[0]))
        bg_table.blockSignals(True)
        bg_table.setRowCount(len(rows))
        for row, (label, count) in enumerate(rows):
            label_item = QTableWidgetItem(label)
            label_item.setFlags(label_item.flags() | QtCore.ItemIsEditable)
            label_item.setData(QtCore.UserRole, label)
            bg_table.setItem(row, 0, label_item)
            count_item = QTableWidgetItem(str(count))
            count_item.setFlags(count_item.flags() & ~QtCore.ItemIsEditable)
            bg_table.setItem(row, 1, count_item)
            color_button = QPushButton()
            self._set_label_color_button(color_button, self.get_label_color(label))
            color_button.clicked.connect(lambda _, value=label, button=color_button: self._change_label_color(value, dialog, button))
            bg_table.setCellWidget(row, 2, color_button)
        bg_table.blockSignals(False)

    def _set_label_color_button(self, button, color):
        button.setText(color)
        button.setStyleSheet(
            f"QPushButton {{ background-color: {color}; color: #FFFFFF; border: 1px solid {color}; }}"
        )

    def _change_label_color(self, label, parent, color_button=None):
        """修改指定类别的颜色。"""
        from ...core import config_manager
        from PyQt5.QtGui import QColor
        from ..dialog_helpers import ThemedColorDialog
        from ..i18n import t as tr
        if not label:
            return
        dialog = ThemedColorDialog(parent)
        dialog.setWindowTitle(tr("颜色"))
        dialog.setCurrentColor(QColor(self.get_label_color(label)))
        if dialog.exec_() != 1:
            return
        color = dialog.currentColor()
        if not color.isValid():
            return
        self.label_color_map[label] = color.name()
        config_manager.save_all(label_colors=self.label_colors, label_color_map=self.label_color_map)
        cached = getattr(self, '_cached_bg_label_stats', None)
        if isinstance(cached, list):
            for item in cached:
                if isinstance(item, dict) and item.get('label') == label:
                    item['color'] = color.name()
        if color_button is not None:
            self._set_label_color_button(color_button, color.name())
        self.canvas.update()
