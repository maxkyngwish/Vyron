"""Real, reversible performance helpers.

Only documented Windows settings are touched: Game Mode, background game
recording, the active power plan and the game process priority/affinity.
Nothing here disables security services or uses Realtime priority.
"""
import os
import subprocess

import psutil

HIGH_PERFORMANCE = "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c"
ULTIMATE_PERFORMANCE = "e9a42b02-d5df-448d-aa00-03f14749eb61"

_REGISTRY = {
    "game_mode": (r"Software\Microsoft\GameBar", "AutoGameModeEnabled"),
    "game_dvr": (r"System\GameConfigStore", "GameDVR_Enabled"),
    "app_capture": (r"Software\Microsoft\Windows\CurrentVersion\GameDVR", "AppCaptureEnabled"),
}

def _no_window():
    return getattr(subprocess, "CREATE_NO_WINDOW", 0)


def _run(args, timeout=8):
    try:
        done = subprocess.run(
            args, capture_output=True, text=True, encoding="oem", errors="replace",
            timeout=timeout, creationflags=_no_window(),
        )
        return done.returncode, (done.stdout or "") + (done.stderr or "")
    except Exception:
        return 1, ""


# --------------------------------------------------------------------- registry
def _read_dword(name):
    if os.name != "nt":
        return None
    import winreg

    path, value_name = _REGISTRY[name]
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, path) as key:
            value, _kind = winreg.QueryValueEx(key, value_name)
        return bool(int(value))
    except FileNotFoundError:
        return None
    except OSError:
        return None


def _write_dword(name, enabled):
    if os.name != "nt":
        return False
    import winreg

    path, value_name = _REGISTRY[name]
    try:
        with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, path, 0, winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, value_name, 0, winreg.REG_DWORD, 1 if enabled else 0)
        return True
    except OSError:
        return False


# ------------------------------------------------------------- per-game profile
# Disabling the fullscreen optimisations removes the DWM composition path for
# true-fullscreen games, and the GPU preference picks the discrete adapter on
# hybrid laptops. Both are HKCU-only and reversible.
_LAYERS = r"Software\Microsoft\Windows NT\CurrentVersion\AppCompatFlags\Layers"
_GPU_PREFS = r"Software\Microsoft\DirectX\UserGpuPreferences"
_DIRECTX_GLOBAL = "DirectXUserGlobalSettings"
_FSO_FLAG = "~ DISABLEDXMAXIMIZEDWINDOWEDMODE"


def _read_sz(path, name):
    if os.name != "nt":
        return None
    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, path) as key:
            value, _kind = winreg.QueryValueEx(key, name)
        return str(value)
    except OSError:
        return None


def _write_sz(path, name, value):
    if os.name != "nt":
        return False
    import winreg

    try:
        with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, path, 0, winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, name, 0, winreg.REG_SZ, value)
        return True
    except OSError:
        return False


def _delete_sz(path, name):
    if os.name != "nt":
        return False
    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, path, 0, winreg.KEY_SET_VALUE) as key:
            winreg.DeleteValue(key, name)
        return True
    except OSError:
        return False


def _merge_tokens(current, token):
    tokens = [item for item in (current or "").split() if item]
    if token in tokens:
        return current
    return " ".join([token] + tokens)


def _set_entry(current, pair):
    prefix = pair.split("=", 1)[0] + "="
    parts = [item for item in (current or "").split(";") if item.strip()]
    parts = [item for item in parts if not item.startswith(prefix)]
    parts.append(pair)
    return ";".join(parts) + ";"


def read_game_profile(game_path):
    layers = _read_sz(_LAYERS, game_path) or ""
    gpu = _read_sz(_GPU_PREFS, game_path) or ""
    return {"fullscreen": _FSO_FLAG in layers, "gpu": "GpuPreference=2" in gpu}


def apply_game_profile(game_path):
    """Fullscreen optimisations off + high-performance GPU for one game."""
    if os.name != "nt" or not game_path or not game_path.lower().endswith(".exe"):
        return None
    saved = {
        "layers": _read_sz(_LAYERS, game_path),
        "gpu": _read_sz(_GPU_PREFS, game_path),
        "swap": _read_sz(_GPU_PREFS, _DIRECTX_GLOBAL),
    }
    layers = _merge_tokens(saved["layers"], _FSO_FLAG)
    if layers != saved["layers"]:
        _write_sz(_LAYERS, game_path, layers)
    gpu = _set_entry(saved["gpu"], "GpuPreference=2")
    if gpu != saved["gpu"]:
        _write_sz(_GPU_PREFS, game_path, gpu)
    swap = _set_entry(saved["swap"], "SwapEffectUpgradeEnable=1")
    if swap != saved["swap"]:
        _write_sz(_GPU_PREFS, _DIRECTX_GLOBAL, swap)
    return saved


def restore_game_profile(game_path, saved):
    if os.name != "nt" or not game_path or not saved:
        return False
    for key, path, name in (
        ("layers", _LAYERS, game_path),
        ("gpu", _GPU_PREFS, game_path),
        ("swap", _GPU_PREFS, _DIRECTX_GLOBAL),
    ):
        previous = saved.get(key)
        if previous is None:
            _delete_sz(path, name)
        else:
            _write_sz(path, name, previous)
    return True


# ------------------------------------------------------------- timer resolution
_TIMER = {"active": False}


def set_timer_resolution(enabled):
    """1 ms system timer while playing: steadier frame pacing, released after."""
    if os.name != "nt":
        return False
    try:
        import ctypes

        winmm = ctypes.WinDLL("winmm")
        winmm.timeBeginPeriod.argtypes = [ctypes.c_uint]
        winmm.timeEndPeriod.argtypes = [ctypes.c_uint]
        if enabled and not _TIMER["active"]:
            _TIMER["active"] = winmm.timeBeginPeriod(1) == 0
        elif not enabled and _TIMER["active"]:
            winmm.timeEndPeriod(1)
            _TIMER["active"] = False
        return _TIMER["active"]
    except Exception:
        return False


def timer_active():
    return bool(_TIMER["active"])


# --------------------------------------------------------------------- power plan
def parse_power_plan(text):
    """Extract the active power-plan GUID from `powercfg /getactivescheme` output."""
    import re

    match = re.search(r"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})", text or "", re.I)
    if not match:
        return None
    return match.group(1).lower()


def current_power_plan():
    if os.name != "nt":
        return None
    code, out = _run(["powercfg", "/getactivescheme"])
    if code != 0:
        return None
    guid = parse_power_plan(out)
    if not guid:
        return None
    name = ""
    for line in (out or "").splitlines():
        if guid in line.lower():
            name = line.split(":", 1)[-1].strip().strip("()")
    return {"guid": guid, "name": name}


def set_power_plan(guid):
    if os.name != "nt" or not guid:
        return False
    code, _ = _run(["powercfg", "/setactive", guid])
    return code == 0


def high_performance_plan():
    """Return the High performance GUID when it exists on this PC."""
    if os.name != "nt":
        return None
    code, out = _run(["powercfg", "/list"])
    if code != 0:
        return None
    available = (out or "").lower()
    for guid in (ULTIMATE_PERFORMANCE, HIGH_PERFORMANCE):
        if guid in available:
            return guid
    return None


# --------------------------------------------------------------------- state
def read_state():
    plan = current_power_plan()
    return {
        "game_mode": _read_dword("game_mode"),
        "game_dvr": _read_dword("game_dvr"),
        "app_capture": _read_dword("app_capture"),
        "power_plan": plan,
    }


def apply_system(include_power=True):
    """Apply the reversible Windows tweaks. Returns (previous, results)."""
    previous = read_state()
    results = []
    for name, desired in (("game_mode", True), ("game_dvr", False), ("app_capture", False)):
        results.append({"key": name, "ok": _write_dword(name, desired)})
    if include_power:
        guid = high_performance_plan()
        results.append({"key": "power_plan", "ok": set_power_plan(guid) if guid else False})
    return previous, results


def restore_system(previous):
    """Put back the values captured by apply_system()."""
    if not previous:
        return False
    for name in ("game_mode", "game_dvr", "app_capture"):
        value = previous.get(name)
        if value is not None:
            _write_dword(name, value)
    plan = previous.get("power_plan") or {}
    if plan.get("guid"):
        set_power_plan(plan["guid"])
    return True


# --------------------------------------------------------------------- process
def tune_process(pid):
    """Raise a game process priority, allow all cores and high I/O priority."""
    results = {"priority": False, "affinity": False, "io": False, "eco": False}
    if not pid:
        return results
    try:
        process = psutil.Process(int(pid))
    except Exception:
        return results

    try:
        from . import trim as _trim

        # Make sure the game never sits in Windows' Efficiency mode, and drop
        # any leftover background throttling VYRON applied to it earlier.
        _trim.release(int(pid))
        results["eco"] = _trim.set_efficiency(int(pid), False)
    except Exception:
        pass

    try:
        if os.name == "nt":
            # Above normal is the sane ceiling: High/Realtime can starve the
            # compositor and audio threads, which shows up as frame stutter.
            process.nice(psutil.ABOVE_NORMAL_PRIORITY_CLASS)
        else:
            process.nice(-5)
        results["priority"] = True
    except Exception:
        pass

    try:
        cores = list(range(psutil.cpu_count(logical=True) or 1))
        process.cpu_affinity(cores)
        results["affinity"] = True
    except Exception:
        pass

    if os.name == "nt":
        try:
            import ctypes

            process_set_information = 0x0200
            handle = ctypes.windll.kernel32.OpenProcess(process_set_information, False, int(pid))
            if handle:
                value = ctypes.c_int(3)  # IoPriorityHigh
                status = ctypes.windll.ntdll.NtSetInformationProcess(
                    handle, 33, ctypes.byref(value), ctypes.sizeof(value)
                )
                ctypes.windll.kernel32.CloseHandle(handle)
                results["io"] = status == 0
        except Exception:
            pass
    return results


# --------------------------------------------------------------------- state
def state_is_optimised(state):
    if not state:
        return False
    return bool(
        state.get("game_mode") is True
        and state.get("game_dvr") is False
        and state.get("app_capture") is False
    )


def plan_is_high(state):
    plan = (state or {}).get("power_plan") or {}
    return (plan.get("guid") or "") in (HIGH_PERFORMANCE, ULTIMATE_PERFORMANCE)
