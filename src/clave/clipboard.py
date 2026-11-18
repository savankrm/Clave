"""Send plain text to the local OS clipboard without echoing it."""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from .exceptions import ClaveError


def _command() -> list[str]:
    if sys.platform == "win32":
        windows = Path(os.environ.get("SystemRoot", r"C:\Windows"))
        powershell = windows / "System32/WindowsPowerShell/v1.0/powershell.exe"
        return [
            str(powershell),
            "-NoProfile",
            "-NonInteractive",
            "-STA",
            "-Command",
            "$utf8 = [System.Text.UTF8Encoding]::new($false, $true); "
            "$reader = [System.IO.StreamReader]::new("
            "[Console]::OpenStandardInput(), $utf8, $false); "
            "Set-Clipboard -Value ($reader.ReadToEnd()) -ErrorAction Stop",
        ]
    if sys.platform == "darwin":
        return [
            "/usr/bin/osascript",
            "-l",
            "JavaScript",
            "-e",
            "ObjC.import('AppKit'); "
            "const data = $.NSFileHandle.fileHandleWithStandardInput.readDataToEndOfFile; "
            "const json = ObjC.unwrap($.NSString.alloc.initWithDataEncoding(data, $.NSUTF8StringEncoding)); "
            "const board = $.NSPasteboard.generalPasteboard; "
            "board.clearContents; "
            "if (!board.setStringForType($(JSON.parse(json)), $.NSPasteboardTypeString)) "
            "throw new Error('Could not write pasteboard');",
        ]
    if sys.platform.startswith("linux"):
        if os.environ.get("WAYLAND_DISPLAY") and (wl_copy := shutil.which("wl-copy")):
            return [wl_copy, "--type", "text/plain;charset=utf-8"]
        if os.environ.get("DISPLAY"):
            if xclip := shutil.which("xclip"):
                return [xclip, "-selection", "clipboard"]
            if xsel := shutil.which("xsel"):
                return [xsel, "--clipboard", "--input"]
        raise ClaveError(
            "Clipboard unavailable. Use a desktop session with wl-copy on Wayland "
            "or xclip or xsel on X11."
        )
    raise ClaveError("Clipboard copying is unavailable on this platform.")


def copy_password(password: str) -> None:
    if "\0" in password:
        raise ClaveError(
            "This password contains a null character that the clipboard cannot preserve."
        )
    command = _command()
    try:
        # The macOS helper decodes JSON and explicitly sets a plain-text entry.
        data = json.dumps(password) if sys.platform == "darwin" else password
        subprocess.run(
            command,
            input=data.encode("utf-8"),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError, UnicodeError):
        raise ClaveError(
            "Could not copy to the clipboard. Check your desktop session."
        ) from None
