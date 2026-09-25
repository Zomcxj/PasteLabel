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


def test_pipeline_section_source_has_recipe_widgets():
    import inspect
    from pastelabel.ui.mixins.processing_panel_builder import ProcessingPanelBuilderMixin
    src = inspect.getsource(ProcessingPanelBuilderMixin._build_pipeline_section)
    assert "_recipe_combo" in src
    assert "_recipe_save_btn" in src
    assert "_recipe_apply_btn" in src
    assert "_recipe_del_btn" in src


def test_processing_panel_exposes_recipe_methods():
    import inspect
    from pastelabel.ui.processing_panel import ProcessingPanel
    for name in ("_load_recipes", "_collect_pipeline_state", "_save_recipe",
                 "_apply_recipe", "_delete_recipe"):
        assert hasattr(ProcessingPanel, name), name
    src = inspect.getsource(ProcessingPanel)
    assert "capture_recipe" in src
    assert "apply_recipe_to_labels" in src


def test_apply_recipe_coerces_float_params_for_int_spinboxes():
    from PyQt5.QtWidgets import QSpinBox
    from pastelabel.ui.processing_panel import ProcessingPanel
    from pastelabel.engine.pipeline_recipe import capture_recipe

    class IntSpin(QSpinBox):
        def __init__(self):
            self.v = None

        def setValue(self, v):
            if not isinstance(v, int):
                raise TypeError("int required")
            self.v = v

    class Dummy:
        def setChecked(self, v):
            self.checked = v

        def isChecked(self):
            return getattr(self, 'checked', False)

        def setCurrentIndex(self, i):
            self.idx = i

        def currentIndex(self):
            return getattr(self, 'idx', 0)

        def findText(self, t):
            return 0

        def setValue(self, v):
            self.v = v

        def value(self):
            return getattr(self, 'v', 0.0)

    panel = ProcessingPanel.__new__(ProcessingPanel)
    panel._recipes = [capture_recipe('r', {
        'steps': ['augment', 'export'],
        'augment': {'transforms': {
            'bright': {'checked': True, 'params': {'delta': [-10.0, 20.0]}}}},
        'export': {'labels': []},
    })]
    panel._recipe_combo = Dummy()
    panel._pipe_aug = Dummy()
    panel._pipe_exp = Dummy()
    panel._pipe_split = Dummy()
    panel._aug_widgets = {'bright': (Dummy(), {'delta': (IntSpin(), IntSpin())}, 'bright')}
    panel._aug_ratio = Dummy()
    panel._aug_mode = Dummy()
    panel._aug_inc_orig = Dummy()
    panel._aug_skip_empty = Dummy()
    panel._exp_format = Dummy()
    panel._exp_skip_empty = Dummy()
    panel._exp_label_checkboxes = {}
    panel._split_train = Dummy()
    panel._split_val = Dummy()
    panel._split_test = Dummy()
    panel._log = lambda msg: None
    panel._apply_recipe()
    spins = panel._aug_widgets['bright'][1]['delta']
    assert spins[0].v == -10
    assert spins[1].v == 20


def test_apply_recipe_rejects_invalid_recipe():
    from pastelabel.ui.processing_panel import ProcessingPanel

    class Combo:
        def currentIndex(self):
            return 0

    panel = ProcessingPanel.__new__(ProcessingPanel)
    panel._recipes = [{'name': 'bad', 'steps': ['augment']}]
    panel._recipe_combo = Combo()
    logs = []
    panel._log = logs.append
    panel._apply_recipe()
    assert logs and '两步' in logs[0]
