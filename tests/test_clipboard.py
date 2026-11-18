import json
import subprocess
from unittest.mock import Mock

import pytest

from clave import ClaveError
from clave.clipboard import copy_password


@pytest.mark.parametrize(
    ("platform", "display", "tools", "executable"),
    [
        ("win32", {}, [], "powershell.exe"),
        ("darwin", {}, [], "osascript"),
        ("linux", {"WAYLAND_DISPLAY": "wayland-0"}, ["wl-copy"], "wl-copy"),
        ("linux", {"DISPLAY": ":0"}, ["xclip"], "xclip"),
        ("linux", {"DISPLAY": ":0"}, ["xsel"], "xsel"),
    ],
)
def test_clipboard_uses_standard_input(
    monkeypatch, platform, display, tools, executable
):
    monkeypatch.setattr("clave.clipboard.sys.platform", platform)
    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)
    monkeypatch.delenv("DISPLAY", raising=False)
    for key, value in display.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setattr(
        "clave.clipboard.shutil.which",
        lambda tool: f"/test-bin/{tool}" if tool in tools else None,
    )
    run = Mock()
    monkeypatch.setattr("clave.clipboard.subprocess.run", run)

    password = " FAKE-café-🔑\n"
    copy_password(password)
    run.assert_called_once()
    (command,), options = run.call_args
    assert command[0].endswith(executable)
    assert password not in " ".join(command)
    if platform == "darwin":
        assert json.loads(options["input"]) == password
    else:
        assert options["input"] == password.encode("utf-8")
    assert options["stdout"] == options["stderr"] == subprocess.DEVNULL
    assert options["check"]


def test_clipboard_rejects_null_and_unavailable_session(monkeypatch):
    monkeypatch.setattr("clave.clipboard.sys.platform", "linux")
    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)
    monkeypatch.delenv("DISPLAY", raising=False)
    run = Mock()
    monkeypatch.setattr("clave.clipboard.subprocess.run", run)
    with pytest.raises(ClaveError, match="null character"):
        copy_password("fake\0password")
    with pytest.raises(ClaveError, match="Clipboard unavailable"):
        copy_password("fake password")
    run.assert_not_called()


def test_clipboard_error_keeps_tool_output_private(monkeypatch):
    monkeypatch.setattr("clave.clipboard.sys.platform", "darwin")
    password = "FAKE-CLIPBOARD-PASSWORD"
    error = subprocess.CalledProcessError(1, ["osascript"], stderr=password)
    monkeypatch.setattr("clave.clipboard.subprocess.run", Mock(side_effect=error))
    with pytest.raises(ClaveError, match="Could not copy") as exc:
        copy_password(password)
    assert password not in str(exc.value)
