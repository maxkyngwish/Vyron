"""List running desktop applications so a game can be picked in one click."""
import os
import sys

import psutil

_SKIP_EXES = {
    "aggregatorhost.exe", "applicationframehost.exe", "audiodg.exe",
    "backgroundtaskhost.exe", "bravecrashhandler.exe", "bravecrashhandler64.exe",
    "conhost.exe", "crashpad_handler.exe", "ctfmon.exe", "dllhost.exe",
    "dwm.exe", "explorer.exe", "fontdrvhost.exe", "lockapp.exe",
    "python.exe", "pythonw.exe", "runtimebroker.exe", "searchhost.exe",
    "shellexperiencehost.exe", "sihost.exe", "spoolsv.exe",
    "startmenuexperiencehost.exe", "systemsettings.exe", "taskhostw.exe",
    "textinputhost.exe", "widgets.exe", "wmiprvse.exe",
}
_SKIP_TITLES = {"program manager", "windows input experience"}
_GWL_EXSTYLE = -20
_WS_EX_TOOLWINDOW = 0x00000080
_GW_OWNER = 4


def _process_path(pid, cache):
    if pid in cache:
        return cache[pid]
    path = ""
    try:
        path = psutil.Process(pid).exe() or ""
    except Exception:
        path = ""
    cache[pid] = path
    return path


def _is_skipped(path):
    name = os.path.basename(path).lower()
    return not path or name in _SKIP_EXES


def _windows_apps():
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

    user32.IsWindowVisible.argtypes = [wintypes.HWND]
    user32.IsWindowVisible.restype = wintypes.BOOL
    user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
    user32.GetWindowTextLengthW.restype = ctypes.c_int
    user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user32.GetWindowTextW.restype = ctypes.c_int
    user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    user32.GetWindowThreadProcessId.restype = wintypes.DWORD
    user32.GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
    user32.GetWindowLongW.restype = ctypes.c_long
    user32.GetWindow.argtypes = [wintypes.HWND, wintypes.UINT]
    user32.GetWindow.restype = wintypes.HWND
    user32.EnumWindows.argtypes = [ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM), wintypes.LPARAM]
    user32.EnumWindows.restype = wintypes.BOOL
    kernel32.GetCurrentProcessId.restype = wintypes.DWORD

    own_pid = int(kernel32.GetCurrentProcessId())
    cache = {}
    seen = set()
    found = []

    def callback(hwnd, _lparam):
        if not user32.IsWindowVisible(hwnd):
            return True
        if user32.GetWindow(hwnd, _GW_OWNER):
            return True
        if user32.GetWindowLongW(hwnd, _GWL_EXSTYLE) & _WS_EX_TOOLWINDOW:
            return True
        length = user32.GetWindowTextLengthW(hwnd)
        if length <= 0:
            return True
        buffer = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buffer, length + 1)
        title = buffer.value.strip()
        if not title or title.lower() in _SKIP_TITLES or title.lower().endswith("overlay"):
            return True
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        pid = int(pid.value)
        if not pid or pid == own_pid or pid in seen:
            return True
        path = _process_path(pid, cache)
        if _is_skipped(path):
            return True
        seen.add(pid)
        found.append({
            "pid": pid,
            "name": os.path.basename(path),
            "title": title,
            "path": path,
        })
        return True

    callback_ref = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)(callback)
    try:
        user32.EnumWindows(callback_ref, 0)
    except Exception:
        return []
    return found


def _process_list():
    found = []
    own_pid = os.getpid()
    for proc in psutil.process_iter(["pid", "name", "exe"]):
        try:
            info = proc.info
            path = (info.get("exe") or "").strip()
            pid = int(info.get("pid") or 0)
            if not pid or pid == own_pid or _is_skipped(path):
                continue
            found.append({
                "pid": pid,
                "name": os.path.basename(path),
                "title": info.get("name") or os.path.basename(path),
                "path": path,
            })
        except Exception:
            continue
    return found


def list_running_apps():
    """Return running apps with a visible window (Windows) or any executable."""
    apps = []
    if sys.platform.startswith("win"):
        try:
            apps = _windows_apps()
        except Exception:
            apps = []
    if not apps:
        apps = _process_list()
    apps.sort(key=lambda app: (app["name"].lower(), app["title"].lower()))
    return apps
