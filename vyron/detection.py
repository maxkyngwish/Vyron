"""Detect the game currently running, Discord-style, without configuration."""
import os
import re

from .processes import list_running_apps

# Executables we can name with certainty.
KNOWN = {
    "scpsl.exe": "SCP: Secret Laboratory",
    "cs2.exe": "Counter-Strike 2",
    "csgo.exe": "Counter-Strike: Global Offensive",
    "valorant.exe": "VALORANT",
    "valorant-win64-shipping.exe": "VALORANT",
    "r5apex.exe": "Apex Legends",
    "r5apex_dx12.exe": "Apex Legends",
    "fortniteclient-win64-shipping.exe": "Fortnite",
    "fortniteclient-win64-shipping_eac.exe": "Fortnite",
    "gta5.exe": "Grand Theft Auto V",
    "gta5_enhanced.exe": "Grand Theft Auto V",
    "eldenring.exe": "ELDEN RING",
    "league of legends.exe": "League of Legends",
    "leagueclientux.exe": "League of Legends",
    "rocketleague.exe": "Rocket League",
    "overwatch.exe": "Overwatch 2",
    "destiny2.exe": "Destiny 2",
    "rainbowsix.exe": "Rainbow Six Siege",
    "rainbowsix_dx11.exe": "Rainbow Six Siege",
    "rustclient.exe": "Rust",
    "dayz_x64.exe": "DayZ",
    "escapefromtarkov.exe": "Escape from Tarkov",
    "minecraft.windows.exe": "Minecraft",
    "dota2.exe": "Dota 2",
    "tf_win64.exe": "Team Fortress 2",
    "pubg.exe": "PUBG: BATTLEGROUNDS",
    "tslgame.exe": "PUBG: BATTLEGROUNDS",
    "deadbydaylight-win64-shipping.exe": "Dead by Daylight",
    "beamng.drive.exe": "BeamNG.drive",
    "forzahorizon5.exe": "Forza Horizon 5",
    "cyberpunk2077.exe": "Cyberpunk 2077",
    "witcher3.exe": "The Witcher 3",
    "hl2.exe": "Half-Life 2",
    "portal2.exe": "Portal 2",
    "l4d2.exe": "Left 4 Dead 2",
    "sekiro.exe": "Sekiro",
    "darksouls3.exe": "Dark Souls III",
    "armoredcore6.exe": "ARMORED CORE VI",
    "starfield.exe": "Starfield",
    "bg3.exe": "Baldur's Gate 3",
    "bg3_dx11.exe": "Baldur's Gate 3",
    "hades.exe": "Hades",
    "hades2.exe": "Hades II",
    "stardew valley.exe": "Stardew Valley",
    "terraria.exe": "Terraria",
    "among us.exe": "Among Us",
    "fall guys.exe": "Fall Guys",
    "fallguys_client.exe": "Fall Guys",
    "rocketleague_x64.exe": "Rocket League",
    "wow.exe": "World of Warcraft",
    "ffxiv_dx11.exe": "FINAL FANTASY XIV",
    "eso64.exe": "The Elder Scrolls Online",
    "gw2-64.exe": "Guild Wars 2",
    "warframe.x64.exe": "Warframe",
    "pathofexile.exe": "Path of Exile",
    "pathofexile_x64.exe": "Path of Exile",
    "arma3_x64.exe": "Arma 3",
    "squadgame.exe": "Squad",
    "hellletloose.exe": "Hell Let Loose",
    "huntgame.exe": "Hunt: Showdown",
    "deeprockgalactic.exe": "Deep Rock Galactic",
    "valheim.exe": "Valheim",
    "7daystodie.exe": "7 Days to Die",
    "oxygennotincluded.exe": "Oxygen Not Included",
    "farming simulator 22.exe": "Farming Simulator 22",
    "eurotrucks2.exe": "Euro Truck Simulator 2",
    "amtrucks.exe": "American Truck Simulator",
    "assettocorsa.exe": "Assetto Corsa",
    "ac2-win64-shipping.exe": "Assetto Corsa Competizione",
    "raceroom.exe": "RaceRoom",
    "f1_24.exe": "F1 24",
    "f1_23.exe": "F1 23",
    "nba2k24.exe": "NBA 2K24",
    "fc24.exe": "EA SPORTS FC 24",
    "fc25.exe": "EA SPORTS FC 25",
    "eafc24.exe": "EA SPORTS FC 24",
    "rk.exe": "Roblox",
    "robloxplayerbeta.exe": "Roblox",
    "javaw.exe": "Minecraft",
}

# Executables that are never games, even when they live in a game folder.
NEVER = {
    "steam.exe", "steamwebhelper.exe", "steamservice.exe", "epicgameslauncher.exe",
    "riotclientservices.exe", "riotclientux.exe", "battle.net.exe", "origin.exe",
    "eaapp.exe", "eadesktop.exe", "ubisoftconnect.exe", "upc.exe", "goggalaxy.exe",
    "discord.exe", "chrome.exe", "msedge.exe", "firefox.exe", "opera.exe",
    "brave.exe", "vivaldi.exe", "spotify.exe", "code.exe", "explorer.exe",
    "python.exe", "pythonw.exe", "cmd.exe", "powershell.exe", "windowsterminal.exe",
    "obs64.exe", "nvcontainer.exe", "radeonsoftware.exe", "armourycrate.exe",
    "wallpaper32.exe", "wallpaper64.exe", "taskmgr.exe", "regedit.exe",
}

# Markers used by game stores to lay out installed games.
_MARKERS = (
    "\\steamapps\\common\\",
    "\\epic games\\",
    "\\gog games\\",
    "\\xboxgames\\",
    "\\ubisoft game launcher\\games\\",
    "\\ea games\\",
    "\\riot games\\",
)


def _pretty(folder):
    name = re.sub(r"\s*\((?:x64|x86|64-bit|32-bit|dx11|dx12)\)\s*$", "", folder, flags=re.I)
    name = name.replace("_", " ").strip(" .-")
    return name if len(name) >= 2 else ""


def _from_path(path):
    """Guess a game name from a store install path (any game, not just known exes)."""
    path = path or ""
    lower = path.replace("/", "\\").lower()
    if "\\.minecraft\\" in lower and os.path.basename(lower) in ("javaw.exe", "java.exe"):
        return "Minecraft"
    for marker in _MARKERS:
        index = lower.find(marker)
        if index < 0:
            continue
        rest = path[index + len(marker):].replace("/", "\\").split("\\")[0]
        name = _pretty(rest)
        if name:
            return name
    return ""


def detect_game(apps=None, excluded=()):
    """Return the most likely running game as a dict, or None.

    Known executables win over names guessed from a store folder. Names in
    *excluded* are ignored so a capture tool or overlay can be muted.
    """
    ignored = {str(name).strip().lower() for name in excluded or ()}
    try:
        running = apps if apps is not None else list_running_apps()
    except Exception:
        running = []

    best = None
    for app in running:
        path = (app.get("path") or "").strip()
        exe = os.path.basename(path).lower()
        if not path or exe in NEVER:
            continue
        name = KNOWN.get(exe)
        source = "known"
        score = 3
        if not name:
            name = _from_path(path)
            if not name:
                continue
            source = "folder"
            score = 2
        if not name or name.strip().lower() in ignored:
            continue
        candidate = {
            "name": name,
            "path": path,
            "pid": app.get("pid"),
            "title": app.get("title") or name,
            "source": source,
            "score": score,
        }
        if best is None or candidate["score"] > best["score"]:
            best = candidate
    if best is not None:
        best.pop("score", None)
    return best


# ------------------------------------------------------------------ catalog
# Games installed on this PC, so the Servers page can list real entries even
# when nothing is running. Results are cached because store folders are large.
_SCAN_CACHE = {"at": 0.0, "games": []}
_SCAN_TTL = 180.0
_SKIP_NAMES = {
    "steamworks common redistributables", "steamworks shared", "steamvr", "proton",
    "wallpaper engine", "easy anti-cheat", "easyanticheat", "battleye",
    "steam linux runtime", "riot client", "steam", "epic games launcher",
    "battle.net", "ea app", "ea desktop", "ubisoft connect", "gog galaxy",
    "rockstar games launcher", "social club", "xbox app", "minecraft launcher",
}
_FOLDER_ALIASES = {
    "garrysmod": "Garry's Mod",
    "scp secret laboratory": "SCP: Secret Laboratory",
    "schedule i": "Schedule I",
}


def _clean_name(name):
    cleaned = _pretty(re.sub(r"[®™©]", "", name or "").strip())
    if not cleaned:
        return ""
    return _FOLDER_ALIASES.get(cleaned.lower(), cleaned)


def _is_skippable(name):
    lower = (name or "").strip().lower()
    if not lower or lower in _SKIP_NAMES:
        return True
    return any(token in lower for token in (
        "redistributable", "dedicated server", "soundtrack", "artbook",
        "launcher", "shared", "steamworks",
    ))


def _steam_roots():
    roots = []
    if os.name == "nt":
        try:
            import winreg

            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam") as key:
                path, _kind = winreg.QueryValueEx(key, "SteamPath")
            if path:
                roots.append(path)
        except Exception:
            pass
    for env, tail in (
        ("ProgramFiles(x86)", r"Steam"),
        ("ProgramFiles", r"Steam"),
        ("ProgramFiles(x86)", r"SteamLibrary"),
        ("ProgramFiles", r"SteamLibrary"),
    ):
        base = os.environ.get(env)
        if base:
            roots.append(os.path.join(base, tail))
    return [root for root in roots if root and os.path.isdir(root)]


def _steam_libraries():
    libraries = []
    for root in _steam_roots():
        libraries.append(root)
        manifest = os.path.join(root, "steamapps", "libraryfolders.vdf")
        try:
            with open(manifest, "r", encoding="utf-8", errors="replace") as handle:
                text = handle.read()
        except OSError:
            continue
        for match in re.finditer(r'"path"\s+"([^"]+)"', text):
            path = match.group(1).replace("\\\\", "\\")
            if path and os.path.isdir(path):
                libraries.append(path)
    unique = []
    seen = set()
    for path in libraries:
        key = os.path.normcase(os.path.abspath(path))
        if key in seen:
            continue
        seen.add(key)
        unique.append(path)
    return unique


def _scan_steam():
    found = []
    for library in _steam_libraries():
        common = os.path.join(library, "steamapps", "common")
        try:
            entries = list(os.scandir(common))
        except OSError:
            continue
        for entry in entries:
            try:
                if not entry.is_dir():
                    continue
            except OSError:
                continue
            name = _clean_name(entry.name)
            if name and not _is_skippable(name):
                found.append({"name": name, "path": entry.path, "source": "steam"})
    return found


def _scan_epic():
    found = []
    base = os.path.join(os.environ.get("ProgramData", r"C:\ProgramData"),
                        "Epic", "EpicGamesLauncher", "Data", "Manifests")
    try:
        entries = list(os.scandir(base))
    except OSError:
        return found
    for entry in entries:
        if not entry.name.lower().endswith(".item"):
            continue
        try:
            import json

            with open(entry.path, "r", encoding="utf-8", errors="replace") as handle:
                data = json.load(handle)
        except Exception:
            continue
        name = _clean_name(data.get("DisplayName") or data.get("AppName") or "")
        location = data.get("InstallLocation") or ""
        if name and not _is_skippable(name):
            found.append({"name": name, "path": location, "source": "epic"})
    return found


_GAME_DIRS = (
    (os.environ.get("ProgramFiles", r"C:\Program Files"), r"XboxGames"),
    ("C:\\", r"XboxGames"),
    ("C:\\", r"GOG Games"),
    (os.path.join(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
                  r"GOG Galaxy"), r"Games"),
    (os.path.join(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
                  r"Ubisoft", r"Ubisoft Game Launcher"), r"games"),
    (os.environ.get("ProgramFiles", r"C:\Program Files"), r"EA Games"),
    (os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"), r"EA Games"),
    ("C:\\", r"Riot Games"),
)


def _scan_dirs():
    found = []
    for base, tail in _GAME_DIRS:
        root = os.path.join(base, tail) if base else tail
        try:
            entries = list(os.scandir(root))
        except OSError:
            continue
        for entry in entries:
            try:
                if not entry.is_dir():
                    continue
            except OSError:
                continue
            name = _clean_name(entry.name)
            if name and not _is_skippable(name):
                found.append({"name": name, "path": entry.path, "source": "folder"})
    return found


def installed_games(use_cache=True, ttl=_SCAN_TTL):
    """Games installed through the main stores and folders on this PC."""
    import time

    now = time.time()
    if use_cache and _SCAN_CACHE["games"] and now - _SCAN_CACHE["at"] < ttl:
        return list(_SCAN_CACHE["games"])
    games = _scan_steam() + _scan_epic() + _scan_dirs()
    unique = []
    seen = set()
    for game in games:
        key = game["name"].strip().lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(game)
    unique.sort(key=lambda item: item["name"].lower())
    _SCAN_CACHE["at"] = now
    _SCAN_CACHE["games"] = unique
    return list(unique)


def detected_games(running=None, extra=(), excluded=(), limit=60, use_cache=True):
    """Everything VYRON considers a game: installed, running and saved ones."""
    ignored = {str(name).strip().lower() for name in excluded or ()}
    rows = []

    def add(game):
        name = (game.get("name") or "").strip()
        key = name.lower()
        if not name or key in ignored or _is_skippable(name):
            return
        if any((row.get("name") or "").strip().lower() == key for row in rows):
            return
        rows.append({
            "name": name,
            "path": game.get("path") or "",
            "source": game.get("source") or "installed",
            "running": bool(game.get("running")),
        })

    try:
        current = detect_game(apps=running, excluded=ignored)
    except Exception:
        current = None
    if current:
        add({**current, "source": "running", "running": True})
    for game in extra or ():
        add(game)
    for game in installed_games(use_cache=use_cache):
        add(game)
    return rows[:limit]
