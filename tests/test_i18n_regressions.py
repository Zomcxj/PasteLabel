"""国际化回归测试。"""
from pastelabel.ui import i18n


def test_iou_axis_label_has_explicit_translation():
    """轴标签走 tr('IoU')，两个语言表都要有该键（否则回退到键名，语言表不完整）。"""
    assert 'IoU' in i18n._strings['zh']
    assert 'IoU' in i18n._strings['en']


def test_english_translates_magnifier_and_detection_box_wheel_settings():
    original_lang = i18n.get_lang()
    try:
        i18n.set_lang('en')
        assert i18n.t('窗口放大器倍率') == 'Magnifier Zoom'
        assert i18n.t('检测框缩放步长') == 'Box Wheel Scale Step'
        assert i18n.t('单侧位移像素') == 'Box Edge Nudge Pixels'
    finally:
        i18n.set_lang(original_lang)
