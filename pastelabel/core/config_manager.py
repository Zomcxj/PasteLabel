"""
配置管理器 - 统一管理用户配置的加载和保存
"""
import os
import json
from .config import SHORTCUT_CONFIG, STATUSBAR_CONFIG, DETECTION_BOX_CONFIG, MAGNIFIER_CONFIG, LABEL_CACHE_SLOTS, NUDGE_CONFIG, DETECTION_BOX_WHEEL_CONFIG, CROSSHAIR_CONFIG, BOX_BORDER_CONFIG, LABEL_COLORS


CONFIG_PATH = os.path.join(os.path.expanduser("~"), '.pastelabel.json')
MEMORY_LIMIT = 10
DISABLED_SHORTCUT_ACTIONS = {'save', 'save_all'}


def _normalize_label_cache_slots(slots):
    defaults = [dict(slot) for slot in LABEL_CACHE_SLOTS]
    if not isinstance(slots, list):
        return defaults

    normalized = []
    for index, default in enumerate(defaults):
        slot = slots[index] if index < len(slots) and isinstance(slots[index], dict) else {}
        items = slot.get('items', default['items'])
        normalized.append({
            'name': str(slot.get('name', default['name']) or default['name']),
            'locked': bool(slot.get('locked', default['locked'])),
            'items': items if isinstance(items, list) else [],
            'shortcut': str(slot.get('shortcut', default['shortcut']) or default['shortcut']),
            'copy_order': int(slot.get('copy_order', 0) or 0),
            'copied_at': str(slot.get('copied_at', '') or ''),
        })
    return normalized


def _filter_shortcuts(shortcuts):
    """过滤已禁用的快捷键动作，避免旧配置继续生效。"""
    if not isinstance(shortcuts, dict):
        return {}
    return {k: v for k, v in shortcuts.items() if k not in DISABLED_SHORTCUT_ACTIONS}


def _normalize_label_colors(colors):
    if not isinstance(colors, list) or not colors:
        return list(LABEL_COLORS)
    normalized = [str(color) for color in colors]
    try:
        if all(len(color) == 7 and color.startswith('#') and int(color[1:], 16) >= 0 for color in normalized):
            return normalized
    except ValueError:
        pass
    return list(LABEL_COLORS)


def get_label_color(labels, label, palette=None):
    """按标签名字符加权和稳定分配颜色，新增标签不影响已有标签颜色。"""
    colors = _normalize_label_colors(palette if palette is not None else LABEL_COLORS)
    if not label:
        return colors[0]
    idx = sum(ord(c) * (i + 1) for i, c in enumerate(label)) % len(colors)
    return colors[idx]


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
    return _filter_shortcuts(config.get('shortcuts', SHORTCUT_CONFIG))


def save_shortcuts(shortcuts):
    """保存快捷键配置"""
    config = load_config()
    config['shortcuts'] = _filter_shortcuts(shortcuts)
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


def _normalize_memory_path(value):
    value = str(value or '').strip()
    return os.path.normpath(value) if value else ''


def _normalize_memory_record(record):
    try:
        background_index = max(0, int(record.get('background_index', 0) or 0))
    except (TypeError, ValueError):
        background_index = 0
    edit_mode = record.get('edit_mode', 'paste')
    if edit_mode not in ('paste', 'annotate'):
        edit_mode = 'paste'
    return {
        'note': str(record.get('note', '') or ''),
        'background_path': _normalize_memory_path(record.get('background_path', '')),
        'paste_path': _normalize_memory_path(record.get('paste_path', '')),
        'label_path': _normalize_memory_path(record.get('label_path', '')),
        'background_index': background_index,
        'edit_mode': edit_mode,
        'updated_at': str(record.get('updated_at', '') or ''),
    }


def _memory_key(record):
    return (record['background_path'], record['paste_path'], record['label_path'])


def load_memory_records():
    """加载记忆记录，最多返回 10 条。"""
    config = load_config()
    records = config.get('memory', [])
    if not isinstance(records, list):
        return []
    return [_normalize_memory_record(r) for r in records if isinstance(r, dict)][:MEMORY_LIMIT]


def save_memory_records(records):
    """保存记忆记录，按路径组合去重并限制 10 条。"""
    seen = set()
    normalized = []
    for record in records:
        if not isinstance(record, dict):
            continue
        item = _normalize_memory_record(record)
        if not any([item['background_path'], item['paste_path'], item['label_path']]):
            continue
        key = _memory_key(item)
        if key in seen:
            continue
        seen.add(key)
        normalized.append(item)
        if len(normalized) >= MEMORY_LIMIT:
            break
    config = load_config()
    config['memory'] = normalized
    config.pop('handy_records', None)
    return save_config(config)


def upsert_memory_record(record):
    """新增或更新记忆记录，最新记录排在最前。"""
    item = _normalize_memory_record(record)
    if not any([item['background_path'], item['paste_path'], item['label_path']]):
        return False
    key = _memory_key(item)
    remaining = [r for r in load_memory_records() if _memory_key(r) != key]
    return save_memory_records([item] + remaining)


def delete_memory_record(index):
    records = load_memory_records()
    if index < 0 or index >= len(records):
        return False
    records.pop(index)
    return save_memory_records(records)


def load_all():
    """加载所有配置"""
    config = load_config()
    legacy_wheel_scale_step = config.get('detection_box_wheel_scale_step')
    saved_sc = _filter_shortcuts(config.get('shortcuts', {}))
    if saved_sc.get('delete_selected') == 'Delete':
        saved_sc['delete_selected'] = SHORTCUT_CONFIG['delete_selected']
    merged_sc = {**SHORTCUT_CONFIG, **saved_sc}
    return {
        'shortcuts': merged_sc,
        'theme': config.get('theme', 'light'),
        'language': config.get('language', 'zh'),
        'max_labels': config.get('max_labels', STATUSBAR_CONFIG['max_labels']),
        'grid_line_width': config.get('grid_line_width', None),
        'grid_alpha': config.get('grid_alpha', None),
        'resize_handle_size': config.get('resize_handle_size', DETECTION_BOX_CONFIG['resize_handle_size']),
        'label_font_size': config.get('label_font_size', DETECTION_BOX_CONFIG['label_font_size']),
        'label_position': config.get('label_position', DETECTION_BOX_CONFIG['label_position']),
        'canvas_image_copy_enabled': bool(config.get('canvas_image_copy_enabled', False)),
        'magnifier_enabled': bool(config.get('magnifier_enabled', False)),
        'magnifier_position': str(config.get('magnifier_position', MAGNIFIER_CONFIG['position'])),
        'magnifier_zoom': float(config.get('magnifier_zoom', MAGNIFIER_CONFIG['zoom'])),
        'magnifier_size': int(config.get('magnifier_size', MAGNIFIER_CONFIG['size'])),
        'label_cache_slots': _normalize_label_cache_slots(config.get('label_cache_slots')),
        'nudge_step': int(config.get('nudge_step', NUDGE_CONFIG['step'])),
        'detection_box_scale_step': float(config.get(
            'detection_box_scale_step',
            legacy_wheel_scale_step if legacy_wheel_scale_step is not None else DETECTION_BOX_WHEEL_CONFIG['detection_box_scale_step'],
        )),
        'paste_item_scale_step': float(config.get(
            'paste_item_scale_step',
            legacy_wheel_scale_step if legacy_wheel_scale_step is not None else DETECTION_BOX_WHEEL_CONFIG['paste_item_scale_step'],
        )),
        'detection_box_wheel_edge_step': int(config.get('detection_box_wheel_edge_step', DETECTION_BOX_WHEEL_CONFIG['edge_step'])),
        'crosshair_width': float(config.get('crosshair_width', CROSSHAIR_CONFIG['width'])),
        'crosshair_color': str(config.get('crosshair_color', CROSSHAIR_CONFIG['color'])),
        'crosshair_alpha': int(config.get('crosshair_alpha', CROSSHAIR_CONFIG['alpha'])),
        'box_border_width': float(config.get('box_border_width', BOX_BORDER_CONFIG['width'])),
        'label_colors': _normalize_label_colors(config.get('label_colors')),
        'memory': load_memory_records(),
    }


def save_all(shortcuts=None, theme=None, language=None, max_labels=None,
             grid_line_width=None, grid_alpha=None, resize_handle_size=None,
             label_font_size=None, label_position=None,
             canvas_image_copy_enabled=None, magnifier_enabled=None,
             magnifier_position=None, magnifier_zoom=None, magnifier_size=None,
             label_cache_slots=None, nudge_step=None,
               detection_box_scale_step=None, paste_item_scale_step=None,
               detection_box_wheel_edge_step=None,
              crosshair_width=None, crosshair_color=None, crosshair_alpha=None,
              box_border_width=None, label_colors=None):
    """保存所有配置"""
    config = load_config()
    if shortcuts is not None:
        config['shortcuts'] = _filter_shortcuts(shortcuts)
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
    if resize_handle_size is not None:
        config['resize_handle_size'] = resize_handle_size
    if label_font_size is not None:
        config['label_font_size'] = label_font_size
    if label_position is not None:
        config['label_position'] = label_position
    if canvas_image_copy_enabled is not None:
        config['canvas_image_copy_enabled'] = bool(canvas_image_copy_enabled)
    if magnifier_enabled is not None:
        config['magnifier_enabled'] = bool(magnifier_enabled)
    if magnifier_position is not None:
        config['magnifier_position'] = str(magnifier_position)
    if magnifier_zoom is not None:
        config['magnifier_zoom'] = max(0.8, min(3.0, float(magnifier_zoom)))
    if magnifier_size is not None:
        config['magnifier_size'] = max(80, min(400, int(magnifier_size)))
    if label_cache_slots is not None:
        config['label_cache_slots'] = _normalize_label_cache_slots(label_cache_slots)
    if nudge_step is not None:
        config['nudge_step'] = max(1, min(5, int(nudge_step)))
    if detection_box_scale_step is not None:
        config['detection_box_scale_step'] = max(0.01, min(0.30, float(detection_box_scale_step)))
    if paste_item_scale_step is not None:
        config['paste_item_scale_step'] = max(0.01, min(0.30, float(paste_item_scale_step)))
    if detection_box_scale_step is not None or paste_item_scale_step is not None:
        config.pop('detection_box_wheel_scale_step', None)
    if detection_box_wheel_edge_step is not None:
        config['detection_box_wheel_edge_step'] = max(1, min(50, int(detection_box_wheel_edge_step)))
    if crosshair_width is not None:
        config['crosshair_width'] = max(0.5, min(3.0, float(crosshair_width)))
    if crosshair_color is not None:
        color = str(crosshair_color)
        config['crosshair_color'] = color if len(color) == 7 and color.startswith('#') else CROSSHAIR_CONFIG['color']
    if crosshair_alpha is not None:
        config['crosshair_alpha'] = max(0, min(255, int(crosshair_alpha)))
    if box_border_width is not None:
        config['box_border_width'] = max(1, min(4, float(box_border_width)))
    if label_colors is not None:
        config['label_colors'] = _normalize_label_colors(label_colors)
    return save_config(config)
