"""流水线配方纯逻辑测试。"""


def _state(**over):
    state = {
        'steps': ['augment', 'export', 'split'],
        'augment': {
            'transforms': {
                'fliph': {'checked': True, 'params': {}},
                'bright': {'checked': True, 'params': {'delta': [-30, 30]}},
            },
            'ratio': 0.5, 'mode': 'random',
            'include_original': False, 'skip_empty': True,
        },
        'export': {'format': 'YOLO Seg', 'labels': ['cat', 'dog'], 'skip_empty': False},
        'split': {'train': 0.7, 'val': 0.2, 'test': 0.1},
    }
    state.update(over)
    return state


def test_normalize_fills_defaults_on_empty():
    from pastelabel.engine.pipeline_recipe import normalize_recipe
    r = normalize_recipe({})
    assert r['version'] == 1
    assert r['name'] == ''
    assert r['steps'] == []
    assert r['augment']['transforms'] == {}
    assert r['augment']['ratio'] == 1.0
    assert r['augment']['mode'] == 'all'
    assert r['augment']['include_original'] is True
    assert r['augment']['skip_empty'] is True
    assert r['export']['format'] == 'YOLO Detection'
    assert r['export']['labels'] == []
    assert r['export']['skip_empty'] is True
    assert r['split'] == {'train': 0.8, 'val': 0.1, 'test': 0.1}


def test_normalize_coerces_bad_types_and_unknown_format():
    from pastelabel.engine.pipeline_recipe import normalize_recipe
    r = normalize_recipe({
        'steps': 'augment',
        'augment': {'ratio': 'x', 'mode': 'bogus',
                    'transforms': {'fliph': 'yes', 'bad': {'checked': 1, 'params': 'z'}}},
        'export': {'format': 'Nope', 'labels': 'cat'},
        'split': {'train': 'a', 'val': 2.0, 'test': -1},
    })
    assert r['steps'] == []
    assert r['augment']['ratio'] == 1.0
    assert r['augment']['mode'] == 'all'
    assert r['augment']['transforms']['fliph'] == {'checked': False, 'params': {}}
    assert r['augment']['transforms']['bad'] == {'checked': True, 'params': {}}
    assert r['export']['format'] == 'YOLO Detection'
    assert r['export']['labels'] == []
    assert r['split']['train'] == 0.8
    assert r['split']['val'] == 1.0
    assert r['split']['test'] == 0.0


def test_normalize_keeps_valid_values():
    from pastelabel.engine.pipeline_recipe import normalize_recipe, capture_recipe
    r = capture_recipe('my recipe', _state())
    assert r['name'] == 'my recipe'
    assert r['steps'] == ['augment', 'export', 'split']
    assert r['augment']['transforms']['bright']['params'] == {'delta': [-30.0, 30.0]}
    assert r['augment']['ratio'] == 0.5
    assert r['augment']['mode'] == 'random'
    assert r['augment']['include_original'] is False
    assert r['export']['format'] == 'YOLO Seg'
    assert r['export']['labels'] == ['cat', 'dog']
    assert r['export']['skip_empty'] is False
    assert r['split'] == {'train': 0.7, 'val': 0.2, 'test': 0.1}


def test_normalize_filters_unknown_steps_and_orders_them():
    from pastelabel.engine.pipeline_recipe import normalize_recipe
    r = normalize_recipe({'steps': ['split', 'bogus', 'augment', 'split']})
    assert r['steps'] == ['augment', 'split']


def test_validate_requires_two_steps():
    from pastelabel.engine.pipeline_recipe import normalize_recipe, validate_recipe
    assert validate_recipe(normalize_recipe({'steps': ['augment']}))


def test_validate_flags_split_sum():
    from pastelabel.engine.pipeline_recipe import normalize_recipe, validate_recipe
    bad = normalize_recipe({'steps': ['augment', 'split'],
                            'split': {'train': 0.5, 'val': 0.5, 'test': 0.5}})
    assert any('比例' in p for p in validate_recipe(bad))


def test_validate_ok_for_good_recipe():
    from pastelabel.engine.pipeline_recipe import capture_recipe, validate_recipe
    assert validate_recipe(capture_recipe('r', _state())) == []


def test_apply_labels_intersection():
    from pastelabel.engine.pipeline_recipe import capture_recipe, apply_recipe_to_labels
    r = capture_recipe('r', _state())
    assert apply_recipe_to_labels(r, ['dog', 'bird']) == ['dog']


def test_apply_labels_all_missing_returns_empty():
    from pastelabel.engine.pipeline_recipe import capture_recipe, apply_recipe_to_labels
    r = capture_recipe('r', _state())
    assert apply_recipe_to_labels(r, ['bird']) == []


def test_apply_labels_case_sensitive():
    from pastelabel.engine.pipeline_recipe import capture_recipe, apply_recipe_to_labels
    r = capture_recipe('r', _state())
    assert apply_recipe_to_labels(r, ['Cat', 'DOG']) == []


def test_normalize_pipeline_recipes_dedup_and_limit():
    from pastelabel.core.config_manager import _normalize_pipeline_recipes
    recipes = [
        {'name': 'a', 'steps': ['augment', 'export']},
        {'name': ''},
        {'name': 'a', 'steps': ['augment', 'split']},  # later wins
        'junk',
    ]
    out = _normalize_pipeline_recipes(recipes)
    assert [r['name'] for r in out] == ['a']
    assert out[0]['steps'] == ['augment', 'split']
    assert _normalize_pipeline_recipes('not a list') == []


def test_normalize_pipeline_recipes_caps_at_50_keeping_last():
    from pastelabel.core.config_manager import _normalize_pipeline_recipes
    recipes = [{'name': f'r{i}', 'steps': ['augment', 'export']} for i in range(55)]
    out = _normalize_pipeline_recipes(recipes)
    assert len(out) == 50
    assert [r['name'] for r in out] == [f'r{i}' for i in range(5, 55)]


def test_save_all_without_recipes_keeps_stored(tmp_path, monkeypatch):
    from pastelabel.core import config_manager
    config_path = tmp_path / "config.json"
    monkeypatch.setattr(config_manager, 'CONFIG_PATH', str(config_path))
    recipe = {'name': 'kept', 'steps': ['augment', 'export']}
    config_manager.save_all(pipeline_recipes=[recipe])
    config_manager.save_all(theme='dark')
    loaded = config_manager.load_config().get('pipeline_recipes')
    assert [r['name'] for r in loaded] == ['kept']


def test_i18n_recipe_terms():
    from pastelabel.ui.i18n import _strings
    for key in ("配方", "保存为配方", "应用配方", "删除配方", "配方名称",
                "配方已保存", "已应用配方", "配方标签在当前数据集均不存在",
                "覆盖同名配方", "确定删除配方", "至少选择两步", "删除"):
        assert key in _strings["zh"], key
        assert key in _strings["en"], key


def test_save_all_roundtrips_pipeline_recipes(tmp_path, monkeypatch):
    from pastelabel.core import config_manager
    from pastelabel.engine.pipeline_recipe import capture_recipe
    config_path = tmp_path / "config.json"
    monkeypatch.setattr(config_manager, 'CONFIG_PATH', str(config_path))
    recipe = capture_recipe('demo', {'steps': ['augment', 'export'],
                                     'export': {'labels': ['cat']}})
    config_manager.save_all(pipeline_recipes=[recipe])
    loaded = config_manager.load_config().get('pipeline_recipes')
    assert len(loaded) == 1
    assert loaded[0]['name'] == 'demo'
    assert loaded[0]['export']['labels'] == ['cat']
