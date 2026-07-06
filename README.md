# PasteLabel

PasteLabel 是一个基于 PyQt5 的图像标注工具，支持**贴图合成**和**检测框标注**（LabelMe 格式），有效解决样本采集困难的问题。

![界面展示](./ico_image/demo.png)

---

## 支持平台

**Windows 10+** · **Linux (x86_64)**

## 功能特性

### 核心标注
- **贴图合成** — 单张/批量放置贴图，支持随机避让算法放置
- **检测框标注** — LabelMe 格式 JSON 输出，16 色自动分配
- **贴图/标注模式切换** — 切换鼠标交互优先级（悬停高亮 + 点击优先级反转）
- **标签管理** — 全局标签列表，支持增删改，级联更新所有图片 JSON

### 图片管理
- **工作/移除路径** — 移除图片到 `_delete_` 文件夹，支持恢复
- **拖拽操作** — 拖入图片/JSON 上传，拖出画布复制文件
- **记忆** — 自动记录最近 10 组背景图/贴图/标签路径组合，保存工作状态
- **自动保存** — 切图时静默保存合成图 + JSON

### 编辑能力
- **Undo/Redo** — 双栈撤销重做，最多 50 条历史
- **网格辅助线** — 可调间距/线宽/透明度，深色主题下自动适配
- **背景缩放** — 滚轮缩放（0.5x ~ 3.0x），Ctrl+F 适应视图
- **右键菜单** — 画布/贴图/检测框各有独立右键操作

### 界面体验
- **深色/浅色主题** — 一键切换，DWM API 同步 Windows 标题栏
- **中英文切换** — 全界面 + 弹窗按钮同步本地化
- **快捷键自定义** — 20+ 快捷键可在设置中修改
- **标签统计** — 实时统计背景图标签/贴图标签数量
- **全局异常捕获** — 崩溃日志自动写入 `crash_log.txt`

---

## 源码运行

### 依赖

```bash
pip install PyQt5 opencv-python pyinstaller
```

Windows 深色标题栏依赖 `ffi.dll`。使用 `conda` 环境时，该文件通常在：

```text
<conda_env>/Library/bin/ffi.dll
```

### 运行

```bash
python PasteY/main.py
```

## 项目结构

```
PasteLabel/
├── PasteY/                    # 主代码包
│   ├── main.py                # 程序入口
│   ├── canvas/                # 画布模块
│   │   ├── canvas.py          # 画布控件（继承链中枢）
│   │   ├── canvas_renderer.py # 渲染（背景/贴图/检测框/网格）
│   │   ├── canvas_interaction.py # 鼠标交互（点击/拖拽/缩放/悬停）
│   │   ├── canvas_drawing.py  # 检测框绘制模式
│   │   └── canvas_menu.py     # 右键菜单（贴图/检测框/背景）
│   ├── ui/                    # 界面模块
│   │   ├── main_window.py     # 主窗口（状态管理/主题/快捷键/视图切换）
│   │   ├── ui_builder.py      # UI 构建（工具栏/面板/列表）
│   │   ├── dialogs.py         # 标签选择对话框
│   │   ├── handy_dialog.py    # 记忆记录弹窗
│   │   ├── settings_dialog.py # 设置对话框（快捷键/前缀/网格）
│   │   ├── segmented_control.py # 分段按钮（贴图/标注模式滑动切换）
│   │   ├── theme.py           # 深色/浅色主题（40+ 色值/完整 QSS）
│   │   ├── i18n.py            # 中英文国际化（148 键值对）
│   │   └── dwm.py             # Windows DWM 标题栏颜色同步
│   ├── engine/                # 业务逻辑
│   │   ├── paste_engine.py    # 贴图引擎（随机避让/批量/清空）
│   │   ├── image_loader.py    # 图片加载（LRU 缓存/自然排序/JSON 解析）
│   │   ├── label_manager.py   # 标签管理（增删改/级联更新/统计列表）
│   │   ├── save_manager.py    # 保存管理（合成/LabelMe JSON/自动保存）
│   │   ├── undo_manager.py    # 撤销/重做（双栈 50 条）
│   │   └── event_handler.py   # 事件处理（快捷键/翻页/绘制模式）
│   ├── core/                  # 核心配置
│   │   ├── config.py          # 配置常量（快捷键/颜色/参数）
│   │   ├── config_manager.py  # 配置持久化（~/.pastelabel.json）
│   │   ├── utils.py           # 工具函数（IoU/排序/缩略图/路径）
│   │   ├── editor_protocol.py # 编辑器接口协议
│   │   └── exception_hook.py  # 全局异常捕获 → crash_log.txt
├── tests/                     # 单元测试（55 用例）
├── ico_image/                 # 图标资源
├── user_guide.md              # 用户使用指南
├── README.md                  # 项目说明
└── LICENSE                    # MIT 许可证
```

## 测试

```bash
pip install pytest pytest-qt
pytest tests/ -v
```

## 许可证

MIT License

Copyright (c) 2026 Zomcxj
