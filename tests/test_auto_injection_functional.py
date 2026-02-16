"""Functional tests for automatic `llm` command injection via sitecustomize."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"

AUTO_CLI_SCRIPT = textwrap.dedent(
    """
    import click


    @click.group()
    def cli() -> None:
        pass


    @cli.command()
    def hello() -> None:
        click.echo("hello")


    if __name__ == "__main__":
        cli()
    """
)


ATTACH_CLI_SCRIPT = textwrap.dedent(
    """
    import click
    from click_llm import attach


    @click.group()
    def cli() -> None:
        pass


    @cli.command()
    def hello() -> None:
        click.echo("hello")


    attach(cli)


    if __name__ == "__main__":
        cli()
    """
)


def _run_cli(
    *args: str,
    script: str = AUTO_CLI_SCRIPT,
    disable_auto: bool = False,
) -> subprocess.CompletedProcess[str]:
    with tempfile.TemporaryDirectory() as tmpdir:
        script_path = Path(tmpdir) / "sample_cli.py"
        script_path.write_text(script, encoding="utf-8")

        env = os.environ.copy()
        existing_pythonpath = env.get("PYTHONPATH")
        env["PYTHONPATH"] = (
            f"{SRC_DIR}{os.pathsep}{existing_pythonpath}"
            if existing_pythonpath
            else str(SRC_DIR)
        )

        if disable_auto:
            env["CLICK_LLM_DISABLE_AUTO"] = "1"
        else:
            env.pop("CLICK_LLM_DISABLE_AUTO", None)

        return subprocess.run(
            [sys.executable, str(script_path), *args],
            capture_output=True,
            text=True,
            check=False,
            env=env,
        )


def test_auto_injection() -> None:
    result = _run_cli("--help")
    assert result.returncode == 0, result.stderr
    assert "llm" in result.stdout


def test_llm_json_command_is_available_without_importing_click_llm() -> None:
    result = _run_cli("llm", "--json")
    assert result.returncode == 0, result.stderr

    payload = json.loads(result.stdout)
    command_names = {entry.get("name") for entry in payload.get("commands", [])}
    assert "hello" in command_names


def test_disable_env_var_turns_off_auto_injection() -> None:
    result = _run_cli("llm", disable_auto=True)
    assert result.returncode != 0
    combined_output = f"{result.stdout}\n{result.stderr}"
    assert "No such command" in combined_output


def test_attach_enables_llm_when_auto_mode_is_disabled() -> None:
    result = _run_cli(
        "llm",
        "--json",
        script=ATTACH_CLI_SCRIPT,
        disable_auto=True,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    command_names = {entry.get("name") for entry in payload.get("commands", [])}
    assert "hello" in command_names
