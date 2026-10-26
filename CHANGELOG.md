# Changelog

All notable changes to VYRON are documented here. Format based on
[Keep a Changelog](https://keepachangelog.com/), versioning follows
[Semantic Versioning](https://semver.org/).

## [1.0.0] - 2026-10-26

First public release.

### Added

- Automatic game detection (Steam, Epic, GOG, Xbox, Ubisoft, EA, Riot and
  standalone executables), with a manual picker and **Not a game** muting.
- **Boost engine** with reversible Windows settings: Game Mode, background
  recording off, High performance power plan, Above Normal priority, all cores
  and high I/O priority for the game.
- **FPS boost**: per-game fullscreen/GPU profile (fullscreen optimisations off,
  high-performance GPU, DXGI swap-effect upgrade) and a 1 ms system timer.
- **Background app optimiser** grouped like Task Manager, with per-app
  **Optimise** (Efficiency mode + Below Normal priority + working-set trim) and
  **Close**.
- **Suspend heavy background apps while playing**, with foreground auto-wake and
  crash recovery via `~/.vyron_suspended.json`.
- **Servers** page: games detected on the PC, concurrent TCP/443 region tests,
  latency ranking, packet loss and saved preference.
- Live CPU, RAM and storage rings, plus NVIDIA GPU usage and temperature.
- Local accounts (PBKDF2-HMAC-SHA256), per-account game library and guest mode.
- Six languages: English, French, Russian, Italian, Spanish, Portuguese.
- Silent one-click launchers (`VYRON.vbs`, `RUN_VYRON.bat`,
  `INSTALL_VYRON.bat`) and a PyInstaller build script.

### Performance

- VYRON runs at Below Normal priority and never queries `nvidia-smi` outside the
  Performance page.
- Game polling slows down while playing; dashboard polling pauses when the
  window is minimised or another page is open.
- GPU telemetry is cached; DPI polling is throttled.

### Protected

- The **Made by Maxkingwish** credit is part of the project identity and licence
  ([ATTRIBUTION.md](ATTRIBUTION.md)). It is checked by
  `tools/check_attribution.py` on every CI run.
