"""Real background-app trimming for Windows.

Browsers, launchers and sync clients keep polling the CPU, animating
off-screen and holding RAM while a game runs. VYRON applies Windows' own
Efficiency mode (EcoQoS) + background priority and trims their working set,
then restores everything when the game exits.

This module never terminates a process: closing an app stays an explicit
user action in the interface.
"""
import json
import os
import time

import psutil

IS_WINDOWS = os.name == "nt"

# Suspended apps are written here so a crash or a hard kill cannot leave a
# frozen window behind: the next VYRON start resumes them.
_SUSPEND_FILE = os.path.join(os.path.expanduser("~"), ".vyron_suspended.json")

# Windows process access rights / priority classes.
_SET_INFORMATION = 0x0200
_SET_QUOTA = 0x0100
_QUERY_LIMITED = 0x1000
_SUSPEND_RESUME = 0x0800
# Below Normal, not Idle: if VYRON is ever killed mid-session the leftovers
# stay perfectly usable instead of dragging the app down.
_BACKGROUND_PRIORITY = 0x00004000

# SetProcessInformation(ProcessPowerThrottling, ...)
_POWER_THROTTLING = 4
_POWER_VERSION = 1
_EXECUTION_SPEED = 0x1

# Never touched: shell/system, security, audio, voice chat, capture and
# hardware control tools. Anything living under %WINDIR% is skipped too.
_SYSTEM_EXES = {
    "system", "registry", "memory compression", "smss.exe", "csrss.exe",
    "wininit.exe", "winlogon.exe", "services.exe", "lsass.exe", "svchost.exe",
    "dwm.exe", "explorer.exe", "fontdrvhost.exe", "ctfmon.exe", "sihost.exe",
    "taskhostw.exe", "runtimebroker.exe", "searchhost.exe", "searchapp.exe",
    "startmenuexperiencehost.exe", "shellexperiencehost.exe",
    "textinputhost.exe", "applicationframehost.exe", "conhost.exe",
    "dllhost.exe", "spoolsv.exe", "wmiprvse.exe", "audiodg.exe",
    "securityhealthservice.exe", "securityhealthsystray.exe",
    "smartscreen.exe", "msmpeng.exe", "nissrv.exe", "mpdefendercoreservice.exe",
    "lockapp.exe", "logonui.exe", "userinit.exe", "backgroundtaskhost.exe",
    "aggregatorhost.exe", "widgets.exe", "systemsettings.exe",
    "settingssynchost.exe", "gamebar.exe", "gamebarftserver.exe",
    "xboxgamebar.exe", "gamebarpresencewriter.exe", "python.exe", "pythonw.exe",
    "py.exe", "python3.exe", "java.exe", "javaw.exe",
}

# User apps that must keep full speed: voice chat, streaming/capture and
# hardware/fan control. Throttling those costs more than it wins.
_KEEP_FAST = {
    "discord.exe", "discordcanary.exe", "discordptb.exe", "teams.exe",
    "ms-teams.exe", "zoom.exe", "obs64.exe", "obs32.exe", "obs.exe",
    "streamlabs obs.exe", "voicemeeter.exe", "voicemeeter8.exe",
    "voicemeeter8x64.exe", "voicemeeterpro.exe", "medal.exe",
    "nvcontainer.exe", "nvsphelper64.exe", "nvidia share.exe",
    "nvidia overlay.exe", "msiafterburner.exe", "rtss.exe",
    "rivertunerstatistics.exe", "hwinfo64.exe", "hwinfo32.exe",
    "fancontrol.exe", "nzxt cam.exe", "armourycrate.service.exe",
    "crashpad_handler.exe", "crashreporter.exe",
}

_NEVER = _SYSTEM_EXES | _KEEP_FAST
# Voice/capture/fan-control suites change executable names between versions.
_KEEP_PREFIXES = ("medal", "voicemeeter", "obs64", "obs32", "nvidia", "rtss", "hwinfo")

_PRETTY = {
    "msedge.exe": "Microsoft Edge", "chrome.exe": "Google Chrome",
    "firefox.exe": "Firefox", "brave.exe": "Brave", "opera.exe": "Opera",
    "opera_gx.exe": "Opera GX", "vivaldi.exe": "Vivaldi",
    "msedgewebview2.exe": "Edge WebView2", "iexplore.exe": "Internet Explorer",
    "steam.exe": "Steam", "steamwebhelper.exe": "Steam Web Helper",
    "epicgameslauncher.exe": "Epic Games Launcher",
    "battle.net.exe": "Battle.net", "riotclientservices.exe": "Riot Client",
    "riotclientux.exe": "Riot Client", "galaxyclient.exe": "GOG Galaxy",
    "eadesktop.exe": "EA app", "ubisoftconnect.exe": "Ubisoft Connect",
    "onedrive.exe": "OneDrive", "dropbox.exe": "Dropbox",
    "googledrivefs.exe": "Google Drive", "mega.exe": "MEGA",
    "spotify.exe": "Spotify", "telegram.exe": "Telegram",
    "whatsapp.exe": "WhatsApp", "slack.exe": "Slack",
    "code.exe": "Visual Studio Code", "cursor.exe": "Cursor",
    "wallpaper32.exe": "Wallpaper Engine", "wallpaper64.exe": "Wallpaper Engine",
    "notion.exe": "Notion", "obsidian.exe": "Obsidian",
    "acrobat.exe": "Acrobat", "photoshop.exe": "Photoshop",
    "thunderbird.exe": "Thunderbird", "outlook.exe": "Outlook",
    "windowsapps.exe": "Microsoft Store", "msstore.exe": "Microsoft Store",
}

_THROTTLED = {}  # pid -> {"created": float, "bg": bool, "eco": bool}
_K32 = None
_POWER_STATE = None
_WINDOWS_DIR = None


# ------------------------------------------------------------------ Win32 glue
def _k32():
    global _K32
    if _K32 is None:
        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel32.OpenProcess.restype = wintypes.HANDLE
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel32.CloseHandle.restype = wintypes.BOOL
        kernel32.SetPriorityClass.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        kernel32.SetPriorityClass.restype = wintypes.BOOL
        kernel32.GetPriorityClass.argtypes = [wintypes.HANDLE]
        kernel32.GetPriorityClass.restype = wintypes.DWORD
        kernel32.SetProcessInformation.argtypes = [
            wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD,
        ]
        kernel32.SetProcessInformation.restype = wintypes.BOOL
        kernel32.K32EmptyWorkingSet.argtypes = [wintypes.HANDLE]
        kernel32.K32EmptyWorkingSet.restype = wintypes.BOOL
        _K32 = kernel32
    return _K32


def _power_state_type():
    global _POWER_STATE
    if _POWER_STATE is None:
        import ctypes

        class _State(ctypes.Structure):
            _fields_ = [
                ("Version", ctypes.c_uint),
                ("ControlMask", ctypes.c_uint),
                ("StateMask", ctypes.c_uint),
            ]

        _POWER_STATE = _State
    return _POWER_STATE


def _open(pid, suspend=False):
    """Open a process with the smallest set of rights the caller needs."""
    kernel32 = _k32()
    if suspend:
        handle = kernel32.OpenProcess(
            _SET_INFORMATION | _SUSPEND_RESUME, False, int(pid)
        )
        if not handle:
            handle = kernel32.OpenProcess(_SUSPEND_RESUME, False, int(pid))
        return handle
    handle = kernel32.OpenProcess(
        _SET_INFORMATION | _SET_QUOTA | _QUERY_LIMITED, False, int(pid)
    )
    if not handle:
        handle = kernel32.OpenProcess(_SET_INFORMATION, False, int(pid))
    return handle


def _priority_class(pid):
    try:
        kernel32 = _k32()
        handle = _open(pid)
        if not handle:
            return 0
        try:
            return int(kernel32.GetPriorityClass(handle) or 0)
        finally:
            kernel32.CloseHandle(handle)
    except Exception:
        return 0


def _set_priority(pid, value):
    try:
        kernel32 = _k32()
        handle = _open(pid)
        if not handle:
            return False
        try:
            return bool(kernel32.SetPriorityClass(handle, int(value)))
        finally:
            kernel32.CloseHandle(handle)
    except Exception:
        return False


def set_efficiency(pid, enabled=True):
    """Windows' Efficiency mode: the process only gets CPU nobody else wants."""
    try:
        import ctypes

        kernel32 = _k32()
        handle = _open(pid)
        if not handle:
            return False
        try:
            state = _power_state_type()()
            state.Version = _POWER_VERSION
            state.ControlMask = _EXECUTION_SPEED
            state.StateMask = _EXECUTION_SPEED if enabled else 0
            return bool(kernel32.SetProcessInformation(
                handle, _POWER_THROTTLING, ctypes.byref(state), ctypes.sizeof(state),
            ))
        finally:
            kernel32.CloseHandle(handle)
    except Exception:
        return False


def _empty_working_set(pid):
    try:
        kernel32 = _k32()
        handle = _open(pid)
        if not handle:
            return False
        try:
            if kernel32.K32EmptyWorkingSet(handle):
                return True
        finally:
            kernel32.CloseHandle(handle)
    except Exception:
        pass
    try:
        import ctypes

        psapi = ctypes.WinDLL("psapi")
        kernel32 = _k32()
        handle = _open(pid)
        if not handle:
            return False
        try:
            return bool(psapi.EmptyWorkingSet(handle))
        finally:
            kernel32.CloseHandle(handle)
    except Exception:
        return False


def _rss(pid):
    try:
        return psutil.Process(int(pid)).memory_info().rss / (1024 ** 2)
    except Exception:
        return None


def _foreground_pid():
    try:
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.WinDLL("user32", use_last_error=True)
        user32.GetForegroundWindow.restype = wintypes.HWND
        user32.GetWindowThreadProcessId.argtypes = [
            wintypes.HWND, ctypes.POINTER(wintypes.DWORD),
        ]
        window = user32.GetForegroundWindow()
        if not window:
            return 0
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(window, ctypes.byref(pid))
        return int(pid.value)
    except Exception:
        return 0


# --------------------------------------------------------------------- state
def is_throttled(pid):
    try:
        pid = int(pid)
    except Exception:
        return False
    record = _THROTTLED.get(pid)
    if not record:
        return False
    try:
        process = psutil.Process(pid)
        return abs(process.create_time() - record["created"]) < 0.01
    except Exception:
        _THROTTLED.pop(pid, None)
        return False


def throttled_count():
    return sum(1 for pid in list(_THROTTLED) if is_throttled(pid))


def _record(pid, priority=0, eco=False, suspended=False):
    try:
        created = psutil.Process(int(pid)).create_time()
    except Exception:
        created = 0.0
    _THROTTLED[int(pid)] = {
        "created": created, "priority": priority, "eco": eco, "suspended": suspended,
    }
    if suspended:
        _write_suspend_file()


def _write_suspend_file():
    """Persist which processes are frozen, so a crash can be undone next run."""
    try:
        rows = []
        for pid, record in list(_THROTTLED.items()):
            if not record.get("suspended"):
                continue
            rows.append([int(pid), float(record.get("created") or 0.0)])
        if rows:
            with open(_SUSPEND_FILE, "w", encoding="utf-8") as handle:
                json.dump(rows, handle)
        else:
            _remove_suspend_file()
    except Exception:
        pass


def _remove_suspend_file():
    try:
        os.remove(_SUSPEND_FILE)
    except OSError:
        pass


# --------------------------------------------------------------------- suspend
_NTDLL = None


def _ntdll():
    global _NTDLL
    if _NTDLL is None:
        import ctypes
        from ctypes import wintypes

        ntdll = ctypes.WinDLL("ntdll")
        ntdll.NtSuspendProcess.argtypes = [wintypes.HANDLE]
        ntdll.NtSuspendProcess.restype = ctypes.c_long
        ntdll.NtResumeProcess.argtypes = [wintypes.HANDLE]
        ntdll.NtResumeProcess.restype = ctypes.c_long
        _NTDLL = ntdll
    return _NTDLL


def _suspend(pid):
    try:
        kernel32 = _k32()
        handle = _open(pid, suspend=True)
        if not handle:
            return False
        try:
            return _ntdll().NtSuspendProcess(handle) == 0
        finally:
            kernel32.CloseHandle(handle)
    except Exception:
        return False


def _resume(pid):
    try:
        kernel32 = _k32()
        handle = _open(pid, suspend=True)
        if not handle:
            return False
        try:
            return _ntdll().NtResumeProcess(handle) == 0
        finally:
            kernel32.CloseHandle(handle)
    except Exception:
        return False


def _trim_suspended(pid):
    before = _rss(pid)
    if before is None:
        return 0
    if not _empty_working_set(pid):
        return 0
    after = _rss(pid)
    return int(round(max(0, before - after))) if after is not None else 0


def suspend_foreground():
    """Wake the app the user just switched to: never leave a frozen window."""
    foreground = _foreground_pid()
    if not foreground:
        return False
    record = _THROTTLED.get(foreground)
    if not record or not record.get("suspended"):
        return False
    return release(foreground)


def suspended_count():
    return sum(
        1 for pid in list(_THROTTLED)
        if _THROTTLED[pid].get("suspended") and is_throttled(pid)
    )


def throttle(pid, trim=True):
    """Slow a process down and give its RAM back. Returns (ok, freed_mb)."""
    if not IS_WINDOWS:
        return False, 0
    try:
        pid = int(pid)
    except Exception:
        return False, 0
    before = _rss(pid)
    if before is None:
        return False, 0

    original = _priority_class(pid)
    lowered = _set_priority(pid, _BACKGROUND_PRIORITY) if original else False
    efficiency = set_efficiency(pid, True)
    if not (lowered or efficiency):
        return False, 0

    freed = 0
    if trim and _empty_working_set(pid):
        after = _rss(pid)
        if after is not None:
            freed = max(0, before - after)

    try:
        created = psutil.Process(pid).create_time()
    except Exception:
        created = 0.0
    _record(pid, priority=original, eco=efficiency)
    return True, int(round(freed))


def release(pid):
    record = _THROTTLED.pop(int(pid), None)
    if record is None:
        return False
    if record.get("suspended"):
        _resume(pid)
    if record.get("priority"):
        _set_priority(pid, record["priority"])
    if record.get("eco"):
        set_efficiency(pid, False)
    if record.get("suspended"):
        _write_suspend_file()
    return True


def release_all():
    """Give every throttled app its normal priority back."""
    released = 0
    for pid in list(_THROTTLED):
        try:
            if release(pid):
                released += 1
        except Exception:
            continue
    _write_suspend_file()
    return released


def resume_leftovers():
    """Resume apps a previous VYRON session left frozen (crash or hard kill)."""
    try:
        with open(_SUSPEND_FILE, encoding="utf-8") as handle:
            rows = json.load(handle)
    except Exception:
        rows = []
    resumed = 0
    for item in rows or []:
        try:
            pid, created = int(item[0]), float(item[1])
        except Exception:
            continue
        if not created:
            continue
        try:
            process = psutil.Process(pid)
            if abs(process.create_time() - created) > 0.01:
                continue
            if _resume(pid):
                resumed += 1
        except Exception:
            continue
    _remove_suspend_file()
    return resumed


# --------------------------------------------------------------------- listing
def _windows_dir():
    global _WINDOWS_DIR
    if _WINDOWS_DIR is None:
        _WINDOWS_DIR = (os.environ.get("WINDIR") or r"C:\Windows").lower()
    return _WINDOWS_DIR


def _session_user():
    try:
        return psutil.Process().username()
    except Exception:
        return ""


def _pretty(exe):
    return _PRETTY.get(exe) or exe[:1].upper() + exe[1:].replace(".exe", "")


def _expand_exclusions(exclude_pids):
    """Exclude the game, VYRON and the whole process tree of the game."""
    excluded = set()
    for pid in exclude_pids:
        if not pid:
            continue
        try:
            pid = int(pid)
        except Exception:
            continue
        excluded.add(pid)
        try:
            for child in psutil.Process(pid).children(recursive=True):
                excluded.add(child.pid)
        except Exception:
            continue
    return excluded


def list_apps(exclude_pids=(), min_ram=90, limit=16):
    """Group every user app like Task Manager, summed by executable name."""
    if not IS_WINDOWS:
        return []
    own = os.getpid()
    user = _session_user()
    excluded = _expand_exclusions(exclude_pids)
    windows_dir = _windows_dir()

    candidates = []
    for process in psutil.process_iter(["pid", "name", "exe"]):
        try:
            info = process.info
            pid = int(info.get("pid") or 0)
            if not pid or pid in (0, 4, own) or pid in excluded:
                continue
            path = (info.get("exe") or "").strip()
            exe = os.path.basename(path).lower() or (info.get("name") or "").lower()
            stem = exe[:-4] if exe.endswith(".exe") else exe
            if not path or exe in _NEVER or stem.startswith(_KEEP_PREFIXES):
                continue
            if path.lower().startswith(windows_dir):
                continue
            if user:
                try:
                    if process.username().lower() != user.lower():
                        continue
                except Exception:
                    continue
            candidates.append((process, pid, exe))
        except Exception:
            continue

    # Two CPU samples 200 ms apart give real numbers instead of 0.0.
    try:
        for process, _pid, _exe in candidates:
            process.cpu_percent(None)
        time.sleep(0.2)
    except Exception:
        pass

    groups = {}
    for process, pid, exe in candidates:
        try:
            memory = process.memory_info().rss / (1024 ** 2)
            cpu = process.cpu_percent(None) or 0.0
        except Exception:
            continue
        group = groups.get(exe)
        if group is None:
            group = groups[exe] = {
                "key": exe, "name": _pretty(exe), "pids": [],
                "ram": 0.0, "cpu": 0.0,
            }
        group["pids"].append(pid)
        group["ram"] += memory
        group["cpu"] += cpu

    rows = [row for row in groups.values() if row["ram"] >= min_ram]
    rows.sort(key=lambda row: (row["ram"], row["cpu"]), reverse=True)
    for row in rows:
        row["ram"] = int(round(row["ram"]))
        row["cpu"] = int(round(row["cpu"]))
        row["count"] = len(row["pids"])
        row["throttled"] = bool(row["pids"]) and all(is_throttled(pid) for pid in row["pids"])
    return rows[:limit]


# --------------------------------------------------------------------- action
def optimize(apps=None, exclude_pids=(), trim_ram=True, skip_foreground=False, suspend=False):
    """Slow or suspend background apps. Returns a summary for the interface.

    ``apps`` may be a list of rows from list_apps() to target a single app.
    ``suspend`` freezes the processes completely (strongest CPU saving).
    """
    rows = list(apps) if apps is not None else list_apps(exclude_pids=exclude_pids)
    foreground = _foreground_pid() if skip_foreground else 0
    summary = {
        "apps": 0, "processes": 0, "freed": 0, "already": 0,
        "suspended": 0, "names": [],
    }

    for row in rows:
        touched = 0
        freed = 0
        frozen = 0
        for pid in row.get("pids") or []:
            if pid == foreground:
                continue
            if is_throttled(pid):
                summary["already"] += 1
                continue
            if suspend and _suspend(pid):
                touched += 1
                frozen += 1
                freed += _trim_suspended(pid) if trim_ram else 0
                _record(pid, suspended=True)
                continue
            ok, gained = throttle(pid, trim=trim_ram)
            if ok:
                touched += 1
                freed += gained
        if touched:
            summary["apps"] += 1
            summary["processes"] += touched
            summary["suspended"] += frozen
            summary["freed"] += freed
            summary["names"].append(row.get("name") or row.get("key") or "app")
    return summary


def close_apps(pids):
    """Close a whole app (children first), used by the explicit CLOSE button."""
    if not pids:
        return 0
    targets = []
    for pid in pids:
        try:
            targets.append(psutil.Process(int(pid)))
        except Exception:
            continue
    ordered = []
    for process in targets:
        try:
            ordered.extend(reversed(process.children(recursive=True)))
        except Exception:
            pass
        ordered.append(process)

    closed = 0
    for process in ordered:
        try:
            process.terminate()
            closed += 1
        except Exception:
            continue
    deadline = time.time() + 2.5
    for process in ordered:
        try:
            process.wait(max(0.0, deadline - time.time()))
        except Exception:
            try:
                process.kill()
            except Exception:
                pass
    return closed


# Safety net: even on an unexpected shutdown, apps get their priority back.
import atexit as _atexit

_atexit.register(release_all)
