from __future__ import annotations

from dataclasses import dataclass
import ctypes
import ctypes.wintypes
import os
from pathlib import Path
import subprocess
import time
from typing import Iterable

from .config import AppConfig


FACTORIO_STEAM_APP_ID = "427520"
FORBIDDEN_ACHIEVEMENT_ARGS = {
    "--mod-directory",
    "--rcon-port",
    "--rcon-password",
    "--start-server",
    "--start-server-load-scenario",
    "--load-scenario",
    "--create",
    "--map2scenario",
    "--scenario2map",
}
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
KEYEVENTF_KEYUP = 0x0002
SW_RESTORE = 9


class AchievementPolicyError(ValueError):
    pass


class GuiAutomationError(RuntimeError):
    pass


@dataclass(frozen=True)
class WindowRect:
    left: int
    top: int
    right: int
    bottom: int

    @property
    def width(self) -> int:
        return self.right - self.left

    @property
    def height(self) -> int:
        return self.bottom - self.top


def validate_achievement_safe_args(args: Iterable[str]) -> list[str]:
    normalized = [str(arg) for arg in args]
    for index, arg in enumerate(normalized):
        option = arg.split("=", 1)[0]
        if option in FORBIDDEN_ACHIEVEMENT_ARGS:
            raise AchievementPolicyError(f"argument is not achievement-compatible: {option}")
        if index > 0 and normalized[index - 1] in FORBIDDEN_ACHIEVEMENT_ARGS:
            raise AchievementPolicyError(f"argument follows forbidden option: {normalized[index - 1]}")
    return normalized


def launch_vanilla_gui(cfg: AppConfig, *, via_steam: bool = True, args: Iterable[str] = ()) -> subprocess.Popen[bytes] | None:
    safe_args = validate_achievement_safe_args(args)
    if via_steam:
        if safe_args:
            raise AchievementPolicyError("Steam vanilla launch must not include custom Factorio args")
        os.startfile(f"steam://rungameid/{FACTORIO_STEAM_APP_ID}")  # type: ignore[attr-defined]
        return None

    if not cfg.factorio_exe.exists():
        raise FileNotFoundError(f"Factorio executable not found: {cfg.factorio_exe}")
    return subprocess.Popen([str(cfg.factorio_exe), *safe_args], cwd=str(Path.cwd()))


class VanillaGuiDriver:
    """Windows keyboard/mouse executor for the no-mod achievement track."""

    def __init__(self, cfg: AppConfig) -> None:
        if os.name != "nt":
            raise GuiAutomationError("vanilla GUI driver currently supports Windows only")
        self.cfg = cfg
        self.user32 = ctypes.windll.user32

    def launch(self) -> None:
        launch_vanilla_gui(self.cfg, via_steam=True)

    def activate_factorio(self, timeout_seconds: float = 30.0) -> bool:
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            hwnd = self._find_window_containing("Factorio")
            if hwnd:
                self.user32.ShowWindow(hwnd, SW_RESTORE)
                self.user32.SetForegroundWindow(hwnd)
                return True
            time.sleep(0.5)
        return False

    def click(self, x: int, y: int) -> None:
        self.user32.SetCursorPos(int(x), int(y))
        self.user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
        self.user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)

    def press(self, virtual_key: int, duration_seconds: float = 0.05) -> None:
        self.user32.keybd_event(virtual_key, 0, 0, 0)
        time.sleep(duration_seconds)
        self.user32.keybd_event(virtual_key, 0, KEYEVENTF_KEYUP, 0)

    def click_steam_continue_prompt(self, timeout_seconds: float = 15.0) -> bool:
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            hwnd = self._find_steam_prompt()
            if hwnd:
                rect = self._window_rect(hwnd)
                self.user32.SetForegroundWindow(hwnd)
                self.click(rect.left + int(rect.width * 0.66), rect.top + int(rect.height * 0.88))
                return True
            time.sleep(0.25)
        return False

    def _find_steam_prompt(self) -> int | None:
        candidates = []
        for hwnd, title in self._top_level_windows():
            lowered = title.lower()
            if "사용자 지정 인수" in title or "custom arguments" in lowered or title == "Steam":
                rect = self._window_rect(hwnd)
                if 350 <= rect.width <= 900 and 180 <= rect.height <= 500:
                    candidates.append(hwnd)
        return candidates[0] if candidates else None

    def _find_window_containing(self, text: str) -> int | None:
        needle = text.lower()
        for hwnd, title in self._top_level_windows():
            if needle in title.lower():
                return hwnd
        return None

    def _top_level_windows(self) -> list[tuple[int, str]]:
        windows: list[tuple[int, str]] = []

        enum_proc_type = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

        def callback(hwnd: int, _lparam: int) -> bool:
            if not self.user32.IsWindowVisible(hwnd):
                return True
            length = self.user32.GetWindowTextLengthW(hwnd)
            if length <= 0:
                return True
            buffer = ctypes.create_unicode_buffer(length + 1)
            self.user32.GetWindowTextW(hwnd, buffer, length + 1)
            windows.append((int(hwnd), buffer.value))
            return True

        self.user32.EnumWindows(enum_proc_type(callback), 0)
        return windows

    def _window_rect(self, hwnd: int) -> WindowRect:
        rect = ctypes.wintypes.RECT()
        if not self.user32.GetWindowRect(hwnd, ctypes.byref(rect)):
            raise GuiAutomationError("GetWindowRect failed")
        return WindowRect(rect.left, rect.top, rect.right, rect.bottom)
