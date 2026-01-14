#!/bin/bash

# 打包脚本：生成无控制台、带图标的可执行文件
echo "开始打包应用程序..."

# 使用PyInstaller打包，添加优化选项以减少可执行文件大小
python -m PyInstaller \
    -F \
    -w \
    -n PasteLabel \
    --icon=ico_image/icoo.png \
    --add-data "ico_image;ico_image" \
    --clean \
    --noconfirm \
    --python-option=-O2 \
    image_editor.py

if [ $? -eq 0 ]; then
    echo "打包完成！可执行文件位于：dist/PasteLabel.exe"
    echo "应用程序特性："
    echo "- 无控制台窗口"
    echo "- 应用图标为 ico_image/icoo.png"
    echo "- 包含ico_image文件夹中的所有图片"
    echo "- 包含所有必要依赖"
else
    echo "打包失败，请检查错误信息。"
    exit 1
fi
