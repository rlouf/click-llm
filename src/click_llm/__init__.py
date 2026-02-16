"""Public API for click-llm."""

from __future__ import annotations

import os
from typing import Any

_TRUTHY_VALUES = {"1", "true", "TRUE", "yes", "YES"}


def _autopatch_if_enabled() -> None:
    """Enable Click monkeypatching when auto mode is not disabled."""
    if os.environ.get("CLICK_LLM_DISABLE_AUTO", "") in _TRUTHY_VALUES:
        return
    try:
        from .inject import autopatch

        autopatch()
    except Exception:
        # Never break startup for unrelated programs.
        if os.environ.get("CLICK_LLM_DEBUG", "") in _TRUTHY_VALUES:
            import traceback

            traceback.print_exc()


def attach(*args: Any, **kwargs: Any) -> Any:
    from .inject import attach as _attach

    return _attach(*args, **kwargs)


def autopatch(*args: Any, **kwargs: Any) -> Any:
    from .inject import autopatch as _autopatch

    return _autopatch(*args, **kwargs)


def unpatch(*args: Any, **kwargs: Any) -> Any:
    from .inject import unpatch as _unpatch

    return _unpatch(*args, **kwargs)


def build_click_catalog(*args: Any, **kwargs: Any) -> Any:
    from .catalog import build_click_catalog as _build_click_catalog

    return _build_click_catalog(*args, **kwargs)


def render_catalog_text(*args: Any, **kwargs: Any) -> Any:
    from .catalog import render_catalog_text as _render_catalog_text

    return _render_catalog_text(*args, **kwargs)


__all__ = [
    "attach",
    "autopatch",
    "build_click_catalog",
    "render_catalog_text",
    "unpatch",
]
