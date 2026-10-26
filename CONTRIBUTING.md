# Contributing to VYRON

Thanks for helping. VYRON is deliberately small: two runtime dependencies and
the Windows standard library.

## Before you start

1. Read [AGENTS.md](AGENTS.md) for the project rules.
2. Read [ATTRIBUTION.md](ATTRIBUTION.md). The **Made by Maxkingwish** credit is
   protected and must remain visible and unchanged.

## Development setup

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python main.py
```

## Checks before a pull request

```powershell
py -m compileall -q vyron tools main.py
py tools/check_attribution.py
py tools/check_languages.py
```

All three must pass. A GUI smoke test is expected for UI changes: the app must
open all pages with zero callback exceptions, including the guest Boost page.

## What makes a good change

- **Reversible by default.** Any Windows tweak captures its previous value and
  restores it on game exit, app close, or `atexit`.
- **No new dependencies.** Stick to `customtkinter`, `psutil` and the standard
  library.
- **No hidden costs.** Do not add polling or GPU queries that run while a game
  is active outside the Performance page.
- **Six languages.** Add keys to `en`, `fr`, `ru`, `it`, `es` and `pt` with the
  same key names.
- **Small, focused commits** with a clear message.

## Reporting bugs

Include:

- Windows version and Python version;
- what you launched and what you expected;
- whether the game was detected;
- relevant lines from `%USERPROFILE%\.vyron_crash.log`;
- a screenshot if it is a UI issue.

Do not paste passwords or full account files.
