import pytest
from typer.testing import CliRunner

from clave import Vault
from clave.cli import app


@pytest.fixture
def cli(tmp_path):
    runner = CliRunner()

    def run(args, **kwargs):
        return runner.invoke(app, ["--data-dir", str(tmp_path), *args], **kwargs)

    return run


def test_cli_metadata(cli):
    result = cli(["store", "db.dev", "fake-user", "DO-NOT-PRINT-PASSWORD"])
    assert result.exit_code == 0, result.output
    assert "Credential created: db.dev" in result.stdout
    assert "Vault created automatically" in result.stderr
    assert "WARNING" in result.stderr
    assert "DO-NOT-PRINT" not in result.output
    assert (
        "replaced"
        in cli(["store", "db.dev", "fake-user", "DO-NOT-PRINT-PASSWORD"]).output
    )
    assert "fake-user" in cli(["get", "db.dev"]).output
    assert "DO-NOT-PRINT" not in cli(["get", "db.dev"]).output
    assert "db.dev" in cli(["list", "--env", "dev"]).output
    assert "db.dev" not in cli(["list", "--env", "qa"]).output
    assert cli(["delete", "db.dev"]).exit_code != 0
    assert cli(["delete", "db.dev", "--yes"]).exit_code == 0
    assert cli(["get", "db.dev"]).exit_code != 0


def test_secret_commands(cli):
    assert cli(["secret", "store", "api_token", "DO-NOT-PRINT-TOKEN"]).exit_code == 0
    result = cli(["secret", "get", "api_token"])
    assert result.exit_code == 0
    assert "DO-NOT-PRINT" not in result.output
    assert "type: secret" in result.output
    assert "scope: global" in result.output
    assert "environment:" not in result.output
    assert cli(["secret", "store", "api_token.qa", "scoped-token"]).exit_code == 0
    scoped = cli(["secret", "get", "api_token.qa"])
    assert scoped.exit_code == 0
    assert "environment: qa" in scoped.output
    assert "api_token" not in cli(["list", "--env", "dev"]).output
    assert "api_token.qa" in cli(["list", "--env", "qa"]).output


def test_hidden_prompts(cli, monkeypatch):
    monkeypatch.setattr("clave.cli.interactive", lambda: True)
    result = cli(["store", "db.dev", "fake-user"], input="HIDDEN-FAKE-PASSWORD\n")
    assert result.exit_code == 0, result.output
    assert "HIDDEN-FAKE" not in result.output
    assert "Password:" in result.output
    assert cli(["store", "db.dev", "other"], input="new-fake\n").exit_code == 0
    assert "other" in cli(["get", "db.dev"]).output
    assert cli(["secret", "store", "api_token"], input="hidden-token\n").exit_code == 0
    assert cli(["secret", "store", "api_token"], input="new-token\n").exit_code == 0
    assert cli(["delete", "db.dev"], input="n\n").exit_code != 0
    assert "[y/N]" in cli(["delete", "db.dev"], input="n\n").output
    assert cli(["get", "db.dev"]).exit_code == 0
    assert cli(["delete", "db.dev"], input="y\n").exit_code == 0


def test_noninteractive(cli):
    assert cli(["store", "db.dev", "u"]).exit_code != 0
    assert cli(["secret", "store", "api_token"]).exit_code != 0
    assert cli(["store", "db.dev", "u", " "]).exit_code != 0


@pytest.mark.parametrize(
    ("args", "message"),
    [
        (["store", "missing_dot", "user"], "exactly one dot"),
        (["store", "db.dev", " "], "nonblank"),
        (["secret", "store", "token.with.extra"], "topic.environment"),
    ],
)
def test_invalid_store_does_not_prompt(cli, monkeypatch, args, message):
    def unexpected_prompt(*args, **kwargs):
        pytest.fail("Prompted for a secret before validating the arguments")

    monkeypatch.setattr("clave.cli.interactive", lambda: True)
    monkeypatch.setattr("clave.cli.typer.prompt", unexpected_prompt)
    result = cli(args)
    assert result.exit_code == 1
    assert message in result.stderr


def test_nested_invocation_keeps_its_own_vault(tmp_path, monkeypatch):
    runner = CliRunner()
    first, second = tmp_path / "first", tmp_path / "second"
    Vault(first).store_secret("entry", "one")
    Vault(second).store_secret("entry", "two")

    def confirm(*args, **kwargs):
        result = runner.invoke(
            app, ["--data-dir", str(second), "secret", "get", "entry"]
        )
        assert result.exit_code == 0, result.output

    monkeypatch.setattr("clave.cli.interactive", lambda: True)
    monkeypatch.setattr("clave.cli.typer.confirm", confirm)
    result = runner.invoke(app, ["--data-dir", str(first), "delete", "entry"])
    assert result.exit_code == 0, result.output
    assert Vault(first).list() == []
    assert Vault(second).get_secret("entry") == "two"


def test_missing_argument_reports_only_its_name(cli):
    result = cli(["store", "DO-NOT-ECHO.dev"])
    assert result.exit_code == 2
    assert "missing argument USERNAME" in result.stderr
    assert "DO-NOT-ECHO" not in result.output


def test_removed_init_and_update_commands():
    runner = CliRunner()
    help_result = runner.invoke(app, ["--help"])
    assert help_result.exit_code == 0
    assert " init " not in help_result.stdout
    assert " update " not in help_result.stdout
    assert runner.invoke(app, ["init"]).exit_code != 0
    assert runner.invoke(app, ["update", "db.dev"]).exit_code != 0
    assert runner.invoke(app, ["secret", "update", "api_token"]).exit_code != 0


def test_parser_does_not_echo(cli):
    result = cli(["secret", "store", "api_token", "x", "DO-NOT-ECHO"])
    assert result.exit_code != 0
    assert "DO-NOT-ECHO" not in result.output


def test_help():
    assert CliRunner().invoke(app, ["--help"]).exit_code == 0
