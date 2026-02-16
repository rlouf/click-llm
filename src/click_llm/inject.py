"""Command injection helpers for Click CLIs."""

from __future__ import annotations

import json
import threading
from typing import Any, cast
from weakref import WeakKeyDictionary

import click

from .catalog import build_click_catalog, render_catalog_text

_LOCK = threading.Lock()
_INJECTED_COMMANDS: WeakKeyDictionary[click.Group, click.Command] = WeakKeyDictionary()

_PATCHED = False
_PATCH_COMMAND_NAME = "llm"
_ORIG_GET_COMMAND: Any = None
_ORIG_LIST_COMMANDS: Any = None


def _build_llm_command(root_group: click.Group, command_name: str) -> click.Command:
    """Create the injected `llm` command for a specific root group."""

    @click.command(name=command_name, help="Expose command catalog for LLMs")
    @click.option(
        "--json/--no-json",
        "as_json",
        default=False,
        show_default=True,
        help="Emit JSON output",
    )
    def llm_cmd(as_json: bool) -> None:
        ctx = click.get_current_context()
        root_ctx = ctx.find_root()
        if isinstance(root_ctx.command, click.Command):
            root_cmd = root_ctx.command
        else:
            root_cmd = root_group
        root_name = root_ctx.info_name or root_cmd.name or "cli"
        catalog = build_click_catalog(root_cmd, root_name=root_name)
        if as_json:
            click.echo(json.dumps(catalog, indent=2, sort_keys=True))
            return
        click.echo(render_catalog_text(catalog))

    return llm_cmd


def attach(group: click.Group, command_name: str = "llm") -> click.Command:
    """Attach `command_name` directly to a Click group."""
    if command_name in group.commands:
        return group.commands[command_name]
    command = _build_llm_command(group, command_name)
    group.add_command(command, name=command_name)
    return command


def autopatch(command_name: str = "llm") -> None:
    """Monkeypatch Click so root groups expose `command_name` automatically.

    This only affects the current Python process.
    """
    global _PATCHED
    global _PATCH_COMMAND_NAME
    global _ORIG_GET_COMMAND
    global _ORIG_LIST_COMMANDS

    if _PATCHED:
        if _PATCH_COMMAND_NAME != command_name:
            raise RuntimeError(
                f"click-llm already patched with command name {_PATCH_COMMAND_NAME!r}"
            )
        return

    _PATCH_COMMAND_NAME = command_name
    _ORIG_GET_COMMAND = click.Group.get_command
    _ORIG_LIST_COMMANDS = click.Group.list_commands

    def patched_get_command(
        self: click.Group, ctx: click.Context, cmd_name: str
    ) -> click.Command | None:
        command = _ORIG_GET_COMMAND(self, ctx, cmd_name)
        if command is not None:
            return command
        if cmd_name != _PATCH_COMMAND_NAME:
            return None
        if ctx.parent is not None:
            return None
        if _PATCH_COMMAND_NAME in self.commands:
            return None
        with _LOCK:
            injected = _INJECTED_COMMANDS.get(self)
            if injected is None:
                injected = _build_llm_command(self, _PATCH_COMMAND_NAME)
                _INJECTED_COMMANDS[self] = injected
            return injected

    def patched_list_commands(self: click.Group, ctx: click.Context) -> list[str]:
        names = list(_ORIG_LIST_COMMANDS(self, ctx))
        if (
            ctx.parent is None
            and _PATCH_COMMAND_NAME not in self.commands
            and _PATCH_COMMAND_NAME not in names
        ):
            names.append(_PATCH_COMMAND_NAME)
            names.sort()
        return names

    click.Group.get_command = cast(Any, patched_get_command)
    click.Group.list_commands = cast(Any, patched_list_commands)
    _PATCHED = True


def unpatch() -> None:
    """Restore Click methods patched by :func:`autopatch`."""
    global _PATCHED
    if not _PATCHED:
        return
    assert _ORIG_GET_COMMAND is not None
    assert _ORIG_LIST_COMMANDS is not None
    click.Group.get_command = _ORIG_GET_COMMAND
    click.Group.list_commands = _ORIG_LIST_COMMANDS
    _PATCHED = False
