"""Metadata-only command line interface."""

import sys
from collections.abc import Callable
from functools import wraps
from pathlib import Path
from typing import Any

import typer
from typer import _click as click
from typer.core import TyperGroup
from typer.exceptions import Abort

from .exceptions import ClaveError
from .identifiers import nonblank
from .storage import RECOVERY
from .vault import Vault


class SafeGroup(TyperGroup):
    def main(self, *args: Any, **kwargs: Any) -> Any:
        kwargs["standalone_mode"] = False
        try:
            result = super().main(*args, **kwargs)
            if isinstance(result, int) and result != 0:
                raise SystemExit(result)
            return result
        except click.ClickException:
            typer.echo(
                "Error: invalid command or arguments. Run clave --help.", err=True
            )
            raise SystemExit(2) from None
        except (Abort, EOFError, KeyboardInterrupt):
            typer.echo("Error: interactive input unavailable or cancelled.", err=True)
            raise SystemExit(1) from None


app = typer.Typer(
    cls=SafeGroup,
    pretty_exceptions_enable=False,
    no_args_is_help=True,
    help="Local encrypted vault. Reads display metadata only.",
)
secrets = typer.Typer(help="Manage standalone secrets; values are never displayed.")
app.add_typer(secrets, name="secret")
_vault: Vault | None = None


def friendly(fn: Callable[..., Any]) -> Callable[..., Any]:
    @wraps(fn)
    def wrapped(*args: Any, **kwargs: Any) -> Any:
        try:
            return fn(*args, **kwargs)
        except (ClaveError, OSError) as exc:
            message = (
                str(exc)
                if isinstance(exc, ClaveError)
                else "Vault files are inaccessible."
            )
            typer.echo(f"Error: {message}", err=True)
            raise typer.Exit(1) from None

    return wrapped


@app.callback()
def configure(
    data_dir: Path | None = typer.Option(
        None, help="Isolated vault root (both key and database)."
    ),
) -> None:
    global _vault
    _vault = Vault(data_dir=data_dir)


def vault() -> Vault:
    assert _vault is not None
    return _vault


def interactive() -> bool:
    return sys.stdin.isatty()


def value_or_prompt(value: str | None, label: str) -> str:
    if value is not None:
        typer.echo(
            "WARNING: positional secrets can be exposed in shell history and process arguments.",
            err=True,
        )
    else:
        if not interactive():
            raise Abort()
        value = typer.prompt(label, hide_input=True)
    nonblank(value)
    return value


@app.command()
@friendly
def store(id: str, username: str, password: str | None = typer.Argument(None)) -> None:
    result = vault().store(id, username, value_or_prompt(password, "Password"))
    if result.vault_created:
        typer.echo("Vault created automatically. " + RECOVERY, err=True)
    typer.echo(f"Credential {result.action}: {id}")


@app.command()
@friendly
def get(id: str) -> None:
    credential = vault().get(id)
    typer.echo(
        f"id: {id}\nenvironment: {id.split('.')[1]}\ntype: credential\nusername: {credential.username}"
    )


@app.command(name="list")
@friendly
def list_entries(env: str | None = typer.Option(None)) -> None:
    for entry in vault().list(env):
        typer.echo(f"{entry.id}\t{entry.entry_type}")


@app.command()
@friendly
def delete(
    id: str,
    yes: bool = typer.Option(
        False, "--yes", help="Bypass interactive deletion confirmation."
    ),
) -> None:
    if not yes:
        if not interactive():
            raise Abort()
        typer.confirm(
            f"Delete {id}? SQLite deletion is not forensic erasure.",
            default=False,
            abort=True,
        )
    vault().delete(id)
    typer.echo(f"Entry deleted: {id}")


@secrets.command(name="store")
@friendly
def secret_store(id: str, value: str | None = typer.Argument(None)) -> None:
    result = vault().store_secret(id, value_or_prompt(value, "Value"))
    if result.vault_created:
        typer.echo("Vault created automatically. " + RECOVERY, err=True)
    typer.echo(f"Secret {result.action}: {id}")


@secrets.command(name="get")
@friendly
def secret_get(id: str) -> None:
    vault().get_secret(id)
    scope = "scope: global" if "." not in id else f"environment: {id.split('.')[1]}"
    typer.echo(f"id: {id}\n{scope}\ntype: secret")
