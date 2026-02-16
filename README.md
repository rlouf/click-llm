# click-llm

A tiny package that makes Click CLIs self-describing for LLMs.

`click-llm` adds an `llm` command to your CLI so models (and humans) can
discover commands, options, arguments, and command structure.

The command supports one flag:

- `--json`: output machine-readable catalog JSON
- default output: concise text catalog

## Install

```bash
pip install click-llm
```

After install, `llm` is auto-enabled for Click CLIs in that Python environment.

## Usage

```bash
mycli llm
mycli llm --json
```

## Example CLI

```python
import click


@click.group(help="Acme operations CLI.")
def acme() -> None:
    pass


@acme.group(help="Deployment workflows.")
def deploy() -> None:
    pass


@deploy.command(help="Roll out a service release.")
@click.argument("service")
@click.option(
    "--env",
    type=click.Choice(["staging", "prod"]),
    default="staging",
    show_default=True,
)
@click.option("--dry-run", is_flag=True, help="Plan only; do not execute.")
def release(service: str, env: str, dry_run: bool) -> None:
    click.echo(f"release {service} to {env} (dry_run={dry_run})")


@acme.command(help="Show system health.")
@click.option("--json", "as_json", is_flag=True, help="Machine-readable health.")
def health(as_json: bool) -> None:
    click.echo("ok")


if __name__ == "__main__":
    acme()
```

Example output:

```bash
$ acme llm
catalog_version: 1
root_command: acme
commands: 4

### acme deploy release
summary: Roll out a service release.
usage: acme deploy release [OPTIONS] SERVICE
params:
- option `--env`, type=choice, required=False, default="staging"
- option `--dry-run`, type=boolean, required=False, default=false, is_flag=True
- argument `service`, type=text, required=True, nargs=1, default=null
```

```bash
$ acme llm --json
```

The JSON output includes the full command tree and a flattened `commands` list,
which is useful for prompt context, tool routing, and command planning.

## Explicit integration

If you prefer explicit wiring in the host CLI:

```python
import click
from click_llm import attach

@click.group()
def cli():
    pass

attach(cli)
```

## Notes

Auto mode uses a `.pth` startup hook plus a Click monkeypatch
(`click.Group.get_command` and `click.Group.list_commands`).
