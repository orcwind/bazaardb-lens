# -*- coding: utf-8 -*-
"""
Proxy module so `ui.components` resolves to `main_script.ui.components`.
This avoids changing many import sites and makes PyInstaller include the real module.
"""
from main_script.ui.components import *  # re-export everything

try:
    __all__ = main_script.ui.components.__all__  # type: ignore[name-defined]
except Exception:
    __all__ = [n for n in globals().keys() if not n.startswith('_')]

