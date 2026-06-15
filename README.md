# PasteLabel

PasteLabel 是一个基于 PyQt5 的图像标注工具，支持**贴图**（合成）和**检测框**（LabelMe 格式）标注，有效解决样本采集困难的问题。

![界面展示](./ico_image/demo.png)

---

## 支持平台

**Windows 10+** · **Linux (x86_64)**

> 可使用 `PasteY/build.sh` 在对应平台自行构建。

📖 详细使用教程请参阅 [用户指南](./user_guide.md)

## 源码运行

### 依赖库

```bash
pip install PyQt5 opencv-python
```

### 运行

```bash
python PasteY/main.py
```

## 项目结构

```
PasteLabel/
├── PasteY/                # 模块化代码包
│   ├── main.py            # 程序入口
│   ├── main_window.py     # 主窗口逻辑
│   ├── widgets.py         # 自定义控件（画布）
│   ├── label_manager.py   # 标签管理
│   ├── save_manager.py    # 保存管理
│   ├── config.py          # 配置常量
│   ├── utils.py           # 工具函数
│   ├── models.py          # 数据模型
│   ├── dialogs.py         # 对话框
│   ├── styles.py          # 样式管理
│   ├── theme.py           # 主题管理（深色/浅色）
│   ├── exception_hook.py  # 全局异常捕获
│   ├── build.sh           # 构建脚本（PyInstaller）
│   ├── PasteLabel.spec    # PyInstaller 配置文件
│   ├── __init__.py        # 包初始化
│   └── tests/             # 单元测试
├── PasteX/                # 旧版单文件版本（归档）
├── images/                # 样本图片数据
├── ico_image/             # 图标资源
├── paste_label.txt        # 贴图标签文件
├── conftest.py            # pytest 配置（mock PyQt5）
├── README.md              # 项目说明
├── LICENSE                # MIT 许可证
└── .gitignore
```

## 测试

```bash
# 安装测试依赖
pip install pytest

# 运行测试
pytest PasteY/tests/ -v
```

## 许可证

遵循MIT

Copyright © 2026 Zomcxj
