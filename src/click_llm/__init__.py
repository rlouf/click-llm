"""Public API for click-llm."""

from .catalog import build_click_catalog, render_catalog_text
from .inject import attach, autopatch, unpatch

__all__ = [
    "attach",
    "autopatch",
    "build_click_catalog",
    "render_catalog_text",
    "unpatch",
]
