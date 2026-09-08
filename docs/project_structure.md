# 项目结构

[返回 README](../README.md)

```
PasteLabel/
├── .gitattributes             # 文本属性（Shell 脚本使用 LF）
├── .gitignore                 # Git 忽略规则
├── .python-version            # 项目 Python 版本锚点
├── build.sh                   # 跨平台 PyInstaller 构建脚本
├── paste_label.txt            # 默认贴图标签文件
├── requirements.txt           # 运行期依赖
├── requirements-dev.txt       # 开发与测试依赖
├── requirements-build.txt     # PyInstaller 构建依赖
├── README.md                  # 项目说明
├── LICENSE                    # MIT 许可证
├── ico_image/                 # 图标、演示图和字体资源
├── .github/
│   └── workflows/
│       ├── build.yml          # 发布构建工作流
│       └── test.yml           # 测试工作流
├── pastelabel/                # 主代码包
│   ├── __init__.py
│   ├── main.py                # 程序入口
│   ├── PasteLabel.spec        # PyInstaller spec
│   ├── sip.py                 # PyInstaller 的 PyQt5 SIP 兼容模块
│   ├── canvas/                # 画布绘制与交互
│   │   ├── __init__.py
│   │   ├── canvas.py
│   │   ├── canvas_drawing.py
│   │   ├── canvas_interaction.py
│   │   ├── canvas_menu.py
│   │   └── canvas_renderer.py
│   ├── core/                  # 配置、工具与异常处理
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── config_manager.py
│   │   ├── editor_protocol.py
│   │   ├── exception_hook.py
│   │   └── utils.py
│   ├── engine/                # 图片、标签、保存、事件与数据处理
│   │   ├── __init__.py
│   │   ├── base_exporter.py
│   │   ├── coco_exporter.py
│   │   ├── dataset_classifier.py
│   │   ├── event_handler.py
│   │   ├── image_loader.py
│   │   ├── label_manager.py
│   │   ├── paste_engine.py
│   │   ├── save_manager.py
│   │   ├── splitter.py
│   │   ├── undo_manager.py
│   │   ├── voc_exporter.py
│   │   ├── yolo_exporter.py
│   │   └── augmenter/
│   │       ├── __init__.py
│   │       ├── base.py
│   │       ├── color.py
│   │       ├── flipt.py
│   │       ├── noise.py
│   │       ├── rotate.py
│   │       ├── scale.py
│   │       └── translate.py
│   ├── ui/                    # 主窗口、对话框、主题与国际化
│   │   ├── __init__.py
│   │   ├── dialog_helpers.py
│   │   ├── dialogs.py
│   │   ├── dwm.py
│   │   ├── i18n.py
│   │   ├── icons.py           # SVG 图标常量与渲染辅助函数
│   │   ├── main_window.py     # ImageEditor 协调器
│   │   ├── memory_dialog.py
│   │   ├── processing_panel.py # ProcessingPanel 执行与日志逻辑
│   │   ├── segmented_control.py
│   │   ├── settings_dialog.py
│   │   ├── theme.py
│   │   ├── ui_builder.py      # UI 构建 mixin 兼容组合壳
│   │   └── mixins/
│   │       ├── __init__.py
│   │       ├── background_list.py
│   │       ├── cache_menu.py
│   │       ├── dataset_classifier.py
│   │       ├── label_cache_slot.py
│   │       ├── lists.py
│   │       ├── memory_record.py
│   │       ├── options_popup.py
│   │       ├── panels.py
│   │       ├── processing_panel_builder.py
│   │       ├── stats.py
│   │       ├── theme.py
│   │       ├── toolbar.py
│   │       └── translation.py
│   └── widgets/               # 可复用 Qt 控件
│       ├── canvas_adjustment.py
│       ├── drag_out_list.py
│       ├── hover_menu.py
│       ├── hover_popup.py
│       ├── processing.py      # 扫描提示、Worker 与折叠区控件
│       └── spinner.py
├── tests/                     # pytest 回归测试
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_canvas_interaction_regressions.py
│   ├── test_canvas_menu_regressions.py
│   ├── test_canvas_renderer_regressions.py
│   ├── test_config.py
│   ├── test_config_manager.py
│   ├── test_dataset_classifier.py
│   ├── test_dialogs_regressions.py
│   ├── test_documentation_regressions.py
│   ├── test_i18n_regressions.py
│   ├── test_label_cache_multi_select_red.py
│   ├── test_background_label_scan.py # ProcessingPanel/background scan regression
│   ├── test_theme_style_consolidation.py
│   ├── test_silent_interaction_theme.py
│   ├── test_ui_layout_regressions.py
│   └── ...                     # 其他领域回归测试
└── docs/
    ├── project_structure.md   # 本文档
    ├── settings_guide.md      # 设置指南
    └── user_guide.md          # 用户使用指南
```
```
运行时文件（不属于仓库源码树）：
└── ~/pastelabel.log          # 未处理异常和 Qt 消息日志
```

运行时日志写入用户主目录 `~/pastelabel.log`，不属于仓库源码树中的持久文件。
