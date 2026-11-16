"""Run with only the installed wheel's dependency root on PYTHONPATH."""

import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

import clave
from clave import Vault


def main() -> None:
    installed_root = Path(sys.argv[1]).resolve()
    launcher = (
        [str(Path(sys.argv[2]).resolve())]
        if len(sys.argv) > 2
        else [sys.executable, "-m", "clave"]
    )
    assert Path(clave.__file__).is_relative_to(installed_root)
    with TemporaryDirectory() as directory:
        root = Path(directory).resolve()

        def cli(*args: str, success: bool = True) -> subprocess.CompletedProcess[str]:
            result = subprocess.run(
                [*launcher, "--data-dir", str(root), *args],
                cwd=root,
                capture_output=True,
                text=True,
                timeout=45,
                check=False,
            )
            assert (result.returncode == 0) == success, result.stderr
            assert "fake-smoke-password" not in result.stdout + result.stderr
            assert "fake-smoke-token" not in result.stdout + result.stderr
            return result

        assert "Usage" in cli("--help").stdout
        result = cli("store", "smoke.dev", "fake-user", "fake-smoke-password")
        assert "Vault created automatically" in result.stderr
        assert "WARNING" in result.stderr
        assert "fake-smoke-password" not in result.stdout + result.stderr
        assert "fake-smoke-password" not in cli("get", "smoke.dev").stdout
        assert (
            "replaced"
            in cli("store", "smoke.dev", "fake-user", "fake-smoke-password").stdout
        )
        assert "smoke.dev" in cli("list", "--env", "dev").stdout
        assert "smoke.dev" not in cli("list", "--env", "qa").stdout
        vault = Vault(root)
        assert vault.get("smoke.dev").password == "fake-smoke-password"
        cli("secret", "store", "token", "fake-smoke-token")
        assert vault.get_secret("token") == "fake-smoke-token"
        assert "scope: global" in cli("secret", "get", "token").stdout
        cli("secret", "store", "regional_token.qa", "fake-smoke-token")
        assert vault.get_secret("regional_token.qa") == "fake-smoke-token"
        assert "environment: qa" in cli("secret", "get", "regional_token.qa").stdout
        cli("get", "regional_token.qa", success=False)
        cli("secret", "store", "smoke.dev", "fake-smoke-token", success=False)
        cli("store", "bad.id.extra", "fake-user", "fake-smoke-password", success=False)
        cli("secret", "store", "blank", " ", success=False)
        cli("init", success=False)
        cli("delete", "smoke.dev", success=False)
        cli("delete", "smoke.dev", "--yes")
        cli("get", "smoke.dev", success=False)
        cli("delete", "token", "--yes")
        cli("delete", "regional_token.qa", "--yes")
        assert not vault.list()
    print("Clean-wheel import, CLI and encrypted API smoke checks passed.")


if __name__ == "__main__":
    main()
