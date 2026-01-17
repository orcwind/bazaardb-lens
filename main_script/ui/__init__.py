# -*- coding: utf-8 -*-
"""
Package initializer for main_script.ui
Provides exports so that imports like `from ui.components import ...`
work when the package is included by PyInstaller.
"""
from .components import IconFrame, ScrollableFrame  # explicit re-exports

__all__ = ["IconFrame", "ScrollableFrame"]

"""
UI组件模块
"""
from .components import IconFrame, ScrollableFrame

__all__ = ['IconFrame', 'ScrollableFrame']
