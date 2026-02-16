"""Auto-enable click-llm at interpreter startup.

Python imports ``sitecustomize`` automatically if it is importable on ``sys.path``.
Installing this package in an environment therefore enables click-llm globally for
Click CLIs in that environment.
"""

from __future__ import annotations

import os

_DISABLED_VALUES = {"1", "true", "TRUE", "yes", "YES"}

if os.environ.get("CLICK_LLM_DISABLE_AUTO", "") not in _DISABLED_VALUES:
    try:
        from click_llm.inject import autopatch

        autopatch()
    except Exception:
        # Never break startup for unrelated programs.
        if os.environ.get("CLICK_LLM_DEBUG", "") in _DISABLED_VALUES:
            import traceback

            traceback.print_exc()
