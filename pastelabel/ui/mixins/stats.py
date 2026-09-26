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

        from ...engine.image_loader import collect_background_label_counts, collect_background_label_tasks
        bg_stats = collect_background_label_counts(list(self.background_images or []))
        bg_tasks = collect_background_label_tasks(list(self.background_images or []))
        for lbl in getattr(self, 'background_dataset_labels', set()) or set():
            bg_stats.setdefault(lbl, 0)
        for lbl in self.global_labels:
            if lbl in bg_stats or lbl in (getattr(self, 'background_dataset_labels', set()) or set()):
                bg_stats.setdefault(lbl, 0)
        self._cached_bg_label_stats = [
            {'label': label, 'count': count, 'color': self.get_label_color(label),
             'tasks': sorted(bg_tasks.get(label, set()))}
            for label, count in sorted(bg_stats.items(), key=lambda x: (-x[1], x[0]))
        ]
        self._cached_bg_label_stats_path = current_path
        return bg_stats

    def _collect_bg_label_tasks_for_dialog(self):
        """{label: [task,...]} 用于统计界面「框类型」列。"""
        from ...core.utils import shape_task_type
        cached = getattr(self, '_cached_bg_label_stats', None) or []
        tasks = {}
        for item in cached:
            if not isinstance(item, dict):
                continue
            label = str(item.get('label', '') or '').strip()
            if not label:
                continue
            for t in item.get('tasks') or []:
                tasks.setdefault(label, set()).add(t)
        # 实时内存框（改名/新建后缓存可能滞后）
        for boxes in list(getattr(self, 'detection_boxes_dict', {}).values()) + [getattr(self, 'detection_boxes', [])]:
            for box in boxes or []:
                if not isinstance(box, dict):
                    continue
                label = str(box.get('label', '') or '').strip()
                if label:
                    tasks.setdefault(label, set()).add(shape_task_type(box))
        return {label: sorted(ts) for label, ts in tasks.items()}

    def _show_label_stats(self):
        """显示标签统计弹窗"""
        self._close_health_worker()
        from PyQt5.QtWidgets import (
            QDialog, QVBoxLayout, QLabel, QTableWidget, QTableWidgetItem,
            QHeaderView, QPushButton, QWidget, QAbstractItemView,
            QMainWindow, QTabWidget,
        )
        from PyQt5.QtCore import Qt as QtCore
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
        dialog.setMinimumSize(810, 600)
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
        host = QMainWindow()
        host.setDockNestingEnabled(True)
        dialog._dock_host = host
        central = QWidget()
        central_layout = QVBoxLayout(central)
        central_layout.setContentsMargins(0, 0, 0, 0)
        host.setCentralWidget(central)
        layout.addWidget(host)
        bg_stats = self._collect_bg_stats_for_dialog()
        bg_tasks = self._collect_bg_label_tasks_for_dialog()
        bg_table = QTableWidget(len(bg_stats), 4)
        bg_table.setHorizontalHeaderLabels([tr("类别"), tr("数量"), tr("框类型"), tr("颜色")])
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
            task_item = QTableWidgetItem(" ".join(bg_tasks.get(label, [])))
            task_item.setFlags(task_item.flags() & ~QtCore.ItemIsEditable)
            bg_table.setItem(row, 2, task_item)
            color_button = QPushButton()
            self._set_label_color_button(color_button, self.get_label_color(label))
            color_button.clicked.connect(lambda _, value=label, button=color_button: self._change_label_color(value, dialog, button))
            bg_table.setCellWidget(row, 3, color_button)

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
            if self.label_manager.rename_paste_label(old_label, new_label, rewrite_disk=True):
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
        dialog._paste_table = paste_table
        tabs = QTabWidget()
        tabs.setDocumentMode(True)
        bg_tab = QWidget()
        bg_tl = QVBoxLayout(bg_tab)
        bg_tl.setContentsMargins(0, 0, 0, 0)
        bg_tl.addWidget(bg_table)
        paste_tab = QWidget()
        paste_tl = QVBoxLayout(paste_tab)
        paste_tl.setContentsMargins(0, 0, 0, 0)
        paste_tl.addWidget(paste_table)
        tabs.addTab(bg_tab, tr('背景图标签'))
        tabs.addTab(paste_tab, tr('贴图标签_list'))
        central_layout.addWidget(tabs)
        dialog._tabs = tabs
        self._build_health_section(dialog, central_layout)
        total = QLabel()
        total.setStyleSheet("font-size: 12px; margin-top: 8px;")
        central_layout.addWidget(total)
        dialog._total_label = total
        self._update_stats_total_label(
            dialog, bg_count=sum(bg_stats.values()), paste_count=sum(paste_stats.values()))
        dialog.exec_()

    def _update_stats_total_label(self, dialog, bg_count=None, paste_count=None):
        """更新统计弹窗底部总计标签。

        计数来源：背景 = 实时统计缓存 `_collect_bg_stats_for_dialog()`（与背景表同源，
        勿传 payload 的 annot 计数，它排除贴图/关键点）；贴图 = payload 整库统计优先，
        缺省回退会话内存 `_get_session_paste_stats()`。
        """
        from ..i18n import t as tr
        label = getattr(dialog, '_total_label', None)
        if label is None:
            return
        if not isinstance(bg_count, int) or isinstance(bg_count, bool):
            bg_count = sum(self._collect_bg_stats_for_dialog().values())
        if not isinstance(paste_count, int) or isinstance(paste_count, bool):
            paste_count = sum(self._get_session_paste_stats().values())
        label.setText(
            f"{tr('总计')}: {tr('背景图标签')} {bg_count} {tr('个')} | "
            f"{tr('贴图标签_list')} {paste_count} {tr('个')}"
        )

    def _close_health_worker(self):
        """中断并清理健康扫描 worker。"""
        worker = getattr(self, '_health_worker', None)
        self._health_worker = None
        if worker is not None:
            try:
                if worker.isRunning():
                    worker.requestInterruption()
                    worker.wait(3000)
                if worker.isRunning():
                    # 超时未停：先断开信号再丢引用，避免 worker 向已销毁的弹窗发结果
                    try:
                        worker.health_ready.disconnect()
                    except Exception:
                        pass
            except Exception:
                pass

    def _build_health_section(self, dialog, layout):
        """构建「数据集健康」区：5 个可拖拽 dock 面板 + 建议，切换标签页切换数据源。"""
        from PyQt5.QtCore import Qt
        from PyQt5.QtWidgets import (
            QPushButton, QLabel, QWidget, QVBoxLayout, QDockWidget)
        from ..i18n import t as tr
        from ..widgets.health_charts import HealthBarChart

        header = QPushButton(f"▼  {tr('数据集健康')}")
        header.setFlat(True)
        header.setCursor(Qt.PointingHandCursor)
        header.setStyleSheet(
            "border: none; text-align: left; font-weight: bold; "
            "font-size: 13px; padding: 2px 0;")
        header.setFixedHeight(24)
        layout.addWidget(header)

        source_label = QLabel(tr('数据源：背景图标签（切换标签页）'))
        source_label.setStyleSheet("color: gray; font-size: 11px;")
        layout.addWidget(source_label)

        class_chart = HealthBarChart()
        size_chart = HealthBarChart()
        aspect_chart = HealthBarChart()
        iou_chart = HealthBarChart()
        paste_chart = HealthBarChart()
        charts = {
            'class': class_chart, 'size': size_chart, 'aspect': aspect_chart,
            'iou': iou_chart, 'paste': paste_chart,
        }
        panels = (
            ('class', tr('类别分布'), tr('各类别占比应接近均衡；长尾类别建议多合成')),
            ('size', tr('尺寸分布'), tr('框尺寸应覆盖多种尺度，避免集中于单一范围')),
            ('aspect', tr('长宽比分布'), tr('长宽比多样化更贴近真实场景')),
            ('iou', tr('IoU 重叠分布'), tr('高 IoU 区间框多说明重复标注偏多')),
            ('paste', tr('贴图 vs 标注'), tr('贴图尺寸中位数与标注接近时合成更自然')),
        )
        host = getattr(dialog, '_dock_host', None) or dialog
        dialog._health_docks = {}
        if hasattr(host, 'addDockWidget'):
            for key, title, desc in panels:
                panel = QWidget()
                pl = QVBoxLayout(panel)
                pl.setContentsMargins(6, 4, 6, 4)
                desc_label = QLabel(desc)
                desc_label.setWordWrap(True)
                desc_label.setStyleSheet("color: gray; font-size: 11px;")
                pl.addWidget(desc_label)
                pl.addWidget(charts[key])
                dock = QDockWidget(title, host)
                dock.setObjectName(f"health_{key}")
                dock.setWidget(panel)
                dock.setFeatures(QDockWidget.DockWidgetMovable)
                dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
                host.addDockWidget(Qt.LeftDockWidgetArea, dock)
                dialog._health_docks[key] = dock
                charts[key].set_placeholder(tr('正在分析'))
            # 两列布局：左列 class/size/aspect，右列 iou/paste；拖动后自动让位
            d = dialog._health_docks
            host.splitDockWidget(d['class'], d['iou'], Qt.Horizontal)
            host.splitDockWidget(d['iou'], d['paste'], Qt.Vertical)
            host.splitDockWidget(d['size'], d['aspect'], Qt.Vertical)
            host.splitDockWidget(d['class'], d['size'], Qt.Vertical)
        else:
            for key in charts:
                charts[key].set_placeholder(tr('正在分析'))
        advice_label = QLabel(f"{tr('建议')}: {tr('正在分析')}")
        advice_label.setWordWrap(True)
        layout.addWidget(advice_label)

        expanded = True
        def _toggle():
            nonlocal expanded
            expanded = not expanded
            for dock in dialog._health_docks.values():
                dock.setVisible(expanded)
            source_label.setVisible(expanded)
            advice_label.setVisible(expanded)
            header.setText(
                f"{'▼' if expanded else '▶'}  {tr('数据集健康')}")
        header.clicked.connect(_toggle)

        dialog._health_charts = charts
        dialog._health_advice_label = advice_label
        dialog._health_source_label = source_label
        dialog._health_source = 'annot'
        dialog._health_payload = None

        def _render_source(source, payload=None):
            payload = payload if payload is not None else dialog._health_payload
            dialog._health_source = source
            source_label.setText(
                tr('数据源：背景图标签（切换标签页）') if source == 'annot'
                else tr('数据源：贴图标签（切换标签页）'))
            if not payload:
                return
            if payload.get('error'):
                for chart in charts.values():
                    chart.set_placeholder(tr('分析失败'))
                advice_label.setText(tr('分析失败'))
                return
            section = payload.get(source) or {}
            stats = section.get('stats') or {}
            if source == 'paste' and not stats:
                for key in ('class', 'size', 'aspect', 'iou'):
                    charts[key].set_placeholder(tr('暂无贴图数据'))
                charts['paste'].set_placeholder(tr('暂无贴图数据'))
                advice_label.setText("")
                return
            class_dist = stats.get('class_dist') or []
            if class_dist:
                charts['class'].set_data(
                    [{'label': c['label'], 'value': c['count'],
                      'color': self.get_label_color(c['label'])}
                     for c in class_dist],
                    horizontal=True, highlight_extremes=True)
            else:
                charts['class'].set_placeholder(tr('未发现明显失衡'))
            size = stats.get('size_hist') or {}
            charts['size'].set_histogram(size.get('edges'), size.get('counts'),
                                         xlabel=tr('面积'), ylabel=tr('框数'))
            aspect = stats.get('aspect_hist') or {}
            charts['aspect'].set_histogram(aspect.get('edges'),
                                           aspect.get('counts'),
                                           xlabel=tr('长宽比'), ylabel=tr('框数'))
            iou = stats.get('iou_hist') or {}
            charts['iou'].set_histogram(iou.get('edges'), iou.get('counts'),
                                        xlabel=tr('IoU'), ylabel=tr('框数'))
            pva = (payload.get('annot') or {}).get('stats', {}).get(
                'paste_vs_annot') or {}
            if pva.get('has_paste'):
                annot_q = pva.get('annot_quantiles') or [0, 0, 0, 0]
                paste_q = pva.get('paste_quantiles') or [0, 0, 0, 0]
                charts['paste'].set_data([
                    {'label': tr('标注'), 'value': annot_q[2]},
                    {'label': tr('贴图'), 'value': paste_q[2]},
                ], horizontal=True)
            else:
                charts['paste'].set_placeholder(tr('暂无贴图数据'))
            advice = section.get('advice') or [tr('未发现明显失衡')]
            advice_label.setText(f"{tr('建议')}: " + "；".join(advice))

        def _set_health_source(source):
            _render_source(source)

        dialog._set_health_source = _set_health_source
        tabs = getattr(dialog, '_tabs', None)
        if tabs is not None:
            tabs.currentChanged.connect(
                lambda idx: _set_health_source('annot' if idx == 0 else 'paste'))

        if not getattr(self, 'background_images', None):
            for chart in charts.values():
                chart.set_placeholder(tr('请先加载数据集'))
            advice_label.setText("")
            return

        from ...engine.dataset_health import DatasetHealthWorker
        self._close_health_worker()
        memory_boxes = {
            idx: list(boxes) for idx, boxes in
            (getattr(self, 'detection_boxes_dict', None) or {}).items()}
        canvas_items = dict(getattr(self, 'canvas_items_dict', None) or {})
        current = getattr(self, 'current_background_index', -1)
        if current >= 0:
            canvas_items[current] = list(getattr(self, 'canvas_items', None) or [])
        worker = DatasetHealthWorker(
            tuple(self.background_images), memory_boxes, canvas_items, self)
        worker.finished.connect(worker.deleteLater)

        def _on_payload(payload):
            dialog._health_payload = payload
            paste_class = ((payload.get('paste') or {}).get('stats') or {}).get(
                'class_dist') or []
            if paste_class:
                self._reload_stats_paste_table(dialog, paste_class)
            paste_total = (payload.get('paste') or {}).get('stats', {}).get(
                'summary', {}).get('total_boxes')
            if not isinstance(paste_total, int) or isinstance(paste_total, bool):
                paste_total = None
            # 背景计数不取 payload：annot 统计排除贴图/关键点，与背景表（sidecar 全量）
            # 不同源；交由 helper 回退到 _collect_bg_stats_for_dialog()，保证与表一致。
            self._update_stats_total_label(dialog, paste_count=paste_total)
            _render_source(dialog._health_source, payload)

        dialog._on_health_payload = _on_payload
        worker.health_ready.connect(_on_payload)
        self._health_worker = worker
        worker.start()

        def _on_close(*_a):
            self._close_health_worker()
        dialog.finished.connect(_on_close)

    def _reload_stats_bg_table(self, bg_table, dialog):
        """Rebuild stats dialog background table from live cache after rename/color."""
        from PyQt5.QtWidgets import QTableWidgetItem, QPushButton
        from PyQt5.QtCore import Qt as QtCore
        bg_stats = self._collect_bg_stats_for_dialog()
        bg_tasks = self._collect_bg_label_tasks_for_dialog()
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
            task_item = QTableWidgetItem(" ".join(bg_tasks.get(label, [])))
            task_item.setFlags(task_item.flags() & ~QtCore.ItemIsEditable)
            bg_table.setItem(row, 2, task_item)
            color_button = QPushButton()
            self._set_label_color_button(color_button, self.get_label_color(label))
            color_button.clicked.connect(lambda _, value=label, button=color_button: self._change_label_color(value, dialog, button))
            bg_table.setCellWidget(row, 3, color_button)
        bg_table.blockSignals(False)

    def _reload_stats_paste_table(self, dialog, class_dist):
        """用整库贴图统计重建贴图表格（worker payload 到达后调用）。"""
        from PyQt5.QtWidgets import QTableWidgetItem, QPushButton
        from PyQt5.QtCore import Qt as QtCore
        table = getattr(dialog, '_paste_table', None)
        if table is None:
            return
        rows = [(str(e.get('label', '') or ''), int(e.get('count', 0) or 0))
                for e in class_dist if isinstance(e, dict)]
        rows.sort(key=lambda x: (-x[1], x[0]))
        table.blockSignals(True)
        table.setRowCount(len(rows))
        for row, (label, count) in enumerate(rows):
            label_item = QTableWidgetItem(label)
            label_item.setFlags(label_item.flags() | QtCore.ItemIsEditable)
            label_item.setData(QtCore.UserRole, label)
            table.setItem(row, 0, label_item)
            count_item = QTableWidgetItem(str(count))
            count_item.setFlags(count_item.flags() & ~QtCore.ItemIsEditable)
            table.setItem(row, 1, count_item)
            color_button = QPushButton()
            self._set_label_color_button(color_button, self.get_label_color(label))
            color_button.clicked.connect(
                lambda _, value=label, button=color_button: self._change_label_color(value, dialog, button))
            table.setCellWidget(row, 2, color_button)
        table.blockSignals(False)

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
