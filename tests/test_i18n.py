"""
i18n.py 测试 - 翻译系统
"""
import os
import sys
import importlib.util

def _load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, os.path.abspath(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

_ui = os.path.join(os.path.dirname(__file__), '..', 'pastelabel', 'ui')
i18n = _load_module('i18n', os.path.join(_ui, 'i18n.py'))


class TestTranslation:

    def test_zh_translation(self):
        i18n.set_lang('zh')
        assert i18n.t('显示BOX') == '显示检测框'
        assert i18n.t('保存') == '保存'

    def test_en_translation(self):
        i18n.set_lang('en')
        assert i18n.t('显示BOX') == 'Show Detection Box'
        assert i18n.t('保存') == 'Save'

    def test_label_selection_dialog_translations(self):
        i18n.set_lang('en')
        assert i18n.t('选择标签') == 'Select Label'
        assert i18n.t('现有标签：') == 'Existing labels:'
        assert i18n.t('或输入新标签：') == 'Or enter new label:'
        assert i18n.t('确定') == 'OK'
        assert i18n.t('取消') == 'Cancel'

    def test_memory_records_translations(self):
        i18n.set_lang('en')
        assert i18n.t('记忆') == 'Memory'
        assert i18n.t('记忆记录') == 'Memory Records'
        assert i18n.t('修改备注') == 'Edit Note'

    def test_fallback_to_key(self):
        i18n.set_lang('zh')
        assert i18n.t('nonexistent_key') == 'nonexistent_key'

    def test_fallback_en(self):
        i18n.set_lang('en')
        assert i18n.t('nonexistent_key') == 'nonexistent_key'


class TestLanguageSwitch:

    def test_toggle_zh_to_en(self):
        i18n.set_lang('zh')
        result = i18n.toggle_lang()
        assert result == 'en'
        assert i18n.get_lang() == 'en'

    def test_toggle_en_to_zh(self):
        i18n.set_lang('en')
        result = i18n.toggle_lang()
        assert result == 'zh'
        assert i18n.get_lang() == 'zh'

    def test_set_lang(self):
        i18n.set_lang('en')
        assert i18n.get_lang() == 'en'
        i18n.set_lang('zh')
        assert i18n.get_lang() == 'zh'


class TestCoverage:

    def test_all_zh_keys_have_en(self):
        i18n.set_lang('zh')
        zh_keys = set(i18n._strings.get('zh', {}).keys())
        en_keys = set(i18n._strings.get('en', {}).keys())
        missing = zh_keys - en_keys
        assert not missing, f"Missing EN translations: {missing}"

    def test_all_en_keys_have_zh(self):
        i18n.set_lang('en')
        zh_keys = set(i18n._strings.get('zh', {}).keys())
        en_keys = set(i18n._strings.get('en', {}).keys())
        missing = en_keys - zh_keys
        assert not missing, f"Missing ZH translations: {missing}"

    def test_translation_count(self):
        zh_count = len(i18n._strings.get('zh', {}))
        en_count = len(i18n._strings.get('en', {}))
        assert zh_count == en_count
        assert zh_count > 50, f"only {zh_count} translations"
