"""
config_manager.py 测试 - 配置读写一致性
"""
import os
import sys
import json
import importlib.util
import tempfile
from pathlib import Path

def _load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, os.path.abspath(path),
        submodule_search_locations=[])
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod

_base = os.path.join(os.path.dirname(__file__), '..', 'pastelabel', 'core')
config = _load_module('config', os.path.join(_base, 'config.py'))
config_manager = _load_module('config_manager', os.path.join(_base, 'config_manager.py'))


def _with_temp_config(tmp_path):
    original = config_manager.CONFIG_PATH
    config_manager.CONFIG_PATH = str(Path(tmp_path) / 'missing.json')
    return original


class TestLoadAll:

    def test_returns_dict_with_expected_keys(self):
        result = config_manager.load_all()
        assert {'shortcuts', 'theme', 'language', 'max_labels',
                'grid_line_width', 'grid_alpha', 'memory'}.issubset(result.keys())

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

    def test_magnifier_disabled_by_default_when_config_missing(self, tmp_path):
        original = _with_temp_config(tmp_path)
        try:
            assert config_manager.load_all()['magnifier_enabled'] is False
        finally:
            config_manager.CONFIG_PATH = original

    def test_magnifier_zoom_defaults_to_config_when_config_missing(self, tmp_path):
        original = _with_temp_config(tmp_path)
        try:
            assert config_manager.load_all()['magnifier_zoom'] == config.MAGNIFIER_CONFIG['zoom']
        finally:
            config_manager.CONFIG_PATH = original

    def test_label_cache_slots_defaults_to_three_numeric_shortcuts(self, tmp_path):
        original = _with_temp_config(tmp_path)
        try:
            result = config_manager.load_all()
            assert 'label_cache_slots' in result
            assert len(result['label_cache_slots']) == 3
            assert [slot['name'] for slot in result['label_cache_slots']] == ['缓存槽1', '缓存槽2', '缓存槽3']
            assert [slot['shortcut'] for slot in result['label_cache_slots']] == ['1', '2', '3']
        finally:
            config_manager.CONFIG_PATH = original

    def test_label_cache_slots_load_preserves_saved_shortcuts(self, tmp_path):
        original = _with_temp_config(tmp_path)
        try:
            config_manager.save_all(label_cache_slots=[
                {'name': '一号槽', 'locked': True, 'items': [], 'shortcut': 'Ctrl+1'},
                {'name': '二号槽', 'locked': False, 'items': [], 'shortcut': 'Ctrl+2'},
                {'name': '三号槽', 'locked': False, 'items': [], 'shortcut': 'Ctrl+3'},
            ])
            result = config_manager.load_all()['label_cache_slots']
            assert [slot['name'] for slot in result] == ['一号槽', '二号槽', '三号槽']
            assert [slot['shortcut'] for slot in result] == ['Ctrl+1', 'Ctrl+2', 'Ctrl+3']
        finally:
            config_manager.CONFIG_PATH = original


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

    def test_magnifier_enabled_roundtrip_through_save_all(self, tmp_path):
        original = _with_temp_config(tmp_path)
        try:
            config_manager.save_all(magnifier_enabled=True)
            assert config_manager.load_all()['magnifier_enabled'] is True
        finally:
            config_manager.CONFIG_PATH = original

    def test_magnifier_zoom_roundtrip_through_save_all(self, tmp_path):
        original = _with_temp_config(tmp_path)
        try:
            config_manager.save_all(magnifier_zoom=2.5)
            assert config_manager.load_all()['magnifier_zoom'] == 2.5
        finally:
            config_manager.CONFIG_PATH = original

    def test_detection_box_wheel_settings_roundtrip_through_save_all(self, tmp_path):
        original = _with_temp_config(tmp_path)
        try:
            config_manager.save_all(detection_box_wheel_scale_step=0.08, detection_box_wheel_edge_step=9)
            result = config_manager.load_all()
            assert result['detection_box_wheel_scale_step'] == 0.08
            assert result['detection_box_wheel_edge_step'] == 9
        finally:
            config_manager.CONFIG_PATH = original

    def test_crosshair_settings_roundtrip_through_save_all(self, tmp_path):
        original = _with_temp_config(tmp_path)
        try:
            config_manager.save_all(crosshair_width=2.5, crosshair_color='#123456', crosshair_alpha=96)
            result = config_manager.load_all()
            assert result['crosshair_width'] == 2.5
            assert result['crosshair_color'] == '#123456'
            assert result['crosshair_alpha'] == 96
        finally:
            config_manager.CONFIG_PATH = original

    def test_memory_records_dedupe_limit_and_edit_mode(self):
        original = config_manager.load_memory_records()
        try:
            records = [
                {'note': f'n{i}', 'background_path': f'b{i}', 'paste_path': '', 'label_path': ''}
                for i in range(11)
            ]
            config_manager.save_memory_records(records)
            assert len(config_manager.load_memory_records()) == 10

            config_manager.upsert_memory_record({
                'note': 'updated', 'background_path': 'b10', 'paste_path': '', 'label_path': '',
                'background_index': 3, 'edit_mode': 'annotate',
            })
            loaded = config_manager.load_memory_records()
            assert loaded[0]['note'] == 'updated'
            assert loaded[0]['background_index'] == 3
            assert loaded[0]['edit_mode'] == 'annotate'
            assert sum(1 for r in loaded if r['background_path'] == 'b10') == 1
            assert loaded[0]['paste_path'] == ''
            assert loaded[0]['label_path'] == ''

            config_manager.upsert_memory_record({
                'note': '', 'background_path': 'b10', 'paste_path': '', 'label_path': ''
            })
            assert config_manager.load_memory_records()[0]['note'] == ''
        finally:
            config_manager.save_memory_records(original)

    def test_load_memory_records_ignores_legacy_config_key(self):
        original = config_manager.load_config()
        try:
            config_manager.save_config({
                'handy_records': [{
                    'note': 'legacy', 'background_path': 'legacy_bg',
                    'paste_path': '', 'label_path': '', 'edit_mode': 'annotate',
                }]
            })
            loaded = config_manager.load_memory_records()
            assert loaded == []
        finally:
            config_manager.save_config(original)

    def test_save_memory_records_writes_memory_and_removes_legacy_key(self):
        original = config_manager.load_config()
        try:
            config_manager.save_config({'handy_records': [{'background_path': 'old'}]})
            config_manager.save_memory_records([
                {'note': 'new', 'background_path': 'new_bg', 'paste_path': '', 'label_path': ''}
            ])
            saved = config_manager.load_config()
            assert 'memory' in saved
            assert 'handy_records' not in saved
            assert saved['memory'][0]['background_path'].endswith('new_bg')
        finally:
            config_manager.save_config(original)


class TestDefaults:

    def test_load_shortcuts_fallback(self):
        """load_shortcuts returns SHORTCUT_CONFIG when no saved shortcuts"""
        loaded = config_manager.load_shortcuts()
        for key in config.SHORTCUT_CONFIG:
            assert key in loaded
