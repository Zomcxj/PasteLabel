"""A compact panel docked at the bottom-left of the canvas.

It groups three sliders that let the user fine tune how the annotations and the
underlying image are displayed:

- ``Opacity``    : transparency of the labels/shapes (0-100%, default 100%).
- ``Brightness`` : brightness of the image (slider 0-150, displayed as a
  0.00-3.00 factor, neutral 1.00).
- ``Contrast``   : contrast of the image, same range/mapping as brightness.
"""

from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QSize
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QSlider, QPushButton, QToolButton
)


class CanvasAdjustmentWidget(QWidget):
    """Three-slider panel for label opacity, image brightness and contrast."""

    opacity_changed = pyqtSignal(int)
    brightness_contrast_changed = pyqtSignal(int, int)
    geometry_changed = pyqtSignal()

    SLIDER_WIDTH = 120
    BC_UPDATE_INTERVAL_MS = 33

    OPACITY_MIN = 0
    OPACITY_MAX = 100
    OPACITY_DEFAULT = 100

    BC_MIN = 0
    BC_MAX = 150
    BC_DEFAULT = 50

    _LABEL_CSS = (
        "QLabel { color: #333; font-size: 11px; background: transparent; }"
    )
    _TITLE_CSS = (
        "QLabel { color: #333; font-size: 11px; font-weight: 600;"
        " background: transparent; }"
    )
    _RESET_CSS = (
        "QPushButton { background: rgba(120, 120, 120, 60);"
        " border-radius: 3px; font-size: 11px; color: #333; padding: 0; }"
        "QPushButton:hover { background: rgba(120, 120, 120, 110); }"
        "QPushButton:pressed { background: rgba(120, 120, 120, 150); }"
    )

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("canvas_adjustment")
        self._collapsed = False
        self.setProperty("collapsed", False)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet(self._build_stylesheet())

        layout = QVBoxLayout()
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(5)

        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        self.title_label = QLabel(self.tr("Canvas Display"))
        self.title_label.setStyleSheet(self._TITLE_CSS)
        self.toggle_button = QToolButton()
        self.toggle_button.setText("▲")
        self.toggle_button.setFixedSize(20, 20)
        self.toggle_button.setToolTip(self.tr("Collapse adjustments"))
        self.toggle_button.setFocusPolicy(Qt.NoFocus)
        self.toggle_button.setStyleSheet(
            "QToolButton { background: transparent; border: none;"
            " border-radius: 3px; padding: 4px; }"
            "QToolButton:hover { background: rgba(120, 120, 120, 60); }"
            "QToolButton:pressed { background: rgba(120, 120, 120, 100); }"
        )
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.toggle_button)
        layout.addLayout(header_layout)

        self.content_widget = QWidget()
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(5)
        self.content_widget.setLayout(content_layout)

        self.opacity_slider, self.opacity_value_label = self._build_row(
            content_layout,
            self.tr("Opacity"),
            self.OPACITY_MIN,
            self.OPACITY_MAX,
            self.OPACITY_DEFAULT,
            self.tr(
                "Adjust the transparency of annotation shapes and masks. "
                "Label text remains fully visible."
            ),
            display="percent",
        )
        self.brightness_slider, self.brightness_value_label = self._build_row(
            content_layout,
            self.tr("Brightness"),
            self.BC_MIN,
            self.BC_MAX,
            self.BC_DEFAULT,
            self.tr("Adjust the brightness of the underlying image."),
            display="factor",
        )
        self.contrast_slider, self.contrast_value_label = self._build_row(
            content_layout,
            self.tr("Contrast"),
            self.BC_MIN,
            self.BC_MAX,
            self.BC_DEFAULT,
            self.tr("Adjust the contrast of the underlying image."),
            display="factor",
        )
        layout.addWidget(self.content_widget)

        self.setLayout(layout)
        self.adjustSize()

        self._bc_update_timer = QTimer(self)
        self._bc_update_timer.setSingleShot(True)
        self._bc_update_timer.setInterval(self.BC_UPDATE_INTERVAL_MS)
        self._bc_update_timer.timeout.connect(self._emit_bc_changed)

        self.toggle_button.clicked.connect(self._toggle_collapsed)
        self.opacity_slider.valueChanged.connect(self._on_opacity_changed)
        self.brightness_slider.valueChanged.connect(self._on_bc_changed)
        self.contrast_slider.valueChanged.connect(self._on_bc_changed)

    def _build_stylesheet(self):
        primary = "#0071e3"
        return f"""
        #canvas_adjustment {{
            background: rgba(255, 255, 255, 220);
            border: none;
            border-radius: 6px;
        }}
        #canvas_adjustment[collapsed="true"] {{
            background: transparent;
        }}
        #canvas_adjustment QSlider::groove:horizontal {{
            height: 4px;
            background: rgba(0, 0, 0, 55);
            border-radius: 2px;
        }}
        #canvas_adjustment QSlider::handle:horizontal {{
            background: {primary};
            border: none;
            width: 14px;
            height: 14px;
            margin: -5px 0;
            border-radius: 7px;
        }}
        #canvas_adjustment QSlider::sub-page:horizontal {{
            background: {primary};
            border-radius: 2px;
        }}
        """

    def _build_row(self, layout, title, minimum, maximum, default,
                   tooltip, display="percent"):
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(4)

        name_label = QLabel(title)
        name_label.setFixedWidth(64)
        name_label.setStyleSheet(self._LABEL_CSS)
        name_label.setToolTip(tooltip)

        slider = QSlider(Qt.Horizontal)
        slider.setRange(minimum, maximum)
        slider.setValue(default)
        slider.setFixedWidth(self.SLIDER_WIDTH)
        slider.setTracking(True)
        slider.setFocusPolicy(Qt.NoFocus)
        slider.setToolTip(tooltip)

        value_label = QLabel()
        value_label.setProperty("display", display)
        value_label.setFixedWidth(36)
        value_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        value_label.setStyleSheet(self._LABEL_CSS)
        value_label.setToolTip(tooltip)
        self._set_value_text(value_label, default)

        reset_btn = QPushButton("↺")
        reset_btn.setFixedSize(22, 20)
        reset_btn.setStyleSheet(self._RESET_CSS)
        reset_btn.setToolTip(self.tr("Reset to default"))
        reset_btn.setFocusPolicy(Qt.NoFocus)
        reset_btn.clicked.connect(
            lambda _=False, s=slider: s.setValue(default)
        )

        row.addWidget(name_label)
        row.addWidget(slider)
        row.addWidget(value_label)
        row.addWidget(reset_btn)
        layout.addLayout(row)
        return slider, value_label

    @staticmethod
    def _set_value_text(label, value):
        if label.property("display") == "factor":
            label.setText(f"{value / 50:.2f}")
        else:
            label.setText(f"{value}%")

    def _on_opacity_changed(self, value):
        self._set_value_text(self.opacity_value_label, value)
        self.opacity_changed.emit(value)

    def _on_bc_changed(self, _=None):
        self._set_value_text(
            self.brightness_value_label, self.brightness_slider.value()
        )
        self._set_value_text(
            self.contrast_value_label, self.contrast_slider.value()
        )
        if not self._bc_update_timer.isActive():
            self._bc_update_timer.start()

    def _emit_bc_changed(self):
        self.brightness_contrast_changed.emit(
            self.brightness_slider.value(), self.contrast_slider.value()
        )

    def _toggle_collapsed(self):
        self._collapsed = not self._collapsed
        self.setProperty("collapsed", self._collapsed)
        self.title_label.setVisible(not self._collapsed)
        self.content_widget.setVisible(not self._collapsed)
        margins = (4, 4, 4, 4) if self._collapsed else (10, 8, 10, 8)
        self.layout().setContentsMargins(*margins)
        icon = "▼" if self._collapsed else "▲"
        self.toggle_button.setText(icon)
        tooltip = (
            self.tr("Expand adjustments")
            if self._collapsed
            else self.tr("Collapse adjustments")
        )
        self.toggle_button.setToolTip(tooltip)
        self.style().unpolish(self)
        self.style().polish(self)
        self.layout().activate()
        self.adjustSize()
        self.geometry_changed.emit()

    def set_opacity(self, value):
        self.opacity_slider.blockSignals(True)
        self.opacity_slider.setValue(value)
        self.opacity_slider.blockSignals(False)
        self._set_value_text(self.opacity_value_label, value)

    def set_brightness_contrast(self, brightness, contrast):
        self._bc_update_timer.stop()
        for slider, value, label in (
            (self.brightness_slider, brightness, self.brightness_value_label),
            (self.contrast_slider, contrast, self.contrast_value_label),
        ):
            slider.blockSignals(True)
            slider.setValue(value)
            slider.blockSignals(False)
            self._set_value_text(label, value)
