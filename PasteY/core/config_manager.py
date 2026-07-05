"""
配置管理器 - 统一管理用户配置的加载和保存
"""
import os
import json
from .config import SHORTCUT_CONFIG, STATUSBAR_CONFIG


CONFIG_PATH = os.path.join(os.path.expanduser("~"), '.pastelabel.json')
HANDY_LIMIT = 10


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


def _normalize_handy_path(value):
    value = str(value or '').strip()
    return os.path.normpath(value) if value else ''


def _normalize_handy_record(record):
    try:
        background_index = max(0, int(record.get('background_index', 0) or 0))
    except (TypeError, ValueError):
        background_index = 0
    return {
        'note': str(record.get('note', '') or ''),
        'background_path': _normalize_handy_path(record.get('background_path', '')),
        'paste_path': _normalize_handy_path(record.get('paste_path', '')),
        'label_path': _normalize_handy_path(record.get('label_path', '')),
        'background_index': background_index,
        'updated_at': str(record.get('updated_at', '') or ''),
    }


def _handy_key(record):
    return (record['background_path'], record['paste_path'], record['label_path'])


def load_handy_records():
    """加载巧手记录，最多返回 10 条。"""
    records = load_config().get('handy_records', [])
    if not isinstance(records, list):
        return []
    return [_normalize_handy_record(r) for r in records if isinstance(r, dict)][:HANDY_LIMIT]


def save_handy_records(records):
    """保存巧手记录，按路径组合去重并限制 10 条。"""
    seen = set()
    normalized = []
    for record in records:
        if not isinstance(record, dict):
            continue
        item = _normalize_handy_record(record)
        if not any([item['background_path'], item['paste_path'], item['label_path']]):
            continue
        key = _handy_key(item)
        if key in seen:
            continue
        seen.add(key)
        normalized.append(item)
        if len(normalized) >= HANDY_LIMIT:
            break
    config = load_config()
    config['handy_records'] = normalized
    return save_config(config)


def upsert_handy_record(record):
    """新增或更新巧手记录，最新记录排在最前。"""
    item = _normalize_handy_record(record)
    if not any([item['background_path'], item['paste_path'], item['label_path']]):
        return False
    key = _handy_key(item)
    remaining = [r for r in load_handy_records() if _handy_key(r) != key]
    return save_handy_records([item] + remaining)


def delete_handy_record(index):
    records = load_handy_records()
    if index < 0 or index >= len(records):
        return False
    records.pop(index)
    return save_handy_records(records)


def load_all():
    """加载所有配置"""
    config = load_config()
    saved_sc = config.get('shortcuts', {})
    merged_sc = {**SHORTCUT_CONFIG, **saved_sc}
    return {
        'shortcuts': merged_sc,
        'theme': config.get('theme', 'light'),
        'language': config.get('language', 'zh'),
        'max_labels': config.get('max_labels', STATUSBAR_CONFIG['max_labels']),
        'grid_line_width': config.get('grid_line_width', None),
        'grid_alpha': config.get('grid_alpha', None),
        'handy_records': load_handy_records(),
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
