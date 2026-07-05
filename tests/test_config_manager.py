"""
config_manager.py 测试 - 配置读写一致性
"""
import os
import sys
import json
import importlib.util
import tempfile

def _load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, os.path.abspath(path),
        submodule_search_locations=[])
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod

_base = os.path.join(os.path.dirname(__file__), '..', 'PasteY', 'core')
config = _load_module('config', os.path.join(_base, 'config.py'))
config_manager = _load_module('config_manager', os.path.join(_base, 'config_manager.py'))


class TestLoadAll:

    def test_returns_dict_with_expected_keys(self):
        result = config_manager.load_all()
        assert {'shortcuts', 'theme', 'language', 'max_labels',
                'grid_line_width', 'grid_alpha'}.issubset(result.keys())

    def test_shortcuts_has_all_keys(self):
        sc = config_manager.load_all()['shortcuts']
        for key in config.SHORTCUT_CONFIG:
            assert key in sc, f"fallback missing: {key}"

    def test_default_theme(self):
        theme = config_manager.load_all()['theme']
        assert theme in ('light', 'dark')

    def test_default_language(self):
        lang = config_manager.load_all()['language']
        assert lang in ('zh', 'en')


class TestSaveLoadRoundtrip:

    def test_shortcuts_roundtrip(self):
        original = config.SHORTCUT_CONFIG.copy()
        test_sc = original.copy()
        test_sc['toggle_labels'] = 'X'
        config_manager.save_shortcuts(test_sc)
        loaded = config_manager.load_shortcuts()
        assert loaded['toggle_labels'] == 'X'
        config_manager.save_shortcuts(original)

    def test_theme_roundtrip(self):
        original = config_manager.load_theme()
        config_manager.save_theme('dark')
        assert config_manager.load_theme() == 'dark'
        config_manager.save_theme(original)

    def test_language_roundtrip(self):
        original = config_manager.load_language()
        config_manager.save_language('en')
        assert config_manager.load_language() == 'en'
        config_manager.save_language(original)

    def test_save_all(self):
        original = config_manager.load_all()
        config_manager.save_all(theme='dark', language='en')
        result = config_manager.load_all()
        assert result['theme'] == 'dark'
        assert result['language'] == 'en'
        config_manager.save_all(
            theme=original['theme'],
            language=original['language'],
        )

    def test_handy_records_dedupe_and_limit(self):
        original = config_manager.load_handy_records()
        try:
            records = [
                {'note': f'n{i}', 'background_path': f'b{i}', 'paste_path': '', 'label_path': ''}
                for i in range(11)
            ]
            config_manager.save_handy_records(records)
            assert len(config_manager.load_handy_records()) == 10

            config_manager.upsert_handy_record({
                'note': 'updated', 'background_path': 'b10', 'paste_path': '', 'label_path': '',
                'background_index': 3,
            })
            loaded = config_manager.load_handy_records()
            assert loaded[0]['note'] == 'updated'
            assert loaded[0]['background_index'] == 3
            assert sum(1 for r in loaded if r['background_path'] == 'b10') == 1
            assert loaded[0]['paste_path'] == ''
            assert loaded[0]['label_path'] == ''

            config_manager.upsert_handy_record({
                'note': '', 'background_path': 'b10', 'paste_path': '', 'label_path': ''
            })
            assert config_manager.load_handy_records()[0]['note'] == ''
        finally:
            config_manager.save_handy_records(original)


class TestDefaults:

    def test_load_shortcuts_fallback(self):
        """load_shortcuts returns SHORTCUT_CONFIG when no saved shortcuts"""
        loaded = config_manager.load_shortcuts()
        for key in config.SHORTCUT_CONFIG:
            assert key in loaded
