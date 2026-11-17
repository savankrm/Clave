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
    result = cli(["store", "db.dev", "wrong-user", "DO-NOT-PRINT-PASSWORD"])
    assert result.exit_code == 1
    assert "--replace" in result.stderr
    assert (
        "replaced"
        in cli(
            ["store", "db.dev", "fake-user", "DO-NOT-PRINT-PASSWORD", "--replace"]
        ).output
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


def test_hidden_prompts(cli, monkeypatch, tmp_path):
    monkeypatch.setattr("clave.cli.interactive", lambda: True)
    result = cli(["store", "db.dev", "fake-user"], input="HIDDEN-FAKE-PASSWORD\n")
    assert result.exit_code == 0, result.output
    assert "HIDDEN-FAKE" not in result.output
    assert "Password:" in result.output
    result = cli(["store", "db.dev", "other"], input="new-fake\ny\n")
    assert result.exit_code == 0, result.output
    assert (
        "'db.dev' is already saved. Replace it with the new credential? [y/N]"
        in result.output
    )
    assert "new-fake" not in result.output
    assert Vault(tmp_path).get("db.dev").password == "new-fake"
    assert "other" in cli(["get", "db.dev"]).output
    assert cli(["secret", "store", "api_token"], input="hidden-token\n").exit_code == 0
    for answer in ("", "n"):
        result = cli(["secret", "store", "api_token"], input=f"new-token\n{answer}\n")
        assert result.exit_code == 1
        assert (
            "'api_token' is already saved. Replace it with the new secret? [y/N]"
            in result.output
        )
        assert "Kept your saved secret." in result.stderr
        assert "new-token" not in result.output
        assert Vault(tmp_path).get_secret("api_token") == "hidden-token"
    result = cli(["secret", "store", "api_token"], input="new-token\ny\n")
    assert result.exit_code == 0, result.output
    assert Vault(tmp_path).get_secret("api_token") == "new-token"
    result = cli(["secret", "store", "api_token", "--replace"], input="another-token\n")
    assert result.exit_code == 0, result.output
    assert "already saved" not in result.output
    assert Vault(tmp_path).get_secret("api_token") == "another-token"
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


def test_recovery_commands(tmp_path, monkeypatch):
    runner = CliRunner()
    source, target = tmp_path / "source", tmp_path / "target"
    archive = tmp_path / "backup.clave"
    passphrase = "fake recovery passphrase"
    value = "FAKE-SECRET-NOT-FOR-OUTPUT"
    Vault(source).store_secret("token", value)
    assert (
        runner.invoke(
            app, ["--data-dir", str(source), "backup", str(archive)]
        ).exit_code
        == 1
    )
    assert not archive.exists()
    monkeypatch.setattr("clave.cli.interactive", lambda: True)
    result = runner.invoke(
        app,
        ["--data-dir", str(source), "backup", str(archive)],
        input=f"{passphrase}\n{passphrase}\n",
    )
    assert result.exit_code == 0, result.output
    assert "Repeat for confirmation" in result.output
    assert passphrase not in result.output
    assert value not in result.output
    result = runner.invoke(
        app,
        ["--data-dir", str(target), "restore", str(archive)],
        input=f"{passphrase}\n",
    )
    assert result.exit_code == 0, result.output
    assert passphrase not in result.output
    result = runner.invoke(app, ["--data-dir", str(target), "doctor"])
    assert result.exit_code == 0, result.output
    assert value not in result.output
    assert Vault(target).get_secret("token") == value
