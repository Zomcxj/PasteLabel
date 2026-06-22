"""
Language module - Chinese/English switching
"""

_strings = {
    "zh": {
        "背景图:": "背景图:",
        "贴图:": "贴图:",
        "标签:": "标签:",
        "绘制BOX": "绘制BOX",
        "自动保存": "自动保存",
        "显示BOX": "显示BOX",
        "显示Label": "显示Label",
        "贴图标签": "贴图标签",
        "添加文件名前缀": "添加文件名前缀",
        "显示网格": "显示网格",
        "显示贴图名": "显示贴图名",
        "背景图列表": "背景图列表",
        "标签管理": "标签管理",
        "背景图标签": "背景图标签",
        "贴图标签_list": "贴图标签",
        "贴图列表": "贴图列表",
        "随机贴图": "随机贴图",
        "一键贴图": "一键贴图",
        "列表视图": "列表视图",
        "缩略视图": "缩略视图",
        "贴图个数:": "贴图个数:",
        "短边尺寸:": "短边尺寸:",
        "清空画布": "清空画布",
        "保存图片": "保存图片",
        "全部保存": "全部保存",
        "选择背景图片": "选择背景图片",
        "加载文件夹图片": "加载文件夹图片",
        "选择贴图": "选择贴图",
        "加载贴图文件夹": "加载贴图文件夹",
        "选择标签文件": "选择标签文件",
        "绘制检测框": "绘制检测框",
        "切换深色/浅色主题": "切换深色/浅色主题",
        "切换中英文": "切换中英文",
        "已切换到深色主题": "已切换到深色主题",
        "已切换到浅色主题": "已切换到浅色主题",
        "缩略图模式": "缩略图模式",
        "列表模式": "列表模式",
        "最小值不能大于最大值": "最小值不能大于最大值",
        "警告": "警告",
        "请先选择背景图片": "请先选择背景图片",
        "无法获取保存信息": "无法获取保存信息",
        "没有背景图片可保存": "没有背景图片可保存",
        "保存完成": "保存完成",
        "保存结果": "保存结果",
        "保存": "保存",
        "取消": "取消",
        "快捷键设置": "快捷键设置",
        "撤销": "撤销",
        "重做": "重做",
        "退出绘制": "退出绘制",
        "下一张": "下一张",
        "上一张": "上一张",
        "删除选中": "删除选中",
        "适应视图": "适应视图",
        "放大": "放大",
        "缩小": "缩小",
        "重置缩放": "重置缩放",
        "选项": "选项",
        "显示贴图名": "显示贴图名",
        "设置": "设置",
        "重置": "重置",
        "保存失败": "保存失败",
        "无法保存设置": "无法保存设置",
        "选项设置": "选项设置",
    },
    "en": {
        "背景图:": "Image:",
        "贴图:": "Paste:",
        "标签:": "Label:",
        "绘制BOX": "Draw BOX",
        "自动保存": "Auto Save",
        "显示BOX": "Show BOX",
        "显示Label": "Show Label",
        "贴图标签": "Paste Label",
        "添加文件名前缀": "Add Filename Prefix",
        "显示网格": "Show Grid",
        "显示贴图名": "Show Paste Names",
        "背景图列表": "Image List",
        "标签管理": "Label Manager",
        "背景图标签": "Image Labels",
        "贴图标签_list": "Paste Labels",
        "贴图列表": "Paste List",
        "随机贴图": "Random Paste",
        "一键贴图": "Batch Paste",
        "列表视图": "List View",
        "缩略视图": "Thumb View",
        "贴图个数:": "Count:",
        "短边尺寸:": "Size:",
        "清空画布": "Clear",
        "保存图片": "Save",
        "全部保存": "Save All",
        "选择背景图片": "Select background image",
        "加载文件夹图片": "Load folder images",
        "选择贴图": "Select paste image",
        "加载贴图文件夹": "Load paste folder",
        "选择标签文件": "Select label file",
        "绘制检测框": "Draw detection box (W)",
        "切换深色/浅色主题": "Toggle dark/light theme",
        "切换中英文": "Toggle Chinese/English",
        "已切换到深色主题": "Switched to dark theme",
        "已切换到浅色主题": "Switched to light theme",
        "缩略图模式": "Thumbnail mode",
        "列表模式": "List mode",
        "最小值不能大于最大值": "Min cannot exceed max",
        "警告": "Warning",
        "请先选择背景图片": "Please select background image first",
        "无法获取保存信息": "Cannot get save info",
        "没有背景图片可保存": "No background images to save",
        "保存完成": "Save complete",
        "保存结果": "Save result",
        "保存": "Save",
        "取消": "Cancel",
        "快捷键设置": "Shortcut Settings",
        "撤销": "Undo",
        "重做": "Redo",
        "退出绘制": "Exit Draw",
        "下一张": "Next",
        "上一张": "Previous",
        "删除选中": "Delete Selected",
        "适应视图": "Fit View",
        "放大": "Zoom In",
        "缩小": "Zoom Out",
        "重置缩放": "Reset Zoom",
        "选项": "Options",
        "显示贴图名": "Show Paste Names",
        "确定": "OK",
        "设置": "Settings",
        "重置": "Reset",
        "保存失败": "Save Failed",
        "无法保存设置": "Cannot save settings",
        "选项设置": "Options",
    }
}

_current_lang = "zh"


def t(key):
    """Translate key to current language"""
    return _strings.get(_current_lang, _strings["zh"]).get(key, key)


def get_lang():
    return _current_lang


def set_lang(lang):
    global _current_lang
    _current_lang = lang


def toggle_lang():
    global _current_lang
    if _current_lang == "zh":
        _current_lang = "en"
    else:
        _current_lang = "zh"
    return _current_lang
