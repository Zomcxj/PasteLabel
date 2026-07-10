"""全局异常提示回归测试。"""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_exception_dialog_uses_localized_ok_and_show_details_buttons():
    source = (ROOT / "pastelabel" / "core" / "exception_hook.py").read_text(encoding="utf-8")

    assert 'ok_button.setText(i18n.t("确定"))' in source
    assert 'msg_box.findChild(QPushButton, "qt_msgbox_details")' in source
    assert 'details_button.setText(i18n.t("显示详情"))' in source


def test_exception_log_uses_user_config_directory_and_pastelabel_name():
    source = (ROOT / "pastelabel" / "core" / "exception_hook.py").read_text(encoding="utf-8")

    assert 'config_manager.CONFIG_PATH' in source
    assert '"pastelabel.log"' in source
    assert 'crash_log.txt' not in source
