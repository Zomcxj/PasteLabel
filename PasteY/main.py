"""
贴图标注工具 - 主程序入口
"""
import sys
import os

# 将项目根目录加入系统路径，确保 from PasteY.xxx 导入正常工作
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 安装全局异常钩子（必须在导入 PyQt5 之前）
from PasteY.exception_hook import install_exception_hook
install_exception_hook()

from PasteY.main_window import main

if __name__ == "__main__":
    main()
