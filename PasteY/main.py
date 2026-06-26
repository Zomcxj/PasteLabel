"""
贴图标注工具 - 主程序入口
"""
import sys
import os

# 动态添加项目根目录到 sys.path，确保打包后也能找到 PasteY 包
if getattr(sys, 'frozen', False):
    # 打包后：exe 所在目录
    base_dir = os.path.dirname(sys.executable)
else:
    # 开发时：PasteY 的父目录
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)

# 安装全局异常钩子（必须在导入 PyQt5 之前）
from PasteY.core.exception_hook import install_exception_hook
install_exception_hook()

from PasteY.ui.main_window import main

if __name__ == "__main__":
    main()
