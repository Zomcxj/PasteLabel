"""④ B 组借鉴功能测试：一键重置设置 + CLI 入口。"""
import inspect
import json
import sys
from pathlib import Path

import pytest

from pastelabel.core import config as config_module
from pastelabel.core import config_manager
from pastelabel.ui import i18n
from pastelabel.ui.main_window import _parse_args

ROOT = Path(__file__).resolve().parents[1]
SETTINGS_SRC = ROOT / "pastelabel" / "ui" / "settings_dialog.py"
MAIN_WINDOW_SRC = ROOT / "pastelabel" / "ui" / "main_window.py"
MAIN_SRC = ROOT / "pastelabel" / "main.py"


@pytest.fixture
def temp_config(tmp_path, monkeypatch):
    path = tmp_path / "pastelabel.json"
    monkeypatch.setattr(config_manager, "CONFIG_PATH", str(path))
    yield path


# ---------- B-1 config.reset_defaults ----------

def test_reset_defaults_restores_mutated_config_dicts():
    original = dict(config_module.GRID_CONFIG)
    try:
        config_module.GRID_CONFIG["line_width"] = 99
        config_module.GRID_CONFIG["alpha"] = 1
        config_module.DETECTION_BOX_CONFIG["label_font_size"] = 42
        config_module.NUDGE_CONFIG["step"] = 5

        config_module.reset_defaults()

        assert config_module.GRID_CONFIG == original
        assert config_module.DETECTION_BOX_CONFIG["label_font_size"] == 9
        assert config_module.NUDGE_CONFIG["step"] == 1
    finally:
        config_module.reset_defaults()


def test_reset_defaults_snapshot_is_not_aliased():
    """快照必须和运行时字典是两份对象，否则重置无效。"""
    for name, snapshot in config_module._DEFAULT_SNAPSHOT.items():
        target = getattr(config_module, name)
        assert snapshot is not target, name


def test_reset_defaults_covers_the_mutated_config_dicts():
    for name in ("GRID_CONFIG", "DETECTION_BOX_CONFIG", "NUDGE_CONFIG",
                 "MAGNIFIER_CONFIG", "CROSSHAIR_CONFIG", "BOX_BORDER_CONFIG",
                 "DETECTION_BOX_WHEEL_CONFIG", "SHORTCUT_CONFIG"):
        assert name in config_module._DEFAULT_SNAPSHOT, name


# ---------- B-1 config_manager.reset_all ----------

def test_reset_all_deletes_the_config_file(temp_config):
    temp_config.write_text(json.dumps({"theme": "dark"}), encoding="utf-8")

    assert config_manager.reset_all() is True
    assert not temp_config.exists()


def test_reset_all_succeeds_when_config_file_is_absent(temp_config):
    assert not temp_config.exists()

    assert config_manager.reset_all() is True


def test_reset_all_restores_in_memory_defaults(temp_config):
    config_module.GRID_CONFIG["line_width"] = 77
    temp_config.write_text(json.dumps({"grid_line_width": 77}), encoding="utf-8")

    config_manager.reset_all()

    assert config_module.GRID_CONFIG["line_width"] == 1


def test_reset_all_drops_custom_theme_language_and_shortcuts(temp_config):
    config_manager.save_all(theme="dark", language="en")
    config_manager.save_shortcuts({"undo": "Ctrl+Q"})

    config_manager.reset_all()

    loaded = config_manager.load_all()
    assert loaded["theme"] == "light"
    assert loaded["language"] == "zh"
    assert loaded["shortcuts"]["undo"] == "Ctrl+Z"


def test_reset_all_removes_memory_records(temp_config):
    config_manager.upsert_memory_record({"background_path": "C:/data", "paste_path": "", "label_path": ""})
    assert config_manager.load_memory_records()

    config_manager.reset_all()

    assert config_manager.load_memory_records() == []


# ---------- B-1 settings dialog button ----------

def test_settings_dialog_has_a_reset_button_with_confirmation():
    source = SETTINGS_SRC.read_text(encoding="utf-8")
    assert "self.reset_all_btn = QPushButton(tr(\"恢复默认设置\"))" in source
    assert "self.reset_all_btn.clicked.connect(self._reset_all_settings)" in source
    # 必须二次确认，避免误触清空配置
    assert "question(" in source
    assert "QMessageBox.Yes" in source


def test_reset_button_uses_the_danger_style():
    source = SETTINGS_SRC.read_text(encoding="utf-8")
    block = source[source.index("self.reset_all_btn = QPushButton("):]
    block = block[:block.index("self.reset_all_btn.clicked.connect")]
    assert 'setObjectName("dangerBtn")' in block


def test_reset_button_is_placed_at_the_bottom_left_of_the_dialog():
    """按钮必须在底部按钮行里、且排在保存/取消之前（左下角）。"""
    source = SETTINGS_SRC.read_text(encoding="utf-8")
    block = source[source.index("btn_layout = QHBoxLayout()"):source.index("layout.addLayout(btn_layout)")]
    assert "btn_layout.addWidget(self.reset_all_btn)" in block
    assert block.index("btn_layout.addWidget(self.reset_all_btn)") < block.index('QPushButton(tr("保存"))')
    # 重置按钮后紧跟 stretch，才会贴左边
    assert block.index("btn_layout.addWidget(self.reset_all_btn)") < block.index("btn_layout.addStretch()")


def test_both_settings_pages_align_their_first_row():
    """快捷键页与参数页的第一行必须处在同一高度。"""
    source = SETTINGS_SRC.read_text(encoding="utf-8")
    # 两页 group 的边距都要显式设为同一组值
    assert source.count("setContentsMargins(19, 14, 9, 9)") == 2
    # 快捷键页里 scroll 内容不能再叠加一层边距，否则首行会下移
    assert "scroll_layout.setContentsMargins(0, 0, 0, 0)" in source


def test_editor_exposes_reset_settings_to_default():
    from pastelabel.ui.main_window import ImageEditor
    assert hasattr(ImageEditor, "reset_settings_to_default")


def test_reset_settings_to_default_reloads_and_refreshes(temp_config, monkeypatch):
    """reset 后必须重新加载设置并刷新界面，不能只删文件。"""
    source = inspect.getsource(
        __import__("pastelabel.ui.main_window", fromlist=["ImageEditor"]).ImageEditor.reset_settings_to_default
    )
    assert "config_manager.reset_all()" in source
    assert "self._load_settings()" in source
    assert "self._apply_theme()" in source
    assert "self._refresh_ui_texts()" in source


# ---------- B-2 CLI ----------

def test_cli_parses_directory_positional():
    args = _parse_args(["D:/data"])
    assert args.path == "D:/data"
    assert args.labels is None


def test_cli_parses_labels_option():
    args = _parse_args(["D:/data", "--labels", "labels.txt"])
    assert args.path == "D:/data"
    assert args.labels == "labels.txt"


def test_cli_accepts_labels_without_directory():
    args = _parse_args(["--labels", "labels.txt"])
    assert args.path is None
    assert args.labels == "labels.txt"


def test_cli_defaults_are_empty():
    args = _parse_args([])
    assert args.path is None
    assert args.labels is None
    assert args.version is False


def test_cli_version_flag():
    args = _parse_args(["--version"])
    assert args.version is True


def test_cli_rejects_unknown_option():
    with pytest.raises(SystemExit):
        _parse_args(["--nope"])


def test_main_window_applies_startup_args():
    from pastelabel.ui.main_window import ImageEditor
    source = inspect.getsource(ImageEditor.apply_startup_args)
    assert "load_background_folder" in source
    assert "load_background_label_file" in source
    # 路径不存在时给状态栏提示，不能静默失败
    assert "路径不存在" in source


def test_apply_startup_args_ignores_missing_paths():
    class Editor:
        def __init__(self):
            self.status_label = type("L", (), {"texts": [], "setText": lambda self, t: self.texts.append(t)})()
            self.folder_calls = []
            self.label_calls = []

        def load_background_folder(self, p):
            self.folder_calls.append(p)

        def load_background_label_file(self, p):
            self.label_calls.append(p)

    from pastelabel.ui.main_window import ImageEditor

    editor = Editor()
    ImageEditor.apply_startup_args(editor, "Z:/definitely/missing/dir", "Z:/missing.txt")

    assert editor.folder_calls == []
    assert editor.label_calls == []
    assert len(editor.status_label.texts) == 2


def test_apply_startup_args_loads_existing_paths(tmp_path):
    folder = tmp_path / "bg"
    folder.mkdir()
    labels = tmp_path / "labels.txt"
    labels.write_text("cat\n", encoding="utf-8")

    class Editor:
        def __init__(self):
            self.status_label = type("L", (), {"setText": lambda self, t: None})()
            self.folder_calls = []
            self.label_calls = []

        def load_background_folder(self, p):
            self.folder_calls.append(p)

        def load_background_label_file(self, p):
            self.label_calls.append(p)

    from pastelabel.ui.main_window import ImageEditor

    editor = Editor()
    ImageEditor.apply_startup_args(editor, str(folder), str(labels))

    assert editor.folder_calls == [str(folder)]
    assert editor.label_calls == [str(labels)]


def test_main_entry_point_parses_args_before_creating_qapplication():
    source = MAIN_WINDOW_SRC.read_text(encoding="utf-8")
    block = source[source.index("def main():"):]
    assert "_parse_args(sys.argv[1:])" in block
    assert block.index("_parse_args(sys.argv[1:])") < block.index("QApplication(")
    assert "editor.apply_startup_args(args.path, args.labels)" in block


def test_main_module_still_delegates_to_ui_main():
    source = MAIN_SRC.read_text(encoding="utf-8")
    assert "from pastelabel.ui.main_window import main" in source


def test_cli_help_text_is_not_empty():
    import argparse
    from pastelabel.ui.main_window import _parse_args
    parser_source = inspect.getsource(_parse_args)
    assert "argparse" in parser_source
    assert "--labels" in parser_source
