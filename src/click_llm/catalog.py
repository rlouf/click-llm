"""Catalog builders for Click command trees."""

from __future__ import annotations

import datetime as dt
import enum
import json
from pathlib import Path
from typing import Any

import click


def _jsonable(value: Any) -> Any:
    """Convert Click metadata values into JSON-safe values."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, enum.Enum):
        # Click uses Sentinel.UNSET for required arguments with no default.
        if type(value).__name__ == "Sentinel" and value.name == "UNSET":
            return None
        raw = value.value
        return raw if isinstance(raw, (str, int, float, bool)) else value.name
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, tuple):
        return [_jsonable(v) for v in value]
    if isinstance(value, list):
        return [_jsonable(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if callable(value):
        name = getattr(value, "__name__", value.__class__.__name__)
        return f"<callable:{name}>"
    return repr(value)


def _serialize_type(param_type: click.ParamType) -> dict[str, Any]:
    info: dict[str, Any] = {
        "name": param_type.name or type(param_type).__name__.lower(),
        "class": type(param_type).__name__,
    }
    if isinstance(param_type, click.types.Choice):
        info["choices"] = list(param_type.choices)
        info["case_sensitive"] = param_type.case_sensitive
    return info


def _serialize_option(param: click.Option) -> dict[str, Any]:
    return {
        "kind": "option",
        "name": param.name or "",
        "flags": [*param.opts, *param.secondary_opts],
        "help": (param.help or "").strip(),
        "required": param.required,
        "default": _jsonable(param.default),
        "multiple": param.multiple,
        "nargs": param.nargs,
        "is_flag": param.is_flag,
        "count": param.count,
        "type": _serialize_type(param.type),
    }


def _serialize_argument(param: click.Argument) -> dict[str, Any]:
    return {
        "kind": "argument",
        "name": param.name or "",
        "required": param.required,
        "default": _jsonable(param.default),
        "nargs": param.nargs,
        "type": _serialize_type(param.type),
    }


def _serialize_params(params: list[click.Parameter]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for param in params:
        if isinstance(param, click.Option):
            out.append(_serialize_option(param))
        elif isinstance(param, click.Argument):
            out.append(_serialize_argument(param))
    return out


def _serialize_command(
    command: click.Command,
    path_parts: list[str],
    *,
    include_hidden: bool,
    is_root: bool = False,
) -> dict[str, Any] | None:
    if command.hidden and not include_hidden and not is_root:
        return None

    path = " ".join(path_parts)
    entry: dict[str, Any] = {
        "path": path,
        "name": path_parts[-1],
        "kind": "group" if isinstance(command, click.Group) else "command",
        "summary": (command.short_help or command.help or "").strip(),
        "hidden": command.hidden,
        "deprecated": bool(command.deprecated),
        "params": _serialize_params(command.params),
        "subcommands": [],
    }
    if isinstance(command, click.Group):
        children: list[dict[str, Any]] = []
        for child_name, child in sorted(command.commands.items()):
            child_entry = _serialize_command(
                child,
                [*path_parts, child_name],
                include_hidden=include_hidden,
            )
            if child_entry is not None:
                children.append(child_entry)
        entry["subcommands"] = children
    return entry


def _flatten(tree_entry: dict[str, Any]) -> list[dict[str, Any]]:
    flat = [
        {
            "path": tree_entry["path"],
            "name": tree_entry["name"],
            "kind": tree_entry["kind"],
            "summary": tree_entry["summary"],
            "hidden": tree_entry["hidden"],
            "deprecated": tree_entry["deprecated"],
            "params": tree_entry["params"],
        }
    ]
    for child in tree_entry.get("subcommands", []):
        flat.extend(_flatten(child))
    return flat


def build_click_catalog(
    root: click.Command,
    root_name: str = "cli",
    include_hidden: bool = False,
) -> dict[str, Any]:
    """Build a structured catalog for a Click command tree."""
    tree = _serialize_command(
        root,
        [root_name],
        include_hidden=include_hidden,
        is_root=True,
    )
    assert tree is not None
    return {
        "catalog_version": 1,
        "generated_at": dt.datetime.now(tz=dt.timezone.utc).isoformat(),
        "root_command": root_name,
        "tree": tree,
        "commands": _flatten(tree),
    }


def _usage_for(path: str, params: list[dict[str, Any]]) -> str:
    tokens = [path]
    if any(p.get("kind") == "option" for p in params):
        tokens.append("[OPTIONS]")
    for param in params:
        if param.get("kind") != "argument":
            continue
        name = str(param.get("name", "arg")).upper()
        nargs = int(param.get("nargs", 1) or 1)
        required = bool(param.get("required", False))
        if nargs == -1:
            name = f"{name}..."
        elif nargs > 1:
            name = " ".join(name for _ in range(nargs))
        tokens.append(name if required else f"[{name}]")
    return " ".join(tokens)


def _fmt(value: Any) -> str:
    return "null" if value is None else json.dumps(value, ensure_ascii=False)


def render_catalog_text(catalog: dict[str, Any]) -> str:
    """Render a concise text catalog intended for LLM prompts."""
    lines = [
        f"catalog_version: {catalog.get('catalog_version')}",
        f"generated_at: {catalog.get('generated_at')}",
        f"root_command: {catalog.get('root_command')}",
        "",
    ]
    commands = list(catalog.get("commands", []))
    lines.append(f"commands: {len(commands)}")
    for command in commands:
        path = str(command.get("path", "")).strip()
        if not path:
            continue
        lines.append("")
        lines.append(f"### {path}")
        lines.append(f"kind: {command.get('kind', 'command')}")
        summary = str(command.get("summary", "") or "").strip()
        if summary:
            lines.append(f"summary: {summary}")
        params = list(command.get("params", []))
        lines.append(f"usage: {_usage_for(path, params)}")
        if not params:
            lines.append("params: none")
            continue
        lines.append("params:")
        for param in params:
            if param.get("kind") == "argument":
                lines.append(
                    "- argument `{}`, type={}, required={}, nargs={}, default={}".format(
                        param.get("name", ""),
                        param.get("type", {}).get("name", "unknown"),
                        param.get("required", False),
                        param.get("nargs", 1),
                        _fmt(param.get("default")),
                    )
                )
                continue
            flags = ", ".join(str(f) for f in param.get("flags", []))
            line = "- option `{}`, type={}, required={}, default={}".format(
                flags,
                param.get("type", {}).get("name", "unknown"),
                param.get("required", False),
                _fmt(param.get("default")),
            )
            if param.get("is_flag", False):
                line += ", is_flag=True"
            if param.get("multiple", False):
                line += ", multiple=True"
            lines.append(line)
            help_text = str(param.get("help", "") or "").strip()
            if help_text:
                lines.append(f"  help: {help_text}")
    return "\n".join(lines)
