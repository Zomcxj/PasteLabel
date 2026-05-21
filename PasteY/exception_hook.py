"""
全局异常捕获模块 - 捕获所有未处理的 Python 异常并写入日志文件
"""
import sys
import os
import traceback
from datetime import datetime


LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "crash_log.txt")


def _write_log(message):
    """写入日志文件"""
    try:
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"[{timestamp}] {message}\n")
    except Exception:
        pass  # 无法写入日志时忽略


def _qt_message_handler(mode, context, message):
    """Qt 消息处理器 - 捕获 Qt 级别的警告/错误"""
    _write_log(f"Qt [{mode}]: {message}")


def install_exception_hook():
    """安装全局异常钩子"""
    sys.excepthook = exception_hook
    # 安装 Qt 消息处理器
    try:
        from PyQt5.QtCore import qInstallMessageHandler
        qInstallMessageHandler(_qt_message_handler)
    except Exception:
        pass


def exception_hook(exctype, value, tb):
    """全局异常处理"""
    error_msg = "".join(traceback.format_exception(exctype, value, tb))
    _write_log(f"未捕获的异常:\n{error_msg}")
    
    # 尝试使用 QMessageBox 显示错误
    try:
        from PyQt5.QtWidgets import QMessageBox, QApplication
        app = QApplication.instance()
        if app:
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Critical)
            msg_box.setWindowTitle("程序错误")
            msg_box.setText("程序遇到意外错误，错误信息已保存到 crash_log.txt")
            msg_box.setDetailedText(error_msg)
            msg_box.exec_()
    except Exception:
        pass
    
    # 调用原始的 excepthook
    sys.__excepthook__(exctype, value, tb)
