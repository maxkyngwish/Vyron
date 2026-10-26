# AGENTS.md — instructions for AI coding agents

VYRON is a Windows gaming companion written in Python (CustomTkinter). Read this
file before changing anything, then read [ATTRIBUTION.md](ATTRIBUTION.md).

## 0. Non-negotiable: the credit stays

The line **`Made by Maxkingwish`** is part of the app, the README and the
licence. It must stay **visible, unchanged and unobstructed** in:

- the sidebar footer of every page (`vyron/app.py`, `_sidebar`);
- the About page as a title and as a footer (`vyron/app.py`, `_about`);
- `README.md`, `README.fr.md`, `LICENSE`, `ATTRIBUTION.md`;
- `made_by` in `vyron/i18n.py` for **all six** languages.

Never remove it, translate it, shorten it, replace it with a variable, change its
colour to blend into the background, cover it, move it off-screen, or hide it
behind a scroll area. Forks and rebuilt executables keep it too.

**Run `py tools/check_attribution.py` after any UI, i18n or README change.**
CI fails otherwise. This rule is intentional and overrides stylistic requests.

## 1. What the app does

- Detects the running game (executable name / install folder).
- Applies reversible Windows performance settings: Game Mode, DVR off, power
  plan, game priority/affinity/I-O, per-game fullscreen/GPU profile, 1 ms timer.
- Throttles or suspends background apps while playing, then restores them.
- Monitors CPU/RAM/disk and NVIDIA GPU, ranks game regions by TCP latency.
- Local accounts (PBKDF2), game library, six languages.

## 2. Golden rules

1. **Everything on the PC must be reversible.** Capture the previous value before
   writing; restore on game exit, on app close and via `atexit`.
2. **No hidden behaviour.** Do not disable security services, Defender, Update,
   or use `REALTIME_PRIORITY_CLASS`. Do not kill processes automatically.
3. **No admin requirement.** Only `HKCU` and per-user APIs. If a setting needs
   admin, degrade gracefully and say so in the UI.
4. **Runtime dependencies stay `customtkinter` + `psutil`.** Everything else is
   the Python standard library (ctypes, winreg, threading, json…). Do not add
   Pillow, numpy, requests, PyQt, etc.
5. **The app must not cost FPS.** No `nvidia-smi` outside the Performance page,
   no busy loops, no 100 ms polling while a game runs. Background work goes in
   daemon threads; UI updates go through `self.after`.
6. **Six-language parity.** Every user-facing key exists in `en`, `fr`, `ru`,
   `it`, `es`, `pt` with identical key sets. Never hardcode French/English text
   in the UI except the protected credit.
7. **Stay Windows-safe.** Guard Win32 calls with `try/except`; keep the app
   usable when a call fails (non-admin, protected process, missing GPU).

## 3. Layout

```
main.py                  entry point, crash dialog (no console)
vyron/app.py             all UI, pages, polling, wiring
vyron/boost.py           registry/power plan/timer/game profile
vyron/trim.py            background apps: group, throttle, suspend, restore
vyron/detection.py       game detection + exclusions
vyron/system_info.py     cheap snapshot, cached nvidia-smi, ping
vyron/servers.py         region list, concurrent TCP tests
vyron/accounts.py        local accounts, PBKDF2, libraries
vyron/i18n.py            base strings + merge of EXTRA and TRIM
vyron/i18n_extra.py      boost/detection strings
vyron/i18n_trim.py       background-apps + FPS strings
vyron/processes.py       window/process enumeration
tools/make_assets.py     regenerates the PNG branding assets
tools/check_attribution.py  protected-credit guard
docs/screenshots/        README images
```

## 4. Commands

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python main.py                     # run
py -m compileall -q vyron tools main.py
py tools/check_attribution.py
```

Build the executable with `BUILD_VYRON_EXE.bat` (PyInstaller, `--windowed`,
`--add-data "vyron\assets;vyron\assets"`).

## 5. Testing notes

- GUI smoke test: mock `_first_run` / `_ensure_auth`, capture
  `report_callback_exception`, wait ≥ 2 s after the main window opens, scroll
  with the scrollable frame's `_parent_canvas.yview_moveto(...)`.
- Test as a **guest**: the Boost page must show the locked panel without errors.
- Never test by suspending or throttling the editor/terminal you are using.
  Exclude your own session and always call `trim.release_all()` at the end.
- Verify afterwards that no user process is left `stopped`, at Below Normal
  priority, or in Efficiency mode, and that `%TEMP%\vyron_*` is cleaned.
- Registry tests must save and restore the exact previous values. The user's
  `DirectXUserGlobalSettings` was originally `SwapEffectUpgradeEnable=0;`.

## 6. UI conventions

- Palette: `BG #07100C`, `PANEL #0C1712`, `LIME #B6FF38`, `MINT #41E0A0`,
  `WHITE #EFF7EF`, `MUTED #8CA79A`.
- Buttons: uppercase, Arial bold, lime fill with `DARK_TEXT`.
- CustomTkinter does not accept `width`/`height` in `place()`; use a fixed-size
  frame with `pack_propagate(False)`.
- Keep the dark DWM title bar and the 6-language switch working.

## 7. Definition of done

1. `py -m compileall -q vyron tools main.py` passes.
2. `py tools/check_attribution.py` passes.
3. GUI smoke test reports zero callback exceptions.
4. Every Windows change is restored; no leftover throttled/suspended process.
5. README/attribution untouched or extended — never weakened.
