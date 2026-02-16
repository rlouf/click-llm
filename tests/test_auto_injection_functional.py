"""Functional tests for automatic `llm` command injection via .pth startup hook."""

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
PTH_FILE = REPO_ROOT / "click_llm.pth"

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


LAUNCHER_SCRIPT = textwrap.dedent(
    """
    import runpy
    import site
    import sys

    # site.addsitedir() processes .pth files with the same machinery used
    # during interpreter startup. We use it here to test hook behavior
    # without building and installing a wheel inside this test.
    pth_dir = sys.argv[1]
    cli_script = sys.argv[2]
    cli_args = sys.argv[3:]

    site.addsitedir(pth_dir)
    sys.argv = [cli_script, *cli_args]
    runpy.run_path(cli_script, run_name="__main__")
    """
)


def _run_cli(
    *args: str,
    script: str = AUTO_CLI_SCRIPT,
    disable_auto: bool = False,
) -> subprocess.CompletedProcess[str]:
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        script_path = tmpdir_path / "sample_cli.py"
        script_path.write_text(script, encoding="utf-8")
        launcher_path = tmpdir_path / "launcher.py"
        launcher_path.write_text(LAUNCHER_SCRIPT, encoding="utf-8")
        pth_dir = tmpdir_path / "site-packages"
        pth_dir.mkdir(parents=True, exist_ok=True)
        (pth_dir / "click_llm.pth").write_text(
            PTH_FILE.read_text(encoding="utf-8"),
            encoding="utf-8",
        )

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
            [sys.executable, str(launcher_path), str(pth_dir), str(script_path), *args],
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


def test_text_output_lists_commands_but_not_groups() -> None:
    result = _run_cli("llm")
    assert result.returncode == 0, result.stderr
    assert "kind: group" not in result.stdout
    assert result.stdout.count("\n### ") == 1


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


def test_setup_py_build_py_copies_pth_file() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        result = subprocess.run(
            [
                sys.executable,
                "setup.py",
                "build_py",
                "--build-lib",
                tmpdir,
            ],
            capture_output=True,
            text=True,
            check=False,
            cwd=REPO_ROOT,
        )
        assert result.returncode == 0, result.stderr
        built_pth = Path(tmpdir) / "click_llm.pth"
        assert built_pth.exists()
        assert built_pth.read_text(encoding="utf-8") == PTH_FILE.read_text(
            encoding="utf-8"
        )
