# pastelabel/engine/pipeline_recipe.py
"""流水线配方：纯逻辑，无 Qt 控件依赖。

把「一键流水线」的完整配置规整为可持久化的 dict，支持校验与标签交集。
"""
RECIPE_VERSION = 1

STEPS = ('augment', 'export', 'split')

VALID_FORMATS = (
    'YOLO Detection', 'YOLO Seg', 'YOLO Pose', 'YOLO OBB',
    'VOC Detection', 'COCO Detection',
)
DEFAULT_FORMAT = 'YOLO Detection'

DEFAULT_TRANSFORM_PARAMS = {}

_DEFAULT_SPLIT = {'train': 0.8, 'val': 0.1, 'test': 0.1}


def _as_float(value, default):
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _clamp01(value):
    return max(0.0, min(1.0, value))


def _normalize_transforms(raw):
    if not isinstance(raw, dict):
        return {}
    result = {}
    for name, entry in raw.items():
        if not isinstance(name, str) or not name:
            continue
        if not isinstance(entry, dict):
            entry = {}
        params = {}
        raw_params = entry.get('params')
        if isinstance(raw_params, dict):
            for pname, pair in raw_params.items():
                if not isinstance(pname, str) or not pname:
                    continue
                if not isinstance(pair, (list, tuple)) or len(pair) != 2:
                    continue
                params[pname] = [_as_float(pair[0], 0.0),
                                 _as_float(pair[1], 0.0)]
        result[name] = {'checked': bool(entry.get('checked', False)),
                        'params': params}
    return result


def normalize_recipe(recipe):
    """校验/补默认，容忍旧配置与损坏数据。"""
    if not isinstance(recipe, dict):
        recipe = {}

    steps = []
    raw_steps = recipe.get('steps')
    if isinstance(raw_steps, (list, tuple)):
        for step in raw_steps:
            if step in STEPS and step not in steps:
                steps.append(step)
    steps = [s for s in STEPS if s in steps]

    aug = recipe.get('augment') if isinstance(recipe.get('augment'), dict) else {}
    mode = aug.get('mode')
    if mode not in ('all', 'random'):
        mode = 'all'

    exp = recipe.get('export') if isinstance(recipe.get('export'), dict) else {}
    fmt = exp.get('format')
    if fmt not in VALID_FORMATS:
        fmt = DEFAULT_FORMAT
    labels = []
    raw_labels = exp.get('labels')
    if isinstance(raw_labels, (list, tuple)):
        labels = [str(l) for l in raw_labels if str(l or '').strip()]

    split = recipe.get('split') if isinstance(recipe.get('split'), dict) else {}
    split_out = {}
    for key in ('train', 'val', 'test'):
        split_out[key] = _clamp01(_as_float(split.get(key), _DEFAULT_SPLIT[key]))

    name = recipe.get('name')
    name = str(name).strip() if isinstance(name, str) else ''

    return {
        'version': RECIPE_VERSION,
        'name': name,
        'steps': steps,
        'augment': {
            'transforms': _normalize_transforms(aug.get('transforms')),
            'ratio': _clamp01(_as_float(aug.get('ratio'), 1.0)),
            'mode': mode,
            'include_original': bool(aug.get('include_original', True)),
            'skip_empty': bool(aug.get('skip_empty', True)),
        },
        'export': {
            'format': fmt,
            'labels': labels,
            'skip_empty': bool(exp.get('skip_empty', True)),
        },
        'split': split_out,
    }


def capture_recipe(name, state):
    """从 UI 收集的 state 生成配方。"""
    base = dict(state) if isinstance(state, dict) else {}
    base['name'] = name
    base['version'] = RECIPE_VERSION
    return normalize_recipe(base)


def validate_recipe(recipe):
    """返回问题列表（空 = 有效）。每项为 (i18n 键, 格式化参数)。"""
    recipe = normalize_recipe(recipe)
    problems = []
    if len(recipe['steps']) < 2:
        problems.append(('至少选择两步', {}))
    split = recipe['split']
    if recipe['steps'] and 'split' in recipe['steps']:
        total = split['train'] + split['val'] + split['test']
        if abs(total - 1.0) > 1e-6:
            problems.append(('划分比例之和应为 1.0（当前 {total:.2f}）', {'total': total}))
    return problems


def apply_recipe_to_labels(recipe, available_labels):
    """配方标签 ∩ 当前数据集标签（按名称匹配，缺失忽略）。"""
    recipe = normalize_recipe(recipe)
    available = {str(l) for l in (available_labels or [])}
    return [l for l in recipe['export']['labels'] if l in available]
