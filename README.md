<div align="center">

<img src="vyron/assets/vyron-wordmark-xl.png" alt="VYRON" width="340">

**A lightweight Windows gaming companion that actually frees resources.**

[![Platform](https://img.shields.io/badge/platform-Windows%2010%20%7C%2011-0C1712?style=flat-square&logo=windows11&logoColor=B6FF38)](#install)
[![Python](https://img.shields.io/badge/python-3.10%2B-0C1712?style=flat-square&logo=python&logoColor=B6FF38)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-0C1712?style=flat-square)](LICENSE)
[![Telemetry](https://img.shields.io/badge/telemetry-none-0C1712?style=flat-square&logo=shieldsdotio&logoColor=B6FF38)](#privacy)

**English** · [Français](README.fr.md)

</div>

![VYRON overview](docs/screenshots/01-overview.png)

VYRON detects the game you launch, gives it the CPU and RAM back, applies real
Windows performance settings — and undoes every single one when you stop
playing. No account on a server, no telemetry, no admin rights, no console
window.

**Made by Maxkingwish** · [Attribution rules](ATTRIBUTION.md)

## Why VYRON

Most "game boosters" just close a few processes and call it a day. VYRON does
the boring, measurable work:

- finds the game on its own (Steam, Epic, GOG, Xbox, Ubisoft, EA, Riot, standalone);
- puts browsers, launchers and sync clients in Windows **Efficiency mode**, trims
  their working set, and optionally **freezes** them while you play;
- raises the game to Above Normal priority, gives it every core and high I/O;
- disables fullscreen optimisations and selects the high-performance GPU for
  that game;
- asks Windows for a **1 ms timer** to steady frame pacing;
- restores priorities, RAM, registry values, power plan and timer when the game
  exits — and even after a crash.

## Features

### Game detection
Discord-style automatic detection by executable name or install folder, shown in
the sidebar, on the Overview and in the Game Center. A manual "pick a running
app" picker is still available, and false positives can be muted with
**Not a game** (restorable from Settings).

### FPS boost (reversible)
- **Game profile** — fullscreen optimisations off, high-performance GPU,
  DXGI swap-effect upgrade. Per game, `HKCU` only, saved with its original value.
- **Background apps** — grouped like Task Manager (`Microsoft Edge · 14 processes
  · 810 MB`) with **Optimise** (Efficiency mode + Below Normal priority +
  working-set trim) and **Close** (confirmation first).
- **Suspend heavy apps while playing** — freezes them completely; the app you
  switch to wakes up in under a second. Everything resumes when the game exits.
  A suspended app is recorded on disk, so even a hard kill is undone at the next
  launch.
- **1 ms system timer** — requested while playing, released afterwards.
- **Game process tuning** — Above Normal priority, all cores, high I/O priority,
  and never in Efficiency mode.

### Monitoring
Live CPU, RAM and storage rings; NVIDIA GPU usage and temperature through
`nvidia-smi` (cached and only queried while the Performance page is visible).

### Servers
Tests cloud reference regions concurrently over TCP/443 and ranks them fastest
first, with packet loss and unreachable states. **It measures round-trip time to
reference endpoints, not to your game's server, and VYRON does not create a VPN
tunnel.** Picking a region only saves your preference.

### Accounts & library
Local accounts only: PBKDF2-HMAC-SHA256 + random salt, no network. Per-account
game library with one-click launch. Guest mode works for everything except the
boost engine.

### Six languages
English, French, Russian, Italian, Spanish, Portuguese — switchable at any time.

## The boost, honestly

| Setting | Scope | Restored by |
| --- | --- | --- |
| Game Mode on, DVR off, capture off | `HKCU` | **Restore**, game exit, app close |
| High performance power plan | only while playing, never on battery | game exit, app close |
| Game priority / affinity / I/O | game process | game exit |
| Fullscreen + GPU profile | one game, `HKCU` | **Restore** or turning the option off |
| 1 ms timer | process-wide | game exit, app close |
| Throttled apps | user processes | game exit, **Restore apps**, app close, `atexit` |
| Suspended apps | user processes | same + next start after a crash |

VYRON never disables security services, never uses `REALTIME` priority, never
kills a process automatically, and never writes outside `HKCU` or the user's home
directory. Gains depend on your hardware, drivers, temperatures and what was
running in the background; nothing can promise a fixed FPS number.

## Screenshots

| Boost engine | FPS & background apps |
| --- | --- |
| ![Boost](docs/screenshots/02-boost.png) | ![FPS boost](docs/screenshots/03-boost-fps.png) |

| Region latency | |
| --- | --- |
| ![Servers](docs/screenshots/04-servers.png) | |

## Install

### Option A — prebuilt executable
Download `VYRON.exe` from the Releases page and run it. No Python needed.

> The executable is unsigned, so Windows SmartScreen may warn the first time.
> Click **More info → Run anyway**, or build it yourself from source.

### Option B — one-click scripts (from source)
1. Install [Python 3.10+](https://www.python.org/downloads/) and tick
   **Add Python to PATH**.
2. Double-click **`VYRON.vbs`** — silent launch, no console. It installs the two
   dependencies on first run if needed.
3. `INSTALL_VYRON.bat` shows the installer output if something fails;
   `RUN_VYRON.bat` is a shortcut to the silent launcher.

### Option C — manual
```powershell
git clone https://github.com/maxkyngwish/VYRON.git
cd VYRON
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python main.py
```

### Build the executable
```powershell
BUILD_VYRON_EXE.bat
```
or
```powershell
python -m pip install pyinstaller
pyinstaller --noconfirm --clean --onefile --windowed --name VYRON ^
  --icon "vyron\assets\vyron.ico" ^
  --add-data "vyron\assets;vyron\assets" --collect-all customtkinter main.py
```
Output: `dist\VYRON.exe` (window and taskbar icon included, no console).

## What VYRON writes on your PC

| Path | Content |
| --- | --- |
| `%USERPROFILE%\.vyron_settings.json` | language, remembered session, boost preferences |
| `%USERPROFILE%\.vyron_accounts.json` | local accounts (PBKDF2 hashes) and game libraries |
| `%USERPROFILE%\.vyron_suspended.json` | apps frozen by VYRON, for crash recovery |
| `%USERPROFILE%\.vyron_crash.log` | startup errors only |
| `HKCU\Software\Microsoft\GameBar` | Game Mode, restored on **Restore** |
| `HKCU\System\GameConfigStore` + `...\GameDVR` | DVR/capture, restored on **Restore** |
| `HKCU\...\AppCompatFlags\Layers` | fullscreen optimisation flag, per game |
| `HKCU\Software\Microsoft\DirectX\UserGpuPreferences` | GPU preference and swap-effect, per game |

Nothing is sent anywhere. Delete the four files above to reset VYRON completely.

## Privacy

- No telemetry, no analytics, no remote account, no auto-update pings.
- The only network traffic is: region latency tests you start, the optional ping
  test, and your own game traffic.
- Accounts and settings never leave the machine.

## Project structure

```
main.py                 entry point and crash dialog
vyron/
  app.py                UI, pages, polling, wiring
  boost.py              registry, power plan, timer, game profile
  trim.py               background apps: groups, throttle, suspend, restore
  detection.py          game detection and exclusions
  system_info.py        cheap snapshot, cached GPU telemetry, ping
  servers.py            region list and concurrent latency tests
  accounts.py           local accounts and libraries
  i18n*.py              six-language strings
  processes.py          window/process enumeration
  assets/               logo, wordmark and icon
tools/
  make_assets.py        regenerates branding images
  check_attribution.py  protects the "Made by Maxkingwish" credit
docs/screenshots/       README images
```

Runtime dependencies: **CustomTkinter** and **psutil** only. Everything else is
the Python standard library, and VYRON runs itself at Below Normal priority so it
never competes with the game.

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| Nothing happens on double-click | Run `INSTALL_VYRON.bat` to see the error, or `python main.py` in a terminal. |
| "Python 3.10 or more is required" | Reinstall Python and tick **Add Python to PATH**. |
| Some settings show *Partial* / need admin | VYRON is designed for standard users; the remaining settings require an elevated shell and are skipped safely. |
| The game is not detected | Use **Game Center → pick a running app**, or add the game manually. |
| A background app feels slow | Open Boost → **Restore apps**, or untick *Suspend heavy background apps*. |
| Startup error | See `%USERPROFILE%\.vyron_crash.log`. |

## FAQ

**Does it really increase FPS?**
It removes real obstacles: background CPU/RAM contention, fullscreen
composition, timer granularity and GPU selection. The gain depends on your PC and
what was running. VYRON is honest about it and never claims a fixed number.

**Does it need administrator rights?**
No. Everything is per-user (`HKCU`, process priorities). The few settings that
would require admin are skipped with a clear message.

**Will it close my apps?**
Never automatically. **Close** always asks first. The optimiser only slows or
freezes apps, and restores them.

**Can I undo everything?**
Yes: **Restore** on the Boost page, closing the game, or closing VYRON. Even a
crash is recovered at the next start.

**Is my data uploaded?**
No. Accounts are local, hashed with PBKDF2-HMAC-SHA256.

## Contributing

Issues and pull requests are welcome. Please read [AGENTS.md](AGENTS.md) (project
rules) and run:

```powershell
py -m compileall -q vyron tools main.py
py tools/check_attribution.py
```

The **Made by Maxkingwish** credit must stay visible and unchanged everywhere —
see [ATTRIBUTION.md](ATTRIBUTION.md). This applies to forks and AI-generated
changes too.

## Credits & attribution

Created and maintained by **Maxkingwish**.

The credit line `Made by Maxkingwish` is protected: it may not be removed,
translated, shortened, hidden or covered. Details and enforcement:
[ATTRIBUTION.md](ATTRIBUTION.md) · `tools/check_attribution.py`.

<img src="docs/screenshots/05-about.png" alt="The About page shows the protected credit" width="760">

Built with [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) and
[psutil](https://github.com/giampaolo/psutil).

## License

[MIT](LICENSE) © 2026 Maxkingwish.
