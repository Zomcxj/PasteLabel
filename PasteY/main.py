"""
贴图标注工具 - 主程序入口
"""
import sys
import os

# 安装全局异常钩子（必须在导入 PyQt5 之前）
from .core.exception_hook import install_exception_hook
install_exception_hook()

# 将项目根目录加入系统路径
if not getattr(sys, 'frozen', False):
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

from .ui.main_window import main

if __name__ == "__main__":
    main()
