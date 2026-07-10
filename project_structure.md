# 项目结构

[返回 README](./README.md)

```
PasteLabel/
├── .gitattributes             # 文本属性（Shell 脚本使用 LF）
├── .gitignore                 # Git 忽略规则
├── build.sh                   # 跨平台 PyInstaller 构建脚本
├── conftest.py                # PyQt 测试环境配置
├── paste_label.txt            # 默认贴图标签文件
├── requirements.txt           # Python 依赖
├── sip.py                     # PyInstaller 的 PyQt5 SIP 兼容模块
├── README.md                  # 项目说明
├── user_guide.md              # 用户使用指南
├── project_structure.md       # 本文档
├── LICENSE                    # MIT 许可证
├── ico_image/                 # 图标、演示图和字体资源
├── pastelabel/                # 主代码包
│   ├── __init__.py
│   ├── main.py                # 程序入口
│   ├── PasteLabel.spec        # Windows PyInstaller spec
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
│   │   ├── exception_hook.py  # 全局异常与 Qt 消息捕获 -> ~/pastelabel.log
│   │   └── utils.py
│   ├── engine/                # 图片、标签、保存和事件业务逻辑
│   │   ├── __init__.py
│   │   ├── event_handler.py
│   │   ├── image_loader.py
│   │   ├── label_manager.py
│   │   ├── paste_engine.py
│   │   ├── save_manager.py
│   │   └── undo_manager.py
│   └── ui/                    # 主窗口、对话框、主题与国际化
│       ├── __init__.py
│       ├── dialog_helpers.py
│       ├── dialogs.py
│       ├── dwm.py
│       ├── i18n.py
│       ├── main_window.py
│       ├── memory_dialog.py
│       ├── segmented_control.py
│       ├── settings_dialog.py
│       ├── theme.py
│       └── ui_builder.py
└── tests/                     # pytest 回归测试
    ├── __init__.py
    ├── test_canvas_interaction_regressions.py
    ├── test_canvas_menu_regressions.py
    ├── test_canvas_renderer_regressions.py
    ├── test_config.py
    ├── test_config_manager.py
    ├── test_dialog_button_styles.py
    ├── test_dialogs_regressions.py
    ├── test_documentation_regressions.py
    ├── test_event_handler_regressions.py
    ├── test_exception_hook_regressions.py
    ├── test_i18n.py
    ├── test_i18n_regressions.py
    ├── test_label_cache_multi_select_red.py
    ├── test_label_manager_regressions.py
    ├── test_loader_and_wheel_regressions.py
    ├── test_save_dedup_regressions.py
    ├── test_ui_mode_regressions.py
    └── test_utils.py
```
