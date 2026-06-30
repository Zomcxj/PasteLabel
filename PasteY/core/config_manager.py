"""
配置管理器 - 统一管理用户配置的加载和保存
"""
import os
import json
from .config import SHORTCUT_CONFIG, STATUSBAR_CONFIG


CONFIG_PATH = os.path.join(os.path.expanduser("~"), '.pastelabel.json')


def get_config_path():
    """获取配置文件路径"""
    return CONFIG_PATH


def load_config():
    """加载完整配置"""
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_config(config):
    """保存完整配置"""
    try:
        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False


def load_shortcuts():
    """加载快捷键配置"""
    config = load_config()
    return config.get('shortcuts', SHORTCUT_CONFIG)


def save_shortcuts(shortcuts):
    """保存快捷键配置"""
    config = load_config()
    config['shortcuts'] = shortcuts
    return save_config(config)


def load_theme():
    """加载主题配置"""
    config = load_config()
    return config.get('theme', 'light')


def save_theme(theme):
    """保存主题配置"""
    config = load_config()
    config['theme'] = theme
    return save_config(config)


def load_language():
    """加载语言配置"""
    config = load_config()
    return config.get('language', 'zh')


def save_language(language):
    """保存语言配置"""
    config = load_config()
    config['language'] = language
    return save_config(config)


def load_all():
    """加载所有配置"""
    config = load_config()
    return {
        'shortcuts': config.get('shortcuts', SHORTCUT_CONFIG),
        'theme': config.get('theme', 'light'),
        'language': config.get('language', 'zh'),
        'max_labels': config.get('max_labels', STATUSBAR_CONFIG['max_labels']),
        'grid_line_width': config.get('grid_line_width', None),
        'grid_alpha': config.get('grid_alpha', None),
    }


def save_all(shortcuts=None, theme=None, language=None, max_labels=None,
             grid_line_width=None, grid_alpha=None):
    """保存所有配置"""
    config = load_config()
    if shortcuts is not None:
        config['shortcuts'] = shortcuts
    if theme is not None:
        config['theme'] = theme
    if language is not None:
        config['language'] = language
    if max_labels is not None:
        config['max_labels'] = max_labels
    if grid_line_width is not None:
        config['grid_line_width'] = grid_line_width
    if grid_alpha is not None:
        config['grid_alpha'] = grid_alpha
    return save_config(config)
