"""Command line interface for local vaults."""

import sys
from collections.abc import Callable
from functools import wraps
from pathlib import Path
from typing import Any

import typer
from prompt_toolkit import PromptSession
from prompt_toolkit.application import get_app_session
from prompt_toolkit.history import DummyHistory
from prompt_toolkit.utils import is_dumb_terminal

# Parser errors come from Typer's vendored Click, not standalone Click.
from typer import _click as click
from typer.core import TyperGroup

from .clipboard import copy_password
from .exceptions import ClaveError, EntryAlreadyExists
from .identifiers import identifier, nonblank, secret_identifier
from .models import EntryType, StoreResult
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
        except click.exceptions.MissingParameter as exc:
            name = exc.param.name if exc.param is not None else None
            label = {"id": "ID", "username": "USERNAME"}.get(name or "")
            message = f"missing argument {label}" if label else "missing required input"
            typer.echo(f"Error: {message}. Run clave --help.", err=True)
            raise SystemExit(2) from None
        except click.ClickException:
            # Parser messages may include raw arguments, including secrets.
            typer.echo(
                "Error: invalid command or arguments. Run clave --help.", err=True
            )
            raise SystemExit(2) from None
        except (typer.Abort, EOFError, KeyboardInterrupt):
            typer.echo("Error: interactive input unavailable or cancelled.", err=True)
            raise SystemExit(1) from None


app = typer.Typer(
    cls=SafeGroup,
    pretty_exceptions_enable=False,
    invoke_without_command=True,
    no_args_is_help=False,
    subcommand_metavar="[COMMAND [ARGS]...]",
    help="Local encrypted vault. Run clave without a command to open the menu.",
)
secrets = typer.Typer(help="Manage standalone secrets; values are never displayed.")
app.add_typer(secrets, name="secret")


def friendly(fn: Callable[..., Any]) -> Callable[..., Any]:
    @wraps(fn)
    def wrapped(*args: Any, **kwargs: Any) -> Any:
        try:
            return fn(*args, **kwargs)
        except EntryAlreadyExists:
            typer.echo(
                "Error: Entry already exists. Use --replace to overwrite it.", err=True
            )
            raise typer.Exit(1) from None
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
    ctx: typer.Context,
    data_dir: Path | None = typer.Option(
        None, help="Isolated vault root (both key and database)."
    ),
) -> None:
    if ctx.invoked_subcommand is None and not terminal_session():
        typer.echo(ctx.get_help())
        raise typer.Exit(2)
    ctx.obj = Vault(data_dir=data_dir)
    if ctx.invoked_subcommand is None:
        run_menu(ctx)


def vault(ctx: typer.Context) -> Vault:
    instance = ctx.find_object(Vault)
    if instance is None:
        raise ClaveError("Vault context is unavailable.")
    return instance


def interactive() -> bool:
    return sys.stdin.isatty()


def terminal_session() -> bool:
    return interactive() and sys.stdout.isatty()


def value_or_prompt(value: str | None, label: str, *, masked: bool = False) -> str:
    if value is not None:
        typer.echo(
            "WARNING: positional secrets can be exposed in shell history and process arguments.",
            err=True,
        )
    else:
        if not interactive():
            raise typer.Abort()
        if masked and terminal_session() and not is_dumb_terminal():
            # An explicit output keeps prompt_toolkit on its masked renderer.
            session = PromptSession[str](
                history=DummyHistory(), output=get_app_session().output
            )
            try:
                value = session.prompt(f"{label}: ", is_password=True)
            except (EOFError, KeyboardInterrupt):
                raise typer.Abort() from None
        else:
            value = typer.prompt(label, hide_input=True)
    nonblank(value)
    return value


def store_with_confirmation(
    entry_id: str, kind: EntryType, replace: bool, write: Callable[[bool], StoreResult]
) -> StoreResult:
    try:
        return write(replace)
    except EntryAlreadyExists:
        if not interactive():
            raise
        if not typer.confirm(
            f"'{entry_id}' is already saved. Replace it with the new {kind}?",
            default=False,
        ):
            typer.echo(f"Kept your saved {kind}.", err=True)
            raise typer.Exit(1) from None
    return write(True)


def backup_passphrase(*, confirm: bool = False) -> str:
    if not interactive():
        raise typer.Abort()
    passphrase: str = typer.prompt(
        "Backup passphrase", hide_input=True, confirmation_prompt=confirm
    )
    return passphrase


@app.command()
@friendly
def store(
    ctx: typer.Context,
    id: str,
    username: str,
    password: str | None = typer.Argument(None),
    replace: bool = typer.Option(
        False, "--replace", help="Replace an existing credential without asking."
    ),
) -> None:
    identifier(id)
    nonblank(username)
    instance = vault(ctx)
    password = value_or_prompt(password, "Password", masked=True)
    result = store_with_confirmation(
        id,
        "credential",
        replace,
        lambda allow: instance.store(id, username, password, allow_replace=allow),
    )
    if result.vault_created:
        typer.echo("Vault created automatically. " + RECOVERY, err=True)
    typer.echo(f"Credential {result.action}: {id}")


@app.command()
@friendly
def get(ctx: typer.Context, id: str) -> None:
    credential = vault(ctx).get(id)
    typer.echo(
        f"id: {id}\nenvironment: {id.split('.')[1]}\ntype: credential\nusername: {credential.username}"
    )


@app.command(name="list")
@friendly
def list_entries(ctx: typer.Context, env: str | None = typer.Option(None)) -> None:
    for entry in vault(ctx).list(env):
        typer.echo(f"{entry.id}\t{entry.entry_type}")


@app.command()
@friendly
def find(ctx: typer.Context, query: str, env: str | None = typer.Option(None)) -> None:
    """Search credential and secret names."""
    matches = vault(ctx).find(query, env=env)
    if not matches:
        typer.echo("No matching entries.")
    for entry in matches:
        typer.echo(f"{entry.id}\t{entry.entry_type}")


@app.command()
@friendly
def copy(ctx: typer.Context, id: str) -> None:
    """Copy a credential password to the local clipboard."""
    copy_password(vault(ctx).get(id).password)
    typer.echo("Password copied to the clipboard.")
    typer.echo("Clipboard history or sync may retain the password.", err=True)


def view_entries(ctx: typer.Context) -> None:
    query: str = typer.prompt(
        "Search names (Enter to browse)", default="", show_default=False
    )
    if query.strip():
        find(ctx, query, env=None)
    else:
        env: str = typer.prompt(
            "Environment (Enter for all)", default="", show_default=False
        )
        list_entries(ctx, env=env or None)


@app.command()
@friendly
def doctor(ctx: typer.Context) -> None:
    """Check the selected vault for problems without displaying its contents."""
    vault(ctx).doctor()
    typer.echo("Vault checks passed.")
    if sys.platform == "win32":
        typer.echo("Review vault folder access in Windows Security properties.")


@app.command()
@friendly
def backup(ctx: typer.Context, path: Path) -> None:
    """Save an encrypted backup to a new file."""
    vault(ctx).backup(path, backup_passphrase(confirm=True))
    typer.echo("Encrypted backup saved.")


@app.command()
@friendly
def restore(ctx: typer.Context, path: Path) -> None:
    """Restore an encrypted backup into a fresh vault."""
    vault(ctx).restore(path, backup_passphrase())
    typer.echo("Encrypted backup restored.")


@app.command()
@friendly
def delete(
    ctx: typer.Context,
    id: str,
    yes: bool = typer.Option(
        False, "--yes", help="Bypass interactive deletion confirmation."
    ),
) -> None:
    secret_identifier(id)
    if not yes:
        if not interactive():
            raise typer.Abort()
        if not typer.confirm(
            f"Delete {id}? Copies may remain in storage or backups.",
            default=False,
        ):
            typer.echo("Kept your saved entry.", err=True)
            raise typer.Exit(1)
    vault(ctx).delete(id)
    typer.echo(f"Entry deleted: {id}")


@secrets.command(name="store")
@friendly
def secret_store(
    ctx: typer.Context,
    id: str,
    value: str | None = typer.Argument(None),
    replace: bool = typer.Option(
        False, "--replace", help="Replace an existing secret without asking."
    ),
) -> None:
    secret_identifier(id)
    instance = vault(ctx)
    value = value_or_prompt(value, "Value")
    result = store_with_confirmation(
        id,
        "secret",
        replace,
        lambda allow: instance.store_secret(id, value, allow_replace=allow),
    )
    if result.vault_created:
        typer.echo("Vault created automatically. " + RECOVERY, err=True)
    typer.echo(f"Secret {result.action}: {id}")


@secrets.command(name="get")
@friendly
def secret_get(ctx: typer.Context, id: str) -> None:
    vault(ctx).get_secret(id)
    scope = "scope: global" if "." not in id else f"environment: {id.split('.')[1]}"
    typer.echo(f"id: {id}\n{scope}\ntype: secret")


def run_menu(ctx: typer.Context) -> None:
    credential_name = "Credential name (e.g. database.dev)"
    secret_name = "Secret name (e.g. api_token or api_token.qa)"
    actions: dict[str, tuple[str, Callable[[], None]]] = {
        "1": (
            "Save a credential",
            lambda: store(
                ctx,
                typer.prompt(credential_name),
                typer.prompt("Username"),
                password=None,
                replace=False,
            ),
        ),
        "2": (
            "Save a secret",
            lambda: secret_store(
                ctx, typer.prompt(secret_name), value=None, replace=False
            ),
        ),
        "3": ("View entries", lambda: view_entries(ctx)),
        "4": ("Inspect a credential", lambda: get(ctx, typer.prompt(credential_name))),
        "5": ("Inspect a secret", lambda: secret_get(ctx, typer.prompt(secret_name))),
        "6": (
            "Delete an entry",
            lambda: delete(ctx, typer.prompt("Entry name"), yes=False),
        ),
        "7": ("Check vault health", lambda: doctor(ctx)),
        "8": (
            "Back up vault",
            lambda: backup(ctx, Path(typer.prompt("New backup file"))),
        ),
        "9": (
            "Restore into this vault location",
            lambda: restore(ctx, Path(typer.prompt("Backup file to restore"))),
        ),
    }
    labels = "\n".join(
        f"  {typer.style(key, fg=typer.colors.CYAN)}  {label}"
        for key, (label, _) in actions.items()
    )
    header = typer.style("Clave", fg=typer.colors.CYAN, bold=True)
    menu = f"\n{header} | Local encrypted vault\n\n{labels}\n  0  Exit\n"
    while True:
        typer.echo(menu)
        while True:
            choice: str = typer.prompt("Choose an action", default="0")
            choice = choice.strip()
            if choice == "0":
                return
            action = actions.get(choice)
            if action is not None:
                break
            typer.echo("Choose a number from 0 to 9.", err=True)
        try:
            action[1]()
        except typer.Exit:
            # Command feedback is already displayed. Return to the menu.
            continue
