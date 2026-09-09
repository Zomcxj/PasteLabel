"""Compatibility composition for the UI building mixins."""

from .mixins.toolbar import ToolbarMixin
from .mixins.options_popup import OptionsPopupMixin
from .mixins.cache_menu import CacheMenuMixin
from .mixins.lists import ListsMixin
from .mixins.panels import PanelsMixin


class UIBuilderMixin(ToolbarMixin, OptionsPopupMixin, CacheMenuMixin, ListsMixin, PanelsMixin):
    """Backward-compatible composition of UIBuilder responsibility mixins."""
    pass
