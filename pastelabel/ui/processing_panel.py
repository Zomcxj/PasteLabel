import json
import os
import shutil
from datetime import datetime
from typing import List

from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt5.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDoubleSpinBox, QFileDialog, QFrame,
    QGridLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QScrollArea, QSpinBox, QTextEdit, QVBoxLayout, QWidget,
)

from .i18n import t as tr
from .theme import ThemeManager
from .dwm import set_titlebar_dark
from ..core.utils import create_app_icon
from ..engine.yolo_exporter import YoloExporter
from ..engine.splitter import Splitter
from ..engine.augmenter import Augmenter, get_all_transforms
from ..engine.augmenter.base import BaseTransform

SPLIT_KEYS = ["train", "val", "test"]


class _ScanSpinnerWidget(QLabel):
    """内嵌 braille 旋转动画的扫描提示组件"""
    _CHARS = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"

    def __init__(self, parent=None):
        super().__init__(parent)
        self._idx = 0
        self._raw_text = ""
        self._timer = QTimer(self)
        self._timer.setInterval(80)
        self._timer.timeout.connect(self._tick)
        self.setStyleSheet("color: gray; font-size: 11px; padding: 2px;")
        self.setFixedHeight(20)

    def setLabel(self, t):
        self._raw_text = t
        self._idx = 0
        self._refresh()

    def setVisible(self, v):
        super().setVisible(v)
        if v:
            self._idx = 0
            self._timer.start()
            self._refresh()
        else:
            self._timer.stop()

    def _tick(self):
        self._idx += 1
        self._refresh()

    def _refresh(self):
        c = self._CHARS[self._idx % len(self._CHARS)]
        super().setText(f"{c} {self._raw_text}" if self._raw_text else c)

TRANSFORM_META = {
    "fliph":       ("水平翻转", []),
    "flipv":       ("垂直翻转", []),
    "bright":      ("亮度", [("delta", QSpinBox, -100, 100, -30, 30)]),
    "contrast":    ("对比度", [("factor", QDoubleSpinBox, 0.5, 2.0, 1.2, 1.8)]),
    "hue":         ("色相(H)", [("delta", QSpinBox, -180, 180, -30, 30)]),
    "saturation":  ("饱和度(S)", [("factor", QDoubleSpinBox, 0.0, 2.0, 1.2, 1.8)]),
    "value":       ("明度(V)", [("delta", QSpinBox, -100, 100, -30, 30)]),
    "gauss":       ("高斯噪声", [("sigma", QSpinBox, 1, 100, 10, 40)]),
    "saltpepper":  ("椒盐噪声", [("prob", QDoubleSpinBox, 0.0, 0.5, 0.02, 0.08)]),
    "trans":       ("随机平移", [("offset", QSpinBox, 0, 100, 10, 30)]),
    "rotate":      ("随机旋转", [("angle", QSpinBox, 0, 45, 5, 25)]),
    "scale":       ("随机缩放", [("scale", QDoubleSpinBox, 0.5, 1.5, 0.8, 1.2)]),
}

_TRANSFORM_ORDER = ["fliph", "flipv", "bright", "trans", "rotate", "scale",
                    "contrast", "gauss", "saltpepper", "hue", "saturation", "value"]


class Worker(QThread):
    log = pyqtSignal(str)
    progress = pyqtSignal(int, int, str)
    finished = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(self, func):
        super().__init__()
        self._func = func
        self.result = None
        self._error = None

    def run(self):
        try:
            self.result = self._func(self.log.emit, self.progress.emit)
            self.finished.emit(self.result)
        except Exception as e:
            self._error = str(e)
            self.error.emit(str(e))


class CollapsibleSection(QWidget):

    def __init__(self, title: str, parent=None, color: str = "#4CAF50"):
        super().__init__(parent)
        self._expanded = True
        self._title = title
        self._color = color
        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 2, 0, 2)
        outer.setSpacing(0)
        bar = QWidget()
        bar.setFixedWidth(3)
        bar.setStyleSheet(f"background: {color};")
        outer.addWidget(bar)
        inner = QWidget()
        inner_layout = QVBoxLayout(inner)
        inner_layout.setContentsMargins(0, 0, 0, 0)
        inner_layout.setSpacing(0)
        self._header = QPushButton(f"▼ {title}")
        self._header.setObjectName("collapseHeader")
        self._header.setFlat(True)
        self._header.setCursor(Qt.PointingHandCursor)
        self._header.setFixedHeight(24)
        self._header.setStyleSheet("border: none; text-align: left; padding: 2px 8px;")
        self._header.clicked.connect(self._toggle)
        self._content = QWidget()
        self._content.setObjectName("collapseContent")
        self._content_layout = QVBoxLayout(self._content)
        self._content_layout.setContentsMargins(8, 2, 8, 4)
        inner_layout.addWidget(self._header)
        inner_layout.addWidget(self._content)
        outer.addWidget(inner, 1)

    def _toggle(self):
        self._expanded = not self._expanded
        self._content.setVisible(self._expanded)
        self._header.setText(f"{'▼' if self._expanded else '▶'} {self._title}")
        self._update_margins()

    def _update_margins(self):
        outer = self.layout()
        if outer:
            if self._expanded:
                outer.setContentsMargins(0, 2, 0, 2)
                outer.setSpacing(0)
            else:
                outer.setContentsMargins(0, 0, 0, 0)
                outer.setSpacing(0)

    def set_title(self, title: str):
        self._title = title
        self._header.setText(f"{'▼' if self._expanded else '▶'} {title}")

    def content_layout(self):
        return self._content_layout


class ProcessingPanel(QWidget):
    def __init__(self, editor, parent=None):
        super().__init__(parent, Qt.Window | Qt.WindowCloseButtonHint | Qt.WindowMinimizeButtonHint)
        self._editor = editor
        self.setObjectName("processingPanel")
        self.setWindowIcon(create_app_icon(os.path.dirname(__file__)))
        self.setMinimumWidth(500)
        self.resize(832, 850)
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(0)
        self._build_path_selector(main_layout)
        self._collapsible_sections = []
        self._split_lbls = []
        self._interrupted = False
        self._build_augment_section(main_layout)
        self._build_export_section(main_layout)
        self._build_split_section(main_layout)
        self._build_pipeline_section(main_layout)
        self._log_area = QTextEdit()
        self._log_area.setReadOnly(True)
        self._log_area.setMinimumHeight(80)
        self._log_area.setPlaceholderText(tr("操作日志将显示在这里..."))
        self._log_area.setObjectName("logArea")
        main_layout.addWidget(self._log_area, 1)
        self._augment_result = None
        self._pipe_mode = False
        self._pipe_steps = []
        self._pipe_idx = 0
        self._pipe_error = False
        self._spinner_chars = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
        self._spinner_idx = 0
        self._spinner_timer = QTimer(self)
        self._spinner_timer.timeout.connect(self._spinner_tick)
        self._spinner_btn = None
        self._refresh_texts()

    def _build_path_selector(self, layout):
        path_layout = QHBoxLayout()
        path_layout.setContentsMargins(0, 0, 0, 4)
        path_layout.setSpacing(6)
        self._path_lbl = QLabel()
        path_layout.addWidget(self._path_lbl)
        self._path_edit = QLineEdit(self._get_session_dir())
        self._path_edit.setObjectName("outputPath")
        self._path_edit.textChanged.connect(self._update_labels_list)
        path_layout.addWidget(self._path_edit, 1)
        self._browse_btn = QPushButton()
        self._browse_btn.setObjectName("accentBtn")
        self._browse_btn.setFixedWidth(60)
        self._browse_btn.clicked.connect(self._browse_output_dir)
        path_layout.addWidget(self._browse_btn)
        layout.addLayout(path_layout)

    def _get_session_dir(self):
        imgs = self._editor.background_images
        if imgs:
            return os.path.dirname(imgs[0])
        return ""

    def _get_output_dir(self):
        working = self._path_edit.text().strip()
        if not working:
            working = self._get_session_dir()
        if not working:
            return os.getcwd()
        exports_dir = os.path.normpath(os.path.join(os.path.dirname(working), "exports"))
        if not os.path.exists(exports_dir):
            os.makedirs(exports_dir, exist_ok=True)
        return exports_dir

    def _browse_output_dir(self):
        d = QFileDialog.getExistingDirectory(self, tr("选择数据集目录"), self._path_edit.text())
        if d:
            self._path_edit.setText(d)

    def _collapsible_section(self, title, parent_layout, color="#4CAF50"):
        self._collapsible_sections.append(title)
        s = CollapsibleSection(title, color=color)
        parent_layout.addWidget(s)
        return s

    def _build_augment_section(self, parent_layout):
        section = self._collapsible_section("", parent_layout, "#F44336")
        layout = section.content_layout()
        transforms = get_all_transforms()
        order = [n for n in _TRANSFORM_ORDER if n in transforms]
        self._aug_widgets = {}
        grid = QGridLayout()
        grid.setSpacing(6)
        self._aug_inc_orig = QCheckBox()
        self._aug_inc_orig.setChecked(True)
        self._aug_widgets["__orig__"] = (self._aug_inc_orig, {}, "原图")
        orig_cell = QWidget()
        orig_cell.setMinimumWidth(140)
        orig_cl = QHBoxLayout(orig_cell)
        orig_cl.setContentsMargins(2, 1, 2, 1)
        orig_cl.setSpacing(2)
        orig_cl.addWidget(self._aug_inc_orig)
        orig_cl.addStretch()
        grid.addWidget(orig_cell, 0, 0)
        for idx, name in enumerate(order):
            row, col = divmod(idx + 1, 3)
            meta = TRANSFORM_META.get(name, (name, []))
            display_name, param_defs = meta
            cell = QWidget()
            cell.setMinimumWidth(140)
            cl = QHBoxLayout(cell)
            cl.setContentsMargins(2, 1, 2, 1)
            cl.setSpacing(2)
            cb = QCheckBox(display_name)
            cb.setChecked(name in ("fliph", "flipv", "bright", "rotate", "trans"))
            cl.addWidget(cb)
            cl.addStretch()
            param_spins = {}
            for pname, ptype, pmin, pmax, dmin, dmax in param_defs:
                lbl = QLabel("~")
                lbl.setFixedWidth(10)
                spin_min = self._make_spin(ptype, pmin, pmax, dmin)
                spin_max = self._make_spin(ptype, pmin, pmax, dmax)
                cl.addWidget(spin_min)
                cl.addWidget(lbl)
                cl.addWidget(spin_max)
                param_spins[pname] = (spin_min, spin_max)
            grid.addWidget(cell, row, col)
            self._aug_widgets[name] = (cb, param_spins, display_name)
        for c in range(3):
            grid.setColumnStretch(c, 1)
        layout.addLayout(grid)
        rl = QHBoxLayout()
        self._ratio_lbl = QLabel()
        rl.addWidget(self._ratio_lbl)
        self._aug_ratio = QDoubleSpinBox()
        self._aug_ratio.setRange(0.05, 1.0)
        self._aug_ratio.setSingleStep(0.05)
        self._aug_ratio.setDecimals(2)
        self._aug_ratio.setValue(1.0)
        self._aug_ratio.setFixedWidth(70)
        rl.addWidget(self._aug_ratio)
        rl.addSpacing(10)
        self._mode_lbl = QLabel()
        rl.addWidget(self._mode_lbl)
        self._aug_mode = QComboBox()
        self._aug_mode.addItems(["", ""])
        self._aug_mode.setFixedWidth(100)
        rl.addWidget(self._aug_mode)
        rl.addStretch()
        layout.addLayout(rl)
        btn_layout = QHBoxLayout()
        self._aug_btn = QPushButton()
        self._aug_btn.setObjectName("successBtn")
        self._aug_btn.clicked.connect(lambda: self._run_augment())
        btn_layout.addWidget(self._aug_btn, 5)
        btn_layout.addWidget(self._make_btn_with_stop(self._aug_btn, lambda: self._do_interrupt()), 1)
        self._aug_clear_btn = QPushButton()
        self._aug_clear_btn.setObjectName("accentBtn")
        self._aug_clear_btn.clicked.connect(lambda: self._clear_aug())
        btn_layout.addWidget(self._aug_clear_btn, 1)
        layout.addLayout(btn_layout)
        self._aug_section = section

    def _make_spin(self, typ, vmin, vmax, default):
        s = typ()
        s.setRange(vmin, vmax)
        s.setSingleStep(0.05 if typ == QDoubleSpinBox else 1)
        if typ == QDoubleSpinBox:
            s.setDecimals(1)
        s.setValue(default)
        s.setFixedWidth(60)
        return s

    def _build_export_section(self, parent_layout):
        section = self._collapsible_section("", parent_layout, "#FFC107")
        layout = section.content_layout()
        self._exp_label_title = QLabel()
        layout.addWidget(self._exp_label_title)
        self._exp_label_grid_container = QWidget()
        self._exp_label_grid_container.setMaximumHeight(130)
        self._exp_label_grid = QGridLayout(self._exp_label_grid_container)
        self._exp_label_grid.setSpacing(8)
        self._exp_label_grid.setContentsMargins(0, 2, 0, 2)
        self._exp_label_grid.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self._exp_label_checkboxes = {}
        layout.addWidget(self._exp_label_grid_container, 0, Qt.AlignLeft)
        self._exp_scan_label = _ScanSpinnerWidget()
        self._exp_scan_label.setVisible(False)
        layout.addWidget(self._exp_scan_label)
        opts_layout = QHBoxLayout()
        opts_layout.setContentsMargins(0, 0, 0, 0)
        self._exp_skip_empty = QCheckBox()
        self._exp_skip_empty.setChecked(True)
        opts_layout.addWidget(self._exp_skip_empty)
        opts_layout.addStretch()
        layout.addLayout(opts_layout)
        btn_layout = QHBoxLayout()
        self._exp_btn = QPushButton()
        self._exp_btn.setObjectName("successBtn")
        self._exp_btn.clicked.connect(lambda: self._run_export())
        btn_layout.addWidget(self._exp_btn, 5)
        btn_layout.addWidget(self._make_btn_with_stop(self._exp_btn, lambda: self._do_interrupt()), 1)
        self._exp_clear_btn = QPushButton()
        self._exp_clear_btn.setObjectName("accentBtn")
        self._exp_clear_btn.clicked.connect(lambda: self._clear_exp())
        btn_layout.addWidget(self._exp_clear_btn, 1)
        layout.addLayout(btn_layout)
        self._exp_section = section

    def _build_split_section(self, parent_layout):
        section = self._collapsible_section("", parent_layout, "#4CAF50")
        layout = section.content_layout()
        sl = QHBoxLayout()
        for key in SPLIT_KEYS:
            self._split_lbls.append(QLabel())
            sl.addWidget(self._split_lbls[-1])
            s = QDoubleSpinBox()
            s.setRange(0.0, 1.0)
            s.setSingleStep(0.05)
            s.setValue({"train": 0.8, "val": 0.1, "test": 0.1}[key])
            s.setFixedWidth(60)
            s.valueChanged.connect(lambda val, k=key: self._on_split_changed(k))
            sl.addWidget(s)
            setattr(self, f"_split_{key}", s)
        sl.addStretch()
        layout.addLayout(sl)
        btn_layout = QHBoxLayout()
        self._split_btn = QPushButton()
        self._split_btn.setObjectName("successBtn")
        self._split_btn.clicked.connect(lambda: self._run_split())
        btn_layout.addWidget(self._split_btn, 5)
        btn_layout.addWidget(self._make_btn_with_stop(self._split_btn, lambda: self._do_interrupt()), 1)
        self._split_clear_btn = QPushButton()
        self._split_clear_btn.setObjectName("accentBtn")
        self._split_clear_btn.clicked.connect(lambda: self._clear_split())
        btn_layout.addWidget(self._split_clear_btn, 1)
        layout.addLayout(btn_layout)
        self._split_section = section

    def _build_pipeline_section(self, parent_layout):
        section = self._collapsible_section("", parent_layout, "#FFFFFF")
        layout = section.content_layout()
        hl = QHBoxLayout()
        self._pipe_aug = QCheckBox()
        self._pipe_aug.setChecked(True)
        self._pipe_exp = QCheckBox()
        self._pipe_exp.setChecked(True)
        self._pipe_split = QCheckBox()
        self._pipe_split.setChecked(True)
        hl.addWidget(self._pipe_aug)
        hl.addWidget(QLabel(" → "))
        hl.addWidget(self._pipe_exp)
        hl.addWidget(QLabel(" → "))
        hl.addWidget(self._pipe_split)
        hl.addStretch()
        layout.addLayout(hl)
        btn_layout = QHBoxLayout()
        self._pipe_btn = QPushButton()
        self._pipe_btn.setObjectName("accentBtn")
        self._pipe_btn.clicked.connect(self._run_pipeline)
        btn_layout.addWidget(self._pipe_btn)
        btn_layout.addWidget(self._make_btn_with_stop(self._pipe_btn, lambda: self._do_interrupt()))
        layout.addLayout(btn_layout)
        self._pipe_section = section

    def _scan_labels_from_json(self):
        labels = set()
        for boxes in self._editor.detection_boxes_dict.values():
            for b in boxes:
                lbl = b.get("label", "")
                if lbl:
                    labels.add(lbl)
        if labels:
            return sorted(labels)
        if hasattr(self._editor, 'global_labels') and self._editor.global_labels:
            return sorted(self._editor.global_labels)
        total = len(self._editor.background_images)
        for i, img_path in enumerate(self._editor.background_images):
            jp = os.path.splitext(img_path)[0] + ".json"
            if os.path.exists(jp):
                try:
                    with open(jp, encoding='utf-8') as f:
                        data = json.load(f)
                    for sh in data.get("shapes", []):
                        lbl = sh.get("label", "")
                        if lbl:
                            labels.add(lbl)
                except Exception:
                    pass
            if total > 2 and i % 5 == 0:
                QApplication.processEvents()
        if labels:
            return sorted(labels)
        work_dir = self._path_edit.text().strip()
        if not work_dir:
            work_dir = self._get_session_dir()
        if work_dir and os.path.isdir(work_dir):
            jsons = [f for f in os.listdir(work_dir) if f.lower().endswith('.json')]
            for fname in jsons:
                try:
                    with open(os.path.join(work_dir, fname), encoding='utf-8') as f:
                        data = json.load(f)
                    for sh in data.get("shapes", []):
                        lbl = sh.get("label", "")
                        if lbl:
                            labels.add(lbl)
                except Exception:
                    pass
                QApplication.processEvents()
        return sorted(labels)

    def _update_labels_list(self):
        self._clear_grid()
        self._exp_scan_label.setVisible(True)
        self._exp_scan_label.setLabel(tr("识别中..."))
        QApplication.processEvents()
        labels = self._scan_labels_from_json()
        self._exp_scan_label.setVisible(False)
        if not labels:
            msg = QLabel(tr("未检测到标签"))
            msg.setStyleSheet("color: gray; padding: 4px;")
            self._exp_label_grid.addWidget(msg, 0, 0)
            return
        for i, lbl in enumerate(labels):
            cb = QCheckBox(lbl)
            cb.setChecked(True)
            cb.setMinimumWidth(100)
            row, col = divmod(i, 6)
            self._exp_label_grid.addWidget(cb, row, col)
            self._exp_label_checkboxes[lbl] = cb

    def _clear_grid(self):
        for w in list(self._exp_label_grid_container.children()):
            if not isinstance(w, QWidget) or w is self._exp_scan_label:
                continue
            self._exp_label_grid.removeWidget(w)
            w.hide()
            w.deleteLater()
        self._exp_label_checkboxes.clear()

    def _refresh_texts(self):
        self.setWindowTitle(tr("数据处理"))
        if not self._path_edit.text().strip():
            self._path_edit.setText(self._get_session_dir())
        self._path_lbl.setText(tr("数据集目录:"))
        self._browse_btn.setText(tr("选择"))
        self._aug_section.set_title(tr("数据增强"))
        for name, (cb, param_spins, cn_name) in self._aug_widgets.items():
            if name == "__orig__":
                cb.setText(tr("原图"))
            else:
                cb.setText(tr(cn_name))
        self._ratio_lbl.setText(tr("图片比例:"))
        self._mode_lbl.setText(tr("模式:"))
        idx = self._aug_mode.currentIndex()
        self._aug_mode.clear()
        self._aug_mode.addItems([tr("全部增强"), tr("随机几项")])
        self._aug_mode.setCurrentIndex(idx)
        self._aug_btn.setText(tr("增强"))
        self._aug_clear_btn.setText(tr("清空"))
        self._exp_section.set_title(tr("YOLO 导出"))
        self._exp_label_title.setText(tr("类别:"))
        self._exp_skip_empty.setText(tr("跳过空标签"))
        self._exp_btn.setText(tr("导出"))
        self._exp_clear_btn.setText(tr("清空"))
        self._split_section.set_title(tr("数据集划分"))
        for key, lbl in zip(SPLIT_KEYS, self._split_lbls):
            lbl.setText(tr(key))
        self._split_btn.setText(tr("划分"))
        self._split_clear_btn.setText(tr("清空"))
        self._pipe_section.set_title(tr("流水线"))
        self._pipe_aug.setText(tr("增强"))
        self._pipe_exp.setText(tr("导出"))
        self._pipe_split.setText(tr("划分"))
        self._pipe_btn.setText(tr("▶ 一键流水线"))

    def showEvent(self, event):
        super().showEvent(event)
        self._refresh_texts()
        self._update_labels_list()
        try:
            hwnd = int(self.winId())
            is_dark = ThemeManager.get_mode().name == "DARK"
            set_titlebar_dark(hwnd, is_dark)
        except Exception:
            pass

    def closeEvent(self, event):
        self._log_area.clear()
        self.hide()
        event.accept()

    def _button_busy(self, btn, text=None, clear_btn=None):
        if text is None:
            text = tr("执行中...")
        btn._orig_text = btn.text()
        btn._busy_text = text
        btn.setText(text)
        btn.setEnabled(False)
        self._interrupted = False
        if hasattr(btn, '_stop_btn'):
            btn._stop_btn.setVisible(True)
            btn._stop_btn.setEnabled(True)
        if clear_btn:
            clear_btn.setEnabled(False)
        self._spinner_idx = 0
        self._spinner_btn = btn
        self._spinner_timer.start(80)

    def _button_ready(self, btn, clear_btn=None):
        self._spinner_timer.stop()
        self._spinner_btn = None
        btn.setText(getattr(btn, '_orig_text', btn.text()))
        btn.setEnabled(True)
        if hasattr(btn, '_stop_btn'):
            btn._stop_btn.setVisible(False)
        if clear_btn:
            clear_btn.setEnabled(True)

    def _spinner_tick(self):
        if self._spinner_btn is None:
            return
        c = self._spinner_chars[self._spinner_idx % len(self._spinner_chars)]
        self._spinner_idx += 1
        text = getattr(self._spinner_btn, '_busy_text', tr("执行中..."))
        self._spinner_btn.setText(f"{c} {text}")

    def _make_btn_with_stop(self, btn, stop_handler):
        stop_btn = QPushButton("■")
        stop_btn.setObjectName("accentBtn")
        stop_btn.setFixedWidth(28)
        stop_btn.setVisible(False)
        stop_btn.setStyleSheet("QPushButton { color: #F44336; }")
        stop_btn.clicked.connect(stop_handler)
        btn._stop_btn = stop_btn
        return stop_btn

    def _do_interrupt(self):
        self._interrupted = True
        self._log(tr("操作中断"))

    def _ensure_boxes_loaded(self):
        work_dir = self._path_edit.text().strip()
        if not work_dir:
            work_dir = self._get_session_dir()
        if not work_dir or not os.path.isdir(work_dir):
            self._run_images = []
            self._run_boxes = {}
            return
        exts = ('.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif')
        img_files = sorted([
            f for f in os.listdir(work_dir)
            if os.path.splitext(f)[1].lower() in exts
        ])
        self._run_images = [os.path.join(work_dir, f) for f in img_files]
        self._run_boxes = {}
        for idx, img_path in enumerate(self._run_images):
            json_path = os.path.splitext(img_path)[0] + ".json"
            if not os.path.exists(json_path):
                self._run_boxes[idx] = []
                continue
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                boxes = []
                for sh in data.get("shapes", []):
                    pts = sh.get("points", [])
                    if len(pts) >= 2:
                        x_coords = [p[0] for p in pts]
                        y_coords = [p[1] for p in pts]
                        x = min(x_coords)
                        y = min(y_coords)
                        w = max(x_coords) - x
                        h = max(y_coords) - y
                        boxes.append({
                            "x": x, "y": y, "width": w, "height": h,
                            "label": sh.get("label", "")
                        })
                self._run_boxes[idx] = boxes
            except Exception:
                self._run_boxes[idx] = []
            if idx % 5 == 0:
                QApplication.processEvents()

    def _get_selected_labels(self) -> List[str]:
        return [lbl for lbl, cb in self._exp_label_checkboxes.items() if cb.isChecked()]

    def _get_image_size(self, img_path):
        try:
            from PyQt5.QtGui import QImage
            img = QImage(img_path)
            if not img.isNull():
                return img.width(), img.height()
        except Exception:
            pass
        return 0, 0

    def _detect_augmented_images(self):
        output_dir = self._get_output_dir()
        aug_dir = os.path.join(output_dir, "images")
        if not os.path.isdir(aug_dir):
            return None
        imgs = [f for f in os.listdir(aug_dir)
                if f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif'))]
        if not imgs:
            return None
        aug_dir = os.path.normpath(aug_dir)
        aug_images = [os.path.join(aug_dir, f) for f in sorted(imgs)]
        aug_boxes = {}
        for i, img_path in enumerate(aug_images):
            base = os.path.splitext(os.path.basename(img_path))[0]
            json_path = os.path.join(aug_dir, base + ".json")
            if os.path.exists(json_path):
                try:
                    with open(json_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    shapes = data.get("shapes", [])
                    box_list = []
                    for shape in shapes:
                        pts = shape.get("points", [])
                        lbl = shape.get("label", "")
                        if len(pts) >= 2 and lbl:
                            x_coords = [p[0] for p in pts]
                            y_coords = [p[1] for p in pts]
                            x = min(x_coords)
                            y = min(y_coords)
                            w = max(x_coords) - x
                            h = max(y_coords) - y
                            box_list.append({
                                "x": x, "y": y, "width": w, "height": h,
                                "label": lbl,
                            })
                    aug_boxes[i] = box_list
                except Exception:
                    aug_boxes[i] = []
            else:
                aug_boxes[i] = []
        return aug_images, aug_boxes

    def _clear_dir(self, dir_path):
        dir_path = os.path.normpath(dir_path)
        exports_dir = os.path.normpath(self._get_output_dir())
        if not dir_path.startswith(exports_dir):
            return False
        if os.path.isdir(dir_path):
            shutil.rmtree(dir_path)
            return True
        return False

    def _has_files(self, *paths):
        for p in paths:
            if os.path.isdir(p) and os.listdir(p):
                return True
        return False

    def _require_path(self):
        if not self._path_edit.text().strip():
            self._log(tr("log_no_files"))
            return False
        return True

    def _confirm_clear(self, path):
        from PyQt5.QtWidgets import QMessageBox
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Question)
        box.setWindowTitle(tr("清空"))
        box.setText(tr("确认清空") + "\n" + path)
        yes_btn = box.addButton(tr("是"), QMessageBox.YesRole)
        no_btn = box.addButton(tr("否"), QMessageBox.NoRole)
        box.setDefaultButton(no_btn)
        hwnd = int(box.winId())
        set_titlebar_dark(hwnd, True)
        box.exec_()
        return box.clickedButton() == yes_btn

    def _clear_aug(self):
        if not self._require_path():
            return
        output_dir = self._get_output_dir()
        aug_dir = os.path.join(output_dir, "images")
        if not self._has_files(aug_dir):
            self._log(tr("log_no_files"))
            return
        if not self._confirm_clear(aug_dir):
            return
        self._log(tr("log_clearing_path").format(path=aug_dir))
        if self._clear_dir(aug_dir):
            self._log(tr("log_aug_cleared"))
            self._augment_result = None

    def _clear_exp(self):
        if not self._require_path():
            return
        output_dir = self._get_output_dir()
        imgs = os.path.join(output_dir, "images")
        lbls = os.path.join(output_dir, "labels")
        cls_f = os.path.join(output_dir, "classes.txt")
        if not self._has_files(imgs, lbls) and not os.path.exists(cls_f):
            self._log(tr("log_no_files"))
            return
        if not self._confirm_clear(output_dir):
            return
        self._log(tr("log_clearing_path").format(path=output_dir))
        self._clear_dir(imgs)
        self._clear_dir(lbls)
        if os.path.exists(cls_f):
            os.remove(cls_f)
        self._log(tr("log_exp_cleared"))
        self._augment_result = None

    def _clear_split(self):
        if not self._require_path():
            return
        output_dir = self._get_output_dir()
        divide_dir = os.path.join(output_dir, "divide")
        if not self._has_files(divide_dir):
            self._log(tr("log_no_files"))
            return
        if not self._confirm_clear(divide_dir):
            return
        self._log(tr("log_clearing_path").format(path=divide_dir))
        if self._clear_dir(divide_dir):
            self._log(tr("log_split_cleared"))
        else:
            self._log(tr("log_no_files"))

    def _log(self, msg):
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor = self._log_area.textCursor()
        cursor.movePosition(cursor.End)
        self._log_area.setTextCursor(cursor)
        self._log_area.append(f"[{ts}] {msg}")
        sb = self._log_area.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _get_transform_specs(self):
        all_t = get_all_transforms()
        specs = []
        for name, (cb, param_spins, _) in self._aug_widgets.items():
            if not cb.isChecked() or name not in all_t:
                continue
            cls = all_t[name]
            ranges = {}
            for pname, (smin, smax) in param_spins.items():
                ranges[pname] = (smin.value(), smax.value())
            specs.append((cls, ranges))
        return specs

    def _run_augment(self):
        self._ensure_boxes_loaded()
        if not self._run_images:
            self._log(tr("log_no_images"))
            self._pipe_finish(True)
            return
        specs = self._get_transform_specs()
        if not specs:
            self._pipe_finish(True)
            return
        ratio = self._aug_ratio.value()
        mode = "all" if self._aug_mode.currentIndex() == 0 else "random"
        include_original = self._aug_inc_orig.isChecked()
        output_dir = self._get_output_dir()
        transform_names = [name for name, (cb, _, _) in self._aug_widgets.items()
                          if cb.isChecked() and not name.startswith("__")]
        self._log(tr("log_aug_start").format(
            count=len(self._run_images),
            transforms=", ".join(transform_names) if transform_names else tr("原图"),
            ratio=ratio
        ))
        self._button_busy(self._aug_btn, clear_btn=self._aug_clear_btn)
        total = len(self._run_images)
        self._interrupted = False

        def _aug_task(log_fn, progress_fn):
            def _on_transform_progress(tname, cur, tot):
                display = TRANSFORM_META.get(tname, (tname,))[0]
                progress_fn(cur, total, tr(display))
            aug = Augmenter(
                output_dir,
                on_progress=lambda c, t: None,
                is_interrupted=lambda: self._interrupted,
                on_transform_progress=_on_transform_progress,
            )
            return aug.run(self._run_images, self._run_boxes, specs, ratio, mode,
                          include_original=include_original)

        def _on_finished(result):
            self._augment_result = result
            aug_count = len(result) if result else 0
            self._log(tr("log_aug_done").format(aug_count=aug_count, total=aug_count))
            self._button_ready(self._aug_btn, clear_btn=self._aug_clear_btn)
            self._pipe_finish()
        def _on_error(err):
            self._log(tr("log_aug_err").format(err=err))
            self._augment_result = None
            self._button_ready(self._aug_btn, clear_btn=self._aug_clear_btn)
            self._pipe_finish(True)
        self._worker = Worker(_aug_task)
        self._worker.progress.connect(lambda *a: None)
        self._worker.finished.connect(_on_finished)
        self._worker.error.connect(_on_error)
        self._worker.start()

    def _run_export(self):
        self._ensure_boxes_loaded()
        if not self._run_images:
            self._log(tr("log_no_images"))
            self._pipe_finish(True)
            return
        labels = self._get_selected_labels()
        if not labels:
            self._log(tr("log_no_labels"))
            self._pipe_finish(True)
            return
        output_dir = self._get_output_dir()
        self._button_busy(self._exp_btn, clear_btn=self._exp_clear_btn)
        self._interrupted = False

        def _exp_task(log_fn, progress_fn):
            detected = self._detect_augmented_images()
            input_data = []
            if detected:
                aug_images, aug_boxes = detected
                output_dir_inner = os.path.join(output_dir, "images")
                json_count = sum(1 for f in os.listdir(output_dir_inner) if f.endswith('.json'))
                img_count = len(aug_images)
                if json_count != img_count:
                    log_fn(tr("log_split_count_mismatch").format(txt_count=json_count, img_count=img_count))
                    return
                for i, img_path in enumerate(aug_images):
                    w, h = self._get_image_size(img_path)
                    input_data.append({
                        "image": None,
                        "boxes": aug_boxes.get(i, []),
                        "width": w, "height": h,
                        "stem": os.path.splitext(os.path.basename(img_path))[0],
                        "img_path": img_path,
                    })
                log_fn(tr("log_aug_detected").format(count=img_count))
            else:
                for idx in range(len(self._run_images)):
                    w, h = self._get_image_size(self._run_images[idx])
                    input_data.append({
                        "image": None,
                        "boxes": self._run_boxes.get(idx, []),
                        "width": w, "height": h,
                        "stem": os.path.splitext(os.path.basename(self._run_images[idx]))[0],
                        "img_path": self._run_images[idx],
                    })
                log_fn(tr("log_orig_detected").format(count=len(input_data)))
            if not input_data:
                log_fn(tr("log_no_images"))
                return
            log_fn(tr("log_exp_start").format(
                count=len(input_data),
                labels=", ".join(labels),
            ))
            exp = YoloExporter(
                output_dir,
                on_progress=lambda c, t: progress_fn(c, t, ""),
                is_interrupted=lambda: self._interrupted,
            )
            exp.run(
                self._run_images,
                self._run_boxes,
                labels,
                skip_empty=self._exp_skip_empty.isChecked(),
                input_data=input_data
            )

        def _on_finished(_):
            self._log(tr("log_exp_done").format(path=output_dir))
            self._button_ready(self._exp_btn, clear_btn=self._exp_clear_btn)
            self._pipe_finish()
        def _on_error(err):
            self._log(tr("log_exp_err").format(err=err))
            self._button_ready(self._exp_btn, clear_btn=self._exp_clear_btn)
            self._pipe_finish(True)
        self._worker = Worker(_exp_task)
        self._worker.log.connect(self._log)
        self._worker.progress.connect(lambda *a: None)
        self._worker.finished.connect(_on_finished)
        self._worker.error.connect(_on_error)
        self._worker.start()

    def _on_split_changed(self, changed_key):
        others = [k for k in SPLIT_KEYS if k != changed_key]
        other_sum = sum(getattr(self, f"_split_{k}").value() for k in others)
        sb = getattr(self, f"_split_{changed_key}")
        new_val = sb.value()
        max_val = round(1.0 - other_sum, 2)
        if new_val > max_val:
            sb.blockSignals(True)
            sb.setValue(max(0.0, max_val))
            sb.blockSignals(False)

    def _run_split(self):
        self._ensure_boxes_loaded()
        if not self._run_images:
            self._log(tr("log_no_images"))
            self._pipe_finish(True)
            return
        output_dir = self._get_output_dir()
        labels_dir = os.path.join(output_dir, "labels")
        images_dir = os.path.join(output_dir, "images")
        txt_files = [f for f in os.listdir(labels_dir) if f.endswith('.txt')] if os.path.isdir(labels_dir) else []
        if not txt_files:
            self._log(tr("log_split_no_labels"))
            self._pipe_finish(True)
            return
        aug_jpgs = [f for f in os.listdir(images_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png'))] if os.path.isdir(images_dir) else []
        txt_count = len(txt_files)
        if aug_jpgs:
            img_count = len(aug_jpgs)
            if img_count > txt_count:
                self._log(tr("log_split_aug_gt_txt").format(img_count=img_count, txt_count=txt_count))
            elif img_count < txt_count:
                self._log(tr("log_split_aug_lt_txt").format(img_count=img_count, txt_count=txt_count))
            split_images, split_boxes = self._detect_augmented_images()
            txt_bases = {os.path.splitext(f)[0] for f in txt_files}
            filtered = []
            filtered_boxes = {}
            for i, img_path in enumerate(split_images):
                base = os.path.splitext(os.path.basename(img_path))[0]
                if base in txt_bases:
                    new_idx = len(filtered)
                    filtered.append(img_path)
                    filtered_boxes[new_idx] = split_boxes.get(i, [])
            split_images = filtered
            split_boxes = filtered_boxes
        else:
            src_bases = {os.path.splitext(os.path.basename(p))[0]: i
                         for i, p in enumerate(self._run_images)}
            txt_bases = {os.path.splitext(f)[0] for f in txt_files}
            matched_bases = [b for b in txt_bases if b in src_bases]
            if not matched_bases:
                self._log(tr("log_split_no_labels"))
                self._pipe_finish(True)
                return
            self._log(tr("log_aug_detected").format(count=len(matched_bases)))
            split_images = []
            split_boxes = {}
            for i, b in enumerate(matched_bases):
                orig_idx = src_bases[b]
                split_images.append(self._run_images[orig_idx])
                split_boxes[i] = self._run_boxes.get(orig_idx, [])
        ratios = {k: getattr(self, f"_split_{k}").value() for k in SPLIT_KEYS}
        total = len(split_images)
        train_n = int(total * ratios["train"])
        val_n = int(total * ratios["val"])
        test_n = int(total * ratios["test"])
        rest = total - train_n - val_n - test_n
        if rest > 0:
            train_n += rest
        self._log(tr("log_split_start").format(total=total, train=train_n, val=val_n, test=test_n))
        self._button_busy(self._split_btn, clear_btn=self._split_clear_btn)
        self._interrupted = False

        def _split_task(log_fn, progress_fn):
            sp = Splitter(
                output_dir,
                on_progress=lambda c, t: progress_fn(c, t, ""),
                is_interrupted=lambda: self._interrupted,
            )
            sp.run(split_images, split_boxes, ratios)

        def _on_finished(_):
            self._log(tr("log_split_done").format(train=train_n, val=val_n, test=test_n))
            self._button_ready(self._split_btn, clear_btn=self._split_clear_btn)
            self._pipe_finish()
        def _on_error(err):
            self._log(tr("log_split_err").format(err=err))
            self._button_ready(self._split_btn, clear_btn=self._split_clear_btn)
            self._pipe_finish(True)
        self._worker = Worker(_split_task)
        self._worker.progress.connect(lambda *a: None)
        self._worker.finished.connect(_on_finished)
        self._worker.error.connect(_on_error)
        self._worker.start()

    def _run_pipeline(self):
        steps = [s for s in ["augment", "export", "split"]
                 if getattr(self, {"augment": "_pipe_aug",
                                   "export": "_pipe_exp",
                                   "split": "_pipe_split"}[s]).isChecked()]
        if len(steps) < 2:
            return
        self._augment_result = None
        self._interrupted = False
        self._pipe_mode = True
        self._pipe_steps = list(steps)
        self._pipe_idx = 0
        self._pipe_error = False
        self._pipe_next()

    def _pipe_next(self):
        if self._pipe_error or self._interrupted or self._pipe_idx >= len(self._pipe_steps):
            self._pipe_finish(self._pipe_error)
            return
        step = self._pipe_steps[self._pipe_idx]
        self._pipe_idx += 1
        getattr(self, f"_run_{step}")()

    def _pipe_finish(self, error=False):
        if error:
            self._pipe_error = True
        if self._pipe_idx >= len(self._pipe_steps) or self._pipe_error or self._interrupted:
            if self._interrupted:
                self._log(tr("已中断"))
            self._pipe_mode = False
            self._pipe_steps = []
            self._pipe_idx = 0
            self._pipe_error = False
            self._augment_result = None
            self._interrupted = False
        else:
            QTimer.singleShot(50, self._pipe_next)
