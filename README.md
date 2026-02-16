# click-llm

Minimal library that adds an `llm` command to Click CLIs.

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

## Disable auto mode

Set:

```bash
export CLICK_LLM_DISABLE_AUTO=1
```

## Explicit integration (preferred)

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

Auto mode uses Python's `sitecustomize` startup hook plus a Click monkeypatch
(`click.Group.get_command` and `click.Group.list_commands`).
