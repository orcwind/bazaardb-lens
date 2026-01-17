# -*- coding: utf-8 -*-
"""
Top-level proxy package for `ui`.
This package forwards imports to `main_script.ui` so code that does:
    from ui.components import ScrollableFrame
works both in development and in the bundled executable.
"""
from . import components  # noqa: F401

"""
UI组件模块
"""
from .components import IconFrame, ScrollableFrame

__all__ = ['IconFrame', 'ScrollableFrame']
